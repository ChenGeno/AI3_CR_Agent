from __future__ import annotations

import html
from collections import defaultdict

from ai3_cr_agent.domain.models import ContextBundle, Finding


def render_pr_review_page(
    *,
    findings: list[Finding],
    contexts: list[ContextBundle],
    review_summary: str = "",
    repo_owner: str = "mimo-x",
    repo_name: str = "Code-Review-GPT-Gitlab",
    pr_number: int = 57,
    pr_title: str = "feat: 优化开发容器配置和开发环境",
    source_branch: str = "feat/devcontainer-alignment",
    target_branch: str = "main",
) -> str:
    context_by_change_id = {context.change_id: context for context in contexts}
    grouped_findings: dict[str, list[Finding]] = defaultdict(list)
    file_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"findings": 0})
    for finding in findings:
        grouped_findings[finding.file_path].append(finding)
        file_stats[finding.file_path]["findings"] += 1

    ordered_files = sorted(grouped_findings)
    total_comments = len(findings)

    review_cards = []
    for file_path in ordered_files:
        for index, finding in enumerate(grouped_findings[file_path]):
            context = context_by_change_id.get(finding.change_id)
            snippet = _pick_snippet(context)
            severity_label = finding.severity.title()
            category_label = finding.category.replace("_", " ").title()
            query = f"./issue_create.html?finding={html.escape(finding.finding_id)}"
            issue_button = f'<a class="issue-button" href="{query}">Create issue <span>shift ↵</span></a>'
            featured = " review-card-featured" if index == 0 and file_path == ordered_files[0] else ""
            review_cards.append(
                f"""
                <article class="review-card{featured}">
                  <div class="review-card-head">
                    <div class="review-card-tags">
                      <span class="pill pill-{html.escape(finding.severity)}">{html.escape(severity_label)}</span>
                      <span class="badge badge-category">{html.escape(category_label)}</span>
                    </div>
                    {issue_button}
                  </div>
                  <h3 class="review-title">{html.escape(finding.title)}</h3>
                  <p class="review-line"><strong>Issue description:</strong> {html.escape(finding.issue)}</p>
                  <p class="review-line"><strong>Evidence:</strong> {html.escape(finding.evidence)}</p>
                  <div class="snippet-box">
                    <div class="snippet-head">
                      <span>{html.escape(file_path)}</span>
                      <span>Line {finding.line if finding.line is not None else "n/a"}</span>
                    </div>
                    <pre>{html.escape(snippet)}</pre>
                  </div>
                  <p class="review-line"><strong>Suggestion:</strong> {html.escape(finding.suggestion)}</p>
                  <div class="review-meta-row">
                    <span class="badge">{html.escape(severity_label)}</span>
                    <span class="muted">{html.escape(finding.title)}</span>
                  </div>
                </article>
                """
            )

    files_panel = "".join(
        f"""
        <div class="sidebar-file-row">
          <span>{html.escape(file_path)}</span>
          <span>{file_stats[file_path]["findings"]} comments</span>
        </div>
        """
        for file_path in ordered_files
    )

    return f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>PR 内 Code Review 评论页</title>
    <style>
      :root {{
        --bg: #0a0a0a;
        --surface: #ffffff;
        --line: #d0d7de;
        --muted: #57606a;
        --text: #24292f;
        --green: #1f883d;
        --orange: #fb8f44;
        --red: #cf222e;
        --blue: #2f81f7;
      }}

      * {{
        box-sizing: border-box;
      }}

      html, body {{
        min-height: 100%;
      }}

      body {{
        margin: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
        background: #ffffff;
        color: var(--text);
      }}

      .canvas {{
        min-height: 100vh;
        padding: 0;
      }}

      .github-window {{
        width: 100%;
        min-height: 100vh;
        margin: 0;
        background: var(--surface);
        border: 0;
        box-shadow: none;
        overflow: hidden;
      }}

      .topbar {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 16px;
        padding: 10px 16px;
        border-bottom: 1px solid var(--line);
      }}

      .topbar-left, .topbar-right, .repo-tabs, .pr-meta, .pr-tabs, .review-card-head, .snippet-head {{
        display: flex;
        align-items: center;
      }}

      .topbar-left {{
        gap: 12px;
      }}

      .burger, .github-mark {{
        width: 28px;
        height: 28px;
        border-radius: 8px;
        border: 1px solid var(--line);
        background: #f6f8fa;
      }}

      .github-mark {{
        border-radius: 50%;
        background: #24292f;
      }}

      .repo-path {{
        color: var(--muted);
        font-size: 14px;
      }}

      .topbar-right {{
        gap: 10px;
      }}

      .search {{
        min-width: 220px;
        padding: 8px 12px;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: #f6f8fa;
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
        background: #f6f8fa;
      }}

      .icon-row .avatar {{
        border-radius: 50%;
        background: conic-gradient(from 180deg, #f4b7d7, #f6e29c, #c6d6ff, #f4b7d7);
      }}

      .repo-tabs {{
        gap: 22px;
        padding: 0 18px;
        border-bottom: 1px solid var(--line);
        color: var(--muted);
        font-size: 14px;
      }}

      .repo-tabs span, .repo-tabs a {{
        padding: 12px 0;
        color: inherit;
        text-decoration: none;
      }}

      .repo-tabs .active {{
        color: var(--text);
        border-bottom: 2px solid #fd8c73;
      }}

      .page {{
        padding: 18px 28px 28px;
      }}

      .pr-header {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 16px;
      }}

      h1 {{
        margin: 0;
        font-size: 27px;
        font-weight: 500;
        line-height: 1.25;
      }}

      h1 span {{
        color: #7d8590;
      }}

      .pr-meta {{
        gap: 10px;
        margin-top: 10px;
        color: var(--muted);
        font-size: 14px;
        flex-wrap: wrap;
      }}

      .state-pill {{
        padding: 4px 10px;
        border-radius: 999px;
        background: var(--green);
        color: #fff;
        font-size: 13px;
        font-weight: 700;
      }}

      .code-button {{
        padding: 7px 11px;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: #f6f8fa;
        font-weight: 600;
        color: var(--text);
      }}

      .pr-tabs {{
        gap: 14px;
        margin-top: 18px;
        padding-bottom: 12px;
        border-bottom: 1px solid var(--line);
        color: var(--muted);
        font-size: 14px;
      }}

      .pr-tabs span {{
        padding: 8px 12px;
        border-radius: 8px;
      }}

      .pr-tabs .active {{
        color: var(--text);
        border: 1px solid var(--line);
      }}

      .layout {{
        display: grid;
        grid-template-columns: minmax(0, 1fr) 304px;
        gap: 18px;
        margin-top: 12px;
      }}

      .comment-anchor {{
        display: flex;
        gap: 12px;
      }}

      .bot {{
        width: 44px;
        height: 44px;
        flex: 0 0 auto;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #fff;
        font-weight: 800;
        background: radial-gradient(circle at 33% 30%, #101214 42%, #7342df 43%, #f4c76d 74%);
      }}

      .comment-stream {{
        flex: 1;
      }}

      .comment-meta {{
        margin: 10px 0 12px;
        color: #7d8590;
        font-size: 13px;
      }}

      .review-card {{
        padding: 14px 16px;
        border-radius: 12px;
        background: #fbfcfd;
        border: 1px solid #ebeff3;
        margin-bottom: 18px;
      }}

      .review-card-featured {{
        border: 3px solid var(--blue);
        background: #ffffff;
      }}

      .review-card-head {{
        justify-content: space-between;
        gap: 12px;
      }}

      .review-card-tags {{
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
      }}

      .pill, .badge {{
        display: inline-flex;
        align-items: center;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 700;
      }}

      .pill-high {{
        background: rgba(207,34,46,0.12);
        color: var(--red);
      }}

      .pill-medium {{
        background: rgba(251,143,68,0.16);
        color: #bc4c00;
      }}

      .pill-low {{
        background: rgba(9,105,218,0.12);
        color: #0969da;
      }}

      .issue-button {{
        padding: 8px 12px;
        border-radius: 999px;
        background: var(--green);
        color: #fff;
        font-weight: 700;
        font-size: 13px;
      }}

      .issue-button span {{
        margin-left: 6px;
        padding: 1px 6px;
        border-radius: 999px;
        background: rgba(255,255,255,0.16);
        font-size: 11px;
      }}

      .review-line {{
        margin: 14px 0 0;
        font-size: 14px;
        line-height: 1.45;
      }}

      .review-title {{
        margin: 14px 0 0;
        font-size: 20px;
        line-height: 1.3;
      }}

      .snippet-box {{
        margin-top: 14px;
        border: 1px solid #d8dee4;
        border-radius: 10px;
        overflow: hidden;
        background: #fff;
      }}

      .snippet-head {{
        justify-content: space-between;
        gap: 12px;
        padding: 12px 14px;
        border-bottom: 1px solid #d8dee4;
        color: var(--muted);
        font-size: 13px;
      }}

      pre {{
        margin: 0;
        padding: 14px;
        background: #fff;
        color: var(--muted);
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
        font-size: 12px;
        line-height: 1.55;
        overflow: auto;
        white-space: pre-wrap;
      }}

      .review-meta-row {{
        display: flex;
        align-items: center;
        gap: 10px;
        margin-top: 14px;
      }}

      .badge {{
        background: #f6f8fa;
        color: var(--muted);
      }}

      .badge-category {{
        background: rgba(9, 105, 218, 0.08);
        color: #0969da;
      }}

      .muted {{
        color: var(--muted);
        font-size: 13px;
      }}

      .sidebar-section {{
        padding: 12px 0 18px;
        border-bottom: 1px solid #ebeff3;
      }}

      .sidebar-section h4 {{
        margin: 0 0 10px;
        font-size: 13px;
      }}

      .sidebar-section p {{
        margin: 0 0 8px;
        color: var(--muted);
        font-size: 13px;
        line-height: 1.45;
      }}

      .sidebar-file-row {{
        display: flex;
        justify-content: space-between;
        gap: 12px;
        padding: 8px 0;
        border-bottom: 1px solid #eef1f4;
        font-size: 13px;
        color: var(--muted);
      }}

      @media (max-width: 980px) {{
        .layout {{
          grid-template-columns: 1fr;
        }}

        .pr-header, .topbar {{
          flex-direction: column;
          align-items: flex-start;
        }}

        .search {{
          min-width: 0;
          width: 100%;
        }}

        .github-window {{
          width: 100%;
        }}

        .canvas {{
          padding: 0;
        }}
      }}
    </style>
  </head>
  <body>
    <main class="canvas">
      <section class="github-window">
        <div class="topbar">
          <div class="topbar-left">
            <span class="burger"></span>
            <span class="github-mark"></span>
            <span class="repo-path">{html.escape(repo_owner)} / <strong>{html.escape(repo_name)}</strong></span>
          </div>
          <div class="topbar-right">
            <div class="search">Type / to search</div>
            <div class="icon-row"><span></span><span></span><span></span><span></span><span class="avatar"></span></div>
          </div>
        </div>
        <div class="repo-tabs">
          <a href="#">Code</a>
          <a href="./issues.html">Issues</a>
          <a class="active" href="./pr_review.html">Pull requests 8</a>
          <a href="#">Discussions</a>
          <a href="#">Actions</a>
          <a href="#">Projects</a>
          <a href="#">Security</a>
          <a href="#">Insights</a>
        </div>
        <div class="page">
          <section class="pr-header">
            <div>
              <h1>{html.escape(pr_title)} <span>#{pr_number}</span></h1>
              <div class="pr-meta">
                <span class="state-pill">Open</span>
                <span>andaoai wants to merge 6 commits into <strong>{html.escape(target_branch)}</strong> from <strong>{html.escape(source_branch)}</strong></span>
              </div>
            </div>
            <button class="code-button">&lt;&gt; Code</button>
          </section>
          <section class="pr-tabs">
            <span class="active">Conversation 11</span>
            <span>Commits 6</span>
            <span>Checks 0</span>
            <span>Files changed {len(ordered_files)}</span>
          </section>
          <section class="layout">
            <div class="main">
              <div class="comment-anchor">
                <div class="bot">AI</div>
                <div class="comment-stream">
                  <div class="comment-meta">AI³ CR <span class="badge">bot</span> commented 1m ago</div>
                  {''.join(review_cards)}
                </div>
              </div>
            </div>
            <aside class="sidebar">
              <div class="sidebar-section">
                <h4>Reviewers</h4>
                <p>ai^codereviewai[bot]</p>
                <p>Still in progress? Learn about draft PRs</p>
              </div>
              <div class="sidebar-section">
                <h4>Assignees</h4>
                <p>No one assigned</p>
              </div>
              <div class="sidebar-section">
                <h4>Labels</h4>
                <p>None yet</p>
              </div>
              <div class="sidebar-section">
                <h4>Projects</h4>
                <p>None yet</p>
              </div>
              <div class="sidebar-section">
                <h4>Files</h4>
                {files_panel}
              </div>
              <div class="sidebar-section">
                <h4>Summary</h4>
                <p>{html.escape(review_summary or f"{total_comments} review comments generated by AI3 CR Agent.")}</p>
              </div>
            </aside>
          </section>
        </div>
      </section>
    </main>
  </body>
</html>
"""


def _pick_snippet(context: ContextBundle | None) -> str:
    if context is None:
        return ""
    if context.file_excerpt:
        return context.file_excerpt
    return context.symbol_source
