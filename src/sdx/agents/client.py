"""
Shared OpenAI helper used by all agents.

* Forces JSON responses (``response_format={"type": "json_object"}``).
* Screens the LLM reply with the ToxicityGuard **before** any parsing.
* Validates the JSON with :pyfunc:`LLMDiagnosis.from_llm`.
* Persists every raw reply under ``data/llm_raw/<UTC>_<sid>.json``.
"""

from __future__ import annotations

import os
import uuid

from datetime import datetime, timezone
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from fastapi import HTTPException
from guardrails.errors import ValidationError as GuardValidationError
from openai import OpenAI
from pydantic import ValidationError

from sdx.guards.toxicity_validator import get_toxicity_guard
from sdx.schema.clinical_outputs import LLMDiagnosis

load_dotenv(Path(__file__).parents[3] / '.envs' / '.env')

_MODEL_NAME = os.getenv('OPENAI_MODEL', 'o4-mini')
_CLIENT = OpenAI(api_key=os.getenv('OPENAI_API_KEY', ''))

_RAW_DIR = Path('data') / 'llm_raw'
_RAW_DIR.mkdir(parents=True, exist_ok=True)

_TOXIC_GUARD = get_toxicity_guard(threshold=0.85, max_retries=3)


def _dump_llm_json(text: str, sid: str | None) -> None:
    """Write *text* to data/llm_raw/<UTC>_<sid>.json."""
    ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    suffix = sid or uuid.uuid4().hex[:8]
    (_RAW_DIR / f'{ts}_{suffix}.json').write_text(text, encoding='utf-8')


def _llm_call(messages: List[dict[str, str]]) -> str:
    """Low-level OpenAI call returning the raw JSON string."""
    if not messages:
        raise ValueError('Cannot call LLM with empty messages.')

    from typing import Iterable, cast

    # …

    rsp = _CLIENT.chat.completions.create(  # type: ignore[call-overload]
        model=_MODEL_NAME,
        messages=cast(
            Iterable[dict[str, str]],
            messages,
        ),
        response_format={'type': 'json_object'},
    )
    return rsp.choices[0].message.content or '{}'


def chat(
    system: str,
    user: str,
    *,
    session_id: str | None = None,
) -> LLMDiagnosis:
    """Call the LLM with the given *system* and *user* messages."""
    raw: str = _llm_call(
        [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': user},
        ]
    )

    # ── 1️⃣  Guardrails toxicity check ───────────────────────────────────
    try:
        _TOXIC_GUARD.validate(raw)
    except GuardValidationError as exc:
        labels: list[str] = getattr(exc, 'metadata', {}).get('labels', [])
        raise HTTPException(
            status_code=422,
            detail={'error': 'Toxic content', 'labels': labels},
        ) from exc

    # ── 2️⃣  Persist raw (only if it passed the guard) ───────────────────
    _dump_llm_json(raw, session_id)

    # ── 3️⃣  Parse into Pydantic model ───────────────────────────────────
    try:
        return LLMDiagnosis.from_llm(raw)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=f'LLM response is not valid LLMDiagnosis: {exc}',
        ) from exc
