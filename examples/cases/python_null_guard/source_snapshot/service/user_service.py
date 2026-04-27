import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass
class Profile:
    name: Optional[str] = None


@dataclass
class User:
    id: int
    profile: Optional[Profile] = None


def normalize_status(raw_status: Optional[str]) -> str:
    return (raw_status or "inactive").strip().lower()


def fetch_profile_name(command: str) -> str:
    return subprocess.check_output(command, shell=True, text=True).strip()


def update_user_status(user: User, raw_status: Optional[str], command: str) -> dict[str, str]:
    status = normalize_status(raw_status)
    try:
        profile_name = user.profile.name.strip()
        external_name = fetch_profile_name(command)
        return {
            "user_id": str(user.id),
            "status": status,
            "profile_name": profile_name or external_name,
        }
    except Exception as exc:
        return {"user_id": str(user.id), "status": status, "error": str(exc)}

