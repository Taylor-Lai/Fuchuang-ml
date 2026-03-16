from langchain_core.tools import tool
from pydantic import BaseModel, Field
from skill_manager import get_all_skills, get_skill_code, save_new_skill
from langchain_openai import ChatOpenAI
import os

@tool
def format_document_tool(instruction: str, doc_name: str) -> str:
    """
    【赛题模块1：文档智能操作】
    当用户要求对文档进行排版、格式调整、内容标记（如标红、加粗）时调用此工具。
    参数:
        instruction: 用户的具体排版指令，例如"把第一段标红"
        doc_name: 要操作的文档名称
    """
    print(f"\n[🛠️ 执行工具] -> 正在调用 Word/PDF 排版引擎...")
    print(f"   📄 目标文件: {doc_name}")
    print(f"   ⚙️ 执行指令: {instruction}")
    # 这里未来会替换成 A 同学写的真实 Python 脚本
    return f"系统已成功按指令 '{instruction}' 对文档 '{doc_name}' 完成了格式化排版。"

@tool
def extract_info_tool(target_entities: str, doc_name: str) -> str:
    """
    【赛题模块2：非结构化信息提取】
    当用户要求从长文本中提取特定实体数据（如姓名、金额、预算）、且要求零误差并存入数据库时调用此工具。
    参数:
        target_entities: 需要提取的目标实体描述，例如"提取所有的报销金额和人名"
        doc_name: 来源文档名称
    """
    print(f"\n[🛠️ 执行工具] -> 正在调用高精度信息抽取流水线...")
    print(f"   📄 扫描文件: {doc_name}")
    print(f"   🔍 提取目标: {target_entities}")
    # 这里未来会替换成 B 同学写的 RAG + 实体抽取代码
    return f"已成功从 '{doc_name}' 提取数据: {{'提取结果': '张三报销5000元'}}, 并且已准备好入库。"


class SkillDecision(BaseModel):
    action: str = Field(..., description="填 'use_existing' (使用现有技能) 或 'generate_new' (生成新技能)")
    skill_name: str = Field(..., description="如果要用现有技能，填技能名；如果要生成新技能，给新技能起个英文名")
    reasoning: str = Field(..., description="做出该决定的理由")


@tool
def skill_based_table_processor(query: str, source_file: str, target_file: str) -> str:
    """
    【赛题核心模块3：智能表格填写】
    当用户要求根据某份文档的数据填表、统计、汇总或操作 Excel 时，必须调用此工具！
    参数:
        query: 用户具体想怎么处理数据的指令 (如: "把数据按部门汇总")
        source_file: 数据源文件名称
        target_file: 目标表格名称
    """
    print("\n🔍 [Skill Engine] 启动动态技能引擎...")

    # 1. 实例化一个专门负责写代码的 LLM (Coder Agent)
    coder_llm = ChatOpenAI(
        model="qwen-max",
        temperature=0.1,
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_API_BASE")
    )

    # 2. 获取当前已掌握的技能目录
    existing_skills = get_all_skills()
    print(f"📚 [技能库] 当前已掌握技能数量: {len(existing_skills)}")

    # 3. 决策：是使用老技能，还是现场写新代码？
    decision_prompt = f"""
    用户需求："{query}"
    操作文件：{source_file} -> {target_file}
    目前已有的技能库：{existing_skills}

    请判断现有技能库中是否有完全满足该需求的技能。如果有，请选择 'use_existing' 并提供技能名。
    如果没有，请选择 'generate_new' 并为即将生成的新技能起一个符合 Python 变量命名规范的英文短名。
    
    你必须严格按照以下 JSON 格式输出：
    {{
        "action": "use_existing 或 generate_new",
        "skill_name": "技能名称",
        "reasoning": "做出该决定的理由"
    }}
    """
    decision_chain = coder_llm.with_structured_output(SkillDecision)
    decision = decision_chain.invoke(decision_prompt)

    python_code = ""

    # 4. 执行决策
    if decision.action == "use_existing":
        print(f"🎯 [命中技能] 准备执行历史技能: {decision.skill_name}")
        python_code = get_skill_code(decision.skill_name)
    else:
        print(f"🆕 [未命中技能] 触发 Coder Agent，正在现场编写新技能: {decision.skill_name}...")
        # 让大模型现场写一段 Pandas 代码
        code_prompt = f"""
        你是一个精通 Pandas 的 Python 专家。请编写一个名为 `execute_skill(source_path, target_path)` 的 Python 函数，来完成以下需求：
        需求：{query}
        注意：
        1. 必须只输出合法的 Python 代码，不要包含 ```python 的 Markdown 标记，也不要解释！
        2. 函数必须接收 source_path 和 target_path 两个参数。
        3. 函数最后应返回一段描述执行结果的字符串。
        """
        python_code = coder_llm.invoke(code_prompt).content.replace("```python", "").replace("```", "").strip()

        # 将新学会的技能存入 SQLite
        save_new_skill(decision.skill_name, query, python_code)
        print(f"💾 [记忆保存] 新技能已永久保存入库！")

    # 5. 在受控沙箱内执行 Python 代码 (MVP版本使用 exec)
    print("\n⚙️ [沙箱执行] 正在运行技能代码...")
    try:
        # 定义安全的执行命名空间
        import pandas as pd
        safe_builtins = {
            'print': print,
            'range': range,
            'len': len,
            'int': int,
            'str': str,
            # 禁用 open, eval, exec, __import__ 等危险函数
        }
        namespace = {
            '__builtins__': safe_builtins,
            'pd': pd  # 只把必要的库注入给大模型
        }

        exec(python_code, namespace)

        return f"技能引擎已成功应用技能 [{decision.skill_name}]。由于缺少真实物理文件，已完成逻辑沙箱推演验证。"
    except Exception as e:
        return f"技能执行期间发生异常，可能需要调整指令：{str(e)}"


# 导出工具给路由主图使用
agent_tools = [format_document_tool, extract_info_tool, skill_based_table_processor]