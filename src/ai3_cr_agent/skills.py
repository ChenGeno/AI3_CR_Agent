from __future__ import annotations

import json
from pathlib import Path

from ai3_cr_agent.domain.models import ReviewSkill


def load_selected_skills(case_dir: Path) -> list[ReviewSkill]:
    selection_path = case_dir / "review_skills.json"
    if not selection_path.exists():
        return []

    payload = json.loads(selection_path.read_text(encoding="utf-8"))
    selected_ids = payload.get("skills", [])
    if not isinstance(selected_ids, list):
        raise RuntimeError("review_skills.json field 'skills' must be a list.")

    skills_root = _project_root() / "skills"
    registry = {skill.skill_id: skill for skill in list_registered_skills()}
    loaded: list[ReviewSkill] = []
    for item in selected_ids:
        skill_id = str(item).strip()
        if not skill_id:
            continue
        skill = registry.get(skill_id)
        if skill is None:
            raise FileNotFoundError(f"Selected skill not found: {skills_root / skill_id}")
        loaded.append(skill)
    return loaded


def list_registered_skills() -> list[ReviewSkill]:
    skills_root = _project_root() / "skills"
    if not skills_root.exists():
        return []
    loaded: list[ReviewSkill] = []
    for skill_dir in sorted(path for path in skills_root.iterdir() if path.is_dir()):
        meta_path = skill_dir / "skill.json"
        body_path = skill_dir / "SKILL.md"
        if not meta_path.exists() or not body_path.exists():
            continue
        loaded.append(_load_skill(skills_root, skill_dir.name))
    return loaded


def _load_skill(skills_root: Path, skill_id: str) -> ReviewSkill:
    skill_dir = skills_root / skill_id
    meta_path = skill_dir / "skill.json"
    body_path = skill_dir / "SKILL.md"
    if not meta_path.exists():
        raise FileNotFoundError(f"Skill metadata not found: {meta_path}")
    if not body_path.exists():
        raise FileNotFoundError(f"Skill body not found: {body_path}")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    return ReviewSkill(
        skill_id=skill_id,
        name=str(meta.get("name", skill_id)).strip() or skill_id,
        description=str(meta.get("description", "")).strip(),
        content=body_path.read_text(encoding="utf-8").strip(),
        source_path=str(body_path),
    )


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]
