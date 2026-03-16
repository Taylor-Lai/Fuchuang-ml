from langchain_core.messages import HumanMessage
from agent import app
import time
import uuid  # 引入随机ID生成库


def run_test(query: str, thread_id: str):
    print(f"\n\n{'=' * 70}")
    print(f"🧑‍💻 用户指令: {query}")
    print(f"{'=' * 70}")

    config = {"configurable": {"thread_id": thread_id}}
    initial_state = {"messages": [HumanMessage(content=query)]}

    for event in app.stream(initial_state, config, stream_mode="values"):
        last_message = event["messages"][-1]
        if last_message.type == "ai" and not last_message.tool_calls:
            print(f"\n🤖 Agent 最终回复:\n{last_message.content}")


if __name__ == "__main__":
    # 【核心改动】：每次测试使用全新的随机 Thread ID，避免读取到上一次崩溃的坏死记忆！
    fresh_thread_id_1 = str(uuid.uuid4())
    fresh_thread_id_2 = str(uuid.uuid4())

    print("\n>>> 场景一：初次面临全新的财务报表汇总任务 <<<")
    run_test(
        "帮我把《2026年Q1华东区销售明细.xlsx》里的数据，按产品类别汇总求和，填入《年度利润统计模板.xlsx》",
        thread_id=fresh_thread_id_1
    )

    print("\n\n>>> 场景二：下个月，再次面临同类汇总任务 <<<")
    # 为了演示技能复用，这里传入与场景一相同的 thread_id 也是可以的，
    # 但我们为了严谨证明技能库生效，即使开启全新对话(fresh_thread_id_2)，它也能从 SQLite 技能库中读到刚才学过的技能！
    run_test(
        "小助手，帮我把《2026年Q2华东区销售明细.xlsx》的数据，也按产品类别汇总填入《年度利润统计模板.xlsx》",
        thread_id=fresh_thread_id_2
    )