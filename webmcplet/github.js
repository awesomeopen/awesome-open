/* Optional build step: GitHub stars for a list's items. MIT License; see LICENSE.
 * Used by `build.cjs markdown --github-stars` and `build.cjs try --github-stars`. */
"use strict";

const REPOSITORY = /^https?:\/\/(?:www\.)?github\.com\/([\w.-]+)\/([\w.-]+?)(?:\.git)?\/?(?:[?#].*)?$/i;

// "owner/name" for a GitHub repository URL, or null for anything else.
function repositoryOf(url) {
  const match = REPOSITORY.exec(url);
  return match ? match[1] + "/" + match[2] : null;
}

const FIELD = { label: "GitHub stars", type: "number", meaning: "Stargazer count of the GitHub repository.", source: "GitHub REST API" };

// Records `github_stars` on items whose URL is a GitHub repository. Without a token,
// GitHub allows 60 requests an hour; with GITHUB_TOKEN, 5,000. When the limit is
// reached, the remaining items stay unrecorded and read Unknown.
async function addGithubStars(doc, options = {}) {
  const token = options.token === undefined ? process.env.GITHUB_TOKEN : options.token;
  const fetchImpl = options.fetch || fetch;
  const headers = { accept: "application/vnd.github+json", "user-agent": "WebMCPlet build step", "x-github-api-version": "2022-11-28" };
  if (token) headers.authorization = "Bearer " + token;
  const targets = doc.items.map(item => ({ item, repository: repositoryOf(item.url) })).filter(t => t.repository);
  const counts = { repositories: targets.length, recorded: 0, unavailable: 0, notChecked: 0 };
  const observedAt = new Date().toISOString();
  let next = 0, limited = false;

  async function worker() {
    while (!limited && next < targets.length) {
      const target = targets[next++];
      const response = await fetchImpl("https://api.github.com/repos/" + target.repository, { headers });
      if (response.status === 429 || (response.status === 403 && response.headers.get("x-ratelimit-remaining") === "0")) {
        limited = true;
        counts.notChecked++;
        continue;
      }
      const stars = response.ok ? (await response.json()).stargazers_count : undefined;
      if (Number.isInteger(stars) && stars >= 0) {
        target.item.fields = Object.assign({}, target.item.fields, { github_stars: stars });
        counts.recorded++;
      } else {
        counts.unavailable++;
      }
    }
  }
  await Promise.all(Array.from({ length: options.concurrency || 8 }, worker));
  counts.notChecked += targets.length - Math.min(next, targets.length);
  doc.fields = Object.assign({}, doc.fields, { github_stars: Object.assign({}, FIELD, { observed_at: observedAt }) });
  return counts;
}

function describe(counts) {
  return counts.recorded + " of " + counts.repositories + " GitHub repositories have stars; " + counts.unavailable +
    " unavailable" + (counts.notChecked ? ", " + counts.notChecked + " not checked after the rate limit (set GITHUB_TOKEN)" : "") + ".";
}

module.exports = { repositoryOf, addGithubStars, describe };
