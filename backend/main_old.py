from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import asyncio
from typing import Dict, List, Optional

app = FastAPI(
    title="知识库检索工具API",
    description="Web版知识库检索工具，类似Trae执行Skill的方式",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 存储活动的WebSocket连接
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_personal_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(message)

    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            await connection.send_json(message)

manager = ConnectionManager()

# 定义数据模型
class QueryRequest(BaseModel):
    question: str
    client_id: str

class Message(BaseModel):
    type: str  # message, step, tool_call, result, source
    content: str
    data: Optional[dict] = None

# API路由
@app.post("/api/query")
async def query(request: QueryRequest):
    # 这里将启动检索流程，暂时返回模拟数据
    await manager.send_personal_message({
        "type": "step",
        "content": "开始处理查询: " + request.question,
        "data": {"step": 1, "total_steps": 7}
    }, request.client_id)
    
    # 模拟处理过程
    await asyncio.sleep(1)
    await manager.send_personal_message({
        "type": "step",
        "content": "解析用户问题，提取关键词",
        "data": {"step": 2, "total_steps": 7}
    }, request.client_id)
    
    await asyncio.sleep(1)
    await manager.send_personal_message({
        "type": "step",
        "content": "读取知识库索引文件",
        "data": {"step": 3, "total_steps": 7}
    }, request.client_id)
    
    await asyncio.sleep(1)
    await manager.send_personal_message({
        "type": "step",
        "content": "定位相关文件",
        "data": {"step": 4, "total_steps": 7}
    }, request.client_id)
    
    await asyncio.sleep(1)
    await manager.send_personal_message({
        "type": "step",
        "content": "执行渐进式检索",
        "data": {"step": 5, "total_steps": 7}
    }, request.client_id)
    
    await asyncio.sleep(1)
    await manager.send_personal_message({
        "type": "step",
        "content": "分析检索结果",
        "data": {"step": 6, "total_steps": 7}
    }, request.client_id)
    
    await asyncio.sleep(1)
    await manager.send_personal_message({
        "type": "result",
        "content": "这是一个模拟的回答结果。在实际实现中，这里将返回基于检索结果的详细回答。",
        "data": {"sources": ["knowledge/data_structure.md"]}
    }, request.client_id)
    
    return {"status": "success", "message": "查询已开始处理"}

# WebSocket 的路由
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        await manager.send_personal_message({
            "type": "connected",
            "content": f"连接成功"
        }, client_id)
        
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
                message_type = message_data.get('type', 'message')
                content = message_data.get('content', '')
                
                # 如果是查询请求，启动处理流程
                if message_type == 'query' and content:
                    # 发送思考步骤
                    await manager.send_personal_message({
                        "type": "thinking",
                        "step": "解析问题",
                        "content": f"正在解析用户问题：{content}"
                    }, client_id)
                    
                    await asyncio.sleep(0.5)
                    
                    await manager.send_personal_message({
                        "type": "thinking",
                        "step": "检索知识库",
                        "content": "正在检索相关知识库文件..."
                    }, client_id)
                    
                    await asyncio.sleep(0.5)
                    
                    await manager.send_personal_message({
                        "type": "thinking",
                        "step": "分析结果",
                        "content": "正在分析检索结果..."
                    }, client_id)
                    
                    await asyncio.sleep(0.5)
                    
                    # 发送最终回答
                    await manager.send_personal_message({
                        "type": "answer",
                        "content": f'您好！我收到了您的问题："{content}"。\n\n这是一个测试回答，实际应用中我会根据知识库内容给出详细解答。',
                        "data": {
                            "sources": ["knowledge/data_structure.md", "knowledge/ai_agent.md"]
                        }
                    }, client_id)
                else:
                    # 普通消息
                    await manager.send_personal_message({
                        "type": "message",
                        "content": f"收到消息：{content}"
                    }, client_id)
            except json.JSONDecodeError:
                await manager.send_personal_message({
                    "type": "message",
                    "content": f"收到消息：{data}"
                }, client_id)
    except WebSocketDisconnect:
        manager.disconnect(client_id)

# 健康检查
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
