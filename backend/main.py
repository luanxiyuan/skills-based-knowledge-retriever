"""
FastAPI 主应用
集成所有模块，提供 API 和 WebSocket 服务
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import logging
import yaml
from pathlib import Path
import mimetypes
import asyncio

from websocket_server import manager, push_thinking_step, push_answer, clear_stop_flag
from agent import Agent

# 存储每个客户端的处理任务
processing_tasks = {}

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# 加载配置
config_path = Path("config.yaml")
config = {}
if config_path.exists():
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    logger.info(f"配置文件已加载：{config_path}")
else:
    logger.warning("配置文件不存在，使用默认配置")

# 创建 FastAPI 应用
app = FastAPI(
    title="知识库检索工具 API",
    description="基于 Skill 执行机制的知识库检索工具",
    version="1.0.0"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 请求/响应模型
class QueryRequest(BaseModel):
    question: str
    client_id: str


class ModelSwitchRequest(BaseModel):
    model_name: str


# API 路由
@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "connections": manager.get_active_count()}


@app.get("/api/models")
async def list_models():
    """列出可用模型"""
    from agent.llm_manager import LLMManager
    llm_manager = LLMManager()
    return {
        "models": llm_manager.list_models(),
        "current_model": llm_manager.get_current_model()
    }


@app.post("/api/models/switch")
async def switch_model(request: ModelSwitchRequest):
    """切换当前使用的模型"""
    from agent.llm_manager import LLMManager
    llm_manager = LLMManager()
    
    if llm_manager.switch_model(request.model_name):
        return {"success": True, "message": f"已切换到模型：{request.model_name}"}
    else:
        raise HTTPException(status_code=400, detail=f"模型不存在：{request.model_name}")


@app.get("/api/file")
async def get_file_content(path: str):
    """
    获取文件内容（静态文件服务，直接返回文件）
    """
    try:
        # 构建文件路径
        knowledge_root = config.get('knowledge', {}).get('root_path', 'knowledge')
        file_path = Path(knowledge_root) / path
        
        # 安全检查：确保文件在知识库目录内
        file_path = file_path.resolve()
        knowledge_path = Path(knowledge_root).resolve()
        
        if not str(file_path).startswith(str(knowledge_path)):
            raise HTTPException(status_code=400, detail="非法的文件路径")
        
        # 检查文件是否存在
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 检查是否是文件
        if not file_path.is_file():
            raise HTTPException(status_code=400, detail="路径不是文件")
        
        # 获取文件的 MIME 类型
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type is None:
            mime_type = "application/octet-stream"
        
        # 直接返回文件（inline 模式，浏览器预览）
        return FileResponse(
            path=file_path,
            media_type=mime_type,
            filename=file_path.name,
            content_disposition_type="inline"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"读取文件失败：{e}")
        raise HTTPException(status_code=500, detail=f"读取文件失败：{str(e)}")


@app.post("/api/query")
async def query(request: QueryRequest):
    """
    处理查询请求（RESTful 方式，不推荐，推荐使用 WebSocket）
    """
    logger.info(f"收到查询请求：{request.client_id} - {request.question[:50]}...")
    
    # 创建 Agent
    agent = Agent(
        client_id=request.client_id,
        knowledge_root=config.get('knowledge', {}).get('root_path', 'knowledge'),
        skill_path=config.get('skill', {}).get('skill_path', 'rag-skill'),
        config_path="config.yaml"
    )
    
    # 处理查询（注意：这里不会推送结果，因为不是 WebSocket）
    # 实际使用应该通过 WebSocket
    return {
        "status": "accepted",
        "message": "查询已接收，请通过 WebSocket 获取结果"
    }


# WebSocket 路由
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket 端点
    处理客户端连接和消息
    """
    logger.info(f"收到 WebSocket 连接请求：{client_id}, origin: {websocket.headers.get('origin', 'unknown')}")
    
    # 连接 WebSocket
    if not await manager.connect(websocket, client_id):
        logger.error(f"WebSocket 连接失败，关闭连接：{client_id}")
        await websocket.close()
        return
    
    logger.info(f"WebSocket 连接成功：{client_id}")
    
    try:
        # 发送连接成功消息
        await push_thinking_step(client_id, "系统", f"连接成功，客户端 ID: {client_id}")
        
        # 循环接收消息
        while True:
            # 接收消息
            data = await websocket.receive_text()
            logger.info(f"收到消息 {client_id}: {data[:100]}...")
            
            try:
                import json
                message_data = json.loads(data)
                message_type = message_data.get('type', 'message')
                content = message_data.get('content', '')
                
                # 处理查询
                if message_type == 'query' and content:
                    # 清除停止标志
                    clear_stop_flag(client_id)
                    
                    # 如果有正在运行的任务，先取消
                    if client_id in processing_tasks:
                        processing_tasks[client_id].cancel()
                    
                    # 创建 Agent
                    agent = Agent(
                        client_id=client_id,
                        knowledge_root=config.get('knowledge', {}).get('root_path', 'knowledge'),
                        skill_path=config.get('skill', {}).get('skill_path', 'rag-skill'),
                        config_path="config.yaml"
                    )
                    
                    # 创建异步任务处理查询
                    async def process_and_cleanup():
                        try:
                            await agent.process_query(content)
                        except asyncio.CancelledError:
                            logger.info(f"查询处理被取消：{client_id}")
                        finally:
                            if client_id in processing_tasks:
                                del processing_tasks[client_id]
                    
                    processing_tasks[client_id] = asyncio.create_task(process_and_cleanup())
                
                elif message_type == 'stop':
                    # 处理停止请求
                    manager.set_stop_flag(client_id, True)
                    logger.info(f"收到停止请求：{client_id}")
                    
                    # 取消正在运行的任务
                    if client_id in processing_tasks:
                        processing_tasks[client_id].cancel()
                        del processing_tasks[client_id]
                    
                    # 推送停止确认
                    await push_thinking_step(
                        client_id,
                        "系统",
                        "已停止处理"
                    )
                
                elif message_type == 'switch_model':
                    # 切换模型
                    model_name = message_data.get('model_name', '')
                    from agent.llm_manager import LLMManager
                    llm_manager = LLMManager()
                    
                    if llm_manager.switch_model(model_name):
                        await push_thinking_step(
                            client_id,
                            "系统",
                            f"已切换到模型：{model_name}"
                        )
                    else:
                        await push_error(client_id, "模型切换失败", f"模型不存在：{model_name}")
                
                else:
                    # 未知消息类型
                    await push_thinking_step(
                        client_id,
                        "系统",
                        f"收到消息：{content}"
                    )
            
            except json.JSONDecodeError:
                # 不是 JSON 格式
                await push_thinking_step(
                    client_id,
                    "系统",
                    f"收到消息：{data}"
                )
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket 断开连接：{client_id}")
        manager.disconnect(client_id)
    
    except Exception as e:
        logger.error(f"WebSocket 错误 {client_id}: {e}")
        await push_error(client_id, "连接错误", str(e))
        manager.disconnect(client_id)


# 主入口
if __name__ == "__main__":
    import uvicorn
    import sys
    
    server_config = config.get('server', {})
    host = server_config.get('host', '0.0.0.0')
    port = server_config.get('port', 8000)
    debug = server_config.get('debug', False)
    
    logger.info(f"启动服务器：http://{host}:{port}")
    logger.info(f"调试模式：{debug}")
    logger.info(f"日志级别：INFO")
    
    # 禁用 reload 模式，因为需要以脚本方式运行
    if debug:
        logger.info("注意：调试模式已启用，但 reload 功能被禁用")
    
    try:
        # 始终禁用 reload，因为这与直接运行脚本不兼容
        uvicorn.run(app, host=host, port=port, reload=False, log_level="info")
    except KeyboardInterrupt:
        logger.info("服务器已停止")
    except Exception as e:
        logger.error(f"服务器错误：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
