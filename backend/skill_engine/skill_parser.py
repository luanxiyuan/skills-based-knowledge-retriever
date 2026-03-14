"""
Skill 解析器
解析 SKILL.md 和 data_structure.md 文件
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
import sys
import re

# 添加 backend 目录到 Python 路径
backend_path = Path(__file__).parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

logger = logging.getLogger(__name__)


class SkillParser:
    """Skill 解析器"""
    
    def __init__(self, skill_path: str):
        """
        初始化 Skill 解析器
        
        Args:
            skill_path: Skill 目录路径
        """
        self.skill_path = Path(skill_path)
    
    def parse_skill_md(self) -> Dict[str, Any]:
        """
        解析 SKILL.md 文件
        
        Returns:
            dict: {
                "success": bool,
                "data": {
                    "metadata": dict,  # 元数据
                    "description": str,  # 描述
                    "capabilities": List[str],  # 能力列表
                    "knowledge_structure": str  # 知识结构描述
                },
                "error": str
            }
        """
        try:
            skill_file = self.skill_path / "SKILL.md"
            
            if not skill_file.exists():
                return {
                    "success": False,
                    "data": None,
                    "error": f"SKILL.md 文件不存在：{skill_file}"
                }
            
            with open(skill_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析元数据（YAML front matter）
            metadata = {}
            description = ""
            capabilities = []
            knowledge_structure = ""
            
            # 提取 front matter
            front_matter_match = re.search(r'---\n(.*?)\n---', content, re.DOTALL)
            if front_matter_match:
                front_matter = front_matter_match.group(1)
                for line in front_matter.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        metadata[key.strip()] = value.strip()
            
            # 提取描述
            desc_match = re.search(r'# (.*?)\n', content)
            if desc_match:
                description = desc_match.group(1)
            
            # 提取能力列表
            cap_match = re.search(r'## 能力\n(.*?)(?=##|$)', content, re.DOTALL)
            if cap_match:
                cap_text = cap_match.group(1)
                capabilities = [line.strip('- ').strip() for line in cap_text.split('\n') if line.strip().startswith('-')]
            
            # 提取知识结构
            ks_match = re.search(r'## 知识结构\n(.*?)(?=##|$)', content, re.DOTALL)
            if ks_match:
                knowledge_structure = ks_match.group(1).strip()
            
            return {
                "success": True,
                "data": {
                    "metadata": metadata,
                    "description": description,
                    "capabilities": capabilities,
                    "knowledge_structure": knowledge_structure
                },
                "error": None
            }
        
        except Exception as e:
            logger.error(f"解析 SKILL.md 失败：{e}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
    
    def parse_data_structure(self, relative_path: str = "") -> Dict[str, Any]:
        """
        解析 data_structure.md 文件
        
        Args:
            relative_path: 相对于 knowledge_root 的路径
            
        Returns:
            dict: {
                "success": bool,
                "data": {
                    "path": str,
                    "description": str,  # 目录描述
                    "directories": List[dict],  # 子目录列表
                    "files": List[dict]  # 文件列表
                },
                "error": str
            }
        """
        try:
            # 构建完整路径
            if relative_path:
                full_path = self.skill_path.parent / "knowledge" / relative_path
            else:
                full_path = self.skill_path.parent / "knowledge"
            
            data_structure_file = full_path / "data_structure.md"
            
            if not data_structure_file.exists():
                return {
                    "success": False,
                    "data": None,
                    "error": f"data_structure.md 文件不存在：{data_structure_file}"
                }
            
            with open(data_structure_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析目录描述
            description = ""
            directories = []
            files = []
            
            # 提取描述部分
            desc_match = re.search(r'# .*?\n\n(.*?)(?=\n- |\n##|$)', content, re.DOTALL)
            if desc_match:
                description = desc_match.group(1).strip()
            
            # 提取子目录列表
            dir_matches = re.findall(r'- (.*?)/\n\s*- 用途：(.*?)(?=\n- |\n##|$)', content, re.DOTALL)
            for dir_name, dir_desc in dir_matches:
                directories.append({
                    "name": dir_name.strip(),
                    "description": dir_desc.strip()
                })
            
            # 提取文件列表（如果有）
            file_matches = re.findall(r'- \[(.*?)\]\((.*?)\)', content)
            for file_name, file_path in file_matches:
                files.append({
                    "name": file_name,
                    "path": file_path
                })
            
            return {
                "success": True,
                "data": {
                    "path": relative_path,
                    "description": description,
                    "directories": directories,
                    "files": files
                },
                "error": None
            }
        
        except Exception as e:
            logger.error(f"解析 data_structure.md 失败 {relative_path}: {e}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
    
    def get_directory_info(self, dir_path: str) -> Dict[str, Any]:
        """
        获取目录信息（不依赖 data_structure.md）
        
        Args:
            dir_path: 目录路径（相对于 knowledge_root）
            
        Returns:
            dict: {
                "success": bool,
                "data": {
                    "exists": bool,
                    "subdirs": List[str],
                    "files": List[str]
                },
                "error": str
            }
        """
        try:
            full_path = self.skill_path.parent / "knowledge" / dir_path if dir_path else self.skill_path.parent / "knowledge"
            
            if not full_path.exists():
                return {
                    "success": False,
                    "data": None,
                    "error": f"目录不存在：{dir_path}"
                }
            
            subdirs = []
            files = []
            
            for item in full_path.iterdir():
                if item.is_dir():
                    subdirs.append(item.name)
                elif item.is_file() and item.suffix in ['.md', '.txt', '.pdf', '.xlsx', '.xls']:
                    files.append(item.name)
            
            return {
                "success": True,
                "data": {
                    "exists": True,
                    "subdirs": sorted(subdirs),
                    "files": sorted(files)
                },
                "error": None
            }
        
        except Exception as e:
            logger.error(f"获取目录信息失败 {dir_path}: {e}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
