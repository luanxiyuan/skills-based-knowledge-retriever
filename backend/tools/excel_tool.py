"""
Excel 处理工具
使用 pandas 读取和分析 Excel 文件
"""

from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import logging
import json

logger = logging.getLogger(__name__)


class ExcelTool:
    """Excel 处理工具类"""
    
    def __init__(self, knowledge_root: str):
        """
        初始化 Excel 工具
        
        Args:
            knowledge_root: 知识库根目录
        """
        self.knowledge_root = Path(knowledge_root)
    
    def read_sheet(
        self,
        file_path: str,
        sheet_name: Optional[Union[str, int]] = 0,
        nrows: Optional[int] = None,
        usecols: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        读取 Excel 工作表
        
        Args:
            file_path: Excel 文件路径（相对于 knowledge_root）
            sheet_name: 工作表名称或索引（0 表示第一个）
            nrows: 最大读取行数
            usecols: 要读取的列名列表
            
        Returns:
            dict: {
                "success": bool,
                "data": {
                    "columns": List[str],  # 列名
                    "rows": List[List],  # 数据行
                    "total_rows": int,  # 总行数
                    "sheet_name": str,  # 工作表名称
                    "shape": Tuple[int, int]  # 数据形状（行，列）
                },
                "error": str
            }
        """
        try:
            import pandas as pd
            
            full_path = self.knowledge_root / file_path
            
            if not full_path.exists():
                return {
                    "success": False,
                    "data": None,
                    "error": f"文件不存在：{file_path}"
                }
            
            # 读取 Excel
            df = pd.read_excel(
                full_path,
                sheet_name=sheet_name,
                nrows=nrows,
                usecols=usecols
            )
            
            # 获取工作表名称
            with pd.ExcelFile(full_path) as xls:
                if isinstance(sheet_name, int):
                    actual_sheet_name = xls.sheet_names[sheet_name]
                else:
                    actual_sheet_name = sheet_name or xls.sheet_names[0]
            
            # 转换为列表格式
            rows = df.values.tolist()
            columns = df.columns.tolist()
            
            return {
                "success": True,
                "data": {
                    "columns": columns,
                    "rows": rows,
                    "total_rows": len(df),
                    "sheet_name": actual_sheet_name,
                    "shape": df.shape
                },
                "error": None
            }
        
        except Exception as e:
            logger.error(f"读取 Excel 工作表失败 {file_path}: {e}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
    
    def get_sheet_names(self, file_path: str) -> Dict[str, Any]:
        """
        获取 Excel 文件的所有工作表名称
        
        Args:
            file_path: Excel 文件路径（相对于 knowledge_root）
            
        Returns:
            dict: {
                "success": bool,
                "data": {
                    "sheet_names": List[str],  # 工作表名称列表
                    "file": str  # 文件名
                },
                "error": str
            }
        """
        try:
            import pandas as pd
            
            full_path = self.knowledge_root / file_path
            
            if not full_path.exists():
                return {
                    "success": False,
                    "data": None,
                    "error": f"文件不存在：{file_path}"
                }
            
            with pd.ExcelFile(full_path) as xls:
                sheet_names = xls.sheet_names
            
            return {
                "success": True,
                "data": {
                    "sheet_names": sheet_names,
                    "file": file_path
                },
                "error": None
            }
        
        except Exception as e:
            logger.error(f"获取工作表名称失败 {file_path}: {e}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
    
    def analyze_column(
        self,
        file_path: str,
        sheet_name: Optional[Union[str, int]] = 0,
        column_name: Optional[str] = None,
        column_index: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        分析 Excel 列的统计信息
        
        Args:
            file_path: Excel 文件路径（相对于 knowledge_root）
            sheet_name: 工作表名称或索引
            column_name: 列名
            column_index: 列索引（从 0 开始）
            
        Returns:
            dict: {
                "success": bool,
                "data": {
                    "column_name": str,
                    "dtype": str,
                    "count": int,
                    "unique": int,
                    "null_count": int,
                    "statistics": Dict  # 数值列的统计信息
                },
                "error": str
            }
        """
        try:
            import pandas as pd
            
            full_path = self.knowledge_root / file_path
            
            if not full_path.exists():
                return {
                    "success": False,
                    "data": None,
                    "error": f"文件不存在：{file_path}"
                }
            
            # 读取数据
            df = pd.read_excel(full_path, sheet_name=sheet_name)
            
            # 确定列
            if column_name is None and column_index is None:
                return {
                    "success": False,
                    "data": None,
                    "error": "必须指定 column_name 或 column_index"
                }
            
            if column_name:
                column = df[column_name]
                actual_column_name = column_name
            else:
                column = df.iloc[:, column_index]
                actual_column_name = df.columns[column_index]
            
            # 基本统计信息
            stats = {
                "column_name": actual_column_name,
                "dtype": str(column.dtype),
                "count": int(column.count()),
                "unique": int(column.nunique()),
                "null_count": int(column.isnull().sum())
            }
            
            # 数值列的详细统计
            if pd.api.types.is_numeric_dtype(column):
                stats["statistics"] = {
                    "mean": float(column.mean()) if not column.isnull().all() else None,
                    "std": float(column.std()) if not column.isnull().all() else None,
                    "min": float(column.min()) if not column.isnull().all() else None,
                    "max": float(column.max()) if not column.isnull().all() else None,
                    "median": float(column.median()) if not column.isnull().all() else None
                }
            
            # 非数值列的 top values
            if not pd.api.types.is_numeric_dtype(column):
                top_values = column.value_counts().head(10).to_dict()
                stats["top_values"] = {str(k): int(v) for k, v in top_values.items()}
            
            return {
                "success": True,
                "data": stats,
                "error": None
            }
        
        except Exception as e:
            logger.error(f"分析 Excel 列失败 {file_path}: {e}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
    
    def filter_data(
        self,
        file_path: str,
        sheet_name: Optional[Union[str, int]] = 0,
        query: Optional[str] = None,
        column_filter: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        过滤 Excel 数据
        
        Args:
            file_path: Excel 文件路径（相对于 knowledge_root）
            sheet_name: 工作表名称或索引
            query: pandas query 字符串（如 "age > 30 and city == 'Beijing'"）
            column_filter: 列过滤条件字典（如 {"city": "Beijing", "age": 30}）
            
        Returns:
            dict: {
                "success": bool,
                "data": {
                    "columns": List[str],
                    "rows": List[List],
                    "total_rows": int,
                    "filtered_rows": int
                },
                "error": str
            }
        """
        try:
            import pandas as pd
            
            full_path = self.knowledge_root / file_path
            
            if not full_path.exists():
                return {
                    "success": False,
                    "data": None,
                    "error": f"文件不存在：{file_path}"
                }
            
            # 读取数据
            df = pd.read_excel(full_path, sheet_name=sheet_name)
            original_rows = len(df)
            
            # 应用过滤
            if query:
                df = df.query(query)
            
            if column_filter:
                for col, value in column_filter.items():
                    if col in df.columns:
                        df = df[df[col] == value]
            
            filtered_rows = len(df)
            
            return {
                "success": True,
                "data": {
                    "columns": df.columns.tolist(),
                    "rows": df.values.tolist(),
                    "total_rows": original_rows,
                    "filtered_rows": filtered_rows
                },
                "error": None
            }
        
        except Exception as e:
            logger.error(f"过滤 Excel 数据失败 {file_path}: {e}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
    
    def to_json(self, file_path: str, sheet_name: Optional[Union[str, int]] = 0) -> Dict[str, Any]:
        """
        将 Excel 数据转换为 JSON 格式
        
        Args:
            file_path: Excel 文件路径（相对于 knowledge_root）
            sheet_name: 工作表名称或索引
            
        Returns:
            dict: {
                "success": bool,
                "data": {
                    "json": str,  # JSON 字符串
                    "records": int  # 记录数
                },
                "error": str
            }
        """
        try:
            import pandas as pd
            
            full_path = self.knowledge_root / file_path
            
            if not full_path.exists():
                return {
                    "success": False,
                    "data": None,
                    "error": f"文件不存在：{file_path}"
                }
            
            df = pd.read_excel(full_path, sheet_name=sheet_name)
            json_str = df.to_json(orient='records', force_ascii=False)
            
            return {
                "success": True,
                "data": {
                    "json": json_str,
                    "records": len(df)
                },
                "error": None
            }
        
        except Exception as e:
            logger.error(f"转换 Excel 为 JSON 失败 {file_path}: {e}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
