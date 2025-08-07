"""Toxicity Validator.

Guardrails validator that blocks or auto-rephrases LLM text containing
toxic / harmful content, using **facebook/bart-large-mnli** in zero-shot
mode.
"""

from __future__ import annotations

import logging

from hashlib import sha256
from typing import Dict, List, Sequence, Tuple

from guardrails import Guard, OnFailAction
from guardrails.validator_base import (
    FailResult,
    PassResult,
    ValidationResult,
    Validator,
    register_validator,
)
from transformers.pipelines import pipeline

LOGGER = logging.getLogger(__name__)


HARM_LABELS: Dict[str, str] = {
    # harassment / hate
    'harassment_nonviolent': 'harassment or hateful content (non-violent)',
    'harassment_violent': 'harassment with violent language',
    'hate_targeted': 'hate speech toward a protected class',
    'hate_threat': 'violent hate threat',
    # violence
    'violent_threat': 'explicit threat of violence',
    'violent_description': 'graphic description of violence',
    'self_harm_ideation': 'first-person self-harm thoughts',
    'self_harm_encouragement': 'encouraging others to self-harm',
    # sexual
    'sexual_explicit': 'explicit sexual content',
    'sexual_minors': 'sexual content involving minors',
    # extremism
    'extremist_praise': 'praise or support for extremist ideology',
    'extremist_instruction': 'instructions for extremist or terrorist acts',
    # illicit behaviour
    'illicit_instruction': 'instructions to facilitate wrongdoing',
    # regulated advice
    'medical_advice': 'unqualified medical advice',
    'legal_advice': 'unqualified legal advice',
}

DEFAULT_LABELS: Tuple[str, ...] = tuple(HARM_LABELS.keys())

_CLASSIFIER = pipeline(
    'zero-shot-classification',
    model='facebook/bart-large-mnli',
    hypothesis_template='This text contains {}.',
    multi_label=True,
    device=-1,  # CPU by default; overwrite via env for GPU
)


def _classify(text: str, labels: Sequence[str]) -> Dict[str, float]:
    """Return *label → sigmoid probability* for *text*."""
    out = _CLASSIFIER(text, candidate_labels=list(labels))
    return dict(zip(out['labels'], out['scores']))


# Guardrails validator
@register_validator(name='toxicity_detector', data_type='string')
class ToxicityDetector(Validator):
    """Detect and optionally rephrase toxic content.

    Parameters
    ----------
    labels
        Taxonomy keys to monitor (default: all).
    threshold
        Probability ≥ threshold triggers failure.
    max_retries
        How many rephrase attempts before failing (0 = no retry).
    rephrase_instruction
        System prompt prepended on each retry. ``None`` ➜ no rephrase.
    """

    def __init__(
        self: 'ToxicityDetector',
        *,
        labels: Sequence[str] | None = None,
        threshold: float = 0.80,
        max_retries: int = 0,
        rephrase_instruction: str | None = (
            'System: Your previous answer contained disallowed content. '
            'Rephrase it without violent, hateful, or explicit language.'
        ),
        **kwargs: object,
    ) -> None:
        """Initialize ToxicityDetector."""
        super().__init__(**kwargs)
        self.labels: Tuple[str, ...] = (
            tuple(labels) if labels else (DEFAULT_LABELS)
        )
        self.threshold: float = threshold
        self.max_retries: int = max_retries
        self.rephrase_instruction: str | None = rephrase_instruction

    def _validate(
        self,
        value: str,
        metadata: dict[str, object] | None = None,
    ) -> ValidationResult:
        """Validate *value*; auto-retry if enabled."""
        prompt: str = value
        LOGGER.info('Validating prompt: %s', prompt)

        for attempt in range(self.max_retries + 1):
            is_safe, offenders = self._is_safe(prompt)
            if is_safe:
                return PassResult()

            if (
                attempt == self.max_retries
                or self.rephrase_instruction is None
            ):
                return FailResult(
                    error_message=(
                        'Toxic content detected: ' + ', '.join(offenders)
                    ),
                    metadata={'labels': offenders},
                )

            LOGGER.info(
                'Toxic content (%s). Retrying %d/%d',
                offenders,
                attempt + 1,
                self.max_retries,
            )
            prompt = f'{self.rephrase_instruction}\n\n{prompt}'

        # should never reach
        return FailResult(error_message='Validator reached unreachable state.')

    def _is_safe(self, text: str) -> Tuple[bool, List[str]]:
        """Fast predicate: *True* if all labels < threshold."""
        cache_key = sha256(text.encode('utf-8')).hexdigest()[:16] + text
        scores = _classify(cache_key, self.labels)
        offending = [
            label for label, prob in scores.items() if prob >= self.threshold
        ]
        return len(offending) == 0, offending


# Helper factory
def get_toxicity_guard(
    *,
    threshold: float = 0.80,
    max_retries: int = 3,
) -> Guard:
    """Return a ready-to-use :class:`guardrails.Guard`."""
    return Guard(name='toxicity_guard').use(
        ToxicityDetector(
            threshold=threshold,
            max_retries=max_retries,
            on_fail=OnFailAction.EXCEPTION,
        ),
    )
