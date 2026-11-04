/* Full is the safe default. The Python runner supplies a validated per-run plan. */
const fs = require('node:fs');
let plan;
if (process.env.BROWSER_CAPTURE_PLAN) {
  plan = JSON.parse(fs.readFileSync(process.env.BROWSER_CAPTURE_PLAN));
  if (plan.sourceSha !== process.env.SITE_SOURCE_SHA || !['full', 'selective'].includes(plan.mode)) {
    throw new Error('Capture plan source/mode mismatch');
  }
}
module.exports = {
  plan,
  artwork: id => !plan || plan.mode === 'full' || plan.captureIds.includes(id),
  review: (name, { affected = false } = {}) => {
    if (!plan || plan.mode === 'full' || affected || /failure/.test(name)) return true;
    if (name.startsWith('footer-')) return ['footer-production-1440.png', 'footer-mobile.png'].includes(name);
    if (name.startsWith('hero-')) return name === 'hero-desktop-1x-responsive.png';
    return true;
  },
};
