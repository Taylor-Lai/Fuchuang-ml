from langchain_core.tools import tool

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

@tool
def auto_fill_table_tool(source_doc: str, target_excel: str) -> str:
    """
    【赛题模块3：表格自动填写】
    当用户要求根据某份文档的数据，自动填写或生成一个 Excel/表格时调用此工具。
    参数:
        source_doc: 提供数据的源文件
        target_excel: 需要被填写的模板表格名称
    """
    print(f"\n[🛠️ 执行工具] -> 正在调用 Pandas 智能填表引擎...")
    print(f"   📥 数据来源: {source_doc}")
    print(f"   📤 目标表格: {target_excel}")
    # 这里未来会替换成你写的 Pandas 填表逻辑
    return f"已自动从 '{source_doc}' 检索相关信息，并成功填入表格 '{target_excel}' 中。"

# 导出工具列表供 Agent 使用
agent_tools = [format_document_tool, extract_info_tool, auto_fill_table_tool]