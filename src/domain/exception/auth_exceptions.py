class AuthDomainError(Exception):
    """Base class for all domain-specific authentication errors."""

    pass


class InvalidStateError(AuthDomainError):
    """Raised when the OAuth state parameter is invalid or missing."""

    pass


class GoogleAuthError(AuthDomainError):
    """Raised when an error occurs during the Google OAuth process."""

    pass


class UserNotCreatedError(AuthDomainError):
    """Raised when the user entity cannot be created or retrieved after successful auth."""

    pass


class UserNotFoundError(AuthDomainError):
    """Raised when a user is not found during session verification."""

    pass
