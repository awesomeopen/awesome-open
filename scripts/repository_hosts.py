"""Presentation names for recognized repository URLs, independent of collectors."""

import re
from urllib.parse import urlsplit

# Exact host names and repository-shaped paths. Project websites hosted on
# github.io or sourceforge.net subdomains retain the plain Explore label.
REPOSITORY_HOSTS = {
    "github.com": ("GitHub", r"/[^/]+/[^/]+/?"),
    "www.github.com": ("GitHub", r"/[^/]+/[^/]+/?"),
    "gitlab.com": ("GitLab", r"/(?:[^/]+/)+[^/]+/?"),
    "codeberg.org": ("Codeberg", r"/[^/]+/[^/]+/?"),
    "bitbucket.org": ("Bitbucket", r"/[^/]+/[^/]+/?"),
    "sourceforge.net": ("SourceForge", r"/projects/[^/]+/?"),
    "www.sourceforge.net": ("SourceForge", r"/projects/[^/]+/?"),
}

# Reviewed self-hosted repositories. Keep this explicit: a domain containing
# "gitlab" alone does not establish its platform or the destination's role.
REVIEWED_REPOSITORIES = {
    ("gitlab.opengeosys.org", "/ogs/ogs"): "GitLab",
}


def repository_host(url):
    """Return a display name for a recognized repository, otherwise None."""
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https"):
        return None
    reviewed = REVIEWED_REPOSITORIES.get((parsed.hostname, parsed.path.rstrip("/")))
    if reviewed:
        return reviewed
    provider = REPOSITORY_HOSTS.get(parsed.hostname)
    if provider and re.fullmatch(provider[1], parsed.path):
        return provider[0]
    return None
