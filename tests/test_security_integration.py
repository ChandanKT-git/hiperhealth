"""
title: Integration tests verifying security guards at skill entry points.
summary: |-
  These tests check that when ``HIPERHEALTH_REQUIRE_AUTH=true`` the
  core skill functions reject unauthenticated callers, and that
  correct contexts are accepted.
"""

from __future__ import annotations

import io

from unittest.mock import MagicMock

import pytest

from hiperhealth.security.context import Role, SecurityContext
from hiperhealth.security.exceptions import (
    AuthenticationError,
    AuthorizationError,
)


def _physician_ctx(
    *,
    permissions: frozenset[str] = frozenset(),
) -> SecurityContext:
    return SecurityContext(
        user_id='dr-test',
        role=Role.PHYSICIAN,
        patient_id='patient-1',
        permissions=permissions,
    )


# ── MedicalReportFileExtractor ────────────────────────────────────


class TestMedicalReportExtractorSecurity:
    def test_extract_report_data_rejects_no_ctx_when_enforced(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv('HIPERHEALTH_REQUIRE_AUTH', 'true')
        from hiperhealth.skills.extraction.medical_reports import (
            MedicalReportFileExtractor,
        )

        extractor = MedicalReportFileExtractor()
        with pytest.raises(AuthenticationError):
            extractor.extract_report_data(io.BytesIO(b'dummy'))

    def test_extract_report_data_rejects_wrong_permission(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv('HIPERHEALTH_REQUIRE_AUTH', raising=False)
        from hiperhealth.skills.extraction.medical_reports import (
            MedicalReportFileExtractor,
        )

        ctx = _physician_ctx(permissions=frozenset({'write:deidentify'}))
        extractor = MedicalReportFileExtractor()
        with pytest.raises(AuthorizationError, match='read:reports'):
            extractor.extract_report_data(
                io.BytesIO(b'dummy'), security_context=ctx
            )

    def test_extract_text_rejects_no_ctx_when_enforced(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv('HIPERHEALTH_REQUIRE_AUTH', 'true')
        from hiperhealth.skills.extraction.medical_reports import (
            MedicalReportFileExtractor,
        )

        extractor = MedicalReportFileExtractor()
        with pytest.raises(AuthenticationError):
            extractor.extract_text(io.BytesIO(b'dummy'))


# ── WearableDataFileExtractor ────────────────────────────────────


class TestWearableDataExtractorSecurity:
    def test_rejects_no_ctx_when_enforced(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv('HIPERHEALTH_REQUIRE_AUTH', 'true')
        from hiperhealth.skills.extraction.wearable import (
            WearableDataFileExtractor,
        )

        extractor = WearableDataFileExtractor()
        with pytest.raises(AuthenticationError):
            extractor.extract_wearable_data(io.BytesIO(b'{}'))

    def test_rejects_wrong_permission(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv('HIPERHEALTH_REQUIRE_AUTH', raising=False)
        from hiperhealth.skills.extraction.wearable import (
            WearableDataFileExtractor,
        )

        ctx = _physician_ctx(permissions=frozenset({'read:reports'}))
        extractor = WearableDataFileExtractor()
        with pytest.raises(AuthorizationError, match='read:wearables'):
            extractor.extract_wearable_data(
                io.BytesIO(b'{}'), security_context=ctx
            )


# ── Deidentifier ─────────────────────────────────────────────────


class TestDeidentifierSecurity:
    def test_deidentify_rejects_no_ctx_when_enforced(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv('HIPERHEALTH_REQUIRE_AUTH', 'true')

        import hiperhealth.skills.privacy.deidentifier as deid_mod

        # Patch out heavy Presidio engines
        monkeypatch.setattr(deid_mod, 'AnalyzerEngine', lambda: MagicMock())
        monkeypatch.setattr(deid_mod, 'AnonymizerEngine', lambda: MagicMock())

        deid = deid_mod.Deidentifier()
        with pytest.raises(AuthenticationError):
            deid.deidentify('some text')

    def test_deidentify_patient_record_rejects_no_ctx(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv('HIPERHEALTH_REQUIRE_AUTH', 'true')

        import hiperhealth.skills.privacy.deidentifier as deid_mod

        monkeypatch.setattr(deid_mod, 'AnalyzerEngine', lambda: MagicMock())
        monkeypatch.setattr(deid_mod, 'AnonymizerEngine', lambda: MagicMock())

        deid = deid_mod.Deidentifier()
        with pytest.raises(AuthenticationError):
            deid_mod.deidentify_patient_record({'symptoms': 'test'}, deid)


# ── Diagnostics ──────────────────────────────────────────────────


class TestDiagnosticsSecurity:
    def test_differential_rejects_no_ctx_when_enforced(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv('HIPERHEALTH_REQUIRE_AUTH', 'true')
        from hiperhealth.skills.diagnostics.core import differential

        with pytest.raises(AuthenticationError):
            differential({'age': 30})

    def test_exams_rejects_no_ctx_when_enforced(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv('HIPERHEALTH_REQUIRE_AUTH', 'true')
        from hiperhealth.skills.diagnostics.core import exams

        with pytest.raises(AuthenticationError):
            exams(['flu'])

    def test_differential_rejects_wrong_permission(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv('HIPERHEALTH_REQUIRE_AUTH', raising=False)
        from hiperhealth.skills.diagnostics.core import differential

        ctx = _physician_ctx(permissions=frozenset({'write:deidentify'}))
        with pytest.raises(AuthorizationError, match='read:diagnosis'):
            differential({'age': 30}, security_context=ctx)


# ── Default Mode (enforcement off) ──────────────────────────────


class TestDefaultModeAllowsNoContext:
    def test_medical_report_no_ctx_allowed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv('HIPERHEALTH_REQUIRE_AUTH', raising=False)
        from hiperhealth.skills.extraction.medical_reports import (
            MedicalReportFileExtractor,
        )

        extractor = MedicalReportFileExtractor()
        # Will fail at file validation (not auth) — that's expected
        with pytest.raises(FileNotFoundError):
            extractor.extract_report_data(io.BytesIO(b''))

    def test_wearable_no_ctx_allowed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv('HIPERHEALTH_REQUIRE_AUTH', raising=False)
        from hiperhealth.skills.extraction.wearable import (
            WearableDataFileExtractor,
        )

        extractor = WearableDataFileExtractor()
        # Will fail at validation (not auth)
        with pytest.raises(Exception):
            extractor.extract_wearable_data(io.BytesIO(b''))
