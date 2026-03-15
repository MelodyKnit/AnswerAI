from datetime import datetime, UTC
from uuid import uuid4


def success_response(data, message: str = "ok") -> dict:
    """
    处理 success response 请求并返回结果。
    """
    return {
        "code": 0,
        "message": message,
        "data": data,
        "request_id": f"req_{uuid4().hex[:12]}",
        "timestamp": datetime.now(UTC).isoformat(),
    }


def error_response(message: str = "error", code: int = 1, data=None) -> dict:
    """
    处理 error response 请求并返回结果。
    """
    return {
        "code": code,
        "message": message,
        "data": data,
        "request_id": f"req_{uuid4().hex[:12]}",
        "timestamp": datetime.now(UTC).isoformat(),
    }
