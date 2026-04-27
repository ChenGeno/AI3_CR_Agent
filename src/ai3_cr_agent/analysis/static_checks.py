from __future__ import annotations

import re

from ai3_cr_agent.domain.models import ChangeUnit, ContextBundle, Finding

DEEP_ATTRIBUTE_RE = re.compile(r"\b[a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*){2,}\b")


def run_static_checks(change_units: list[ChangeUnit], contexts: list[ContextBundle]) -> list[Finding]:
    context_by_id = {context.change_id: context for context in contexts}
    findings: list[Finding] = []
    for change_unit in change_units:
        context = context_by_id[change_unit.change_id]
        findings.extend(_check_shell_execution(change_unit))
        findings.extend(_check_broad_exception(change_unit))
        findings.extend(_check_deep_attribute_access(change_unit, context))
    return findings


def _check_shell_execution(change_unit: ChangeUnit) -> list[Finding]:
    findings: list[Finding] = []
    for line_no, line in change_unit.hunk.added_line_map:
        if "shell=True" not in line:
            continue
        findings.append(
            Finding(
                change_id=change_unit.change_id,
                file_path=change_unit.file_path,
                severity="high",
                category="security",
                confidence=0.96,
                title="Avoid shell=True in subprocess calls",
                issue="新增的 subprocess 调用启用了 shell=True，外部输入一旦进入命令字符串，存在命令注入风险。",
                evidence=f"Line {line_no}: {line.strip()}",
                suggestion="优先传递参数列表并关闭 shell=True；如果必须使用 shell，先对输入做严格白名单校验。",
                line=line_no,
            )
        )
    return findings


def _check_broad_exception(change_unit: ChangeUnit) -> list[Finding]:
    findings: list[Finding] = []
    for line_no, line in change_unit.hunk.added_line_map:
        if "except Exception" not in line:
            continue
        findings.append(
            Finding(
                change_id=change_unit.change_id,
                file_path=change_unit.file_path,
                severity="medium",
                category="maintainability",
                confidence=0.88,
                title="Broad exception handler introduced",
                issue="使用 except Exception 会掩盖真实失败原因，也可能吞掉本不该在这里处理的异常。",
                evidence=f"Line {line_no}: {line.strip()}",
                suggestion="改为捕获明确异常类型，并保留必要日志或上抛策略。",
                line=line_no,
            )
        )
    return findings


def _check_deep_attribute_access(change_unit: ChangeUnit, context: ContextBundle) -> list[Finding]:
    findings: list[Finding] = []
    guard_tokens = ("if user.profile", "if profile", "getattr(", "is not None")
    for line_no, line in change_unit.hunk.added_line_map:
        match = DEEP_ATTRIBUTE_RE.search(line)
        if not match:
            continue
        if any(token in context.symbol_source for token in guard_tokens):
            continue
        findings.append(
            Finding(
                change_id=change_unit.change_id,
                file_path=change_unit.file_path,
                severity="medium",
                category="correctness",
                confidence=0.72,
                title="Potential null dereference in deep attribute access",
                issue="新增代码直接访问多级属性链，若中间对象为空，运行时可能触发异常。",
                evidence=f"Line {line_no}: {line.strip()}",
                suggestion="在访问链路前增加显式判空，或通过安全默认值封装读取逻辑。",
                line=line_no,
            )
        )
    return findings
