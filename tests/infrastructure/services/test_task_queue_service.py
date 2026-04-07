import time

import pytest

from src.infrastructure.services.task_queue_service import TaskQueueService


@pytest.mark.Dependencies
class TestTaskQueueService:
    def test_enqueue_and_process(self):
        svc = TaskQueueService(num_workers=1)
        svc.start()

        results = []

        def task(val):
            results.append(val)

        svc.enqueue(task, "success")

        # Wait for processing
        timeout = 5.0
        start = time.time()
        while not results and (time.time() - start < timeout):
            time.sleep(0.1)

        assert "success" in results
        svc.stop()

    def test_enqueue_multiple_tasks(self):
        svc = TaskQueueService(num_workers=2)
        svc.start()

        results = []

        def task(val):
            time.sleep(0.1)
            results.append(val)

        svc.enqueue(task, 1)
        svc.enqueue(task, 2)
        svc.enqueue(task, 3)

        # Wait for processing
        timeout = 5.0
        start = time.time()
        while len(results) < 3 and (time.time() - start < timeout):
            time.sleep(0.1)

        assert len(results) == 3
        assert set(results) == {1, 2, 3}
        svc.stop()

    def test_task_exception_does_not_stop_worker(self):
        svc = TaskQueueService(num_workers=1)
        svc.start()

        results = []

        def failing_task():
            raise RuntimeError("Fail")

        def success_task():
            results.append("ok")

        svc.enqueue(failing_task)
        svc.enqueue(success_task)

        # Wait for processing
        timeout = 5.0
        start = time.time()
        while not results and (time.time() - start < timeout):
            time.sleep(0.1)

        assert "ok" in results
        svc.stop()

    def test_start_already_started(self):
        svc = TaskQueueService(num_workers=1)
        svc.start()
        initial_workers = list(svc._workers)
        svc.start()
        assert svc._workers == initial_workers
        svc.stop()
