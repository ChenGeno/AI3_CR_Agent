from __future__ import annotations

import html
import json

from ai3_cr_agent.domain.models import ContextBundle, Finding


def render_issue_creation_page(
    *,
    findings: list[Finding],
    contexts: list[ContextBundle],
    repo_owner: str = "mimo-x",
    repo_name: str = "Code-Review-GPT-Gitlab",
    issue_title_prefix: str = "Code Review",
    pr_number: int = 57,
) -> str:
    drafts = _build_issue_drafts(
        findings=findings,
        contexts=contexts,
        issue_title_prefix=issue_title_prefix,
        pr_number=pr_number,
    )
    first_draft = drafts[0] if drafts else {
        "finding_id": "",
        "title": "Code Review follow-up",
        "body": "No finding was selected.",
        "severity": "medium",
        "category": "maintainability",
        "file_path": "",
        "line": None,
    }
    storage_key_js = json.dumps(f"ai3-cr-agent.issues.{repo_owner}.{repo_name}", ensure_ascii=False)
    drafts_js = json.dumps(drafts, ensure_ascii=False)
    first_draft_js = json.dumps(first_draft, ensure_ascii=False)

    return f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Create new issue</title>
    <style>
      :root {{
        --line: #d0d7de;
        --muted: #57606a;
        --text: #24292f;
        --green: #1f883d;
        --bg-soft: #f6f8fa;
      }}

      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
        color: var(--text);
        background: #fff;
      }}

      .topbar, .topbar-left, .topbar-right, .icon-row, .repo-tabs, .editor-tabs, .footer-actions, .action-group, .page-title-row {{
        display: flex;
        align-items: center;
      }}

      .topbar {{
        justify-content: space-between;
        gap: 16px;
        padding: 10px 12px;
        border-bottom: 1px solid var(--line);
      }}

      .topbar-left, .topbar-right {{ gap: 12px; }}

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

      .github-mark {{
        border-radius: 50%;
        background: #24292f;
        border-color: #24292f;
      }}

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
        padding: 22px 28px 28px;
      }}

      .layout {{
        display: grid;
        grid-template-columns: minmax(0, 1fr) 250px;
        gap: 22px;
      }}

      .page-title-row {{
        gap: 12px;
        margin-bottom: 10px;
      }}

      .issue-avatar {{
        width: 28px;
        height: 28px;
        border-radius: 50%;
        background: conic-gradient(from 180deg, #f4b7d7, #f6e29c, #c6d6ff, #f4b7d7);
      }}

      h1 {{
        margin: 0;
        font-size: 29px;
        font-weight: 600;
      }}

      .selection-meta {{
        margin: 0 0 16px 40px;
        color: var(--muted);
        font-size: 14px;
      }}

      .field-label {{
        display: block;
        margin: 12px 0 8px;
        font-size: 14px;
        color: var(--muted);
      }}

      .input {{
        width: 100%;
        padding: 10px 12px;
        border: 1px solid var(--line);
        border-radius: 6px;
        font: inherit;
      }}

      .editor {{
        border: 2px solid #2f81f7;
        border-radius: 8px;
        overflow: hidden;
      }}

      .editor-tabs {{
        justify-content: space-between;
        padding: 10px 12px;
        background: #fff;
        border-bottom: 1px solid var(--line);
        color: var(--muted);
        font-size: 13px;
      }}

      .editor-tabs .active {{
        color: var(--text);
        font-weight: 700;
      }}

      .editor-tools {{
        display: flex;
        gap: 10px;
      }}

      textarea {{
        width: 100%;
        min-height: 330px;
        border: 0;
        resize: vertical;
        padding: 14px 12px;
        font: inherit;
        line-height: 1.5;
        color: var(--text);
      }}

      .upload-hint {{
        margin-top: 8px;
        color: #7d8590;
        font-size: 12px;
      }}

      .footer-actions {{
        justify-content: space-between;
        gap: 12px;
        margin-top: 18px;
      }}

      .check-row {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        color: var(--muted);
        font-size: 13px;
      }}

      .action-group {{
        gap: 12px;
      }}

      .primary, .ghost {{
        padding: 9px 14px;
        border-radius: 6px;
        border: 1px solid transparent;
        font-weight: 700;
        font-size: 14px;
        text-decoration: none;
      }}

      .primary {{
        background: var(--green);
        color: #fff;
      }}

      .ghost {{
        background: var(--bg-soft);
        color: var(--text);
        border-color: var(--line);
      }}

      .side-block {{
        padding: 14px 0;
        border-bottom: 1px solid #ebeff3;
      }}

      .side-block h4 {{
        margin: 0 0 8px;
        font-size: 13px;
      }}

      .side-block p {{
        margin: 0;
        color: var(--muted);
        font-size: 13px;
        line-height: 1.45;
      }}

      @media (max-width: 1180px) {{
        .layout {{ grid-template-columns: 1fr; }}
      }}

      @media (max-width: 840px) {{
        .topbar, .footer-actions {{
          flex-direction: column;
          align-items: flex-start;
        }}

        .search {{
          min-width: 0;
          width: 100%;
        }}
      }}
    </style>
  </head>
  <body>
    <main>
      <div class="topbar">
        <div class="topbar-left">
          <span class="menu-button"></span>
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
        <div class="layout">
          <section>
            <div class="page-title-row">
              <span class="issue-avatar"></span>
              <h1>Create new issue</h1>
            </div>
            <p id="selection-meta" class="selection-meta"></p>
            <label class="field-label">Add a title *</label>
            <input id="issue-title" class="input" value="{html.escape(first_draft['title'])}" />
            <label class="field-label">Add a description</label>
            <div class="editor">
              <div class="editor-tabs">
                <div><span class="active">Write</span> <span>Preview</span></div>
                <div class="editor-tools"><span>H</span><span>B</span><span>I</span><span>•</span><span>@</span></div>
              </div>
              <textarea id="issue-body">{html.escape(first_draft['body'])}</textarea>
            </div>
            <div class="upload-hint">Paste, drop, or click to add files</div>
            <div class="footer-actions">
              <label class="check-row"><input id="create-more" type="checkbox" /> Create more</label>
              <div class="action-group">
                <a class="ghost" href="./pr_review.html">Cancel</a>
                <button id="create-issue-button" class="primary" type="button">Create</button>
              </div>
            </div>
          </section>
          <aside>
            <div class="side-block"><h4>Selected review</h4><p id="selected-review-copy"></p></div>
            <div class="side-block"><h4>Assignees</h4><p>No one assigned</p></div>
            <div class="side-block"><h4>Labels</h4><p>Derived from review severity and category</p></div>
            <div class="side-block"><h4>Projects</h4><p>No projects</p></div>
            <div class="side-block"><h4>Milestone</h4><p>No milestone</p></div>
          </aside>
        </div>
      </div>
    </main>
    <script>
      const STORAGE_KEY = {storage_key_js};
      const FINDING_DRAFTS = {drafts_js};
      const DEFAULT_DRAFT = {first_draft_js};
      let selectedDraft = DEFAULT_DRAFT;

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

      function nextIssueId(issues) {{
        const maxId = issues.reduce((current, issue) => {{
          const id = Number(issue && issue.id);
          return Number.isFinite(id) ? Math.max(current, id) : current;
        }}, 0);
        return maxId + 1;
      }}

      function pickDraft() {{
        const findingId = new URLSearchParams(window.location.search).get("finding");
        if (!findingId) return DEFAULT_DRAFT;
        return FINDING_DRAFTS.find((item) => item.finding_id === findingId) || DEFAULT_DRAFT;
      }}

      function applyDraft(draft) {{
        selectedDraft = draft;
        document.getElementById("issue-title").value = draft.title || "";
        document.getElementById("issue-body").value = draft.body || "";
        const location = draft.file_path ? `${{draft.file_path}}${{draft.line ? `:${{draft.line}}` : ""}}` : "No file selected";
        document.getElementById("selection-meta").textContent = draft.finding_id
          ? `From review item ${{draft.finding_id}} · ${{location}}`
          : "No review item selected.";
        document.getElementById("selected-review-copy").textContent = draft.summary || "No review content available.";
      }}

      applyDraft(pickDraft());

      document.getElementById("create-issue-button").addEventListener("click", () => {{
        const title = document.getElementById("issue-title").value.trim();
        const body = document.getElementById("issue-body").value.trim();
        if (!title) {{
          window.alert("Issue title is required.");
          return;
        }}

        const issues = readIssues();
        const createdAt = new Date().toLocaleDateString("en-US", {{
          month: "short",
          day: "numeric",
          year: "numeric"
        }});
        const newIssue = {{
          id: nextIssueId(issues),
          title,
          body,
          labels: [selectedDraft.severity || "medium", selectedDraft.category || "maintainability"],
          author: "codex-bot",
          opened_at: createdAt,
          comments: 0,
          source_finding_id: selectedDraft.finding_id || "",
          source_file_path: selectedDraft.file_path || "",
          source_line: selectedDraft.line ?? null,
          source_summary: selectedDraft.summary || ""
        }};
        issues.unshift(newIssue);
        window.localStorage.setItem(STORAGE_KEY, JSON.stringify(issues));

        if (document.getElementById("create-more").checked) {{
          document.getElementById("create-more").checked = false;
          return;
        }}

        window.location.href = `./issue_detail.html?id=${{newIssue.id}}`;
      }});
    </script>
  </body>
</html>
"""


def _build_issue_drafts(
    *,
    findings: list[Finding],
    contexts: list[ContextBundle],
    issue_title_prefix: str,
    pr_number: int,
) -> list[dict[str, object]]:
    context_by_change_id = {context.change_id: context for context in contexts}
    drafts: list[dict[str, object]] = []
    for finding in findings:
        context = context_by_change_id.get(finding.change_id)
        drafts.append(
            {
                "finding_id": finding.finding_id,
                "title": f"{issue_title_prefix}: {finding.title}",
                "body": _build_issue_body(finding, context, pr_number=pr_number),
                "summary": finding.issue,
                "severity": finding.severity,
                "category": finding.category,
                "file_path": finding.file_path,
                "line": finding.line,
            }
        )
    return drafts


def _build_issue_body(
    finding: Finding | None,
    context: ContextBundle | None,
    *,
    pr_number: int,
) -> str:
    if finding is None:
        return "No finding was selected."

    severity = finding.severity.title()
    category = finding.category.replace("_", " ").title()
    location = f"{finding.file_path} (line {finding.line if finding.line is not None else 'n/a'})"
    snippet = context.file_excerpt if context and context.file_excerpt else ""
    blocks = [
        f"PR #{pr_number}",
        "",
        "Severity",
        f"- {severity}",
        "",
        "Category",
        f"- {category}",
        "",
        "Issue description",
        f"- {finding.issue}",
        "",
        "Suggestion",
        f"- {finding.suggestion}",
        "",
        "Impact",
        f"- {finding.evidence}",
        "",
        "Affected files",
        f"- {location}",
    ]
    if snippet:
        blocks.extend(
            [
                "",
                "Context",
                snippet,
            ]
        )
    return "\n".join(blocks)
