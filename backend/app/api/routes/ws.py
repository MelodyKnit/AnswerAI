import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.realtime import realtime_events, submission_channel, task_channel


router = APIRouter()


@router.websocket("/ws/exams/{exam_id}/submissions/{submission_id}")
async def submission_events(websocket: WebSocket, exam_id: int, submission_id: int):
    await websocket.accept()
    channel = submission_channel(exam_id, submission_id)
    last_seq = 0
    await websocket.send_json({"event": "subscribed", "data": {"channel": channel}})

    try:
        while True:
            events = realtime_events.read(channel, last_seq)
            for event in events:
                await websocket.send_json(event)
                last_seq = event["seq"]
            try:
                message = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)
                if message.get("event") == "ping":
                    await websocket.send_json({"event": "pong", "data": {"channel": channel}})
            except TimeoutError:
                continue
    except WebSocketDisconnect:
        return


@router.websocket("/ws/ai-tasks")
async def ai_task_events(websocket: WebSocket):
    await websocket.accept()
    task_ids: list[str] = []
    last_sequences: dict[str, int] = {}
    await websocket.send_json({"event": "connected", "data": {"message": "send {'task_ids': [...]} to subscribe"}})

    try:
        while True:
            for task_id in task_ids:
                channel = task_channel(task_id)
                events = realtime_events.read(channel, last_sequences.get(task_id, 0))
                for event in events:
                    await websocket.send_json(event)
                    last_sequences[task_id] = event["seq"]
            try:
                message = await asyncio.wait_for(websocket.receive_json(), timeout=1.0)
                if "task_ids" in message:
                    task_ids = [str(item) for item in message.get("task_ids", [])]
                    for task_id in task_ids:
                        last_sequences.setdefault(task_id, 0)
                    await websocket.send_json({"event": "subscribed", "data": {"task_ids": task_ids}})
                elif message.get("event") == "ping":
                    await websocket.send_json({"event": "pong", "data": {"task_ids": task_ids}})
            except TimeoutError:
                continue
    except WebSocketDisconnect:
        return