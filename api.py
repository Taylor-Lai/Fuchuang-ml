# api.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
import uvicorn

# 导入你已经写好的 LangGraph 引擎 (这里的 app 就是编译好的 workflow)
from agent import app as agent_app

# 实例化 FastAPI
app = FastAPI(
    title="A23项目 Agent 核心引擎 API",
    description="提供给 Go 网关调用的底层大模型调度接口",
    version="1.0.0"
)


# ==========================================
# 1. 定义接口交互的数据模型 (DTO)
# ==========================================
class ChatRequest(BaseModel):
    query: str
    thread_id: str  # Go 后端必须传一个全局唯一的任务ID过来


class ChatResponse(BaseModel):
    status: str  # "completed" 或 "pending_human_approval"
    reply: str  # 大模型的回复
    thread_id: str


class ResumeRequest(BaseModel):
    thread_id: str
    action: str  # "approve" (目前只支持同意放行)


# ==========================================
# 2. 核心路由：对话与任务分发接口
# ==========================================
# 注意：这里用 def 而不是 async def，因为我们底层的 LangChain 调用是同步的
@app.post("/chat", response_model=ChatResponse)
def chat_with_agent(request: ChatRequest):
    print(f"\n[API 接收请求] Thread: {request.thread_id} | Query: {request.query}")

    config = {"configurable": {"thread_id": request.thread_id}}
    initial_state = {"messages": [HumanMessage(content=request.query)]}

    final_ai_msg = "系统正在处理中..."

    try:
        # 运转状态机
        for event in agent_app.stream(initial_state, config, stream_mode="values"):
            last_message = event["messages"][-1]
            # 捕获大模型的最终文本回复（过滤掉调用工具的中间过程）
            if last_message.type == "ai" and not last_message.tool_calls:
                final_ai_msg = last_message.content

        # 检查图谱是否因为 "人工审核" 被挂起了
        state = agent_app.get_state(config)
        if state.next:
            print("⏸️ [API 状态] 触发人工拦截点，已挂起。")
            return ChatResponse(
                status="pending_human_approval",
                reply="⚠️ 系统已提取关键数据。此操作需要人工授权入库，请确认。",
                thread_id=request.thread_id
            )

        # 正常执行完毕
        return ChatResponse(
            status="completed",
            reply=final_ai_msg,
            thread_id=request.thread_id
        )

    except Exception as e:
        print(f"❌ [API 报错] {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# 3. 核心路由：人工审核恢复接口
# ==========================================
@app.post("/resume", response_model=ChatResponse)
def resume_agent(request: ResumeRequest):
    print(f"\n[API 接收放行] Thread: {request.thread_id}")

    config = {"configurable": {"thread_id": request.thread_id}}
    state = agent_app.get_state(config)

    # 检查这个任务是不是真的被挂起了
    if not state.next:
        raise HTTPException(status_code=400, detail="未找到需要授权的挂起任务。")

    final_ai_msg = "操作已恢复执行..."

    try:
        if request.action == "approve":
            # 传入 None，告诉状态机继续往下跑
            for event in agent_app.stream(None, config, stream_mode="values"):
                last_message = event["messages"][-1]
                if last_message.type == "ai" and not last_message.tool_calls:
                    final_ai_msg = last_message.content

            return ChatResponse(
                status="completed",
                reply=final_ai_msg,
                thread_id=request.thread_id
            )
        else:
            raise HTTPException(status_code=400, detail="暂不支持的操作类型。")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # 启动服务器 (默认运行在 8000 端口)
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)