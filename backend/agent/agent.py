"""
Agent 核心模块
协调整个检索流程，管理工具调用和 LLM 交互
"""

from typing import Dict, Any, List, Optional
import logging
import json
import sys
from pathlib import Path

# 添加 backend 目录到 Python 路径
backend_path = Path(__file__).parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from .llm_manager import LLMManager
from skill_engine.skill_parser import SkillParser
from skill_engine.executor import SkillExecutor
from skill_engine.tool_registry import ToolRegistry
from tools import GrepTool, ReadTool, PDFTool, ExcelTool
from websocket_server import (
    push_thinking_step,
    push_tool_call,
    push_answer,
    push_answer_stream,
    push_error,
    should_stop
)

logger = logging.getLogger(__name__)


class Agent:
    """Agent 核心类"""
    
    def __init__(
        self,
        client_id: str,
        knowledge_root: str = "knowledge",
        skill_path: str = "rag-skill",
        config_path: str = "config.yaml"
    ):
        """
        初始化 Agent
        
        Args:
            client_id: 客户端 ID
            knowledge_root: 知识库根目录
            skill_path: Skill 目录路径
            config_path: 配置文件路径
        """
        self.client_id = client_id
        self.knowledge_root = knowledge_root
        self.skill_path = skill_path
        self.config_path = config_path
        
        # 初始化组件
        self.llm_manager = LLMManager(config_path)
        self.skill_parser = SkillParser(skill_path)
        self.skill_executor = SkillExecutor(knowledge_root, skill_path)
        self.tool_registry = ToolRegistry()
        
        # 注册工具
        self._register_tools()
        
        # 状态
        self.retrieval_round = 0
        self.max_retrieval_rounds = 5
        self.context: List[Dict[str, Any]] = []  # 检索上下文
    
    def _register_tools(self):
        """注册所有工具"""
        self.tool_registry.register("Grep", GrepTool(self.knowledge_root))
        self.tool_registry.register("Read", ReadTool(self.knowledge_root))
        self.tool_registry.register("PDF", PDFTool(self.knowledge_root))
        self.tool_registry.register("Excel", ExcelTool(self.knowledge_root))
    
    def _read_file_content(self, file_path: str) -> str:
        """
        读取文件内容（用于读取 SKILL.md 和 references 文件）
        
        Args:
            file_path: 文件路径（相对于项目根目录）
            
        Returns:
            str: 文件内容
        """
        try:
            full_path = Path(self.skill_path).parent / file_path
            if not full_path.exists():
                logger.error(f"文件不存在：{full_path}")
                return ""
            
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"读取文件失败 {file_path}: {e}")
            return ""
    
    async def process_query(self, question: str):
        """
        处理用户查询（完全 LLM 驱动的流程）
        
        Args:
            question: 用户问题
        """
        try:
            # 检查是否应该停止
            if should_stop(self.client_id):
                logger.info(f"检测到停止信号，终止处理：{self.client_id}")
                return
            
            # ==================== 第 1 步：获取 SKILL.md 内容 ====================
            await push_thinking_step(self.client_id, "第 1 步", "正在读取 SKILL.md 文件内容...")
            skill_content = self._read_file_content("rag-skill/SKILL.md")
            
            if not skill_content:
                await push_error(self.client_id, "Skill 加载失败", "无法读取 SKILL.md 文件")
                return
            
            logger.info(f"SKILL.md 内容长度：{len(skill_content)} 字符")
            
            # 检查是否应该停止
            if should_stop(self.client_id):
                logger.info(f"检测到停止信号，终止处理：{self.client_id}")
                return
            
            # ==================== 第 2 步：读取用户问题 ====================
            await push_thinking_step(self.client_id, "第 2 步", f"解析用户问题：{question}")
            logger.info(f"用户问题：{question}")
            
            # 检查是否应该停止
            if should_stop(self.client_id):
                logger.info(f"检测到停止信号，终止处理：{self.client_id}")
                return
            
            # ==================== 第 3 步：LLM 驱动的递归导航 ====================
            await push_thinking_step(self.client_id, "第 3 步", "开始 LLM 驱动的递归导航...")
            target_file = await self._llm_driven_navigation(question, "")  # 从 knowledge 根目录开始
            
            # 检查是否应该停止
            if should_stop(self.client_id):
                logger.info(f"检测到停止信号，终止处理：{self.client_id}")
                return
            
            if not target_file:
                await push_answer_stream(
                    self.client_id, 
                    "抱歉，我在知识库中没有找到与您的问题相关的内容。\n\n请尝试：\n- 换一种方式描述您的问题\n- 提供更多关键词或上下文\n- 确认您的问题是否在知识库覆盖范围内", 
                    is_done=True
                )
                return
            
            logger.info(f"最终定位到文件：{target_file}")
            
            # 检查是否应该停止
            if should_stop(self.client_id):
                logger.info(f"检测到停止信号，终止处理：{self.client_id}")
                return
            
            # ==================== 第 4 步：根据文件类型选择工具 ====================
            await push_thinking_step(self.client_id, "第 4 步", "正在分析文件类型，选择工具...")
            selected_tool = await self._select_tool_by_file_type(target_file)
            
            # 检查是否应该停止
            if should_stop(self.client_id):
                logger.info(f"检测到停止信号，终止处理：{self.client_id}")
                return
            
            if not selected_tool:
                await push_error(self.client_id, "选择工具失败", "无法确定使用哪个工具")
                return
            
            logger.info(f"选择的工具：{selected_tool}")
            
            # 检查是否应该停止
            if should_stop(self.client_id):
                logger.info(f"检测到停止信号，终止处理：{self.client_id}")
                return
            
            # ==================== 第 5 步：获取工具 schema，决定处理方法 ====================
            await push_thinking_step(self.client_id, "第 5 步", "正在分析工具方法，决定处理流程...")
            execution_plan = await self._plan_tool_execution(selected_tool, target_file, question)
            
            # 检查是否应该停止
            if should_stop(self.client_id):
                logger.info(f"检测到停止信号，终止处理：{self.client_id}")
                return
            
            if not execution_plan:
                await push_error(self.client_id, "规划失败", "无法确定处理方法")
                return
            
            logger.info(f"执行计划：{execution_plan}")
            
            # 检查是否应该停止
            if should_stop(self.client_id):
                logger.info(f"检测到停止信号，终止处理：{self.client_id}")
                return
            
            # ==================== 第 6 步：按顺序执行工具方法 ====================
            await push_thinking_step(self.client_id, "第 6 步", "正在执行工具方法...")
            processed_content = await self._execute_tool_plan(selected_tool, execution_plan, target_file)
            
            # 检查是否应该停止
            if should_stop(self.client_id):
                logger.info(f"检测到停止信号，终止处理：{self.client_id}")
                return
            
            if not processed_content:
                await push_error(self.client_id, "执行失败", "无法处理文件")
                return
            
            # 检查是否应该停止
            if should_stop(self.client_id):
                logger.info(f"检测到停止信号，终止处理：{self.client_id}")
                return
            
            # ==================== 第 7 步：生成最终答案（流式输出） ====================
            await push_thinking_step(self.client_id, "第 7 步", "正在生成最终答案...")
            await self._generate_final_answer_stream(question, processed_content, [target_file])
            
        except Exception as e:
            logger.error(f"处理查询失败：{e}", exc_info=True)
            await push_error(self.client_id, "处理查询失败", str(e))
    
    async def _llm_driven_navigation(self, question: str, current_dir: str) -> str:
        """
        LLM 驱动的递归导航（第 3 步）
        
        Args:
            question: 用户问题
            current_dir: 当前目录路径（相对于 knowledge 根目录）
            
        Returns:
            str: 目标文件路径
        """
        # 读取当前目录下的 data_structure.md 文件
        data_structure_content = self._read_data_structure(current_dir)
        
        if not data_structure_content:
            logger.warning(f"无法读取 data_structure.md：{current_dir}")
            return ""
        
        # 显示当前导航位置
        await push_thinking_step(
            self.client_id,
            "导航位置",
            f"当前目录：{current_dir if current_dir else 'knowledge 根目录'}"
        )
        
        # 让 LLM 分析 data_structure.md 和用户问题
        messages = [{
            "role": "user",
            "content": f"""
你是一个知识库导航助手。请根据用户问题和当前目录的 data_structure.md 文件内容，判断下一步应该：
1. 进入某个子目录（返回目录名）
2. 选择某个文件（返回文件名）

用户问题：{question}

当前目录：{current_dir if current_dir else "knowledge 根目录"}

当前目录的 data_structure.md 文件内容：
{data_structure_content}

请分析并返回：
- 如果应该进入子目录，返回：目录名（必须是 data_structure.md 中列出的目录名）
- 如果应该选择文件，返回：文件名（必须是 data_structure.md 中列出的文件名）
- 如果没有任何相关内容，返回：NONE

重要规则：
1. 你只能返回 data_structure.md 中实际存在的目录名或文件名
2. 不要返回任何其他内容，只返回一个名称或 NONE
3. 如果有多个相关选项，选择最直接相关的
4. 不要尝试回答用户问题，只负责导航到最相关的文件
"""
        }]
        
        result = await self.llm_manager.chat(messages, temperature=0.1)
        
        if not result["success"]:
            logger.error("LLM 分析失败")
            return ""
        
        llm_response = result["data"]["content"].strip()
        logger.info(f"LLM 建议：{llm_response}")
        
        # 检查 LLM 是否返回了无效响应
        if not llm_response or llm_response.lower() == 'none' or llm_response == '':
            logger.warning(f"LLM 返回无效响应：{llm_response}")
            await push_thinking_step(
                self.client_id,
                "导航失败",
                "LLM 无法确定应该进入哪个目录或选择哪个文件"
            )
            return ""
        
        # 判断是目录还是文件
        # 检查是否是文件（有扩展名）
        if '.' in llm_response and not llm_response.endswith('/'):
            # 是文件
            file_path = f"{current_dir}/{llm_response}" if current_dir else llm_response
            await push_thinking_step(
                self.client_id, 
                "导航结果", 
                f"找到目标文件：{file_path}"
            )
            return file_path
        else:
            # 是目录，递归调用
            next_dir = f"{current_dir}/{llm_response}" if current_dir else llm_response
            await push_thinking_step(
                self.client_id,
                "导航结果",
                f"进入目录：{next_dir}"
            )
            logger.info(f"进入目录：{next_dir}")
            
            # 递归调用，传入新的目录路径
            return await self._llm_driven_navigation(question, next_dir)
    
    def _read_data_structure(self, relative_path: str) -> str:
        """
        读取 data_structure.md 文件内容
        
        Args:
            relative_path: 相对于 knowledge 目录的路径
            
        Returns:
            str: 文件内容
        """
        try:
            if relative_path:
                full_path = Path(self.knowledge_root) / relative_path / "data_structure.md"
            else:
                full_path = Path(self.knowledge_root) / "data_structure.md"
            
            if not full_path.exists():
                logger.error(f"data_structure.md 不存在：{full_path}")
                return ""
            
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"读取 data_structure.md 失败：{e}")
            return ""
    
    async def _select_tool_by_file_type(self, file_path: str) -> str:
        """
        根据文件类型选择工具（第 4 步）
        
        Args:
            file_path: 目标文件路径
            
        Returns:
            str: 工具名称
        """
        # 获取文件扩展名
        file_ext = Path(file_path).suffix.lower()
        
        # 获取已注册的工具列表
        tools_list = self.tool_registry.list_tools()
        logger.info(f"可用工具：{tools_list}")
        
        messages = [{
            "role": "user",
            "content": f"""
你是一个文件处理专家。请根据文件扩展名选择最合适的工具。

目标文件：{file_path}
文件扩展名：{file_ext}

可用的工具列表：
{chr(10).join([f"{i+1}. {tool}" for i, tool in enumerate(tools_list)])}

请根据文件扩展名，从上面的工具列表中选择一个最合适的工具。

重要提示：
- 你必须从上面的工具列表中选择一个工具名称
- 只返回工具名称（例如：PDF 或 Excel 或 Read），不要返回其他任何内容
- 不要返回文件名或目录名
- 工具名称必须与列表中的名称完全一致（区分大小写）

示例：
- 如果文件是 .pdf，返回：PDF
- 如果文件是 .xlsx，返回：Excel
- 如果文件是 .md 或 .txt，返回：Read
"""
        }]
        
        result = await self.llm_manager.chat(messages, temperature=0.1)
        
        if result["success"]:
            tool_name = result["data"]["content"].strip()
            
            # 验证工具名是否在可用工具列表中
            if tool_name in tools_list:
                return tool_name
            else:
                logger.error(f"LLM 返回的工具名 '{tool_name}' 不在可用工具列表中")
                # 尝试根据文件扩展名自动选择
                if file_ext == '.pdf':
                    return 'PDF'
                elif file_ext in ['.xlsx', '.xls']:
                    return 'Excel'
                elif file_ext in ['.md', '.txt']:
                    return 'Read'
                else:
                    return 'Read'  # 默认使用 Read 工具
        
        return ""
    
    async def _plan_tool_execution(self, tool_name: str, file_path: str, question: str) -> List[Dict[str, Any]]:
        """
        获取工具 schema，让 LLM 决定处理方法和顺序（第 5 步）
        
        Args:
            tool_name: 工具名称
            file_path: 目标文件路径
            question: 用户问题
            
        Returns:
            List[Dict]: 执行计划列表，每个元素包含 method 和 parameters
        """
        # 获取工具 schema
        tool_schema = self.tool_registry.get_tool_schema(tool_name)
        logger.info(f"工具 schema：{tool_schema}")
        
        messages = [{
            "role": "user",
            "content": f"""
你是一个工具使用专家。请根据工具 schema、用户问题和文件信息，决定如何处理这个文件。

工具名称：{tool_name}

工具 schema：
{tool_schema}

目标文件：{file_path}

用户问题：{question}

请分析并返回执行计划，格式如下：
```json
[
  {{"method": "方法名", "parameters": {{"参数名": "参数值"}}}},
  {{"method": "方法名", "parameters": {{"参数名": "参数值"}}}}
]
```

重要提示：
- method 必须是 schema 中定义的方法
- parameters 必须符合 schema 中定义的参数要求
- 如果需要多个方法，按执行顺序排列
- 只返回 JSON 数组，不要其他内容
- file_path 参数会自动传入，不需要在 parameters 中指定

示例：
```json
[
  {{"method": "extract_text_with_pdftotext", "parameters": {{}}}}
]
```
"""
        }]
        
        result = await self.llm_manager.chat(messages, temperature=0.1)
        
        if not result["success"]:
            return []
        
        # 解析 LLM 返回的 JSON
        try:
            content = result["data"]["content"].strip()
            # 提取 JSON 部分（去除 markdown 代码块标记）
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            execution_plan = json.loads(content)
            return execution_plan
        except Exception as e:
            logger.error(f"解析执行计划失败：{e}")
            return []
    
    async def _execute_tool_plan(self, tool_name: str, execution_plan: List[Dict[str, Any]], file_path: str) -> str:
        """
        按顺序执行工具方法（第 6 步）
        
        Args:
            tool_name: 工具名称
            execution_plan: 执行计划
            file_path: 目标文件路径
            
        Returns:
            str: 处理后的内容
        """
        all_content = []
        
        for i, step in enumerate(execution_plan, 1):
            method = step.get("method", "")
            parameters = step.get("parameters", {})
            
            # 添加 file_path 参数
            parameters["file_path"] = file_path
            
            await push_thinking_step(
                self.client_id, 
                f"执行步骤 {i}", 
                f"正在执行 {tool_name}.{method}..."
            )
            
            logger.info(f"执行 {tool_name}.{method}，参数：{parameters}")
            
            result = self.tool_registry.execute(tool_name, method, **parameters)
            
            if result["success"]:
                # 提取内容
                if "output_file" in result.get("data", {}):
                    # PDF 工具返回临时文件路径
                    text_file = result["data"]["output_file"]
                    with open(text_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                elif "content" in result.get("data", {}):
                    # Read 工具返回内容
                    content = result["data"]["content"]
                elif "data" in result:
                    # Excel 工具返回数据
                    content = json.dumps(result["data"], ensure_ascii=False, indent=2)
                else:
                    content = str(result.get("data", ""))
                
                all_content.append(f"=== {method} 结果 ===\n{content}")
                logger.info(f"{tool_name}.{method} 执行成功")
            else:
                logger.error(f"{tool_name}.{method} 执行失败：{result.get('error')}")
                all_content.append(f"=== {method} 失败 ===\n{result.get('error')}")
        
        return "\n\n".join(all_content)
    
    async def _generate_final_answer(self, question: str, processed_content: str) -> str:
        """
        生成最终答案（第 7 步）
        
        Args:
            question: 用户问题
            processed_content: 处理后的内容
            
        Returns:
            str: 最终答案
        """
        messages = [{
            "role": "user",
            "content": f"""
你是一个知识库问答助手。请根据用户问题和处理后的文件内容，生成准确的答案。

用户问题：{question}

处理后的文件内容：
{processed_content[:5000]}  # 限制长度

请生成清晰、准确的答案。如果内容不足以回答问题，请明确说明。
"""
        }]
        
        result = await self.llm_manager.chat(messages, temperature=0.7)
        
        if result["success"]:
            return result["data"]["content"]
        
        return "抱歉，无法生成答案。"
    
    async def _generate_final_answer_stream(self, question: str, processed_content: str, sources: list):
        """
        生成最终答案（流式输出）
        
        Args:
            question: 用户问题
            processed_content: 处理后的内容
            sources: 来源文件列表
        """
        messages = [{
            "role": "user",
            "content": f"""
你是一个知识库问答助手。请根据用户问题和处理后的文件内容，生成准确的答案。

用户问题：{question}

处理后的文件内容：
{processed_content[:5000]}  # 限制长度

请生成清晰、准确的答案。如果内容不足以回答问题，请明确说明。
"""
        }]
        
        try:
            # 流式生成答案
            async for chunk in self.llm_manager.chat_stream(
                messages, 
                temperature=0.7,
                stop_check=lambda: should_stop(self.client_id)
            ):
                # 推送每个内容片段
                await push_answer_stream(self.client_id, chunk, is_done=False)
            
            # 推送完成消息
            await push_answer_stream(self.client_id, "", is_done=True, sources=sources)
            
        except Exception as e:
            logger.error(f"流式生成答案失败：{e}", exc_info=True)
            await push_error(self.client_id, "生成答案失败", str(e))
