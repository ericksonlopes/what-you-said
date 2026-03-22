from typing import Any, Optional


class ServiceRegistry:
    _instance = None
    _services: dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ServiceRegistry, cls).__new__(cls)
        return cls._instance

    @classmethod
    def register(cls, name: str, service: Any):
        cls._services[name] = service

    @classmethod
    def get(cls, name: str) -> Optional[Any]:
        return cls._services.get(name)


registry = ServiceRegistry()

# Registering services for worker access
# Note: Dependencies are mostly resolved in dependencies.py,
# but workers use the registry to get the app state.
