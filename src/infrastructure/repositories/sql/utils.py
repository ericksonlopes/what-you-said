from typing import Any, Optional
from uuid import UUID
from src.config.logger import Logger

logger = Logger()


def ensure_uuid(
    val: Any, error_msg: str = "Invalid UUID string provided"
) -> Optional[UUID]:
    """Ensures that the provided value is a UUID object or attempt to convert it if it's a string.

    Args:
        val: The value to ensure is a UUID.
        error_msg: The log message if conversion fails.

    Returns:
        Optional[UUID]: The converted UUID or None if conversion fails.
    """
    if val is None:
        return None

    if isinstance(val, UUID):
        return val

    if isinstance(val, str):
        try:
            return UUID(val)
        except ValueError:
            logger.warning(error_msg, context={"value": val})
            return None

    # If it's already an object but not a UUID or string, return as is (SQLAlchemy might handle it)
    return val
