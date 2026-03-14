"""
工具注册表
管理所有可用工具的注册和调用
"""

from typing import Dict, Any, Callable, List
import logging
import sys
from pathlib import Path

# 添加 backend 目录到 Python 路径
backend_path = Path(__file__).parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

logger = logging.getLogger(__name__)


class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        """初始化工具注册表"""
        self.tools: Dict[str, Any] = {}
        self.tool_instances: Dict[str, Any] = {}
    
    def register(self, name: str, tool: Any):
        """
        注册工具
        
        Args:
            name: 工具名称
            tool: 工具实例
        """
        self.tools[name] = tool
        self.tool_instances[name] = tool
        logger.info(f"工具已注册：{name}")
    
    def get_tool(self, name: str) -> Any:
        """
        获取工具实例
        
        Args:
            name: 工具名称
            
        Returns:
            工具实例或 None
        """
        return self.tool_instances.get(name)
    
    def list_tools(self) -> List[str]:
        """
        列出所有已注册的工具
        
        Returns:
            List[str]: 工具名称列表
        """
        return list(self.tools.keys())
    
    def execute(self, name: str, method: str, **kwargs) -> Dict[str, Any]:
        """
        执行工具方法（支持大小写不敏感）
        
        Args:
            name: 工具名称
            method: 方法名
            **kwargs: 方法参数
            
        Returns:
            dict: 执行结果
        """
        # 首先尝试精确匹配
        tool = self.get_tool(name)
        
        # 如果找不到，尝试大小写不敏感匹配
        if not tool:
            for tool_name, tool_instance in self.tool_instances.items():
                if tool_name.lower() == name.lower():
                    tool = tool_instance
                    name = tool_name  # 使用正确的工具名称
                    break
        
        if not tool:
            return {
                "success": False,
                "data": None,
                "error": f"工具不存在：{name}"
            }
        
        try:
            # 首先尝试精确匹配方法
            method_func = getattr(tool, method, None)
            
            # 如果找不到方法，尝试大小写不敏感匹配
            if not method_func:
                for attr_name in dir(tool):
                    if attr_name.lower() == method.lower() and not attr_name.startswith('_'):
                        method_func = getattr(tool, attr_name)
                        method = attr_name  # 使用正确的方法名称
                        break
            
            if not method_func:
                return {
                    "success": False,
                    "data": None,
                    "error": f"工具方法不存在：{name}.{method}"
                }
            
            # 执行方法
            result = method_func(**kwargs)
            return result
        
        except Exception as e:
            logger.error(f"执行工具失败 {name}.{method}: {e}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
    
    def get_tool_schema(self, name: str) -> Dict[str, Any]:
        """
        获取工具的 schema（用于 LLM 调用）
        
        Args:
            name: 工具名称
            
        Returns:
            dict: 工具 schema
        """
        tool = self.get_tool(name)
        if not tool:
            return {
                "name": name,
                "description": f"工具 {name} 未注册",
                "parameters": {}
            }
        
        # 根据工具类的方法生成 schema
        # 这里简化处理，实际应该从方法签名中提取
        schemas = {
            "Grep": {
                "name": "Grep",
                "description": "在知识库中搜索包含关键词的文件",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "搜索模式（支持正则表达式）"
                        },
                        "path": {
                            "type": "string",
                            "description": "搜索路径（相对于 knowledge_root）"
                        },
                        "include": {
                            "type": "string",
                            "description": "包含的文件模式（如 *.md）"
                        }
                    },
                    "required": ["pattern"]
                }
            },
            "Read": {
                "name": "Read",
                "description": "读取文件内容，支持局部读取",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "文件路径（相对于 knowledge_root）"
                        },
                        "start_line": {
                            "type": "integer",
                            "description": "起始行号（从 1 开始）"
                        },
                        "end_line": {
                            "type": "integer",
                            "description": "结束行号（从 1 开始）"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "最大读取行数"
                        }
                    },
                    "required": ["file_path"]
                }
            },
            "PDF": {
                "name": "PDF",
                "description": "提取 PDF 文件的文本和表格",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "PDF 文件路径"
                        },
                        "method": {
                            "type": "string",
                            "enum": ["extract_text", "extract_tables", "get_metadata"],
                            "description": "处理方法"
                        },
                        "pages": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "要提取的页码列表"
                        }
                    },
                    "required": ["file_path", "method"]
                }
            },
            "Excel": {
                "name": "Excel",
                "description": "读取和分析 Excel 文件",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Excel 文件路径"
                        },
                        "method": {
                            "type": "string",
                            "enum": ["read_sheet", "get_sheet_names", "analyze_column", "filter_data"],
                            "description": "处理方法"
                        },
                        "sheet_name": {
                            "type": "string",
                            "description": "工作表名称或索引"
                        },
                        "column_name": {
                            "type": "string",
                            "description": "列名"
                        }
                    },
                    "required": ["file_path", "method"]
                }
            }
        }
        
        return schemas.get(name, {
            "name": name,
            "description": f"工具 {name}",
            "parameters": {}
        })
    
    def get_all_tools_schema(self) -> List[Dict[str, Any]]:
        """
        获取所有工具的 schema（用于 LLM 调用）
        
        Returns:
            List[Dict]: 工具 schema 列表
        """
        return [self.get_tool_schema(name) for name in self.list_tools()]
