"""
title: Security context model for hiperhealth.
summary: |-
  Provides a ``SecurityContext`` that callers attach to library
  operations so that identity, role, and permissions can be verified
  before processing sensitive healthcare data.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Role(str, Enum):
    """
    title: Supported user roles.
    """

    PHYSICIAN = 'physician'
    RESEARCHER = 'researcher'
    ADMIN = 'admin'
    PATIENT = 'patient'


class SecurityContext(BaseModel):
    """
    title: Immutable security context attached to every protected call.
    attributes:
      user_id:
        type: str
        description: Authenticated caller identity.
      role:
        type: Role
        description: Caller role.
      patient_id:
        type: str | None
        description: >-
          The patient being accessed.  Required for patient-scoped operations.
      session_id:
        type: str | None
        description: Optional trace / session correlation id.
      permissions:
        type: frozenset[str]
        description: >-
          Fine-grained permission strings, e.g. ``read:reports``,
          ``write:diagnosis``.
    """

    user_id: str
    role: Role
    patient_id: str | None = None
    session_id: str | None = None
    permissions: frozenset[str] = Field(default_factory=frozenset)

    model_config = ConfigDict(frozen=True)

    def has_permission(self, permission: str) -> bool:
        """
        title: Check whether this context grants a specific permission.
        parameters:
          permission:
            type: str
            description: Value for permission.
        returns:
          type: bool
          description: Return value.
        """
        return permission in self.permissions

    def has_role(self, role: Role) -> bool:
        """
        title: Check whether this context matches a required role.
        parameters:
          role:
            type: Role
            description: Value for role.
        returns:
          type: bool
          description: Return value.
        """
        return self.role == role
