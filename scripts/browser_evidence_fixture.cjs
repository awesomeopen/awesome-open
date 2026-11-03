/* Install only on the requesting test page; ordinary preview responses stay intact. */
const { execFileSync } = require('node:child_process');
const path = require('node:path');
const fixtures = JSON.parse(execFileSync('python3', [path.join(__dirname, 'browser_evidence_fixture.py')],
  { encoding: 'utf8', maxBuffer: 8 * 1024 * 1024 }));
module.exports = async (page, url, state) => {
  const fixture = fixtures[state];
  const base = new URL(url);
  const route = async request => {
    const target = new URL(request.request().url());
    const key = target.pathname.slice(base.pathname.length);
    if (target.origin !== base.origin || !target.pathname.startsWith(base.pathname) ||
        !Object.hasOwn(fixture.responses, key)) return request.fallback();
    await request.fulfill({ status: 200,
      contentType: key.endsWith('.svg') ? 'image/svg+xml' : key.endsWith('.json') ? 'application/json' : 'text/html',
      body: fixture.responses[key] });
  };
  await page.route('**/*', route);
  return { data: fixture.data, dispose: () => page.unroute('**/*', route) };
};
