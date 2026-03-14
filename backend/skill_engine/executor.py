"""
Skill 执行器
提供分层索引导航和文件类型策略
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
import sys

# 添加 backend 目录到 Python 路径
backend_path = Path(__file__).parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

logger = logging.getLogger(__name__)


class SkillExecutor:
    """Skill 执行器"""
    
    def __init__(self, knowledge_root: str, skill_path: str):
        """
        初始化 Skill 执行器
        
        Args:
            knowledge_root: 知识库根目录
            skill_path: Skill 目录路径
        """
        self.knowledge_root = Path(knowledge_root)
        self.skill_path = Path(skill_path)
        self.current_path = self.knowledge_root  # 当前工作目录
    
    def set_current_path(self, path: str):
        """
        设置当前工作目录
        
        Args:
            path: 路径（相对于 knowledge_root）
        """
        self.current_path = self.knowledge_root / path
        logger.info(f"当前工作目录：{self.current_path}")
    
    def navigate_to(self, path: str) -> Dict[str, Any]:
        """
        导航到指定目录
        
        Args:
            path: 目录路径（相对于 knowledge_root）
            
        Returns:
            dict: {
                "success": bool,
                "data": {
                    "path": str,
                    "exists": bool,
                    "has_data_structure": bool
                },
                "error": str
            }
        """
        try:
            target_path = self.knowledge_root / path
            
            if not target_path.exists():
                return {
                    "success": False,
                    "data": None,
                    "error": f"目录不存在：{path}"
                }
            
            if not target_path.is_dir():
                return {
                    "success": False,
                    "data": None,
                    "error": f"不是目录：{path}"
                }
            
            self.set_current_path(path)
            
            # 检查是否有 data_structure.md
            has_data_structure = (target_path / "data_structure.md").exists()
            
            return {
                "success": True,
                "data": {
                    "path": path,
                    "exists": True,
                    "has_data_structure": has_data_structure
                },
                "error": None
            }
        
        except Exception as e:
            logger.error(f"导航失败 {path}: {e}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
    
    def get_file_type_strategy(self, file_extension: str) -> Dict[str, Any]:
        """
        获取特定文件类型的处理策略
        
        Args:
            file_extension: 文件扩展名（如 ".pdf"）
            
        Returns:
            dict: {
                "tool": str,  # 使用的工具
                "method": str,  # 调用的方法
                "requires_learning": bool,  # 是否需要先学习 references
                "reference_docs": List[str],  # 需要学习的参考文档
                "strategy": str  # 策略描述
            }
        """
        strategies = {
            ".md": {
                "tool": "Grep",
                "method": "search",
                "requires_learning": False,
                "reference_docs": [],
                "strategy": "直接使用 Grep 工具搜索关键词，然后使用 Read 工具局部读取"
            },
            ".txt": {
                "tool": "Grep",
                "method": "search",
                "requires_learning": False,
                "reference_docs": [],
                "strategy": "直接使用 Grep 工具搜索关键词，然后使用 Read 工具局部读取"
            },
            ".pdf": {
                "tool": "PDF",
                "method": "extract_text",
                "requires_learning": True,
                "reference_docs": ["pdf_reading.md"],
                "strategy": "先读取 references/pdf_reading.md 学习方法，然后使用 PDF 工具提取文本，再对提取结果进行检索"
            },
            ".xlsx": {
                "tool": "Excel",
                "method": "read_sheet",
                "requires_learning": True,
                "reference_docs": ["excel_reading.md", "excel_analysis.md"],
                "strategy": "先读取 references/excel_reading.md 和 excel_analysis.md 学习方法，然后使用 Excel 工具读取和分析数据"
            },
            ".xls": {
                "tool": "Excel",
                "method": "read_sheet",
                "requires_learning": True,
                "reference_docs": ["excel_reading.md", "excel_analysis.md"],
                "strategy": "同 .xlsx"
            }
        }
        
        return strategies.get(file_extension.lower(), {
            "tool": "Read",
            "method": "read",
            "requires_learning": False,
            "reference_docs": [],
            "strategy": "使用 Read 工具直接读取文件"
        })
    
    def list_files(self, pattern: str = "**/*") -> Dict[str, Any]:
        """
        列出当前目录下的文件
        
        Args:
            pattern: 文件匹配模式
            
        Returns:
            dict: {
                "success": bool,
                "data": {
                    "files": List[str],
                    "directories": List[str]
                },
                "error": str
            }
        """
        try:
            files = []
            directories = []
            
            for item in self.current_path.glob(pattern):
                rel_path = str(item.relative_to(self.knowledge_root))
                if item.is_file():
                    files.append(rel_path)
                else:
                    directories.append(rel_path)
            
            return {
                "success": True,
                "data": {
                    "files": files,
                    "directories": directories
                },
                "error": None
            }
        
        except Exception as e:
            logger.error(f"列出文件失败：{e}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
    
    def check_file_exists(self, file_path: str) -> Dict[str, Any]:
        """
        检查文件是否存在
        
        Args:
            file_path: 文件路径（相对于 knowledge_root）
            
        Returns:
            dict: {
                "success": bool,
                "data": {
                    "exists": bool,
                    "path": str
                },
                "error": str
            }
        """
        try:
            full_path = self.knowledge_root / file_path
            exists = full_path.exists()
            
            return {
                "success": True,
                "data": {
                    "exists": exists,
                    "path": file_path
                },
                "error": None
            }
        
        except Exception as e:
            logger.error(f"检查文件失败 {file_path}: {e}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
