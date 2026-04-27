from __future__ import annotations

import html
import json


def render_issues_page(
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
    <title>Issues</title>
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

      .topbar, .topbar-left, .topbar-right, .repo-tabs, .toolbar, .toolbar-left, .toolbar-right, .issue-meta, .issue-row {{
        display: flex;
        align-items: center;
      }}

      .topbar {{
        justify-content: space-between;
        gap: 16px;
        padding: 10px 16px;
        border-bottom: 1px solid var(--line);
      }}

      .topbar-left, .topbar-right {{ gap: 12px; }}

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

      .icon-row {{ display: flex; gap: 8px; }}

      .icon-row span {{
        width: 28px;
        height: 28px;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--bg-soft);
      }}

      .page {{
        max-width: 1040px;
        margin: 0 auto;
        padding: 20px 24px 36px;
      }}

      .toolbar {{
        justify-content: space-between;
        gap: 16px;
        margin-bottom: 14px;
      }}

      .toolbar-left, .toolbar-right {{
        gap: 10px;
        flex-wrap: wrap;
      }}

      .filter-input {{
        width: 720px;
        max-width: 100%;
        padding: 9px 12px;
        border: 1px solid var(--line);
        border-radius: 6px;
        font: inherit;
      }}

      .ghost, .primary {{
        padding: 8px 12px;
        border-radius: 6px;
        border: 1px solid var(--line);
        background: #fff;
        color: var(--text);
        text-decoration: none;
        font-size: 14px;
        font-weight: 600;
      }}

      .primary {{
        background: var(--green);
        color: #fff;
        border-color: var(--green);
      }}

      .issues-panel {{
        border: 1px solid var(--line);
        border-radius: 8px;
        overflow: hidden;
      }}

      .panel-head {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 16px;
        padding: 12px 16px;
        background: var(--bg-soft);
        border-bottom: 1px solid var(--line);
        color: var(--muted);
        font-size: 14px;
      }}

      .issue-tabs {{
        display: flex;
        gap: 18px;
        font-weight: 600;
      }}

      .issue-tab.active {{ color: var(--text); }}

      .issue-row {{
        justify-content: space-between;
        gap: 16px;
        padding: 14px 16px;
        border-bottom: 1px solid #ebeff3;
        text-decoration: none;
        color: inherit;
      }}

      .issue-row:last-child {{ border-bottom: 0; }}

      .issue-main {{
        display: grid;
        grid-template-columns: 18px minmax(0, 1fr);
        gap: 10px;
        align-items: start;
      }}

      .status-dot {{
        width: 16px;
        height: 16px;
        border-radius: 50%;
        margin-top: 3px;
        border: 2px solid var(--green);
        position: relative;
      }}

      .status-dot::after {{
        content: "";
        position: absolute;
        inset: 3px;
        border-radius: 50%;
        background: var(--green);
      }}

      .issue-title-row {{
        display: flex;
        gap: 8px;
        align-items: center;
        flex-wrap: wrap;
        margin-bottom: 4px;
      }}

      .issue-title {{
        font-size: 18px;
        font-weight: 600;
      }}

      .issue-meta {{
        gap: 6px;
        flex-wrap: wrap;
        color: var(--muted);
        font-size: 13px;
      }}

      .comment-count {{
        color: var(--muted);
        font-size: 13px;
        white-space: nowrap;
      }}

      .label {{
        display: inline-flex;
        align-items: center;
        padding: 2px 8px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 700;
        color: #fff;
      }}

      .label-high {{ background: #cf222e; }}
      .label-medium {{ background: #fb8f44; color: #24292f; }}
      .label-low {{ background: #0969da; }}
      .label-security {{ background: #6f42c1; }}
      .label-correctness {{ background: #1a7f37; }}
      .label-maintainability {{ background: #57606a; }}
      .label-default {{ background: #57606a; }}

      .empty {{
        padding: 36px 16px;
        text-align: center;
        color: var(--muted);
        font-size: 14px;
      }}

      @media (max-width: 900px) {{
        .topbar, .toolbar, .issue-row {{
          align-items: flex-start;
          flex-direction: column;
        }}

        .search, .filter-input {{
          width: 100%;
          min-width: 0;
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
      <a class="active" href="./issues.html">Issues <span id="issues-tab-count"></span></a>
      <a href="./pr_review.html">Pull requests 8</a>
      <a href="#">Discussions</a>
      <a href="#">Actions</a>
      <a href="#">Projects</a>
      <a href="#">Security and quality</a>
      <a href="#">Insights</a>
    </nav>
    <main class="page">
      <div class="toolbar">
        <div class="toolbar-left">
          <input class="filter-input" value="is:issue state:open" />
        </div>
        <div class="toolbar-right">
          <a class="ghost" href="#">Labels</a>
          <a class="ghost" href="#">Milestones</a>
          <a class="primary" href="./issue_create.html">New issue</a>
        </div>
      </div>
      <section class="issues-panel">
        <div class="panel-head">
          <div class="issue-tabs">
            <span class="issue-tab active">Open <span id="open-count"></span></span>
            <span class="issue-tab">Closed 0</span>
          </div>
          <div>Author &nbsp;&nbsp; Labels &nbsp;&nbsp; Projects &nbsp;&nbsp; Milestones &nbsp;&nbsp; Assignees &nbsp;&nbsp; Newest</div>
        </div>
        <div id="issue-list"></div>
      </section>
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

      function labelClass(label) {{
        const normalized = String(label).toLowerCase().replace(/[^a-z0-9]+/g, "-");
        return normalized ? `label-${{normalized}}` : "label-default";
      }}

      function renderIssues() {{
        const issues = readIssues();
        document.getElementById("issues-tab-count").textContent = issues.length;
        document.getElementById("open-count").textContent = issues.length;

        if (!issues.length) {{
          document.getElementById("issue-list").innerHTML =
            '<div class="empty">No issues yet. Create one from the PR review page.</div>';
          return;
        }}

        const html = issues.map((issue) => {{
          const labels = (issue.labels || []).map((label) =>
            `<span class="label ${{labelClass(label)}}">${{escapeHtml(label)}}</span>`
          ).join("");
          const comments = issue.comments ? `💬 ${{issue.comments}}` : "";
          return `
            <a class="issue-row" href="./issue_detail.html?id=${{issue.id}}">
              <div class="issue-main">
                <span class="status-dot"></span>
                <div>
                  <div class="issue-title-row">
                    <span class="issue-title">${{escapeHtml(issue.title)}}</span>
                    ${{labels}}
                  </div>
                  <div class="issue-meta">
                    <span>#${{issue.id}}</span>
                    <span>·</span>
                    <span>${{escapeHtml(issue.author || "codex-bot")}} opened on ${{escapeHtml(issue.opened_at || "")}}</span>
                  </div>
                </div>
              </div>
              <div class="comment-count">${{comments}}</div>
            </a>
          `;
        }}).join("");

        document.getElementById("issue-list").innerHTML = html;
      }}

      renderIssues();
    </script>
  </body>
</html>
"""
