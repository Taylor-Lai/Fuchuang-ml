import os
from dotenv import load_dotenv
from typing import Annotated, Literal
from typing_extensions import TypedDict
from pydantic import BaseModel, Field

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage

# 导入你写好的工具
from tools import agent_tools

load_dotenv()

# ==========================================
# 1. 定义数据结构 (Schema & State)
# ==========================================
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    intent: str # 记录当前任务的意图 (format/extract/fill_table)

class RouteDecision(BaseModel):
    """强制路由器输出的结构"""
    intent: Literal["format", "extract", "fill_table", "chat"] = Field(..., description="用户的核心意图类别")
    reasoning: str = Field(..., description="分类理由")

# ==========================================
# 2. 初始化模型与路由器
# ==========================================
llm = ChatOpenAI(
    model="qwen-max",
    temperature=0,
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_API_BASE")
)
llm_with_tools = llm.bind_tools(agent_tools)

router_prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一个流量分发路由器。请将用户指令精确分类到以下 4 个处理流：
    1. "format": 文档排版、修改格式。
    2. "extract": 信息提取、找数据入库。
    3. "fill_table": 填写表格、跨表汇总数据、Excel 处理（此路径将触发高级技能引擎）。
    4. "chat": 闲聊或无法识别的指令。
    
    你必须严格按照以下 JSON 格式输出，不要多说任何其他内容：
    {{
        "intent": "类别名称",
        "reasoning": "分类理由"
    }}
    
    示例：
    用户输入："把昨天的会议纪要关键数据提取一下存进数据库。"
    输出：{{"intent": "extract", "reasoning": "用户需要从文档中提取数据并存入数据库"}}
    
    重要：必须包含 intent 和 reasoning 两个字段！"""
    ),
    ("user", "{user_input}")
])
# 组装结构化路由器
structured_router = router_prompt | llm.with_structured_output(RouteDecision)

# ==========================================
# 3. 定义图谱节点 (Nodes)
# ==========================================
def router_node(state: AgentState):
    """节点1：只做意图识别，不执行任何工具"""
    print("\n🚥 [路由节点] 正在分析用户意图...")
    user_input = state["messages"][-1].content
    decision = structured_router.invoke({"user_input": user_input})
    print(f"   => 判定意图: {decision.intent} (理由: {decision.reasoning})")
    return {"intent": decision.intent}

def reasoning_node(state: AgentState):
    """节点2：根据意图，大模型思考并决定调用哪个工具"""
    print("[思考节点] 大模型正在决策执行步骤...")
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

# ==========================================
# 4. 定义路由条件 (Edges)
# ==========================================
def route_after_intent(state: AgentState) -> str:
    """根据意图，决定下一步去哪"""
    if state["intent"] == "chat":
        return "chat_end" # 闲聊直接结束
    return "reasoning" # 其他业务指令，进入思考和工具调用

def route_after_reasoning(state: AgentState) -> str:
    """如果大模型决定用工具，就去执行；否则结束"""
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        # 如果是信息提取，我们强制走人工审核断点！
        if state["intent"] == "extract":
            print("\n⚠️ [系统拦截] 触发信息提取，即将挂起等待人工确认...")
            return "human_review_breakpoint"
        return "tools"
    return END

# ==========================================
# 5. 组装状态机工作流
# ==========================================
workflow = StateGraph(AgentState)

# 注册所有节点
workflow.add_node("router", router_node)
workflow.add_node("reasoning", reasoning_node)
workflow.add_node("tools", ToolNode(agent_tools))
workflow.add_node("human_review_breakpoint", ToolNode(agent_tools))

# 设置入口
workflow.add_edge(START, "router")

# 设置条件分发
workflow.add_conditional_edges(
    "router",
    route_after_intent,
    {"reasoning": "reasoning", "chat_end": END}
)
workflow.add_conditional_edges(
    "reasoning",
    route_after_reasoning,
    {"tools": "tools", "human_review_breakpoint": "human_review_breakpoint", END: END}
)

# 工具执行完回到思考节点
workflow.add_edge("tools", "reasoning")
workflow.add_edge("human_review_breakpoint", "reasoning")

#配置长期存储数据库
# check_same_thread=False 允许在微服务/API环境下跨线程访问数据库
db_path = "enterprise_agent_state.db"
conn = sqlite3.connect(db_path, check_same_thread=False)

# 实例化持久化检查点
memory = SqliteSaver(conn)

# 编译图谱（挂载数据库引擎）
app = workflow.compile(
    checkpointer=memory,
    interrupt_before=["human_review_breakpoint"]
)
