from __future__ import annotations

import html
import json
from pathlib import Path

try:
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import JsonLexer
except ImportError:  # pragma: no cover - optional runtime dependency fallback
    highlight = None
    HtmlFormatter = None
    JsonLexer = None

from ai3_cr_agent.domain.models import ReviewSkill


def render_admin_input_page(
    *,
    case_dir: Path,
    model: str,
    registered_skills: list[ReviewSkill],
    active_skills: list[ReviewSkill],
    agent_input: dict[str, object],
) -> str:
    pretty_json = json.dumps(agent_input, indent=2, ensure_ascii=False)
    code_html, pygments_css = _render_json_block(pretty_json)
    active_skill_ids = {skill.skill_id for skill in active_skills}
    registered_text = "、".join(skill.name for skill in registered_skills) if registered_skills else "无"
    active_text = "、".join(skill.name for skill in active_skills) if active_skills else "无"
    skill_cards = "".join(
        _render_skill_card(skill, active=skill.skill_id in active_skill_ids)
        for skill in registered_skills
    ) or '<div class="empty-skills">当前没有注册任何 Skills。</div>'
    return f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Review Backend - Input</title>
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
      .page {{
        max-width: 1200px;
        margin: 0 auto;
        padding: 28px 24px 36px;
      }}
      .header {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 16px;
        margin-bottom: 20px;
      }}
      h1 {{
        margin: 0;
        font-size: 30px;
      }}
      .meta {{
        margin-top: 10px;
        color: var(--muted);
        font-size: 14px;
        line-height: 1.6;
      }}
      .skills-summary {{
        margin-top: 12px;
        color: var(--text);
        font-size: 14px;
        line-height: 1.7;
      }}
      .skills-summary strong {{
        font-weight: 700;
      }}
      .primary {{
        display: inline-flex;
        align-items: center;
        padding: 10px 14px;
        border-radius: 6px;
        background: var(--green);
        color: #fff;
        text-decoration: none;
        font-weight: 700;
      }}
      .panel {{
        border: 1px solid var(--line);
        border-radius: 8px;
        overflow: hidden;
      }}
      .panel-head {{
        padding: 12px 16px;
        background: var(--bg-soft);
        border-bottom: 1px solid var(--line);
        font-size: 14px;
        color: var(--muted);
      }}
      .skills-panel {{
        margin-bottom: 18px;
        border: 1px solid var(--line);
        border-radius: 8px;
        overflow: hidden;
      }}
      .skills-body {{
        padding: 16px;
        background: #fff;
      }}
      .skills-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
        gap: 14px;
      }}
      .skill-card {{
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 14px;
        background: #fff;
      }}
      .skill-card.active {{
        border-color: #1f883d;
        box-shadow: inset 0 0 0 1px #1f883d;
      }}
      .skill-head {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 12px;
      }}
      .skill-title {{
        margin: 0;
        font-size: 16px;
      }}
      .skill-id {{
        margin-top: 4px;
        color: var(--muted);
        font-size: 12px;
      }}
      .skill-desc {{
        margin: 10px 0 0;
        color: var(--muted);
        font-size: 13px;
        line-height: 1.6;
      }}
      .skill-toggle {{
        padding: 8px 12px;
        border-radius: 6px;
        border: 1px solid var(--line);
        background: var(--bg-soft);
        color: var(--text);
        font-weight: 700;
        cursor: pointer;
      }}
      .skill-toggle.active {{
        background: #1f883d;
        border-color: #1f883d;
        color: #fff;
      }}
      details.skill-details {{
        margin-top: 12px;
      }}
      details.skill-details summary {{
        cursor: pointer;
        color: #0969da;
        font-size: 13px;
      }}
      .skill-content {{
        margin-top: 10px;
        padding: 12px;
        border-radius: 6px;
        background: var(--bg-soft);
        white-space: pre-wrap;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
        font-size: 12px;
        line-height: 1.6;
      }}
      .empty-skills {{
        color: var(--muted);
        font-size: 14px;
      }}
      .code-shell {{
        overflow: auto;
        background: #ffffff;
      }}
      pre {{
        margin: 0;
        padding: 16px;
        overflow: auto;
        background: #fff;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
        font-size: 12px;
        line-height: 1.6;
        white-space: pre-wrap;
      }}
      .code-shell pre {{
        white-space: pre;
      }}
      {pygments_css}
      @media (max-width: 900px) {{
        .header {{
          flex-direction: column;
          align-items: flex-start;
        }}
      }}
    </style>
  </head>
  <body>
    <main class="page">
      <div class="header">
        <div>
          <h1>解析 PR 后模型最终输入</h1>
          <div class="skills-summary">
            <div><strong>当前注册 Skills：</strong>{html.escape(registered_text)}</div>
            <div><strong>当前激活 Skills：</strong>{html.escape(active_text)}</div>
          </div>
          <div class="meta">
            <div>Case: {html.escape(str(case_dir))}</div>
            <div>Model: {html.escape(model)}</div>
          </div>
        </div>
        <a class="primary" href="/admin/generate">开始生成 Code Review</a>
      </div>
      <section class="skills-panel">
        <div class="panel-head">Skills 管理</div>
        <div class="skills-body">
          <div class="skills-grid">
            {skill_cards}
          </div>
        </div>
      </section>
      <section class="panel">
        <div class="panel-head">agent_input.json</div>
        <div class="code-shell">{code_html}</div>
      </section>
    </main>
    <script>
      async function toggleSkill(skillId) {{
        const response = await fetch("/api/skills/toggle", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ skill_id: skillId }})
        }});
        if (!response.ok) {{
          const payload = await response.json();
          window.alert(payload.error || "Skill toggle failed.");
          return;
        }}
        window.location.reload();
      }}
    </script>
  </body>
</html>
"""


def _render_json_block(pretty_json: str) -> tuple[str, str]:
    if highlight is None or HtmlFormatter is None or JsonLexer is None:
        return f"<pre>{html.escape(pretty_json)}</pre>", ""

    formatter = HtmlFormatter(nowrap=False, cssclass="json-highlight")
    highlighted = highlight(pretty_json, JsonLexer(), formatter)
    css = formatter.get_style_defs(".json-highlight")
    return highlighted, css


def _render_skill_card(skill: ReviewSkill, *, active: bool) -> str:
    button_label = "取消激活" if active else "激活"
    button_class = "skill-toggle active" if active else "skill-toggle"
    card_class = "skill-card active" if active else "skill-card"
    return f"""
      <article class="{card_class}">
        <div class="skill-head">
          <div>
            <h3 class="skill-title">{html.escape(skill.name)}</h3>
            <div class="skill-id">{html.escape(skill.skill_id)}</div>
          </div>
          <button class="{button_class}" type="button" onclick="toggleSkill('{html.escape(skill.skill_id)}')">{button_label}</button>
        </div>
        <p class="skill-desc">{html.escape(skill.description)}</p>
        <details class="skill-details">
          <summary>查看 Skill 内容</summary>
          <div class="skill-content">{html.escape(skill.content)}</div>
        </details>
      </article>
    """
