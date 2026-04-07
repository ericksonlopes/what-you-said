import json
import threading
import time
from dataclasses import asdict, is_dataclass
from typing import Any, Callable, Dict, Optional, cast
from uuid import UUID

from src.config.logger import Logger
from src.domain.interfaces.services.i_task_queue import ITaskQueue
from src.infrastructure.connectors.redis_connector import RedisConnector

logger = Logger()


def _json_serial(obj):
    """JSON serializer for objects not serializable by default."""
    if isinstance(obj, UUID):
        return str(obj)
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


# Task function registry — maps string names to callable functions.
# Workers look up functions by name instead of deserializing pickled code.
_TASK_REGISTRY: Dict[str, Callable] = {}


def register_task(name: str, func: Callable) -> None:
    """Register a task function by name."""
    _TASK_REGISTRY[name] = func


def get_task_registry() -> Dict[str, Callable]:
    """Return the current task registry (useful for testing)."""
    return _TASK_REGISTRY


class RedisTaskQueueService(ITaskQueue):
    """Redis-backed task queue with a background worker thread.

    Uses JSON serialization with a task registry instead of pickle
    to avoid remote code execution vulnerabilities.
    """

    def __init__(self, queue_name: str = "wys_task_queue", num_workers: int = 1):
        self._redis = RedisConnector.get_client(decode_responses=False)
        self._queue_name = queue_name
        self._workers: list[threading.Thread] = []
        self._num_workers = num_workers
        self._should_stop = False

    def start(self):
        if self._workers:
            logger.warning(
                "RedisTaskQueueService already started.", context={"where": "start"}
            )
            return

        self._should_stop = False
        for i in range(self._num_workers):
            t = threading.Thread(
                target=self._worker_loop, name=f"RedisTaskWorker-{i}", daemon=True
            )
            t.start()
            self._workers.append(t)
        logger.info(
            "RedisTaskQueueService started",
            context={"num_workers": self._num_workers, "queue": self._queue_name},
        )

    def stop(self):
        logger.info("Stopping RedisTaskQueueService...", context="stop")
        self._should_stop = True
        for t in self._workers:
            t.join(timeout=5.0)
        self._workers = []

    def enqueue(
        self,
        func: Callable,
        *args,
        task_title: Optional[str] = None,
        metadata: Optional[Dict] = None,
        **kwargs,
    ):
        """Serializes the task as JSON and pushes it to Redis."""
        # Resolve function name from registry or use __name__
        func_name = None
        for name, registered_func in _TASK_REGISTRY.items():
            if registered_func is func:
                func_name = name
                break

        if func_name is None:
            # Auto-register if not found (backward compatibility)
            func_name = func.__qualname__
            register_task(func_name, func)

        task_data = {
            "func_name": func_name,
            "args": list(args),
            "kwargs": kwargs,
            "task_title": task_title,
            "metadata": metadata,
            "enqueued_at": time.time(),
        }
        payload = json.dumps(task_data, default=_json_serial).encode("utf-8")
        self._redis.lpush(self._queue_name, payload)
        logger.debug(
            "Task enqueued in Redis",
            context={
                "task_title": task_title or func_name,
                "queue": self._queue_name,
            },
        )

    def peek_queue(self, limit: int = 50) -> list[dict]:
        """Fetch pending tasks from the Redis queue without removing them.

        Returns a list of task data dictionaries.
        """
        try:
            # Fetch raw JSON payloads from the list
            # Redis list is LPUSH (front is index 0)
            raw_tasks = cast(list[bytes], self._redis.lrange(self._queue_name, 0, limit - 1))
            tasks = []
            for payload in raw_tasks:
                try:
                    task_data = json.loads(payload.decode("utf-8"))
                    tasks.append(task_data)
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    logger.warning(
                        "Failed to decode task from Redis queue",
                        context={"error": str(e)},
                    )
            return tasks
        except Exception as e:
            logger.error("Error peeking at Redis queue", context={"error": str(e)})
            return []

    def clear_queue(self):
        """Remove all pending tasks from the Redis list."""
        try:
            self._redis.delete(self._queue_name)
            logger.info("Redis task queue cleared", context={"queue": self._queue_name})
        except Exception as e:
            logger.error("Failed to clear Redis queue", context={"error": str(e)})

    def remove_task_by_index(self, index: int) -> Optional[dict]:
        """Remove a specific task from the Redis list by its index and return its data."""
        try:
            # 1. Get the payload at the specified index
            payload = cast(Optional[bytes], self._redis.lindex(self._queue_name, index))
            if payload:
                # 2. Remove exactly ONE instance of this payload
                self._redis.lrem(self._queue_name, 1, cast(Any, payload))
                logger.info(
                    "Task removed from Redis queue",
                    context={"index": index, "queue": self._queue_name},
                )
                # 3. Return the deserialized task data
                try:
                    return json.loads(payload.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    return None
            return None
        except Exception as e:
            logger.error(
                "Failed to remove task from Redis queue",
                context={"index": index, "error": str(e)},
            )
            return None

    def _deserialize_args(self, raw_args: list) -> list:
        """Reconstruct dataclass command objects from serialized dicts."""
        from src.application.dtos.commands.ingest_file_command import IngestFileCommand
        from src.application.dtos.commands.ingest_youtube_command import (
            IngestYoutubeCommand,
        )
        from src.application.dtos.commands.ingest_web_command import IngestWebCommand
        from src.application.dtos.commands.process_audio_command import (
            ProcessAudioCommand,
        )
        from src.application.dtos.commands.ingest_diarization_command import (
            IngestDiarizationCommand,
        )

        command_classes = {
            "IngestFileCommand": IngestFileCommand,
            "IngestYoutubeCommand": IngestYoutubeCommand,
            "IngestWebCommand": IngestWebCommand,
            "ProcessAudioCommand": ProcessAudioCommand,
            "IngestDiarizationCommand": IngestDiarizationCommand,
        }

        result = []
        for arg in raw_args:
            if isinstance(arg, dict) and "__dataclass__" not in arg:
                # Try to detect which command class this dict represents
                reconstructed = False
                for cls_name, cls in command_classes.items():
                    try:
                        obj = cls(**arg)
                        result.append(obj)
                        reconstructed = True
                        break
                    except (TypeError, ValueError):
                        continue
                if not reconstructed:
                    result.append(arg)
            else:
                result.append(arg)
        return result

    def _worker_loop(self):
        while not self._should_stop:
            try:
                result = self._redis.brpop(self._queue_name, timeout=1)
                if result:
                    _, data_blob = result
                    task_data = json.loads(data_blob.decode("utf-8"))

                    func_name = task_data["func_name"]
                    raw_args = task_data.get("args", [])
                    kwargs = task_data.get("kwargs", {})
                    task_title = task_data.get("task_title") or func_name

                    func = _TASK_REGISTRY.get(func_name)
                    if func is None:
                        logger.error(
                            "Unknown task function",
                            context={
                                "func_name": func_name,
                                "registered": list(_TASK_REGISTRY.keys()),
                            },
                        )
                        continue

                    args = self._deserialize_args(raw_args)

                    logger.info(
                        "Redis worker processing task",
                        context={"task": task_title, "where": "worker_loop"},
                    )

                    start_time = time.time()
                    try:
                        func(*args, **kwargs)
                        duration = time.time() - start_time
                        logger.info(
                            "Redis task completed",
                            context={
                                "task": task_title,
                                "duration": round(duration, 2),
                            },
                        )
                    except Exception as e:
                        logger.error(
                            "Error executing Redis task",
                            context={"task": task_title, "error": str(e)},
                        )
            except Exception as e:
                if not self._should_stop:
                    logger.error(
                        "Unexpected error in Redis worker loop",
                        context={"error": str(e)},
                    )
                    time.sleep(1.0)
