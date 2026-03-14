"""
WebSocket 推送模块
负责管理 WebSocket 连接和消息推送
与 Agent 解耦，提供独立的消息推送能力
"""

from typing import Dict, Optional
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.stop_flags: Dict[str, bool] = {}  # 停止标志字典
    
    async def connect(self, websocket: WebSocket, client_id: str) -> bool:
        """
        接受 WebSocket 连接
        
        Args:
            websocket: WebSocket 对象
            client_id: 客户端 ID
            
        Returns:
            bool: 连接是否成功
        """
        try:
            logger.info(f"尝试接受 WebSocket 连接：{client_id}")
            await websocket.accept()
            self.active_connections[client_id] = websocket
            logger.info(f"WebSocket 连接成功：{client_id}, 当前连接数：{len(self.active_connections)}")
            return True
        except Exception as e:
            logger.error(f"WebSocket 连接失败：{client_id}, 错误：{e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def disconnect(self, client_id: str):
        """
        断开 WebSocket 连接
        
        Args:
            client_id: 客户端 ID
        """
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"WebSocket 断开连接：{client_id}")
        
        # 清理停止标志
        if client_id in self.stop_flags:
            del self.stop_flags[client_id]
    
    def set_stop_flag(self, client_id: str, stop: bool = True):
        """
        设置停止标志
        
        Args:
            client_id: 客户端 ID
            stop: 是否停止
        """
        self.stop_flags[client_id] = stop
        logger.info(f"设置停止标志 {client_id}: {stop}")
    
    def should_stop(self, client_id: str) -> bool:
        """
        检查是否应该停止
        
        Args:
            client_id: 客户端 ID
            
        Returns:
            bool: 是否应该停止
        """
        return self.stop_flags.get(client_id, False)
    
    def get_connection(self, client_id: str) -> Optional[WebSocket]:
        """
        获取指定客户端的 WebSocket 连接
        
        Args:
            client_id: 客户端 ID
            
        Returns:
            WebSocket 对象或 None
        """
        return self.active_connections.get(client_id)
    
    async def send_message(self, client_id: str, message: dict) -> bool:
        """
        向指定客户端发送消息
        
        Args:
            client_id: 客户端 ID
            message: 消息字典
            
        Returns:
            bool: 发送是否成功
        """
        websocket = self.get_connection(client_id)
        if websocket:
            try:
                await websocket.send_json(message)
                logger.debug(f"消息已发送到 {client_id}: {message.get('type', 'unknown')}")
                return True
            except Exception as e:
                logger.error(f"发送消息失败 {client_id}: {e}")
                self.disconnect(client_id)
                return False
        else:
            logger.warning(f"客户端 {client_id} 未连接")
            return False
    
    async def broadcast(self, message: dict):
        """
        广播消息到所有连接的客户端
        
        Args:
            message: 消息字典
        """
        disconnected = []
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"广播消息失败 {client_id}: {e}")
                disconnected.append(client_id)
        
        # 清理断开的连接
        for client_id in disconnected:
            self.disconnect(client_id)
    
    def get_active_count(self) -> int:
        """
        获取活跃连接数
        
        Returns:
            int: 连接数
        """
        return len(self.active_connections)


# 全局连接管理器实例
manager = ConnectionManager()


# 便捷推送函数
async def push_thinking_step(client_id: str, step: str, content: str):
    """
    推送思考步骤
    
    Args:
        client_id: 客户端 ID
        step: 步骤名称
        content: 步骤内容
    """
    await manager.send_message(client_id, {
        "type": "thinking",
        "step": step,
        "content": content
    })


async def push_tool_call(client_id: str, tool: str, params: dict, result: str):
    """
    推送工具调用
    
    Args:
        client_id: 客户端 ID
        tool: 工具名称
        params: 工具参数
        result: 工具结果
    """
    await manager.send_message(client_id, {
        "type": "tool_call",
        "tool": tool,
        "params": params,
        "result": result
    })


async def push_answer(client_id: str, content: str, sources: list = None):
    """
    推送最终回答
    
    Args:
        client_id: 客户端 ID
        content: 回答内容
        sources: 来源文件列表
    """
    message = {
        "type": "answer",
        "content": content
    }
    if sources:
        message["data"] = {"sources": sources}
    
    await manager.send_message(client_id, message)


async def push_answer_stream(client_id: str, content: str, is_done: bool = False, sources: list = None):
    """
    推送流式回答
    
    Args:
        client_id: 客户端 ID
        content: 回答内容片段
        is_done: 是否完成
        sources: 来源文件列表（仅在 is_done=True 时发送）
    """
    message = {
        "type": "answer_stream",
        "content": content,
        "is_done": is_done
    }
    if is_done and sources:
        message["data"] = {"sources": sources}
    
    await manager.send_message(client_id, message)


async def push_error(client_id: str, error: str, details: str = None):
    """
    推送错误信息
    
    Args:
        client_id: 客户端 ID
        error: 错误消息
        details: 详细信息
    """
    message = {
        "type": "error",
        "content": error
    }
    if details:
        message["details"] = details
    
    await manager.send_message(client_id, message)


def should_stop(client_id: str) -> bool:
    """
    检查是否应该停止处理
    
    Args:
        client_id: 客户端 ID
        
    Returns:
        bool: 是否应该停止
    """
    return manager.should_stop(client_id)


def clear_stop_flag(client_id: str):
    """
    清除停止标志
    
    Args:
        client_id: 客户端 ID
    """
    manager.set_stop_flag(client_id, False)
