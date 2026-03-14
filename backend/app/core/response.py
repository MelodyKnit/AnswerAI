from datetime import datetime, UTC
from uuid import uuid4


def success_response(data, message: str = "ok") -> dict:
    return {
        "code": 0,
        "message": message,
        "data": data,
        "request_id": f"req_{uuid4().hex[:12]}",
        "timestamp": datetime.now(UTC).isoformat(),
    }
