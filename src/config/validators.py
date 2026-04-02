import os
import sys
from typing import Optional


def docker_host_fallback(
    host: str, docker_names: set[str]
) -> str:
    """Fallback to localhost if docker service names are used on Windows/non-docker."""
    if (
        host in docker_names
        and sys.platform == "win32"
        and not os.path.exists("/.dockerenv")
    ):
        return "localhost"
    return host


def docker_host_fallback_optional(
    host: Optional[str], docker_names: set[str]
) -> Optional[str]:
    """Same as docker_host_fallback but accepts Optional[str]."""
    if host is None:
        return None
    return docker_host_fallback(host, docker_names)
