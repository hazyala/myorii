from __future__ import annotations

import sys
from pathlib import Path


def app_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))


def resource_path(*parts: str) -> Path:
    return app_root().joinpath(*parts)


def data_dir() -> Path:
    """사용자 데이터 저장 디렉토리 (앱 재설치해도 유지)"""
    base = Path.home() / "Library" / "Application Support" / "Myorii"
    base.mkdir(parents=True, exist_ok=True)
    return base


def db_path() -> Path:
    return data_dir() / "myorii.db"