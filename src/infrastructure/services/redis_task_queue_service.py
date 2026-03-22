import pickle
import threading
import time
from typing import Callable, Dict, Optional

import redis
from src.config.logger import Logger
from src.config.settings import settings
from src.domain.interfaces.services.i_task_queue import ITaskQueue

logger = Logger()


class RedisTaskQueueService(ITaskQueue):
    """Redis-backed task queue with a background worker thread.

    This replaces the in-memory threading queue with a persistent Redis queue.
    """

    def __init__(self, queue_name: str = "wys_task_queue", num_workers: int = 1):
        self._redis = redis.Redis(
            host=settings.redis.host,
            port=settings.redis.port,
            db=settings.redis.db,
            password=settings.redis.password,
            decode_responses=False,  # Use False to handle pickled functions
        )
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
        """Serializes the task and pushes it to Redis."""
        task_data = {
            "func": pickle.dumps(func),
            "args": pickle.dumps(args),
            "kwargs": pickle.dumps(kwargs),
            "task_title": task_title,
            "metadata": metadata,
            "enqueued_at": time.time(),
        }
        self._redis.lpush(self._queue_name, pickle.dumps(task_data))
        logger.debug(
            "Task enqueued in Redis",
            context={
                "task_title": task_title or func.__name__,
                "queue": self._queue_name,
            },
        )

    def _worker_loop(self):
        while not self._should_stop:
            try:
                # Use blpop (blocking left pop) with timeout
                result = self._redis.brpop(self._queue_name, timeout=1)
                if result:
                    _, data_blob = result
                    task_data = pickle.loads(data_blob)

                    func = pickle.loads(task_data["func"])
                    args = pickle.loads(task_data["args"])
                    kwargs = pickle.loads(task_data["kwargs"])
                    task_title = task_data.get("task_title") or func.__name__

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
