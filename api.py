from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
import uvicorn

from agent import app as agent_app
from local_kg_engine import init_kg_db  # 导入初始化函数

# 🌟 在 FastAPI 启动前，先初始化知识图谱
init_kg_db()

app = FastAPI(title="A23 Agent API")


class ChatRequest(BaseModel):
    query: str
    thread_id: str


class ChatResponse(BaseModel):
    status: str
    reply: str
    thread_id: str


@app.post("/chat", response_model=ChatResponse)
def chat_with_agent(request: ChatRequest):
    config = {"configurable": {"thread_id": request.thread_id}}
    initial_state = {"messages": [HumanMessage(content=request.query)]}
    final_ai_msg = "处理中..."

    try:
        # 注意：因为你在 agent.py 去掉了 checkpointer，这里跑完是不记仇的（每次都是新对话）
        # 如果需要记仇，要在 api.py 里显式传入 MemorySaver 给 app.stream
        for event in agent_app.stream(initial_state, config, stream_mode="values"):
            last_message = event["messages"][-1]
            if last_message.type == "ai" and not last_message.tool_calls:
                final_ai_msg = last_message.content

        state = agent_app.get_state(config)
        if state.next:
            return ChatResponse(
                status="pending_human_approval",
                reply="⚠️ 系统已提取关键数据。此操作需要人工授权入库，请确认。",
                thread_id=request.thread_id
            )

        return ChatResponse(status="completed", reply=final_ai_msg, thread_id=request.thread_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)