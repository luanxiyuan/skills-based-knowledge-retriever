"""
LLM 管理器
管理多个大模型，支持切换和重试机制
"""

import httpx
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class LLMManager:
    """LLM 管理器"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        初始化 LLM 管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.current_model = self.config.get('llm', {}).get('default_model', 'qwen2.5:7b-instruct')
        self.base_url = "http://localhost:11434"
        self.timeout = self.config.get('llm', {}).get('timeout', 120)
        self.retry_times = self.config.get('llm', {}).get('retry_times', 2)
    
    def _load_config(self) -> Dict[str, Any]:
        """
        加载配置文件
        
        Returns:
            Dict: 配置字典
        """
        if not self.config_path.exists():
            logger.warning(f"配置文件不存在：{self.config_path}，使用默认配置")
            return {
                'llm': {
                    'default_model': 'qwen2.5:7b-instruct',
                    'retry_times': 2,
                    'timeout': 120,
                    'models': [
                        {
                            'name': 'qwen2.5:7b-instruct',
                            'base_url': 'http://localhost:11434',
                            'context_length': 8192
                        }
                    ]
                }
            }
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def get_model_info(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        获取模型信息
        
        Args:
            model_name: 模型名称
            
        Returns:
            Dict: 模型信息或 None
        """
        models = self.config.get('llm', {}).get('models', [])
        for model in models:
            if model.get('name') == model_name:
                return model
        return None
    
    def list_models(self) -> List[str]:
        """
        列出所有可用模型
        
        Returns:
            List[str]: 模型名称列表
        """
        models = self.config.get('llm', {}).get('models', [])
        return [model.get('name') for model in models]
    
    def switch_model(self, model_name: str) -> bool:
        """
        切换当前使用的模型
        
        Args:
            model_name: 模型名称
            
        Returns:
            bool: 是否成功切换
        """
        model_info = self.get_model_info(model_name)
        if model_info:
            self.current_model = model_name
            if 'base_url' in model_info:
                self.base_url = model_info['base_url']
            logger.info(f"已切换到模型：{model_name}")
            return True
        else:
            logger.error(f"模型不存在：{model_name}")
            return False
    
    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stop_check: Optional[callable] = None
    ):
        """
        调用 LLM 进行流式对话
        
        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大 token 数
            stop_check: 停止检查回调函数，返回 True 表示应该停止
            
        Yields:
            str: 流式输出的内容片段
        """
        import asyncio
        import json
        
        model = model or self.current_model
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True
            }
            
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json=payload
                ) as response:
                    if response.status_code == 200:
                        line_iterator = response.aiter_lines()
                        while True:
                            if stop_check and stop_check():
                                logger.info("检测到停止信号，终止流式输出")
                                return
                            
                            try:
                                line = await asyncio.wait_for(
                                    line_iterator.__anext__(),
                                    timeout=0.1
                                )
                            except asyncio.TimeoutError:
                                continue
                            except StopAsyncIteration:
                                break
                            
                            if line.strip():
                                try:
                                    data = json.loads(line)
                                    
                                    if "message" in data:
                                        content = data["message"].get("content", "")
                                        if content:
                                            yield content
                                    
                                    if data.get("done", False):
                                        break
                                        
                                except json.JSONDecodeError:
                                    continue
                    else:
                        logger.error(f"LLM 流式调用失败：{response.status_code}")
                        yield f"[错误：LLM 调用失败 {response.status_code}]"
            
            except Exception as e:
                logger.error(f"LLM 流式调用异常：{e}")
                yield f"[错误：{str(e)}]"
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        调用 LLM 进行对话
        
        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            model: 模型名称（None 表示使用当前模型）
            temperature: 温度参数
            max_tokens: 最大 token 数
            stream: 是否流式输出
            
        Returns:
            dict: {
                "success": bool,
                "data": {
                    "content": str,  # 回答内容
                    "model": str,  # 使用的模型
                    "usage": Dict  # token 使用情况
                },
                "error": str,
                "retry_count": int  # 重试次数
            }
        """
        model = model or self.current_model
        retry_count = 0
        
        while retry_count <= self.retry_times:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    payload = {
                        "model": model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "stream": stream
                    }
                    
                    response = await client.post(
                        f"{self.base_url}/api/chat",
                        json=payload
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        return {
                            "success": True,
                            "data": {
                                "content": result.get("message", {}).get("content", ""),
                                "model": model,
                                "usage": result.get("usage", {})
                            },
                            "error": None,
                            "retry_count": retry_count
                        }
                    else:
                        logger.error(f"LLM 调用失败：{response.status_code} - {response.text}")
                        retry_count += 1
                        if retry_count <= self.retry_times:
                            logger.info(f"重试中... ({retry_count}/{self.retry_times})")
                            continue
                        else:
                            return {
                                "success": False,
                                "data": None,
                                "error": f"LLM 调用失败：{response.status_code}",
                                "retry_count": retry_count
                            }
            
            except httpx.TimeoutException as e:
                logger.error(f"LLM 调用超时：{e}")
                retry_count += 1
                if retry_count > self.retry_times:
                    return {
                        "success": False,
                        "data": None,
                        "error": f"LLM 调用超时：{e}",
                        "retry_count": retry_count
                    }
            
            except Exception as e:
                logger.error(f"LLM 调用异常：{e}")
                return {
                    "success": False,
                    "data": None,
                    "error": str(e),
                    "retry_count": retry_count
                }
        
        # 不应该到达这里
        return {
            "success": False,
            "data": None,
            "error": "未知错误",
            "retry_count": retry_count
        }
    
    async def chat_with_tools(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        调用 LLM 进行对话，支持工具调用
        
        Args:
            messages: 消息列表
            tools: 工具 schema 列表
            model: 模型名称
            
        Returns:
            dict: 与 chat 方法相同的返回格式，但可能包含 tool_calls
        """
        model = model or self.current_model
        
        # 构建带工具的请求
        system_message = {
            "role": "system",
            "content": """你是一个知识库检索助手。你需要根据用户问题和知识库结构，选择合适的工具来检索信息。

可用的工具包括：
- Grep: 在知识库中搜索关键词
- Read: 读取文件内容（支持局部读取）
- PDF: 提取 PDF 文件的文本和表格
- Excel: 读取和分析 Excel 文件

请根据用户问题，选择合适的工具并返回工具调用信息。
"""
        }
        
        messages_with_system = [system_message] + messages
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                payload = {
                    "model": model,
                    "messages": messages_with_system,
                    "tools": tools,
                    "tool_choice": "auto"
                }
                
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    message = result.get("message", {})
                    
                    return {
                        "success": True,
                        "data": {
                            "content": message.get("content", ""),
                            "model": model,
                            "tool_calls": message.get("tool_calls", []),
                            "usage": result.get("usage", {})
                        },
                        "error": None,
                        "retry_count": 0
                    }
                else:
                    return {
                        "success": False,
                        "data": None,
                        "error": f"LLM 调用失败：{response.status_code}",
                        "retry_count": 0
                    }
            
            except Exception as e:
                return {
                    "success": False,
                    "data": None,
                    "error": str(e),
                    "retry_count": 0
                }
    
    def get_current_model(self) -> str:
        """
        获取当前使用的模型
        
        Returns:
            str: 模型名称
        """
        return self.current_model
