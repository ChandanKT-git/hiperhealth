"""
title: Guard functions for verifying security context.
summary: |-
  Provides explicit guard functions that skills call at the top of
  protected methods.  Enforcement is controlled by the
  ``HIPERHEALTH_REQUIRE_AUTH`` environment variable (default ``false``).
"""

from __future__ import annotations

import os

from hiperhealth.security.context import Role, SecurityContext
from hiperhealth.security.exceptions import (
    AuthenticationError,
    AuthorizationError,
    PatientAccessDeniedError,
)


def _is_enforcement_enabled() -> bool:
    """
    title: Return True when mandatory auth enforcement is turned on.
    returns:
      type: bool
      description: Return value.
    """
    return os.getenv('HIPERHEALTH_REQUIRE_AUTH', 'false').lower() in (
        '1',
        'true',
        'yes',
    )


def check_authenticated(ctx: SecurityContext | None) -> None:
    """
    title: Verify a non-None security context is present.
    summary: |-
      When enforcement is disabled (default) and *ctx* is ``None``,
      the call is silently allowed for backward compatibility.
    parameters:
      ctx:
        type: SecurityContext | None
        description: Value for ctx.
    """
    if ctx is None and _is_enforcement_enabled():
        raise AuthenticationError(
            'A SecurityContext is required when '
            'HIPERHEALTH_REQUIRE_AUTH is enabled'
        )


def check_role(ctx: SecurityContext | None, required_role: Role) -> None:
    """
    title: Verify the context's role matches the required role.
    parameters:
      ctx:
        type: SecurityContext | None
        description: Value for ctx.
      required_role:
        type: Role
        description: Value for required_role.
    """
    if ctx is None:
        return
    if not ctx.has_role(required_role):
        raise AuthorizationError(
            f'Role {required_role.value!r} required, got {ctx.role.value!r}'
        )


def check_permission(ctx: SecurityContext | None, permission: str) -> None:
    """
    title: Verify the context grants a specific permission.
    parameters:
      ctx:
        type: SecurityContext | None
        description: Value for ctx.
      permission:
        type: str
        description: Value for permission.
    """
    if ctx is None:
        return
    if not ctx.has_permission(permission):
        raise AuthorizationError(f'Permission {permission!r} required')


def check_patient_access(ctx: SecurityContext | None, patient_id: str) -> None:
    """
    title: Verify the caller is authorized for a specific patient.
    summary: |-
      Admins bypass this check.  For other roles the context's
      ``patient_id`` must match the requested *patient_id*.
    parameters:
      ctx:
        type: SecurityContext | None
        description: Value for ctx.
      patient_id:
        type: str
        description: Value for patient_id.
    """
    if ctx is None:
        return
    # Admins can access any patient.
    if ctx.role == Role.ADMIN:
        return
    if ctx.patient_id != patient_id:
        raise PatientAccessDeniedError(
            user_id=ctx.user_id, patient_id=patient_id
        )
