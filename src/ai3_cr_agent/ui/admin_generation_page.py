from __future__ import annotations

import html


def render_admin_generation_page(*, model: str, batches_payload: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Review Backend - Generate</title>
    <style>
      :root {{
        --line: #d0d7de;
        --muted: #57606a;
        --text: #24292f;
        --bg-soft: #f6f8fa;
        --bg-page: #f3f6fb;
        --surface: #ffffff;
        --green: #1f883d;
        --blue: #0969da;
        --red: #cf222e;
        --shadow: 0 14px 32px rgba(31, 35, 40, 0.08);
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
        color: var(--text);
        background: var(--bg-page);
      }}
      .page {{
        max-width: 1240px;
        margin: 0 auto;
        padding: 28px 24px 36px;
      }}
      .header {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 16px;
        margin-bottom: 18px;
      }}
      h1 {{
        margin: 0;
        font-size: 30px;
      }}
      .meta {{
        margin-top: 10px;
        color: var(--muted);
        font-size: 14px;
      }}
      .actions {{
        display: flex;
        gap: 12px;
      }}
      .primary, .ghost {{
        display: inline-flex;
        align-items: center;
        padding: 10px 14px;
        border-radius: 10px;
        border: 1px solid transparent;
        font-weight: 700;
        text-decoration: none;
        cursor: pointer;
      }}
      .primary {{
        background: var(--green);
        color: #fff;
      }}
      .primary[disabled] {{
        opacity: 0.55;
        cursor: not-allowed;
      }}
      .ghost {{
        background: var(--bg-soft);
        border-color: var(--line);
        color: var(--text);
      }}
      .progress-shell {{
        margin-bottom: 18px;
      }}
      .progress-panel {{
        border: 1px solid rgba(208, 215, 222, 0.9);
        border-radius: 14px;
        overflow: hidden;
        background: var(--surface);
        box-shadow: var(--shadow);
      }}
      .progress-panel .panel-head,
      .panel .panel-head {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
        padding: 14px 16px;
        background: linear-gradient(180deg, #fbfdff 0%, #f6f8fa 100%);
        border-bottom: 1px solid var(--line);
        color: var(--muted);
        font-size: 14px;
      }}
      .panel-head-meta {{
        color: var(--muted);
        font-size: 12px;
      }}
      .progress-summary {{
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 12px;
        padding: 16px;
        background: linear-gradient(180deg, rgba(9, 105, 218, 0.03) 0%, rgba(255, 255, 255, 0) 100%);
        border-bottom: 1px solid #e7ebef;
      }}
      .metric-card {{
        border: 1px solid #e7ebef;
        border-radius: 12px;
        padding: 14px 15px;
        background: #fff;
      }}
      .metric-label {{
        color: var(--muted);
        font-size: 12px;
      }}
      .metric-value {{
        margin-top: 8px;
        font-size: 24px;
        font-weight: 700;
        line-height: 1;
      }}
      .metric-note {{
        margin-top: 8px;
        color: var(--muted);
        font-size: 12px;
      }}
      .layout {{
        display: grid;
        grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
        gap: 18px;
      }}
      .panel {{
        border: 1px solid rgba(208, 215, 222, 0.9);
        border-radius: 14px;
        overflow: hidden;
        min-height: 560px;
        background: var(--surface);
        box-shadow: var(--shadow);
      }}
      .result {{
        margin: 0;
        padding: 16px;
        overflow: auto;
        background: #fbfdff;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
        font-size: 12px;
        line-height: 1.7;
        white-space: pre;
      }}
      .stream-board {{
        padding: 16px;
        overflow: auto;
        background: #fbfdff;
      }}
      .stream-list {{
        display: grid;
        gap: 12px;
      }}
      .step-card {{
        border: 1px solid #d8dee4;
        border-radius: 12px;
        background: #fff;
        overflow: hidden;
        box-shadow: 0 6px 20px rgba(31, 35, 40, 0.04);
      }}
      .step-card.running {{
        border-color: var(--blue);
        box-shadow: inset 0 0 0 1px var(--blue);
      }}
      .step-card.completed {{
        border-color: var(--green);
        box-shadow: inset 0 0 0 1px var(--green);
      }}
      .step-card.failed {{
        border-color: #cf222e;
        box-shadow: inset 0 0 0 1px #cf222e;
      }}
      .step-header {{
        display: flex;
        justify-content: space-between;
        gap: 12px;
        align-items: flex-start;
        padding: 14px 16px;
        cursor: pointer;
        list-style: none;
      }}
      .step-header::-webkit-details-marker {{
        display: none;
      }}
      .step-head {{
        display: flex;
        justify-content: space-between;
        gap: 12px;
        align-items: flex-start;
        flex: 1;
      }}
      .step-head-main {{
        min-width: 0;
        flex: 1;
      }}
      .step-head-side {{
        display: inline-flex;
        align-items: center;
        gap: 8px;
        flex: 0 0 auto;
      }}
      .step-title {{
        margin: 0;
        font-size: 15px;
        font-weight: 700;
      }}
      .step-summary {{
        margin-top: 8px;
        color: var(--muted);
        font-size: 13px;
        line-height: 1.7;
      }}
      .step-chevron {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-height: 28px;
        padding: 0 10px;
        border: 1px solid #d8dee4;
        border-radius: 999px;
        background: #fff;
        color: var(--muted);
        font-size: 12px;
        font-weight: 700;
        line-height: 1;
        white-space: nowrap;
      }}
      .step-content {{
        padding: 0 16px 16px;
      }}
      .step-columns {{
        display: grid;
        grid-template-columns: 1fr;
        gap: 10px;
        margin-top: 12px;
      }}
      .step-block {{
        border: 1px solid #e7ebef;
        border-radius: 10px;
        overflow: hidden;
        background: #fdfefe;
      }}
      .step-block-head {{
        padding: 9px 12px;
        background: var(--bg-soft);
        color: var(--muted);
        font-size: 12px;
        font-weight: 700;
      }}
      .step-block pre {{
        margin: 0;
        padding: 10px 12px;
        background: #fff;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
        font-size: 12px;
        line-height: 1.55;
        white-space: pre-wrap;
        overflow: auto;
      }}
      .activity-log {{
        margin-top: 16px;
        border: 1px solid #e7ebef;
        border-radius: 12px;
        padding: 14px 16px;
        background: #fff;
      }}
      .activity-log h3 {{
        margin: 0 0 8px;
        font-size: 12px;
        color: var(--muted);
      }}
      .activity-log pre {{
        margin: 0;
        padding: 0;
        background: transparent;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
        font-size: 12px;
        line-height: 1.55;
        white-space: pre-wrap;
      }}
      .status {{
        margin-top: 14px;
        color: var(--blue);
        font-size: 14px;
      }}
      .timeline {{
        padding: 16px;
        background: #fff;
      }}
      .timeline-section + .timeline-section {{
        margin-top: 18px;
      }}
      .timeline-label {{
        margin: 0 0 10px;
        color: var(--muted);
        font-size: 13px;
      }}
      .batch-list {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 12px;
      }}
      .batch-card {{
        border: 1px solid #d8dee4;
        border-radius: 12px;
        padding: 14px;
        background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
      }}
      .batch-card.running {{
        border-color: var(--blue);
        box-shadow: inset 0 0 0 1px var(--blue);
      }}
      .batch-card.completed {{
        border-color: var(--green);
        box-shadow: inset 0 0 0 1px var(--green);
      }}
      .batch-card.failed {{
        border-color: #cf222e;
        box-shadow: inset 0 0 0 1px #cf222e;
      }}
      .batch-head {{
        display: flex;
        justify-content: space-between;
        gap: 12px;
        align-items: center;
      }}
      .batch-title {{
        margin: 0;
        font-size: 14px;
        font-weight: 700;
      }}
      .batch-state {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-height: 28px;
        padding: 4px 8px;
        border-radius: 999px;
        background: var(--bg-soft);
        color: var(--muted);
        font-size: 12px;
        font-weight: 700;
        line-height: 1;
        white-space: nowrap;
      }}
      .batch-state.running {{
        background: rgba(9,105,218,0.12);
        color: var(--blue);
      }}
      .batch-state.completed {{
        background: rgba(31,136,61,0.12);
        color: var(--green);
      }}
      .batch-state.failed {{
        background: rgba(207,34,46,0.12);
        color: #cf222e;
      }}
      .batch-meta {{
        margin-top: 8px;
        color: var(--muted);
        font-size: 12px;
        line-height: 1.6;
      }}
      .phase-card {{
        border: 1px solid #d8dee4;
        border-radius: 12px;
        padding: 14px;
        background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
      }}
      .phase-card.running {{
        border-color: var(--blue);
      }}
      .phase-card.completed {{
        border-color: var(--green);
      }}
      .json-key {{
        color: #0550ae;
      }}
      .json-string {{
        color: #0a7f37;
      }}
      .json-number {{
        color: #953800;
      }}
      .json-boolean {{
        color: #8250df;
      }}
      .json-null {{
        color: #cf222e;
      }}
      @media (max-width: 980px) {{
        .header {{
          flex-direction: column;
          align-items: flex-start;
        }}
        .progress-summary,
        .layout {{
          grid-template-columns: 1fr;
        }}
        .panel {{
          min-height: 420px;
        }}
      }}
    </style>
  </head>
  <body>
    <main class="page">
      <div class="header">
        <div>
          <h1>模型推理过程与执行结果</h1>
          <div class="meta">Model: {html.escape(model)}</div>
          <div id="status" class="status">正在建立 SSE 链接...</div>
        </div>
        <div class="actions">
          <a class="ghost" href="/admin/input">返回输入页</a>
          <button id="push-review" class="primary" type="button" disabled>推送 Review</button>
        </div>
      </div>
      <section class="progress-shell">
        <div class="progress-panel">
          <div class="panel-head">
            <span>分层批处理进度</span>
            <span id="progress-meta" class="panel-head-meta">等待任务启动</span>
          </div>
          <div id="progress-summary" class="progress-summary"></div>
          <div id="timeline" class="timeline"></div>
        </div>
      </section>
      <section class="layout">
        <div class="panel">
          <div class="panel-head">
            <span>模型流式输出</span>
            <span class="panel-head-meta">按阶段展开查看输入、输出与轨迹</span>
          </div>
          <div id="stream" class="stream-board"></div>
        </div>
        <div class="panel">
          <div class="panel-head">
            <span>结构化执行结果</span>
            <span class="panel-head-meta">JSON 高亮视图</span>
          </div>
          <pre id="result" class="result"></pre>
        </div>
      </section>
    </main>
    <script>
      const statusNode = document.getElementById("status");
      const progressMetaNode = document.getElementById("progress-meta");
      const progressSummaryNode = document.getElementById("progress-summary");
      const timelineNode = document.getElementById("timeline");
      const streamNode = document.getElementById("stream");
      const resultNode = document.getElementById("result");
      const pushButton = document.getElementById("push-review");
      let completed = false;
      const reviewPlan = {batches_payload};
      const batchStates = new Map((reviewPlan || []).map((item) => [item.batch_id, "pending"]));
      let globalState = "pending";
      const stepStore = new Map();
      const stepOrder = [];
      const activityLines = [];
      const collapsedSteps = new Set();

      function appendLine(text) {{
        activityLines.push(text);
        renderStream();
      }}

      function stringifyBlock(value) {{
        if (value === null || value === undefined) return "";
        if (typeof value === "string") return value;
        return JSON.stringify(value, null, 2);
      }}

      function escapeHtml(text) {{
        return String(text)
          .replaceAll("&", "&amp;")
          .replaceAll("<", "&lt;")
          .replaceAll(">", "&gt;");
      }}

      function renderJsonValue(value, indent = 0) {{
        const pad = "  ".repeat(indent);
        const nextPad = "  ".repeat(indent + 1);
        if (value === null) return `<span class="json-null">null</span>`;
        if (Array.isArray(value)) {{
          if (!value.length) return "[]";
          const items = value
            .map((item) => `${{nextPad}}${{renderJsonValue(item, indent + 1)}}`)
            .join(",\\n");
          return `[\\n${{items}}\\n${{pad}}]`;
        }}
        if (typeof value === "object") {{
          const entries = Object.entries(value);
          if (!entries.length) return "{{}}";
          const items = entries
            .map(([key, item]) => `${{nextPad}}<span class="json-key">"${{escapeHtml(key)}}"</span>: ${{renderJsonValue(item, indent + 1)}}`)
            .join(",\\n");
          return `{{\\n${{items}}\\n${{pad}}}}`;
        }}
        if (typeof value === "string") return `<span class="json-string">"${{escapeHtml(value)}}"</span>`;
        if (typeof value === "number") return `<span class="json-number">${{String(value)}}</span>`;
        if (typeof value === "boolean") return `<span class="json-boolean">${{String(value)}}</span>`;
        return `<span class="json-string">"${{escapeHtml(String(value))}}"</span>`;
      }}

      function renderResult(value) {{
        if (value === null || value === undefined) {{
          resultNode.innerHTML = '<span class="json-null">暂无结果</span>';
          return;
        }}
        if (typeof value === "string") {{
          try {{
            resultNode.innerHTML = renderJsonValue(JSON.parse(value));
            return;
          }} catch (_error) {{
            resultNode.textContent = value;
            return;
          }}
        }}
        resultNode.innerHTML = renderJsonValue(value);
      }}

      function statusLabel(status) {{
        const labels = {{
          pending: "待执行",
          running: "执行中",
          completed: "已完成",
          failed: "失败"
        }};
        return labels[status] || status;
      }}

      function upsertStep(step) {{
        if (!stepStore.has(step.stage_id)) {{
          stepOrder.push(step.stage_id);
        }}
        const existing = stepStore.get(step.stage_id) || {{}};
        stepStore.set(step.stage_id, {{ ...existing, ...step }});
        if ((step.status || "") === "completed") {{
          collapsedSteps.add(step.stage_id);
        }}
        if ((step.status || "") === "running" || (step.status || "") === "failed") {{
          collapsedSteps.delete(step.stage_id);
        }}
        renderStream();
      }}

      function renderStream() {{
        const cards = stepOrder.map((stageId) => {{
          const step = stepStore.get(stageId) || {{}};
          const inputText = stringifyBlock(step.input);
          const outputText = stringifyBlock(step.output);
          const isCollapsed = collapsedSteps.has(stageId);
          return `
            <details class="step-card ${{step.status || "pending"}}" data-stage-id="${{escapeHtml(stageId)}}" ${{isCollapsed ? "" : "open"}}>
              <summary class="step-header">
                <div class="step-head">
                  <div class="step-head-main">
                    <h3 class="step-title">${{escapeHtml(step.title || stageId)}}</h3>
                    <div class="step-summary">${{escapeHtml(step.summary || "")}}</div>
                  </div>
                  <div class="step-head-side">
                    <span class="batch-state ${{step.status || "pending"}}">${{statusLabel(step.status || "pending")}}</span>
                    <span class="step-chevron">${{isCollapsed ? "展开" : "折叠"}}</span>
                  </div>
                </div>
              </summary>
              <div class="step-content">
                <div class="step-columns">
                  <div class="step-block">
                    <div class="step-block-head">输入</div>
                    <pre>${{escapeHtml(inputText || "暂无输入快照。")}}</pre>
                  </div>
                  <div class="step-block">
                    <div class="step-block-head">输出</div>
                    <pre>${{escapeHtml(outputText || "尚未产生输出。")}}</pre>
                  </div>
                </div>
              </div>
            </details>
          `;
        }}).join("");
        const activity = activityLines.length
          ? `
              <section class="activity-log">
                <h3>运行轨迹</h3>
                <pre>${{escapeHtml(activityLines.join("\\n"))}}</pre>
              </section>
            `
          : "";
        streamNode.innerHTML = `<div class="stream-list">${{cards}}</div>${{activity}}`;
        streamNode.querySelectorAll("details[data-stage-id]").forEach((node) => {{
          node.addEventListener("toggle", () => {{
            const stageId = node.dataset.stageId;
            if (!stageId) return;
            if (node.open) {{
              collapsedSteps.delete(stageId);
            }} else {{
              collapsedSteps.add(stageId);
            }}
            const chevron = node.querySelector(".step-chevron");
            if (chevron) {{
              chevron.textContent = node.open ? "折叠" : "展开";
            }}
          }});
        }});
        streamNode.scrollTop = streamNode.scrollHeight;
      }}

      function renderTimeline() {{
        const batchValues = Array.from(batchStates.values());
        const completedCount = batchValues.filter((state) => state === "completed").length;
        const runningCount = batchValues.filter((state) => state === "running").length;
        const failedCount = batchValues.filter((state) => state === "failed").length;
        const totalCount = batchValues.length;
        const globalLabel = statusLabel(globalState);
        const globalNote = failedCount ? `失败批次：${{failedCount}}` : "等待跨批次汇总完成";
        progressMetaNode.textContent = `批次 ${{completedCount}}/${{totalCount}} 已完成，跨批次复审：${{globalLabel}}`;
        progressSummaryNode.innerHTML = `
          <article class="metric-card">
            <div class="metric-label">总批次数</div>
            <div class="metric-value">${{totalCount}}</div>
            <div class="metric-note">按变更切分后的独立审查单元</div>
          </article>
          <article class="metric-card">
            <div class="metric-label">已完成</div>
            <div class="metric-value">${{completedCount}}</div>
            <div class="metric-note">已输出局部 review 结果</div>
          </article>
          <article class="metric-card">
            <div class="metric-label">执行中</div>
            <div class="metric-value">${{runningCount}}</div>
            <div class="metric-note">当前仍在处理的批次</div>
          </article>
          <article class="metric-card">
            <div class="metric-label">全局状态</div>
            <div class="metric-value">${{globalLabel}}</div>
            <div class="metric-note">${{globalNote}}</div>
          </article>
        `;
        const batchCards = (reviewPlan || []).map((item) => {{
          const state = batchStates.get(item.batch_id) || "pending";
          return `
            <article class="batch-card ${{state}}">
              <div class="batch-head">
                <h3 class="batch-title">${{item.batch_id}}</h3>
                <span class="batch-state ${{state}}">${{statusLabel(state)}}</span>
              </div>
              <div class="batch-meta">
                <div>${{item.change_ids.length}} changes</div>
                <div>Estimated tokens: ${{item.estimated_tokens}}</div>
                <div>Files: ${{item.file_paths.join(", ")}}</div>
              </div>
            </article>
          `;
        }}).join("");

        timelineNode.innerHTML = `
          <section class="timeline-section">
            <p class="timeline-label">局部批次审查</p>
            <div class="batch-list">${{batchCards}}</div>
          </section>
          <section class="timeline-section">
            <p class="timeline-label">全局跨批次复审</p>
            <article class="phase-card ${{globalState}}">
              <div class="batch-head">
                <h3 class="batch-title">global-review</h3>
                <span class="batch-state ${{globalState}}">${{statusLabel(globalState)}}</span>
              </div>
              <div class="batch-meta">汇总局部 findings，并检查跨文件、跨批次联动问题。</div>
            </article>
          </section>
        `;
      }}

      renderTimeline();

      const source = new EventSource("/api/generate-stream");

      source.addEventListener("status", (event) => {{
        const payload = JSON.parse(event.data);
        statusNode.textContent = payload.message;
        appendLine(`[status] ${{payload.message}}`);
      }});

      source.addEventListener("token", (event) => {{
        const payload = JSON.parse(event.data);
        appendLine(`[token] ${{payload.text}}`);
      }});

      source.addEventListener("pipeline_step", (event) => {{
        const payload = JSON.parse(event.data);
        upsertStep(payload);
      }});

      source.addEventListener("batch_start", (event) => {{
        const payload = JSON.parse(event.data);
        batchStates.set(payload.batch_id, "running");
        renderTimeline();
      }});

      source.addEventListener("batch_complete", (event) => {{
        const payload = JSON.parse(event.data);
        batchStates.set(payload.batch_id, "completed");
        appendLine(`[batch] ${{payload.batch_id}} completed: ${{payload.summary || ""}}`);
        renderTimeline();
      }});

      source.addEventListener("global_start", () => {{
        globalState = "running";
        renderTimeline();
      }});

      source.addEventListener("global_complete", (event) => {{
        const payload = JSON.parse(event.data);
        globalState = "completed";
        appendLine(`[global] ${{payload.summary || "Cross-batch review completed."}}`);
        renderTimeline();
      }});

      source.addEventListener("complete", (event) => {{
        const payload = JSON.parse(event.data);
        completed = true;
        globalState = "completed";
        statusNode.textContent = payload.summary || "Code Review generation completed.";
        renderResult(payload.review_run);
        pushButton.disabled = false;
        renderTimeline();
        source.close();
      }});

      source.addEventListener("error", (event) => {{
        const payload = event.data ? JSON.parse(event.data) : {{ message: "SSE connection failed." }};
        statusNode.textContent = payload.message;
        appendLine(`[error] ${{payload.message}}`);
      }});

      pushButton.addEventListener("click", async () => {{
        if (!completed) return;
        pushButton.disabled = true;
        statusNode.textContent = "正在推送 Review...";
        const response = await fetch("/api/push-review", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }}
        }});
        const payload = await response.json();
        if (!response.ok) {{
          statusNode.textContent = payload.error || "Push review failed.";
          pushButton.disabled = false;
          return;
        }}
        window.location.href = payload.redirect_url;
      }});
    </script>
  </body>
</html>
"""
