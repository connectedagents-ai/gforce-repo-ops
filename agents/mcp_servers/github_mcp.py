"""
GitHub MCP Server for G Force
--------------------------------
Exposes GitHub operations as MCP tools callable by:
- OpenClaw skills
- Hermes Agent
- Antigravity agents

Tools:
  - list_issues: List open issues in a repo
  - get_pr: Get PR details + diff summary
  - list_prs: List open pull requests
  - get_ci_status: Get GitHub Actions run status
  - create_issue: Create a new issue
  - trigger_workflow: Trigger a GitHub Actions workflow
  - search_code: Search code in a repo
"""

from __future__ import annotations

import os
from typing import Any

import structlog
from github import Auth, Github, GithubException
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

log = structlog.get_logger()


def _get_github_client() -> Github:
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        raise ValueError("GITHUB_TOKEN is not set. Set it via 1Password: op://Private/GForceOps/github_pat")
    return Github(auth=Auth.Token(token))


def _default_repo() -> str:
    org = os.environ.get("GITHUB_ORG", "connectedagents-ai")
    repo = os.environ.get("GITHUB_DEFAULT_REPO", "gforce-repo-ops")
    return f"{org}/{repo}"


# ── MCP Server ────────────────────────────────────────────────────────────────

server = Server("gforce-github-mcp")

TOOLS: list[Tool] = [
    Tool(
        name="list_issues",
        description="List open GitHub issues in a repository",
        inputSchema={
            "type": "object",
            "properties": {
                "repo": {"type": "string", "description": "owner/repo (default: env GITHUB_DEFAULT_REPO)"},
                "state": {"type": "string", "enum": ["open", "closed", "all"], "default": "open"},
                "label": {"type": "string", "description": "Filter by label"},
                "limit": {"type": "integer", "default": 10, "maximum": 50},
            },
        },
    ),
    Tool(
        name="get_pr",
        description="Get details, status, and diff summary for a pull request",
        inputSchema={
            "type": "object",
            "required": ["pr_number"],
            "properties": {
                "pr_number": {"type": "integer"},
                "repo": {"type": "string"},
            },
        },
    ),
    Tool(
        name="list_prs",
        description="List open pull requests",
        inputSchema={
            "type": "object",
            "properties": {
                "repo": {"type": "string"},
                "state": {"type": "string", "enum": ["open", "closed", "all"], "default": "open"},
                "limit": {"type": "integer", "default": 10},
            },
        },
    ),
    Tool(
        name="get_ci_status",
        description="Get GitHub Actions CI run status for a branch or commit",
        inputSchema={
            "type": "object",
            "properties": {
                "repo": {"type": "string"},
                "branch": {"type": "string", "default": "main"},
                "limit": {"type": "integer", "default": 5},
            },
        },
    ),
    Tool(
        name="create_issue",
        description="Create a new GitHub issue",
        inputSchema={
            "type": "object",
            "required": ["title", "body"],
            "properties": {
                "repo": {"type": "string"},
                "title": {"type": "string"},
                "body": {"type": "string"},
                "labels": {"type": "array", "items": {"type": "string"}},
            },
        },
    ),
    Tool(
        name="trigger_workflow",
        description="Trigger a GitHub Actions workflow run",
        inputSchema={
            "type": "object",
            "required": ["workflow_id"],
            "properties": {
                "repo": {"type": "string"},
                "workflow_id": {"type": "string", "description": "Workflow file name, e.g. 'lint.yml'"},
                "ref": {"type": "string", "default": "main"},
            },
        },
    ),
    Tool(
        name="search_code",
        description="Search code in a repository",
        inputSchema={
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {"type": "string"},
                "repo": {"type": "string"},
                "language": {"type": "string"},
            },
        },
    ),
]


@server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    try:
        gh = _get_github_client()
        repo_name = arguments.get("repo") or _default_repo()
        repo = gh.get_repo(repo_name)

        if name == "list_issues":
            state = arguments.get("state", "open")
            label = arguments.get("label")
            limit = arguments.get("limit", 10)
            issues = repo.get_issues(state=state, labels=[label] if label else [])
            result = []
            for i, issue in enumerate(issues):
                if i >= limit:
                    break
                result.append(
                    f"#{issue.number} [{issue.state}] {issue.title}\n"
                    f"  Labels: {', '.join(l.name for l in issue.labels)}\n"
                    f"  URL: {issue.html_url}"
                )
            return [TextContent(type="text", text="\n\n".join(result) or "No issues found.")]

        elif name == "get_pr":
            pr_num = arguments["pr_number"]
            pr = repo.get_pull(pr_num)
            files = list(pr.get_files())[:10]
            file_summary = "\n".join(f"  {f.filename} (+{f.additions}/-{f.deletions})" for f in files)
            text = (
                f"PR #{pr.number}: {pr.title}\n"
                f"State: {pr.state} | Mergeable: {pr.mergeable}\n"
                f"Author: {pr.user.login} | Branch: {pr.head.ref} → {pr.base.ref}\n"
                f"URL: {pr.html_url}\n\n"
                f"Files changed ({pr.changed_files}):\n{file_summary}\n\n"
                f"Body:\n{pr.body or '(no description)'}"
            )
            return [TextContent(type="text", text=text)]

        elif name == "list_prs":
            state = arguments.get("state", "open")
            limit = arguments.get("limit", 10)
            prs = repo.get_pulls(state=state, sort="updated")
            result = []
            for i, pr in enumerate(prs):
                if i >= limit:
                    break
                result.append(f"PR #{pr.number}: {pr.title} ({pr.user.login}) — {pr.html_url}")
            return [TextContent(type="text", text="\n".join(result) or "No PRs found.")]

        elif name == "get_ci_status":
            branch = arguments.get("branch", "main")
            limit = arguments.get("limit", 5)
            runs = repo.get_workflow_runs(branch=branch)
            result = []
            for i, run in enumerate(runs):
                if i >= limit:
                    break
                result.append(
                    f"{run.name}: {run.conclusion or run.status} "
                    f"(#{run.run_number}, {run.created_at.strftime('%Y-%m-%d %H:%M')}) "
                    f"— {run.html_url}"
                )
            return [TextContent(type="text", text="\n".join(result) or "No runs found.")]

        elif name == "create_issue":
            issue = repo.create_issue(
                title=arguments["title"],
                body=arguments["body"],
                labels=arguments.get("labels", []),
            )
            return [TextContent(type="text", text=f"Created issue #{issue.number}: {issue.html_url}")]

        elif name == "trigger_workflow":
            workflow = repo.get_workflow(arguments["workflow_id"])
            ref = arguments.get("ref", "main")
            workflow.create_dispatch(ref=ref)
            return [TextContent(type="text", text=f"Triggered workflow '{arguments['workflow_id']}' on {ref}")]

        elif name == "search_code":
            query = arguments["query"]
            lang = arguments.get("language", "")
            q = f"{query} repo:{repo_name}"
            if lang:
                q += f" language:{lang}"
            results = gh.search_code(q)
            lines = []
            for i, item in enumerate(results):
                if i >= 10:
                    break
                lines.append(f"{item.path} — {item.html_url}")
            return [TextContent(type="text", text="\n".join(lines) or "No results.")]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except GithubException as e:
        log.error("github_mcp_error", tool=name, error=str(e))
        return [TextContent(type="text", text=f"GitHub API error: {e.status} — {e.data}")]
    except Exception as e:
        log.error("github_mcp_error", tool=name, error=str(e))
        return [TextContent(type="text", text=f"Error: {e}")]


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
