import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.realtime import realtime_events, submission_channel, task_channel


router = APIRouter()


@router.websocket("/ws/exams/{exam_id}/submissions/{submission_id}")
async def submission_events(websocket: WebSocket, exam_id: int, submission_id: int):
    """
    处理学生考试提交进度的实时WebSocket服务
    
    监听特定考试(exam_id)和提交实例(submission_id)下的实时事件(如答题状态更新)，
    向客户端主动推送新的事件，同时响应客户端的 ping 消息保活。
    """
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
    """
    处理AI任务状态推送的WebSocket服务
    
    客户端发送需监听的AI任务ID集合(task_ids)，可以实时接收这些任务的进度事件，
    例如状态变更为完成、失败更新等，并响应客户端的心跳检测。
    """
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