"""
Grep 检索工具
支持关键词检索、include 过滤、path 限定
"""

import os
import re
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class GrepTool:
    """Grep 检索工具类"""
    
    def __init__(self, knowledge_root: str):
        """
        初始化 Grep 工具
        
        Args:
            knowledge_root: 知识库根目录
        """
        self.knowledge_root = Path(knowledge_root)
    
    def search(
        self,
        pattern: str,
        path: str = "",
        include: Optional[str] = None,
        exclude: Optional[str] = None,
        case_sensitive: bool = False,
        max_results: int = 100
    ) -> Dict[str, Any]:
        """
        在指定目录下搜索包含关键词的文件
        
        Args:
            pattern: 搜索模式（支持正则表达式）
            path: 搜索路径（相对于 knowledge_root）
            include: 包含的文件模式（如 "*.md"）
            exclude: 排除的文件模式
            case_sensitive: 是否区分大小写
            max_results: 最大结果数
            
        Returns:
            dict: {
                "success": bool,
                "data": List[Dict],  # 匹配结果列表
                "error": str  # 错误信息（如果有）
            }
        """
        try:
            # 构建完整路径
            search_path = self.knowledge_root / path if path else self.knowledge_root
            
            if not search_path.exists():
                return {
                    "success": False,
                    "data": [],
                    "error": f"搜索路径不存在：{search_path}"
                }
            
            # 编译正则表达式
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                regex = re.compile(pattern, flags)
            except re.error as e:
                return {
                    "success": False,
                    "data": [],
                    "error": f"正则表达式错误：{e}"
                }
            
            results = []
            file_count = 0
            
            # 遍历目录
            for root, dirs, files in os.walk(search_path):
                for file in files:
                    # 检查文件模式
                    if include and not re.match(include.replace('*', '.*'), file):
                        continue
                    if exclude and re.match(exclude.replace('*', '.*'), file):
                        continue
                    
                    file_path = Path(root) / file
                    
                    # 跳过二进制文件
                    if self._is_binary_file(file_path):
                        continue
                    
                    # 搜索文件内容
                    matches = self._search_file(file_path, regex, max_results - len(results))
                    if matches:
                        file_count += 1
                        results.extend(matches)
                    
                    if len(results) >= max_results:
                        break
                
                if len(results) >= max_results:
                    break
            
            return {
                "success": True,
                "data": {
                    "matches": results,
                    "total_matches": len(results),
                    "total_files": file_count
                },
                "error": None
            }
        
        except Exception as e:
            logger.error(f"Grep 搜索失败：{e}")
            return {
                "success": False,
                "data": [],
                "error": str(e)
            }
    
    def _search_file(self, file_path: Path, regex: re.Pattern, max_matches: int) -> List[Dict]:
        """
        在单个文件中搜索
        
        Args:
            file_path: 文件路径
            regex: 编译后的正则表达式
            max_matches: 最大匹配数
            
        Returns:
            List[Dict]: 匹配结果列表
        """
        matches = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                if regex.search(line):
                    # 获取相对路径
                    rel_path = str(file_path.relative_to(self.knowledge_root))
                    
                    matches.append({
                        "file": rel_path,
                        "line_number": line_num,
                        "content": line.strip(),
                        "context": self._get_context(lines, line_num - 1, context_lines=2)
                    })
                    
                    if len(matches) >= max_matches:
                        break
        except Exception as e:
            logger.warning(f"读取文件失败 {file_path}: {e}")
        
        return matches
    
    def _get_context(self, lines: List[str], line_idx: int, context_lines: int = 2) -> Dict[str, Any]:
        """
        获取匹配行的上下文
        
        Args:
            lines: 所有行
            line_idx: 匹配行索引（从 0 开始）
            context_lines: 上下文行数
            
        Returns:
            Dict: 上下文信息
        """
        start = max(0, line_idx - context_lines)
        end = min(len(lines), line_idx + context_lines + 1)
        
        return {
            "before": [line.strip() for line in lines[start:line_idx]],
            "match": lines[line_idx].strip(),
            "after": [line.strip() for line in lines[line_idx + 1:end]],
            "line_range": (start + 1, end)  # 行号从 1 开始
        }
    
    def _is_binary_file(self, file_path: Path) -> bool:
        """
        检查文件是否为二进制文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否为二进制文件
        """
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                # 检查是否包含空字节（二进制文件的特征）
                return b'\x00' in chunk
        except Exception:
            return True
    
    # ==================== 别名方法（兼容 LLM 调用） ====================
    
    def find(self, pattern: str, **kwargs):
        """
        别名方法：find
        实际调用 search 方法
        
        Args:
            pattern: 搜索模式
            **kwargs: 其他参数传递给 search 方法
            
        Returns:
            dict: search 方法的返回结果
        """
        return self.search(pattern=pattern, **kwargs)
    
    def grep(self, pattern: str, **kwargs):
        """
        别名方法：grep
        实际调用 search 方法
        """
        return self.search(pattern=pattern, **kwargs)
    
    def search_keywords(self, pattern: str, **kwargs):
        """
        别名方法：search_keywords
        实际调用 search 方法
        """
        return self.search(pattern=pattern, **kwargs)
