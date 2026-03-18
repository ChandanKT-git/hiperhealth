"""
title: Security & access-control primitives for hiperhealth.
summary: |-
  Re-exports from sub-modules for convenient top-level imports::

      from hiperhealth.security import SecurityContext, check_authenticated
"""

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

__all__ = [
    'AuthenticationError',
    'AuthorizationError',
    'PatientAccessDeniedError',
    'Role',
    'SecurityContext',
    'SecurityError',
    'check_authenticated',
    'check_patient_access',
    'check_permission',
    'check_role',
]
