from langchain_core.tools import tool
from pydantic import BaseModel, Field
from skill_manager import get_all_skills, get_skill_code, save_new_skill
from langchain_openai import ChatOpenAI
import os
import sqlite3
from local_kg_engine import search_knowledge_graph # 导入本地图谱引擎

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

# 🌟 新增：本地知识图谱检索工具
@tool
def knowledge_graph_tool(query_entity: str) -> str:
    """
    【核心知识库检索】
    当用户询问复杂的业务事实、项目背景、人员关系、规章制度等问题时调用此工具。
    参数:
        query_entity: 你从用户问题中提取出的核心实体名称。
    """
    print(f"\n🕸️ [调用本地图谱] 正在查询实体: {query_entity}")
    try:
        result = search_knowledge_graph(entity=query_entity)
        return result
    except Exception as e:
        return f"图谱查询发生异常: {str(e)}"

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

    print("\n⚙️ [沙箱执行] 正在注入真实物理数据与 DB 权限并运行代码...")
    try:
        import pandas as pd

        # 🔥 核心升级：打开企业核心数据库的连接
        # 注意：这里假设你本地有一个 enterprise_data.db 存放了提取出的非结构化数据
        db_conn = sqlite3.connect('enterprise_data.db')

        # 把 pandas 和 数据库连接 一并注入无菌手术台
        namespace = {'pd': pd, 'db_conn': db_conn}

        # 编译大模型写的代码
        exec(python_code, namespace)

        if 'execute_skill' not in namespace:
            return "执行失败：代码中未包含 execute_skill 函数。"

        func_to_run = namespace['execute_skill']

        # 真正调用函数
        result = func_to_run(source_file, target_file)

        print(f"✅ [执行成功] 底层返回: {result}")
        return f"技能执行成功！反馈是：{result}"

    except Exception as e:
        print(f"❌ [执行报错] {str(e)}")
        return f"执行异常：{str(e)}"
    finally:
        # 记得关闭数据库连接
        if 'db_conn' in locals():
            db_conn.close()


# 导出工具给路由主图使用
agent_tools = [format_document_tool, extract_info_tool, skill_based_table_processor, knowledge_graph_tool]