from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

_PKG_DIR = Path(__file__).resolve().parent
_PROJECT_DIR = _PKG_DIR.parent


def _bootstrap_env() -> None:
    """Load project ``.env`` files so they win over stale shell exports."""
    load_dotenv(override=False)
    for env_path in (_PROJECT_DIR / ".env", _PKG_DIR / ".env"):
        if env_path.is_file():
            load_dotenv(env_path, override=True)


_bootstrap_env()


def _env_first(*keys: str) -> str | None:
    for k in keys:
        v = os.getenv(k)
        if v:
            return v
    return None


def _env_flag(*keys: str, default: str = "0") -> bool:
    for key in keys:
        val = os.getenv(key)
        if val is not None and val != "":
            return val.lower() in ("1", "true", "yes")
    return default.lower() in ("1", "true", "yes")


def _normalize_neo4j_database(raw: str | None, *, neo4j_uri: str | None) -> str | None:
    """
    Neo4j Aura hostnames look like ``67257d23.databases.neo4j.io``.
    Students often put that instance id into NEO4J_DATABASE_KGA; that is not a
    database name and triggers DatabaseNotFound. Real Aura default DB is ``neo4j``.

    Returns None to let the driver use the default database (correct for typical Aura).
    """
    if not raw:
        return None
    s = raw.strip()
    if not s:
        return None
    # 8-char lowercase hex = Aura instance id mistaken for DB name
    if len(s) == 8 and re.fullmatch(r"[0-9a-f]{8}", s, flags=re.IGNORECASE):
        return None
    if neo4j_uri:
        m = re.search(r"neo4j\+s?://([0-9a-f]{8})\.databases\.neo4j\.io", neo4j_uri, re.I)
        if m and s.lower() == m.group(1).lower():
            return None
    return s


@dataclass(frozen=True)
class Settings:
    """Environment-driven configuration. Never commit real secrets."""

    openai_api_key: str | None
    openai_model: str
    neo4j_uri: str | None
    neo4j_user: str | None
    neo4j_password: str | None
    neo4j_database: str | None
    use_mock_llm: bool
    skip_neo4j: bool
    exit_on_complete: bool
    use_lag: bool  # Logic-Augmented Generation: feed full symbolic context to LLM

    @staticmethod
    def from_env() -> "Settings":
        uri = _env_first("NEO4J_URI", "NEO4J_URI_KGA")
        db_raw = _env_first("NEO4J_DATABASE", "NEO4J_DATABASE_KGA")
        return Settings(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            neo4j_uri=uri,
            neo4j_user=_env_first("NEO4J_USERNAME", "NEO4J_USER", "NEO4J_USERNAME_KGA"),
            neo4j_password=_env_first("NEO4J_PASSWORD", "NEO4J_PASSWORD_KGA"),
            neo4j_database=_normalize_neo4j_database(db_raw, neo4j_uri=uri),
            use_mock_llm=_env_flag("TRACEMIND_MOCK_LLM", ),
            skip_neo4j=_env_flag("TRACEMIND_SKIP_NEO4J",),
            exit_on_complete=_env_flag(
                "TRACEMIND_EXIT_ON_COMPLETE",
                default="1",
            ),
            use_lag=_env_flag("TRACEMIND_USE_LAG"),
        )


Mode = Literal["interpretation", "explanation"]
