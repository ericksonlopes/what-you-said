import json

from src.infrastructure.connectors.redis_connector import RedisConnector


def peek_queue(queue_name="wys_task_queue"):
    r = RedisConnector.get_client(decode_responses=False)

    items = r.lrange(queue_name, 0, -1)
    print(f"--- Queue: {queue_name} ({len(items)} items) ---")

    for i, item in enumerate(items):
        try:
            data = json.loads(item.decode("utf-8"))
            task_title = data.get("task_title", "Unknown")
            enqueued_at = data.get("enqueued_at", "Unknown")

            print(f"[{i}] Task: {task_title}")
            print(f"    Enqueued at: {enqueued_at}")
            if "metadata" in data and data["metadata"]:
                print(f"    Metadata: {data['metadata']}")

        except Exception as e:
            print(f"[{i}] Error decoding item: {e}")


if __name__ == "__main__":
    peek_queue()
