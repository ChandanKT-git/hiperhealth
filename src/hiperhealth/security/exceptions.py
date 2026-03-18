"""
title: Security exception hierarchy for hiperhealth.
"""

from __future__ import annotations


class SecurityError(Exception):
    """
    title: Base class for all security-related errors.
    """

    ...


class AuthenticationError(SecurityError):
    """
    title: Raised when no valid security context is provided.
    summary: |-
      This error indicates that a caller attempted to use a protected
      function without providing a valid ``SecurityContext``.
    """

    def __init__(self, message: str = 'Authentication required') -> None:
        super().__init__(message)


class AuthorizationError(SecurityError):
    """
    title: Raised when the caller lacks a required role or permission.
    """

    def __init__(self, message: str = 'Insufficient permissions') -> None:
        super().__init__(message)


class PatientAccessDeniedError(AuthorizationError):
    """
    title: Raised when the caller is not authorized for the given patient.
    """

    def __init__(
        self,
        *,
        user_id: str = '',
        patient_id: str = '',
    ) -> None:
        detail = (
            f'User {user_id!r} is not authorized to access '
            f'patient {patient_id!r}'
            if user_id and patient_id
            else 'Patient access denied'
        )
        super().__init__(detail)
