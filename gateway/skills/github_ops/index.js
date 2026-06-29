/**
 * G Force GitHub Ops Skill for OpenClaw
 * ----------------------------------------
 * Bridges OpenClaw agent to the GitHub MCP server.
 * Called when a message triggers "github_ops" intent.
 */

const { execSync } = require("child_process");
const https = require("https");

const GITHUB_TOKEN = process.env.GITHUB_TOKEN;
const DEFAULT_REPO = `${process.env.GITHUB_ORG || "connectedagents-ai"}/${process.env.GITHUB_DEFAULT_REPO || "gforce-repo-ops"}`;

/**
 * Main entry point called by OpenClaw gateway.
 * @param {string} action - Detected action (list_issues, get_pr, etc.)
 * @param {object} params - Extracted parameters
 * @param {object} context - OpenClaw context (user, platform, memory)
 * @returns {string} Response text
 */
async function run(action, params, context) {
  const repo = params.repo || DEFAULT_REPO;

  switch (action) {
    case "list_issues":
      return await listIssues(repo, params);
    case "get_pr":
      return await getPR(repo, params.pr_number);
    case "list_prs":
      return await listPRs(repo, params);
    case "get_ci_status":
      return await getCIStatus(repo, params.branch || "main");
    case "create_issue":
      return await createIssue(repo, params.title, params.body, params.labels);
    case "monitor_ci":
      return await monitorCI(repo, context);
    default:
      return `Unknown GitHub action: ${action}. Try: list_issues, get_pr, list_prs, get_ci_status, create_issue`;
  }
}

async function ghRequest(path, method = "GET", body = null) {
  return new Promise((resolve, reject) => {
    const options = {
      hostname: "api.github.com",
      path,
      method,
      headers: {
        Authorization: `Bearer ${GITHUB_TOKEN}`,
        Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "GForce-RepoOps/1.0",
        ...(body ? { "Content-Type": "application/json" } : {}),
      },
    };

    const req = https.request(options, (res) => {
      let data = "";
      res.on("data", (chunk) => (data += chunk));
      res.on("end", () => {
        try {
          resolve({ status: res.statusCode, data: JSON.parse(data) });
        } catch {
          resolve({ status: res.statusCode, data });
        }
      });
    });

    req.on("error", reject);
    if (body) req.write(JSON.stringify(body));
    req.end();
  });
}

async function listIssues(repo, params) {
  const state = params.state || "open";
  const limit = params.limit || 10;
  const { data } = await ghRequest(`/repos/${repo}/issues?state=${state}&per_page=${limit}`);
  if (!Array.isArray(data)) return `Error: ${JSON.stringify(data)}`;

  const issues = data.filter((i) => !i.pull_request); // Exclude PRs
  if (!issues.length) return `No ${state} issues in ${repo}`;

  return issues
    .map((i) => `#${i.number} [${i.state}] ${i.title}\n  ${i.html_url}`)
    .join("\n\n");
}

async function getPR(repo, prNumber) {
  if (!prNumber) return "Please specify a PR number. Example: 'Review PR #42'";
  const { data: pr } = await ghRequest(`/repos/${repo}/pulls/${prNumber}`);
  if (pr.message) return `Error: ${pr.message}`;

  const { data: files } = await ghRequest(`/repos/${repo}/pulls/${prNumber}/files`);
  const fileList = Array.isArray(files)
    ? files
        .slice(0, 8)
        .map((f) => `  ${f.filename} (+${f.additions}/-${f.deletions})`)
        .join("\n")
    : "Unable to fetch files";

  return [
    `📋 PR #${pr.number}: ${pr.title}`,
    `State: ${pr.state} | Mergeable: ${pr.mergeable ?? "unknown"}`,
    `Author: ${pr.user?.login} | ${pr.head?.ref} → ${pr.base?.ref}`,
    `URL: ${pr.html_url}`,
    ``,
    `Files changed (${pr.changed_files || "?"}):`,
    fileList,
    ``,
    `Description: ${pr.body?.slice(0, 300) || "(none)"}`,
  ].join("\n");
}

async function listPRs(repo, params) {
  const state = params.state || "open";
  const limit = params.limit || 10;
  const { data } = await ghRequest(`/repos/${repo}/pulls?state=${state}&per_page=${limit}&sort=updated`);
  if (!Array.isArray(data)) return `Error: ${JSON.stringify(data)}`;
  if (!data.length) return `No ${state} PRs in ${repo}`;

  return data.map((pr) => `PR #${pr.number}: ${pr.title} (${pr.user?.login})\n  ${pr.html_url}`).join("\n\n");
}

async function getCIStatus(repo, branch) {
  const { data } = await ghRequest(`/repos/${repo}/actions/runs?branch=${branch}&per_page=5`);
  if (!data.workflow_runs) return `Error: ${JSON.stringify(data)}`;

  const runs = data.workflow_runs;
  if (!runs.length) return `No CI runs found for branch '${branch}' in ${repo}`;

  const statusEmoji = (s) => ({ success: "✅", failure: "❌", cancelled: "⚠️" }[s] || "🔄");

  return runs
    .map((r) => `${statusEmoji(r.conclusion)} ${r.name}: ${r.conclusion || r.status} (#${r.run_number})\n  ${r.html_url}`)
    .join("\n\n");
}

async function createIssue(repo, title, body, labels = []) {
  if (!title) return "Please provide an issue title.";
  const { data, status } = await ghRequest(`/repos/${repo}/issues`, "POST", {
    title,
    body: body || "",
    labels,
  });
  if (status !== 201) return `Error creating issue: ${JSON.stringify(data)}`;
  return `✅ Created issue #${data.number}: ${data.html_url}`;
}

async function monitorCI(repo, context) {
  // Called by cron job — alert if any recent failure
  const { data } = await ghRequest(`/repos/${repo}/actions/runs?per_page=10`);
  if (!data.workflow_runs) return null;

  const failures = data.workflow_runs.filter((r) => r.conclusion === "failure");
  if (!failures.length) return null; // No alert needed

  const failureList = failures
    .slice(0, 3)
    .map((r) => `❌ ${r.name} on ${r.head_branch}\n  ${r.html_url}`)
    .join("\n");

  return `⚠️ CI Failures in ${repo}:\n\n${failureList}`;
}

module.exports = { run };
