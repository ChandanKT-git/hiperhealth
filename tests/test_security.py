"""
title: Unit tests for the hiperhealth.security module.
"""

from __future__ import annotations

import pytest

from hiperhealth.security.context import Role, SecurityContext
from hiperhealth.security.exceptions import (
    AuthenticationError,
    AuthorizationError,
    PatientAccessDeniedError,
    SecurityError,
)
from hiperhealth.security.guards import (
    check_authenticated,
    check_patient_access,
    check_permission,
    check_role,
)

# ── SecurityContext ──────────────────────────────────────────────────


class TestSecurityContext:
    def test_create_minimal(self) -> None:
        ctx = SecurityContext(user_id='u1', role=Role.PHYSICIAN)
        assert ctx.user_id == 'u1'
        assert ctx.role == Role.PHYSICIAN
        assert ctx.patient_id is None
        assert ctx.permissions == frozenset()

    def test_create_full(self) -> None:
        ctx = SecurityContext(
            user_id='u2',
            role=Role.ADMIN,
            patient_id='p1',
            session_id='s1',
            permissions=frozenset({'read:reports', 'write:deidentify'}),
        )
        assert ctx.patient_id == 'p1'
        assert ctx.session_id == 's1'
        assert ctx.has_permission('read:reports')
        assert not ctx.has_permission('delete:all')

    def test_has_role(self) -> None:
        ctx = SecurityContext(user_id='u1', role=Role.RESEARCHER)
        assert ctx.has_role(Role.RESEARCHER)
        assert not ctx.has_role(Role.ADMIN)

    def test_role_enum_values(self) -> None:
        assert Role.PHYSICIAN.value == 'physician'
        assert Role.RESEARCHER.value == 'researcher'
        assert Role.ADMIN.value == 'admin'
        assert Role.PATIENT.value == 'patient'


# ── Exception Hierarchy ──────────────────────────────────────────────


class TestExceptions:
    def test_authentication_error_is_security_error(self) -> None:
        assert issubclass(AuthenticationError, SecurityError)

    def test_authorization_error_is_security_error(self) -> None:
        assert issubclass(AuthorizationError, SecurityError)

    def test_patient_access_denied_is_authorization_error(self) -> None:
        assert issubclass(PatientAccessDeniedError, AuthorizationError)

    def test_authentication_error_default_message(self) -> None:
        err = AuthenticationError()
        assert 'Authentication required' in str(err)

    def test_authorization_error_default_message(self) -> None:
        err = AuthorizationError()
        assert 'Insufficient permissions' in str(err)

    def test_patient_access_denied_with_details(self) -> None:
        err = PatientAccessDeniedError(user_id='u1', patient_id='p1')
        assert 'u1' in str(err)
        assert 'p1' in str(err)

    def test_patient_access_denied_without_details(self) -> None:
        err = PatientAccessDeniedError()
        assert 'Patient access denied' in str(err)


# ── Guard Functions ──────────────────────────────────────────────────


class TestCheckAuthenticated:
    def test_none_without_enforcement_passes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv('HIPERHEALTH_REQUIRE_AUTH', raising=False)
        check_authenticated(None)  # should not raise

    def test_none_with_enforcement_raises(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv('HIPERHEALTH_REQUIRE_AUTH', 'true')
        with pytest.raises(AuthenticationError):
            check_authenticated(None)

    def test_valid_context_with_enforcement_passes(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv('HIPERHEALTH_REQUIRE_AUTH', 'true')
        ctx = SecurityContext(user_id='u1', role=Role.PHYSICIAN)
        check_authenticated(ctx)  # should not raise

    @pytest.mark.parametrize('value', ['1', 'True', 'YES', 'true'])
    def test_enforcement_truthy_values(
        self, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        monkeypatch.setenv('HIPERHEALTH_REQUIRE_AUTH', value)
        with pytest.raises(AuthenticationError):
            check_authenticated(None)

    @pytest.mark.parametrize('value', ['0', 'false', 'no', ''])
    def test_enforcement_falsy_values(
        self, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        monkeypatch.setenv('HIPERHEALTH_REQUIRE_AUTH', value)
        check_authenticated(None)  # should not raise


class TestCheckRole:
    def test_none_context_passes(self) -> None:
        check_role(None, Role.PHYSICIAN)  # should not raise

    def test_matching_role_passes(self) -> None:
        ctx = SecurityContext(user_id='u1', role=Role.PHYSICIAN)
        check_role(ctx, Role.PHYSICIAN)  # should not raise

    def test_wrong_role_raises(self) -> None:
        ctx = SecurityContext(user_id='u1', role=Role.PATIENT)
        with pytest.raises(AuthorizationError, match='physician'):
            check_role(ctx, Role.PHYSICIAN)


class TestCheckPermission:
    def test_none_context_passes(self) -> None:
        check_permission(None, 'read:reports')  # should not raise

    def test_has_permission_passes(self) -> None:
        ctx = SecurityContext(
            user_id='u1',
            role=Role.PHYSICIAN,
            permissions=frozenset({'read:reports'}),
        )
        check_permission(ctx, 'read:reports')  # should not raise

    def test_missing_permission_raises(self) -> None:
        ctx = SecurityContext(
            user_id='u1',
            role=Role.PHYSICIAN,
            permissions=frozenset({'read:reports'}),
        )
        with pytest.raises(AuthorizationError, match='write:deidentify'):
            check_permission(ctx, 'write:deidentify')


class TestCheckPatientAccess:
    def test_none_context_passes(self) -> None:
        check_patient_access(None, 'p1')  # should not raise

    def test_admin_bypasses_check(self) -> None:
        ctx = SecurityContext(
            user_id='u1', role=Role.ADMIN, patient_id='p_other'
        )
        check_patient_access(ctx, 'p1')  # admin can access any patient

    def test_matching_patient_passes(self) -> None:
        ctx = SecurityContext(
            user_id='u1', role=Role.PHYSICIAN, patient_id='p1'
        )
        check_patient_access(ctx, 'p1')  # should not raise

    def test_wrong_patient_raises(self) -> None:
        ctx = SecurityContext(
            user_id='u1', role=Role.PHYSICIAN, patient_id='p2'
        )
        with pytest.raises(PatientAccessDeniedError):
            check_patient_access(ctx, 'p1')
