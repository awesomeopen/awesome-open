#!/usr/bin/env python3
"""Read public GitHub README evidence with bounded, logged HTTPS requests.

No credentials, cookies, proxy environment, candidate execution or alias decisions.
Other official hosts use the documented operator fallback.
"""
import argparse
import base64
from datetime import datetime, timezone
import http.client
import ipaddress
import json
import re
import socket
import ssl
from urllib.parse import quote, urljoin, urlsplit

HOSTS = {'github.com', 'api.github.com', 'raw.githubusercontent.com'}
REDIRECTS = {301, 302, 303, 307, 308}
STOP = {'authentication', 'denial', 'quota', 'unsafe_target'}
MAX_BYTES = 2 * 1024 * 1024


class SourceFailure(Exception):
    def __init__(self, category):
        super().__init__(category)
        self.category = category


def safe_url(url):
    try:
        p = urlsplit(url)
        if (p.scheme != 'https' or p.hostname not in HOSTS or p.port not in (None, 443)
                or p.username is not None or p.password is not None or p.fragment
                or any(ord(c) < 33 or ord(c) == 127 for c in url) or '\\' in url):
            raise ValueError()
    except ValueError:
        raise SourceFailure('unsafe_target') from None
    return p


def public_addresses(host):
    addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise SourceFailure('unsafe_target')
    return addresses


class PinnedHTTPS(http.client.HTTPSConnection):
    def connect(self):
        # Validate every returned address and connect to that literal IP. TLS
        # still verifies the requested hostname; a second DNS lookup is avoided.
        address = public_addresses(self.host)[0][4][0]
        sock = socket.create_connection((address, 443), timeout=self.timeout)
        try:
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except Exception:
            sock.close()
            raise


def transport(url):
    p = safe_url(url)
    connection = PinnedHTTPS(p.hostname, timeout=20, context=ssl.create_default_context())
    try:
        connection.request('GET', p.path + ('?' + p.query if p.query else ''),
                           headers={'User-Agent': 'awesome-open-alias-evidence',
                                    'Accept': 'application/vnd.github+json'})
        response = connection.getresponse()
        body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise SourceFailure('response_too_large')
        return response.status, dict(response.getheaders()), body
    finally:
        connection.close()


def category_for(status, headers):
    headers = {k.lower(): v for k, v in headers.items()}
    if status == 429 or (status == 403 and
                        (headers.get('x-ratelimit-remaining') == '0' or 'retry-after' in headers)):
        return 'quota'
    if status == 401:
        return 'authentication'
    if status in (403, 451):
        return 'denial'
    if status == 404:
        return 'not_found'
    return 'http_error'


class Reader:
    def __init__(self, fetch=transport, clock=None, max_redirects=5):
        self.fetch = fetch
        self.clock = clock or (lambda: datetime.now(timezone.utc).isoformat())
        self.max_redirects = max_redirects
        self.events = []

    def external_failure(self, url, category, status=None):
        """Record a previous connector result; permission/quota gates stop here."""
        if category not in {'connector', 'not_found', 'authentication', 'denial', 'quota'}:
            raise ValueError('Unknown prior failure category')
        safe_url(url)
        self.events.append({'url': url, 'method': 'connector', 'at': self.clock(),
                            'category': category, 'http_status': status})
        if category in STOP:
            raise SourceFailure(category)

    def get_json(self, url):
        visited = set()
        for hop in range(self.max_redirects + 1):
            safe_url(url)
            if url in visited:
                raise SourceFailure('redirect_loop')
            visited.add(url)
            event = {'url': url, 'method': 'GET', 'at': self.clock(),
                     'http_status': None, 'category': None}
            self.events.append(event)
            try:
                status, headers, body = self.fetch(url)
            except SourceFailure as error:
                event['category'] = error.category
                raise
            except (OSError, http.client.HTTPException):
                event['category'] = 'transport'
                raise SourceFailure('transport') from None
            event['http_status'] = status
            if status in REDIRECTS:
                event['category'] = 'redirect'
                location = {k.lower(): v for k, v in headers.items()}.get('location')
                if not location:
                    raise SourceFailure('invalid_redirect')
                url = urljoin(url, location)
                safe_url(url)
                continue
            if status != 200:
                event['category'] = category_for(status, headers)
                raise SourceFailure(event['category'])
            try:
                result = json.loads(body)
            except (ValueError, UnicodeError):
                event['category'] = 'unreadable'
                raise SourceFailure('unreadable') from None
            event['category'] = 'read'
            return result
        raise SourceFailure('redirect_limit')


def resolve(repository_url, reader=None, *, prior_error=None):
    reader = reader or Reader()
    result = {'canonical_url': repository_url, 'identity_verified': False,
              'events': reader.events, 'branch': None, 'path': None}
    try:
        p = safe_url(repository_url)
        if p.hostname != 'github.com' or not re.fullmatch(r'/[\w.-]+/[\w.-]+/?', p.path) or p.query:
            raise SourceFailure('unsupported_repository')
        if prior_error:
            reader.external_failure(repository_url, prior_error)
        metadata = reader.get_json('https://api.github.com/repos/' + p.path.strip('/'))
        name, branch = metadata['full_name'], metadata['default_branch']
        if not re.fullmatch(r'[\w.-]+/[\w.-]+', name) or not isinstance(branch, str) or not branch:
            raise SourceFailure('invalid_metadata')
        result['branch'] = branch
        readme = reader.get_json('https://api.github.com/repos/' + name + '/readme?ref=' + quote(branch, safe=''))
        path = readme['path']
        if not isinstance(path, str) or not path or readme['encoding'] != 'base64':
            raise SourceFailure('invalid_readme')
        text = base64.b64decode(''.join(readme['content'].split()), validate=True).decode('utf-8')
        source = readme['html_url']
        safe_url(source)
        result.update(resolved_repository=name, repository_id=metadata['id'], path=path,
                      source_url=source, text=text, status='read')
    except SourceFailure as error:
        result.update(status='blocked' if error.category in STOP else 'unresolved', error=error.category)
    except (KeyError, TypeError, ValueError, UnicodeError):
        result.update(status='unresolved', error='invalid_metadata')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repository_url')
    parser.add_argument('--prior-error', choices=['connector', 'not_found', 'authentication', 'denial', 'quota'])
    args = parser.parse_args(argv)
    result = resolve(args.repository_url, prior_error=args.prior_error)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result['status'] == 'read' else 2


if __name__ == '__main__':
    raise SystemExit(main())
