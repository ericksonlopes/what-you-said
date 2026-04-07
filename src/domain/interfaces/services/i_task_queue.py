from abc import ABC, abstractmethod
from typing import Callable, Dict, Optional


class ITaskQueue(ABC):
    """Interface for a task queue that can execute functions in the background."""

    @abstractmethod
    def start(self):
        """Starts the worker(s)."""
        pass

    @abstractmethod
    def stop(self):
        """Stops the worker(s)."""
        pass

    @abstractmethod
    def enqueue(
        self,
        func: Callable,
        *args,
        task_title: Optional[str] = None,
        metadata: Optional[Dict] = None,
        **kwargs,
    ):
        """Adds a task to the queue."""
        pass

    @abstractmethod
    def peek_queue(self, limit: int = 50) -> list[dict]:
        """Fetch pending tasks from the queue without removing them."""
        pass

    @abstractmethod
    def clear_queue(self):
        """Remove all pending tasks from the queue."""
        pass

    @abstractmethod
    def remove_task_by_index(self, index: int) -> Optional[dict]:
        """Remove a specific task from the queue by its index and return its data."""
        pass
