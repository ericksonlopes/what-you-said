import queue
import threading
import time
from typing import Callable, Dict, Optional

from src.config.logger import Logger

logger = Logger()


class TaskQueueService:
    """In-memory task queue with a background worker thread.

    This helps serialize heavy ingestion tasks to avoid concurrency issues
    and model/tokenizer borrow conflicts.
    """

    def __init__(self, num_workers: int = 1):
        self._queue: queue.Queue = queue.Queue()
        self._workers: list[threading.Thread] = []
        self._num_workers = num_workers
        self._should_stop = False

    def start(self):
        """Starts the background worker threads."""
        if self._workers:
            logger.warning(
                "TaskQueueService already started.", context={"where": "start"}
            )
            return

        self._should_stop = False
        for i in range(self._num_workers):
            t = threading.Thread(
                target=self._worker_loop, name="TaskQueueWorker-" + str(i), daemon=True
            )
            t.start()
            self._workers.append(t)
        logger.info(
            "TaskQueueService started",
            context={"num_workers": self._num_workers, "where": "start"},
        )

    def stop(self):
        """Signals workers to stop and waits for them to finish."""
        logger.info("Stopping TaskQueueService...", context="stop")
        self._should_stop = True

        # Add 'None' poison pills to wake up workers from block
        for _ in range(self._num_workers):
            self._queue.put(None)

        for t in self._workers:
            t.join(timeout=5.0)

        self._workers = []
        logger.info("TaskQueueService stopped", context={"where": "stop"})

    def enqueue(
        self,
        func: Callable,
        *args,
        task_title: Optional[str] = None,
        metadata: Optional[Dict] = None,
        **kwargs,
    ):
        """Adds a task to the queue."""
        self._queue.put((func, task_title, metadata, args, kwargs))
        logger.debug(
            "Task enqueued",
            context={
                "task_title": task_title or func.__name__,
                "queue_size": self._queue.qsize(),
                "where": "enqueue",
            },
        )

    def _worker_loop(self):
        """Infinite loop for the worker thread."""
        while not self._should_stop:
            try:
                item = self._queue.get(block=True, timeout=1.0)
                if item is None:
                    self._queue.task_done()
                    break

                func, task_title, metadata, args, kwargs = item
                display_title = task_title or func.__name__

                logger.info(
                    "Worker processing task",
                    context={"task": display_title, "where": "worker_loop"},
                )
                start_time = time.time()

                # Notification removed (WebSocket decommissioned)

                try:
                    func(*args, **kwargs)
                    duration = time.time() - start_time
                    logger.info(
                        "Task completed",
                        context={
                            "task": display_title,
                            "duration": round(duration, 2),
                            "where": "worker_loop",
                        },
                    )
                    # Notification removed (WebSocket decommissioned)

                except Exception as e:
                    logger.error(
                        "Error executing task",
                        context={
                            "task": display_title,
                            "error": str(e),
                            "where": "worker_loop",
                        },
                    )
                    # Notification removed (WebSocket decommissioned)
                finally:
                    self._queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(
                    "Unexpected error in TaskQueue worker loop",
                    context={"error": str(e), "where": "worker_loop"},
                )
                time.sleep(1.0)  # Avoid tight loop on repeated errors
