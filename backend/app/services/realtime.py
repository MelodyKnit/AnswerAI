from collections import defaultdict
from datetime import UTC, datetime
from threading import Lock
from uuid import uuid4


class RealtimeEventStore:
    def __init__(self) -> None:
        self._channels: dict[str, list[dict]] = defaultdict(list)
        self._sequences: dict[str, int] = defaultdict(int)
        self._lock = Lock()

    def publish(self, channel: str, event: str, data: dict) -> dict:
        with self._lock:
            self._sequences[channel] += 1
            payload = {
                "id": f"evt_{uuid4().hex[:12]}",
                "seq": self._sequences[channel],
                "event": event,
                "data": data,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            self._channels[channel].append(payload)
            self._channels[channel] = self._channels[channel][-200:]
            return payload

    def read(self, channel: str, after_seq: int = 0) -> list[dict]:
        with self._lock:
            return [item for item in self._channels.get(channel, []) if item["seq"] > after_seq]


def submission_channel(exam_id: int, submission_id: int) -> str:
    return f"submission:{exam_id}:{submission_id}"


def task_channel(task_id: str) -> str:
    return f"task:{task_id}"


realtime_events = RealtimeEventStore()