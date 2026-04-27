from __future__ import annotations

import argparse
from pathlib import Path

from ai3_cr_agent.pipeline import PipelineRunner
from ai3_cr_agent.server import serve_dashboard


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the AI3 Code Review Agent pipeline.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run one review case")
    run_parser.add_argument("case_dir", type=Path, help="Path to a review case directory")
    run_parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional output directory. Defaults to <case_dir>/build",
    )

    serve_parser = subparsers.add_parser("serve", help="Start the review backend dashboard")
    serve_parser.add_argument("case_dir", type=Path, help="Path to a review case directory")
    serve_parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional output directory. Defaults to <case_dir>/build",
    )
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        output_dir = PipelineRunner().run(args.case_dir, args.output_dir)
        print(f"Artifacts written to: {output_dir}")
        return 0
    if args.command == "serve":
        server = serve_dashboard(
            args.case_dir,
            host=args.host,
            port=args.port,
            output_dir=args.output_dir,
        )
        print(f"Dashboard running at: http://{args.host}:{args.port}/admin/input")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return 0
    parser.print_help()
    return 1
