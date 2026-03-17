import json
from parser import parse_folder

if __name__ == "__main__":
    chunks = parse_folder("./test_docs")

    for chunk in chunks[:5]:
        print(json.dumps(chunk.dict(), ensure_ascii=False, indent=2))

    with open("mock_chunks_for_B.json", "w", encoding="utf-8") as f:
        json.dump([c.dict() for c in chunks], f, ensure_ascii=False, indent=2)

    print(f"已导出 mock_chunks.json，共 {len(chunks)} 条")
