from __future__ import annotations

import html


def render_admin_generation_page(*, model: str) -> str:
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
        --green: #1f883d;
        --blue: #0969da;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
        color: var(--text);
        background: #fff;
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
      }}
      .actions {{
        display: flex;
        gap: 12px;
      }}
      .primary, .ghost {{
        display: inline-flex;
        align-items: center;
        padding: 10px 14px;
        border-radius: 6px;
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
      .layout {{
        display: grid;
        grid-template-columns: minmax(0, 1fr) minmax(360px, 480px);
        gap: 18px;
      }}
      .panel {{
        border: 1px solid var(--line);
        border-radius: 8px;
        overflow: hidden;
        min-height: 480px;
      }}
      .panel-head {{
        padding: 12px 16px;
        background: var(--bg-soft);
        border-bottom: 1px solid var(--line);
        color: var(--muted);
        font-size: 14px;
      }}
      .stream, .result {{
        margin: 0;
        padding: 16px;
        overflow: auto;
        background: #fff;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
        font-size: 12px;
        line-height: 1.6;
        white-space: pre-wrap;
      }}
      .status {{
        margin-top: 14px;
        color: var(--blue);
        font-size: 14px;
      }}
      @media (max-width: 980px) {{
        .header {{
          flex-direction: column;
          align-items: flex-start;
        }}
        .layout {{
          grid-template-columns: 1fr;
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
      <section class="layout">
        <div class="panel">
          <div class="panel-head">模型流式输出</div>
          <pre id="stream" class="stream"></pre>
        </div>
        <div class="panel">
          <div class="panel-head">结构化执行结果</div>
          <pre id="result" class="result"></pre>
        </div>
      </section>
    </main>
    <script>
      const statusNode = document.getElementById("status");
      const streamNode = document.getElementById("stream");
      const resultNode = document.getElementById("result");
      const pushButton = document.getElementById("push-review");
      let completed = false;

      function appendLine(text) {{
        streamNode.textContent += text + "\\n";
        streamNode.scrollTop = streamNode.scrollHeight;
      }}

      const source = new EventSource("/api/generate-stream");

      source.addEventListener("status", (event) => {{
        const payload = JSON.parse(event.data);
        statusNode.textContent = payload.message;
        appendLine(`[status] ${{payload.message}}`);
      }});

      source.addEventListener("token", (event) => {{
        const payload = JSON.parse(event.data);
        streamNode.textContent += payload.text;
        streamNode.scrollTop = streamNode.scrollHeight;
      }});

      source.addEventListener("complete", (event) => {{
        const payload = JSON.parse(event.data);
        completed = true;
        statusNode.textContent = payload.summary || "Code Review generation completed.";
        resultNode.textContent = JSON.stringify(payload.review_run, null, 2);
        pushButton.disabled = false;
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
