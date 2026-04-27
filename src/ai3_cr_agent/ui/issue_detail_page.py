from __future__ import annotations

import html
import json


def render_issue_detail_page(
    *,
    repo_owner: str = "mimo-x",
    repo_name: str = "Code-Review-GPT-Gitlab",
) -> str:
    storage_key_js = json.dumps(f"ai3-cr-agent.issues.{repo_owner}.{repo_name}", ensure_ascii=False)
    return f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Issue</title>
    <style>
      :root {{
        --line: #d0d7de;
        --muted: #57606a;
        --text: #24292f;
        --bg-soft: #f6f8fa;
        --green: #1f883d;
      }}

      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
        color: var(--text);
        background: #fff;
      }}

      .topbar, .topbar-left, .topbar-right, .repo-tabs, .issue-meta, .detail-layout {{
        display: flex;
        align-items: center;
      }}

      .topbar {{
        justify-content: space-between;
        gap: 16px;
        padding: 10px 16px;
        border-bottom: 1px solid var(--line);
      }}

      .topbar-left, .topbar-right {{
        gap: 12px;
      }}

      .menu-button, .github-mark {{
        width: 28px;
        height: 28px;
        border: 1px solid var(--line);
        background: var(--bg-soft);
      }}

      .menu-button {{
        border-radius: 8px;
        position: relative;
      }}

      .menu-button::before {{
        content: "";
        position: absolute;
        left: 7px;
        right: 7px;
        top: 8px;
        height: 2px;
        background: #6e7781;
        box-shadow: 0 5px 0 #6e7781, 0 10px 0 #6e7781;
      }}

      .github-mark {{ border-radius: 50%; background: #24292f; border-color: #24292f; }}
      .repo-path {{ color: var(--muted); font-size: 14px; }}
      .search {{
        min-width: 220px;
        padding: 8px 12px;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--bg-soft);
        color: #7d8590;
        font-size: 13px;
      }}

      .icon-row {{
        display: flex;
        gap: 8px;
      }}

      .icon-row span {{
        width: 28px;
        height: 28px;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--bg-soft);
      }}

      .repo-tabs {{
        gap: 22px;
        padding: 0 18px;
        border-bottom: 1px solid var(--line);
        color: var(--muted);
        font-size: 14px;
      }}

      .repo-tabs a {{
        padding: 12px 0;
        color: inherit;
        text-decoration: none;
      }}

      .repo-tabs .active {{
        color: var(--text);
        border-bottom: 2px solid #fd8c73;
      }}

      .page {{
        max-width: 1120px;
        margin: 0 auto;
        padding: 20px 24px 36px;
      }}

      .detail-layout {{
        align-items: flex-start;
        gap: 24px;
      }}

      .main {{
        flex: 1;
        min-width: 0;
      }}

      .sidebar {{
        width: 280px;
      }}

      .issue-title {{
        margin: 0;
        font-size: 32px;
        line-height: 1.2;
        font-weight: 500;
      }}

      .issue-meta {{
        gap: 10px;
        margin-top: 12px;
        flex-wrap: wrap;
        color: var(--muted);
        font-size: 14px;
      }}

      .state-pill {{
        padding: 4px 10px;
        border-radius: 999px;
        background: var(--green);
        color: #fff;
        font-size: 13px;
        font-weight: 700;
      }}

      .issue-card {{
        margin-top: 18px;
        border: 1px solid var(--line);
        border-radius: 8px;
        overflow: hidden;
      }}

      .issue-card-head {{
        padding: 12px 16px;
        background: var(--bg-soft);
        border-bottom: 1px solid var(--line);
        color: var(--muted);
        font-size: 14px;
      }}

      .issue-body {{
        padding: 16px;
        white-space: pre-wrap;
        line-height: 1.6;
        font-size: 14px;
      }}

      .side-block {{
        padding: 14px 0;
        border-bottom: 1px solid #ebeff3;
      }}

      .side-block h4 {{
        margin: 0 0 8px;
        font-size: 13px;
      }}

      .side-block p, .side-block a {{
        margin: 0;
        color: var(--muted);
        font-size: 13px;
        line-height: 1.5;
        text-decoration: none;
      }}

      .empty {{
        margin-top: 18px;
        padding: 18px;
        border: 1px solid var(--line);
        border-radius: 8px;
        color: var(--muted);
      }}

      @media (max-width: 960px) {{
        .topbar, .detail-layout {{
          flex-direction: column;
          align-items: flex-start;
        }}

        .search {{
          min-width: 0;
          width: 100%;
        }}

        .sidebar {{
          width: 100%;
        }}
      }}
    </style>
  </head>
  <body>
    <div class="topbar">
      <div class="topbar-left">
        <span class="menu-button"></span>
        <span class="github-mark"></span>
        <span class="repo-path">{html.escape(repo_owner)} / <strong>{html.escape(repo_name)}</strong></span>
      </div>
      <div class="topbar-right">
        <div class="search">Type / to search</div>
        <div class="icon-row"><span></span><span></span><span></span><span></span><span></span></div>
      </div>
    </div>
    <nav class="repo-tabs">
      <a href="#">Code</a>
      <a class="active" href="./issues.html">Issues</a>
      <a href="./pr_review.html">Pull requests 8</a>
      <a href="#">Discussions</a>
      <a href="#">Actions</a>
      <a href="#">Projects</a>
      <a href="#">Security and quality</a>
      <a href="#">Insights</a>
    </nav>
    <main class="page">
      <div class="detail-layout">
        <section class="main">
          <h1 id="issue-title" class="issue-title">Issue not found</h1>
          <div id="issue-meta" class="issue-meta"></div>
          <div id="issue-empty" class="empty">Open the PR review page and create an issue from a generated finding.</div>
          <div id="issue-card" class="issue-card" hidden>
            <div id="issue-card-head" class="issue-card-head"></div>
            <div id="issue-body" class="issue-body"></div>
          </div>
        </section>
        <aside class="sidebar">
          <div class="side-block"><h4>Assignees</h4><p>No one assigned</p></div>
          <div class="side-block"><h4>Labels</h4><p id="issue-labels">None</p></div>
          <div class="side-block"><h4>Linked review</h4><p id="linked-review">No linked review item.</p></div>
          <div class="side-block"><h4>Navigation</h4><a href="./issues.html">Back to issues</a></div>
        </aside>
      </div>
    </main>
    <script>
      const STORAGE_KEY = {storage_key_js};

      function escapeHtml(value) {{
        return String(value)
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;")
          .replace(/'/g, "&#39;");
      }}

      function readIssues() {{
        try {{
          const raw = window.localStorage.getItem(STORAGE_KEY);
          if (!raw) return [];
          const parsed = JSON.parse(raw);
          return Array.isArray(parsed) ? parsed : [];
        }} catch (error) {{
          return [];
        }}
      }}

      const issueId = Number(new URLSearchParams(window.location.search).get("id"));
      const issue = readIssues().find((item) => Number(item.id) === issueId);

      if (issue) {{
        document.getElementById("issue-title").textContent = issue.title || "Untitled issue";
        document.getElementById("issue-meta").innerHTML =
          `<span class="state-pill">Open</span><span>#${{issue.id}}</span><span>·</span><span>${{escapeHtml(issue.author || "codex-bot")}} opened on ${{escapeHtml(issue.opened_at || "")}}</span>`;
        document.getElementById("issue-card-head").textContent =
          `${{issue.author || "codex-bot"}} commented on ${{issue.opened_at || ""}}`;
        document.getElementById("issue-body").textContent = issue.body || "";
        document.getElementById("issue-labels").textContent = (issue.labels || []).join(", ") || "None";
        document.getElementById("linked-review").textContent = issue.source_finding_id
          ? `${{issue.source_finding_id}} · ${{issue.source_file_path || ""}}${{issue.source_line ? `:${{issue.source_line}}` : ""}}`
          : "No linked review item.";
        document.getElementById("issue-empty").hidden = true;
        document.getElementById("issue-card").hidden = false;
      }}
    </script>
  </body>
</html>
"""
