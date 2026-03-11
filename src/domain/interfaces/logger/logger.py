from abc import ABC, abstractmethod
from typing import Optional, Dict


class ILogger(ABC):

    @abstractmethod
    def _is_allowed(self, level_name: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def info(self, message: str, context: Optional[Dict] = None) -> None:
        raise NotImplementedError

    @abstractmethod
    def debug(self, message: str, context: Optional[Dict] = None) -> None:
        raise NotImplementedError

    @abstractmethod
    def warning(self, message: str, context: Optional[Dict] = None) -> None:
        raise NotImplementedError

    @abstractmethod
    def error(self, error: Exception, context: Optional[Dict] = None) -> None:
        raise NotImplementedError

    @abstractmethod
    def critical(self, message: str, context: Optional[Dict] = None) -> None:
        raise NotImplementedError
