"""
PDF 处理工具
使用 pdfplumber 提取文本和表格
"""

from pathlib import Path
from typing import Dict, Any, Optional, List
import logging
import subprocess
import tempfile
import os

logger = logging.getLogger(__name__)


class PDFTool:
    """PDF 处理工具类"""
    
    def __init__(self, knowledge_root: str):
        """
        初始化 PDF 工具
        
        Args:
            knowledge_root: 知识库根目录
        """
        self.knowledge_root = Path(knowledge_root)
    
    def extract_text(
        self,
        file_path: str,
        pages: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
        提取 PDF 文本内容
        
        Args:
            file_path: PDF 文件路径（相对于 knowledge_root）
            pages: 要提取的页码列表（从 1 开始），None 表示全部
            
        Returns:
            dict: {
                "success": bool,
                "data": {
                    "text": str,  # 提取的文本
                    "total_pages": int,  # 总页数
                    "extracted_pages": List[int]  # 实际提取的页码
                },
                "error": str
            }
        """
        try:
            import pdfplumber
            
            full_path = self.knowledge_root / file_path
            
            if not full_path.exists():
                return {
                    "success": False,
                    "data": None,
                    "error": f"文件不存在：{file_path}"
                }
            
            extracted_text = []
            extracted_pages = []
            
            with pdfplumber.open(full_path) as pdf:
                total_pages = len(pdf.pages)
                
                # 确定要提取的页码
                if pages is None:
                    pages_to_extract = range(total_pages)
                else:
                    # 转换为 0-based 索引
                    pages_to_extract = [p - 1 for p in pages if 1 <= p <= total_pages]
                
                for page_idx in pages_to_extract:
                    page = pdf.pages[page_idx]
                    text = page.extract_text()
                    if text:
                        extracted_text.append(f"--- 第 {page_idx + 1} 页 ---\n{text}")
                        extracted_pages.append(page_idx + 1)
            
            return {
                "success": True,
                "data": {
                    "text": '\n\n'.join(extracted_text),
                    "total_pages": total_pages,
                    "extracted_pages": extracted_pages
                },
                "error": None
            }
        
        except Exception as e:
            logger.error(f"提取 PDF 文本失败 {file_path}: {e}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
    
    def extract_tables(self, file_path: str, page_num: Optional[int] = None) -> Dict[str, Any]:
        """
        提取 PDF 中的表格
        
        Args:
            file_path: PDF 文件路径（相对于 knowledge_root）
            page_num: 页码（从 1 开始），None 表示所有页
            
        Returns:
            dict: {
                "success": bool,
                "data": {
                    "tables": List[Dict],  # 表格列表
                    "total_pages": int
                },
                "error": str
            }
        """
        try:
            import pdfplumber
            
            full_path = self.knowledge_root / file_path
            
            if not full_path.exists():
                return {
                    "success": False,
                    "data": None,
                    "error": f"文件不存在：{file_path}"
                }
            
            tables = []
            
            with pdfplumber.open(full_path) as pdf:
                total_pages = len(pdf.pages)
                
                pages_to_process = range(total_pages) if page_num is None else [page_num - 1]
                
                for page_idx in pages_to_process:
                    page = pdf.pages[page_idx]
                    page_tables = page.extract_tables()
                    
                    for table_idx, table in enumerate(page_tables):
                        if table:  # 确保表格不为空
                            tables.append({
                                "page": page_idx + 1,
                                "table_index": table_idx,
                                "data": table,
                                "rows": len(table),
                                "cols": len(table[0]) if table else 0
                            })
            
            return {
                "success": True,
                "data": {
                    "tables": tables,
                    "total_pages": total_pages
                },
                "error": None
            }
        
        except Exception as e:
            logger.error(f"提取 PDF 表格失败 {file_path}: {e}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
    
    def extract_text_with_pdftotext(self, file_path: str) -> Dict[str, Any]:
        """
        使用 pdftotext 命令行工具提取文本（更快）
        
        Args:
            file_path: PDF 文件路径（相对于 knowledge_root）
            
        Returns:
            dict: {
                "success": bool,
                "data": {
                    "text": str,
                    "output_file": str  # 临时输出文件路径
                },
                "error": str
            }
        """
        try:
            full_path = self.knowledge_root / file_path
            
            if not full_path.exists():
                return {
                    "success": False,
                    "data": None,
                    "error": f"文件不存在：{file_path}"
                }
            
            # 检查 pdftotext 是否可用
            try:
                result = subprocess.run(['pdftotext', '-v'], 
                                      capture_output=True, text=True)
            except FileNotFoundError:
                return {
                    "success": False,
                    "data": None,
                    "error": "pdftotext 命令未安装，请使用 pdfplumber 方法"
                }
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as tmp:
                tmp_path = tmp.name
            
            try:
                # 执行转换
                subprocess.run(['pdftotext', str(full_path), tmp_path], check=True)
                
                # 读取结果
                with open(tmp_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
                
                return {
                    "success": True,
                    "data": {
                        "text": text,
                        "output_file": tmp_path
                    },
                    "error": None
                }
            except Exception as e:
                # 清理临时文件
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                raise e
        
        except Exception as e:
            logger.error(f"使用 pdftotext 提取失败 {file_path}: {e}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
    
    def get_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        获取 PDF 元数据
        
        Args:
            file_path: PDF 文件路径（相对于 knowledge_root）
            
        Returns:
            dict: {
                "success": bool,
                "data": {
                    "title": str,
                    "author": str,
                    "subject": str,
                    "creator": str,
                    "total_pages": int
                },
                "error": str
            }
        """
        try:
            from pypdf import PdfReader
            
            full_path = self.knowledge_root / file_path
            
            if not full_path.exists():
                return {
                    "success": False,
                    "data": None,
                    "error": f"文件不存在：{file_path}"
                }
            
            reader = PdfReader(full_path)
            metadata = reader.metadata
            
            return {
                "success": True,
                "data": {
                    "title": metadata.title if metadata else None,
                    "author": metadata.author if metadata else None,
                    "subject": metadata.subject if metadata else None,
                    "creator": metadata.creator if metadata else None,
                    "total_pages": len(reader.pages)
                },
                "error": None
            }
        
        except Exception as e:
            logger.error(f"获取 PDF 元数据失败 {file_path}: {e}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
