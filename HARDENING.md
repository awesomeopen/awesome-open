# Repository hardening

How to protect a GitHub repository whose changes are proposed by AI agents and
merged by a human maintainer. Written to be reusable: replace `OWNER/REPO`, the
check names and the publisher details with your own. Applying any of this is a
repository-settings change and is done by the owner, not by an agent.

## Threat model

- **Stolen credentials.** Malware on a developer machine or in CI (for example
  through an install script in a package dependency) collects tokens and pushes
  to every repository they reach. This is how repository worms spread.
- **Compromised dependencies.** A third-party action or package is replaced by a
  malicious version under the same tag or version range.
- **Agent overreach.** An agent, or a prompt injected into its input, uses the
  permissions it holds rather than the workflow it was told to follow.
  "Only opens pull requests" is a product behavior, not a permission boundary.

The goal: nothing reaches the default branch without passing required checks
and, at the target level, the approval of a human who did not author it.

## Current baseline (check first)

```sh
gh api repos/OWNER/REPO/branches/main/protection   # 404 = unprotected
gh api repos/OWNER/REPO/rulesets
gh api repos/OWNER/REPO/actions/permissions
gh api repos/OWNER/REPO/actions/permissions/workflow
gh api repos/OWNER/REPO/collaborators -q '.[]|"\(.login) \(.role_name)"'
gh api orgs/OWNER/installations -q '.installations[]|"\(.app_slug) \(.permissions)"'
```

Record which identities can write and which workflows push to the default branch.

## Level 1: protect the default branch

Works today with a single maintainer whose agents author pull requests under the
maintainer's own account. It stops direct pushes, force pushes and unchecked
merges, including from a stolen copy of the maintainer's token used outside the
pull-request flow. It does not stop someone holding that token from opening and
merging a pull request; Level 2 addresses that.

Save as `ruleset-main.json`:

```json
{
  "name": "Protect default branch",
  "target": "branch",
  "enforcement": "active",
  "conditions": { "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] } },
  "bypass_actors": [
    { "actor_id": 15368, "actor_type": "Integration", "bypass_mode": "always" }
  ],
  "rules": [
    { "type": "deletion" },
    { "type": "non_fast_forward" },
    { "type": "pull_request", "parameters": {
        "required_approving_review_count": 0,
        "dismiss_stale_reviews_on_push": true,
        "require_code_owner_review": false,
        "require_last_push_approval": false,
        "required_review_thread_resolution": false
    } },
    { "type": "required_status_checks", "parameters": {
        "strict_required_status_checks_policy": false,
        "required_status_checks": [ { "context": "brand" }, { "context": "test" } ]
    } }
  ]
}
```

```sh
gh api -X POST repos/OWNER/REPO/rulesets --input ruleset-main.json
```

Notes:

- **No admin bypass.** Do not add the repository-admin role to `bypass_actors`.
  The maintainer's token is an admin token, and so is any stolen copy of it.
  Admins can still edit the ruleset in an emergency; that leaves an audit entry.
- **`15368` is the GitHub Actions app.** Include it only if a workflow pushes
  generated commits directly to the default branch. Remove it if nothing does.
  Caveat: with this bypass, *any* workflow run that requests `contents: write`
  can push to the default branch. That includes a workflow added on a feature
  branch by an identity that may edit workflow files. Level 2 removes the bypass.
- **Check names** must match the check-run names exactly as they appear on a
  pull request. A check that never reports blocks every merge.

## Level 2: separate agent identity and required approval

1. **Give agents their own identity.** Create a machine account (GitHub permits
   one per person) or use a fine-grained token, with **Write**, not Admin, access
   to this repository only. Agents push branches and open pull requests as that
   identity. Do not give agents the maintainer's login or a classic `repo` token.
2. **Require one approval.** In the ruleset, set
   `"required_approving_review_count": 1` and `"require_last_push_approval": true`.
   An author cannot approve its own pull request, so only the maintainer can
   admit agent changes. A later push by the agent invalidates the approval.
3. **Move publishing off the Actions bypass.** Either:
   - have the publisher open a pull request instead of pushing; or
   - push with a deploy key stored as a secret in an environment (for example
     `publish`) whose deployment-branch policy allows only the default branch,
     and replace the `Integration` bypass with
     `{ "actor_type": "DeployKey", "bypass_mode": "always" }`.
     Workflows on other branches cannot read that secret.
4. **Restrict workflow edits.** Prefer agent identities and apps that cannot edit
   `.github/workflows/`. Where an installed app requests `workflows: write`,
   limit it to selected repositories and review its installation periodically.

## Actions settings

```sh
# Workflow token is read-only unless a job asks for more; workflows cannot approve PRs.
gh api -X PUT repos/OWNER/REPO/actions/permissions/workflow \
  -f default_workflow_permissions=read -F can_approve_pull_request_reviews=false
# Only GitHub-owned and verified actions, and only when pinned to a full commit SHA.
gh api -X PUT repos/OWNER/REPO/actions/permissions \
  -F enabled=true -f allowed_actions=selected -F sha_pinning_required=true
gh api -X PUT repos/OWNER/REPO/actions/permissions/selected-actions \
  -F github_owned_allowed=true -F verified_allowed=true
```

- **Pin every action** to a full commit SHA with the release as a comment:
  `uses: actions/checkout@<40-hex-sha> # v4.4.0`. Tags can be moved; commits cannot.
  Resolve a tag with
  `gh api repos/OWNER/ACTION/git/ref/tags/TAG` (dereference annotated tags).
- **Keep pins current** with Dependabot version updates for `github-actions`.
  Its pull requests go through the same review.
- **Per-job permissions.** Declare `permissions:` at workflow level as read-only
  and grant `contents: write`, `pages: write` or `id-token: write` only to the
  job that needs it.
- **Avoid `pull_request_target`** and `workflow_run` with checkout of untrusted
  code unless you have reviewed exactly what runs with secrets.
- **Restrict the Pages environment** (`github-pages`) to deploy only from the
  default branch.

## Account and machine

- Two-factor authentication with a passkey or security key on every account with
  write access.
- Enable secret scanning, push protection and Dependabot alerts.
- Install dependencies without lifecycle scripts where the project allows it
  (`npm ci --ignore-scripts`), especially in automated agent sessions.
- Run agents with the narrowest token that does their job; do not leave a broad
  personal token in the environment of an agent sandbox.
- Review the account security log and the repository audit log after any
  suspicious activity; revoke tokens first, investigate second.

## Reviewing pull requests

A review is the control only if it covers what can run. Look hardest at:

- `.github/workflows/`, and any script a privileged workflow executes;
- dependency manifests and lockfiles (`package.json`, `package-lock.json`, …);
- binary or generated files, and large reformatting diffs that can hide a
  one-line change;
- claims in the pull-request text. Agent statements such as “tests pass” are not
  evidence; required checks are.

## Automating merges

Automatic merging is safe only for a narrow, mechanically verified class of
change. A pull request can make its own checks pass, and an AI reviewer can be
steered by text inside the change. If you automate:

- allow it only for an explicit path allowlist (for example `data/*.json`) and
  add a required check that fails when any file outside that list changes;
- never auto-merge changes to workflows, scripts, dependencies or this file;
- keep the default branch's deployment in mind: an automatic merge is an
  automatic publication.

## Verify

```sh
gh api repos/OWNER/REPO/rulesets
gh api repos/OWNER/REPO/rules/branches/main -q '.[].type'   # rules in force on main
gh api repos/OWNER/REPO/actions/permissions
```

Do not test protection by pushing to the default branch: if a rule is missing,
the push succeeds. Open a test pull request from the agent identity and confirm it cannot be
merged before the required checks pass and, at Level 2, before you approve it.
