import json
import time
from unittest.mock import MagicMock, patch

import pytest
from src.infrastructure.services.redis_task_queue_service import (
    RedisTaskQueueService,
    register_task,
    get_task_registry,
    _json_serial,
)


# Dummy functions for tests (must be module-level)
def dummy_func(a, b):
    return a + b


def task_func(val):
    global _test_results
    _test_results.append(val)


def failing_func():
    raise ValueError("Expected error")


def success_func():
    global _test_results
    _test_results.append("ok")


_test_results = []


@pytest.mark.Dependencies
class TestRedisTaskQueueService:
    @pytest.fixture(autouse=True)
    def clear_results(self):
        global _test_results
        _test_results = []
        # Register test functions
        register_task("dummy_func", dummy_func)
        register_task("task_func", task_func)
        register_task("failing_func", failing_func)
        register_task("success_func", success_func)
        yield
        _test_results = []

    @patch("src.infrastructure.redis_connector.RedisConnector.get_client")
    def test_enqueue_pushes_to_redis(self, mock_get_client):
        mock_redis = MagicMock()
        mock_get_client.return_value = mock_redis

        svc = RedisTaskQueueService(queue_name="test_queue")

        svc.enqueue(dummy_func, 1, 2, task_title="Test Task", metadata={"key": "val"})

        # Verify lpush was called
        assert mock_redis.lpush.called
        args, _ = mock_redis.lpush.call_args
        assert args[0] == "test_queue"

        # Verify JSON data
        pushed_data = json.loads(args[1].decode("utf-8"))
        assert pushed_data["task_title"] == "Test Task"
        assert pushed_data["metadata"] == {"key": "val"}
        assert pushed_data["func_name"] == "dummy_func"
        assert pushed_data["args"] == [1, 2]

    @patch("src.infrastructure.redis_connector.RedisConnector.get_client")
    def test_worker_processes_task(self, mock_get_client):
        mock_redis = MagicMock()
        mock_get_client.return_value = mock_redis

        svc = RedisTaskQueueService(queue_name="test_queue", num_workers=1)

        # Prepare task data for brpop
        task_data = {
            "func_name": "task_func",
            "args": ["success"],
            "kwargs": {},
            "task_title": "Worker Task",
        }
        data_blob = json.dumps(task_data).encode("utf-8")

        # Mock brpop to return the task once, then None (timeout)
        mock_redis.brpop.side_effect = [("test_queue", data_blob), None]

        svc.start()

        # Wait a bit for worker to process
        timeout = 2.0
        start = time.time()
        while not _test_results and (time.time() - start < timeout):
            time.sleep(0.1)

        svc.stop()

        assert "success" in _test_results
        assert mock_redis.brpop.called

    @patch("src.infrastructure.redis_connector.RedisConnector.get_client")
    def test_worker_handles_exception(self, mock_get_client):
        mock_redis = MagicMock()
        mock_get_client.return_value = mock_redis

        svc = RedisTaskQueueService(queue_name="test_queue", num_workers=1)

        task_data = {
            "func_name": "failing_func",
            "args": [],
            "kwargs": {},
        }
        data_blob = json.dumps(task_data).encode("utf-8")

        success_data = {
            "func_name": "success_func",
            "args": [],
            "kwargs": {},
        }
        success_blob = json.dumps(success_data).encode("utf-8")

        mock_redis.brpop.side_effect = [
            ("test_queue", data_blob),
            ("test_queue", success_blob),
            None,
        ]

        svc.start()

        timeout = 2.0
        start = time.time()
        while not _test_results and (time.time() - start < timeout):
            time.sleep(0.1)

        svc.stop()

        assert "ok" in _test_results
