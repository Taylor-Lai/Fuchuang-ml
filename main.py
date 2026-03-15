from langchain_core.messages import HumanMessage
from agent import app
import sys

# 假设这是某个特定任务的全局唯一 ID
# 只要 thread_id 不变，Agent 永远能从数据库里找回它的记忆
config = {"configurable": {"thread_id": "a23_task_001"}}


def start_task():
    print("\n[系统] 接收到前端新任务，正在拉起 Agent...")
    initial_state = {"messages": [HumanMessage(content="把昨天的会议纪要关键数据提取一下存进数据库。")]}

    # 第一次运行：它跑到断点就会把状态写入 SQLite 然后挂起
    for event in app.stream(initial_state, config, stream_mode="values"):
        pass

    state = app.get_state(config)
    if state.next:
        print(f"\n⏸️ [程序已挂起] Agent 已停止运行，数据已持久化到 SQLite。")
        print("💡 你现在可以按 Ctrl+C 彻底关闭这个 Python 脚本！")
        print("💡 假设过了 3 个小时，老板终于在前端点击了'确认'，请运行: python main.py resume")


def resume_task():
    print("\n[系统] 收到网关的恢复执行信号，正在从 SQLite 唤醒 Agent...")
    state = app.get_state(config)

    if not state.next:
        print("❌ 没有找到被挂起的任务，或者任务已经执行完毕。")
        return

    print(f"✅ 成功找回历史状态！即将执行节点: {state.next[0]}")
    print("▶️ [恢复执行] 人类已授权，继续跑完剩下的流程...\n")

    # 传入 None 触发继续执行
    for event in app.stream(None, config, stream_mode="values"):
        if event["messages"][-1].type == "ai" and not event["messages"][-1].tool_calls:
            print(f"\n🤖 Agent 最终回复: {event['messages'][-1].content}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "resume":
        resume_task()
    else:
        start_task()