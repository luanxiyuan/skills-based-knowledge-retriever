"""
Read 文件读取工具
支持局部读取（行号范围）、分段读取
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class ReadTool:
    """Read 文件读取工具类"""
    
    def __init__(self, knowledge_root: str):
        """
        初始化 Read 工具
        
        Args:
            knowledge_root: 知识库根目录
        """
        self.knowledge_root = Path(knowledge_root)
    
    def read(
        self,
        file_path: str,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        读取文件内容
        
        Args:
            file_path: 文件路径（相对于 knowledge_root）
            start_line: 起始行号（从 1 开始，包含）
            end_line: 结束行号（从 1 开始，包含）
            limit: 最大读取行数
            
        Returns:
            dict: {
                "success": bool,
                "data": {
                    "content": str,  # 文件内容
                    "lines": List[str],  # 按行分割的内容
                    "total_lines": int,  # 总行数
                    "line_range": Tuple[int, int]  # 实际读取的行范围
                },
                "error": str  # 错误信息（如果有）
            }
        """
        try:
            # 构建完整路径
            full_path = self.knowledge_root / file_path
            
            if not full_path.exists():
                return {
                    "success": False,
                    "data": None,
                    "error": f"文件不存在：{file_path}"
                }
            
            # 检查文件大小
            file_size_mb = full_path.stat().st_size / (1024 * 1024)
            if file_size_mb > 50:  # 限制 50MB
                return {
                    "success": False,
                    "data": None,
                    "error": f"文件过大：{file_size_mb:.2f}MB，最大支持 50MB"
                }
            
            # 读取文件
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
            
            total_lines = len(all_lines)
            
            # 确定读取范围
            if start_line is None:
                start_line = 1
            if end_line is None:
                end_line = total_lines
            
            # 限制范围
            start_idx = max(0, start_line - 1)  # 转换为 0-based 索引
            end_idx = min(total_lines, end_line)  # 不包含 end_idx
            
            # 应用 limit
            if limit is not None:
                end_idx = min(end_idx, start_idx + limit)
            
            # 提取行
            selected_lines = all_lines[start_idx:end_idx]
            content = ''.join(selected_lines)
            
            return {
                "success": True,
                "data": {
                    "content": content,
                    "lines": [line.rstrip('\n\r') for line in selected_lines],
                    "total_lines": total_lines,
                    "line_range": (start_idx + 1, end_idx),  # 返回 1-based 行号
                    "file_path": file_path  # 添加文件路径
                },
                "error": None
            }
        
        except Exception as e:
            logger.error(f"读取文件失败 {file_path}: {e}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
    
    def read_by_chunk(
        self,
        file_path: str,
        chunk_size: int = 100,
        chunk_index: int = 0
    ) -> Dict[str, Any]:
        """
        分块读取文件
        
        Args:
            file_path: 文件路径（相对于 knowledge_root）
            chunk_size: 每块行数
            chunk_index: 块索引（从 0 开始）
            
        Returns:
            dict: 与 read 方法相同的返回格式
        """
        start_line = chunk_index * chunk_size + 1
        end_line = start_line + chunk_size - 1
        
        return self.read(file_path, start_line=start_line, end_line=end_line, limit=chunk_size)
    
    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        获取文件基本信息
        
        Args:
            file_path: 文件路径（相对于 knowledge_root）
            
        Returns:
            dict: {
                "success": bool,
                "data": {
                    "exists": bool,
                    "size_bytes": int,
                    "size_mb": float,
                    "total_lines": int,
                    "extension": str
                },
                "error": str
            }
        """
        try:
            full_path = self.knowledge_root / file_path
            
            if not full_path.exists():
                return {
                    "success": True,
                    "data": {"exists": False},
                    "error": None
                }
            
            # 读取前 1000 行估算总行数（避免大文件）
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                line_count = sum(1 for _ in f)
            
            return {
                "success": True,
                "data": {
                    "exists": True,
                    "size_bytes": full_path.stat().st_size,
                    "size_mb": full_path.stat().st_size / (1024 * 1024),
                    "total_lines": line_count,
                    "extension": full_path.suffix.lower()
                },
                "error": None
            }
        
        except Exception as e:
            logger.error(f"获取文件信息失败 {file_path}: {e}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
    
    # ==================== 别名方法（兼容 LLM 调用） ====================
    
    def search_keywords(self, file_path: str, **kwargs):
        """
        别名方法：search_keywords
        实际调用 read 方法
        
        Args:
            file_path: 文件路径
            **kwargs: 其他参数传递给 read 方法
            
        Returns:
            dict: read 方法的返回结果
        """
        return self.read(file_path=file_path, **kwargs)
    
    def find(self, file_path: str, **kwargs):
        """
        别名方法：find
        实际调用 read 方法
        """
        return self.read(file_path=file_path, **kwargs)
    
    def open(self, file_path: str, **kwargs):
        """
        别名方法：open
        实际调用 read 方法
        """
        return self.read(file_path=file_path, **kwargs)
