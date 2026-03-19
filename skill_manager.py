import sqlite3

DB_PATH = "enterprise_skills.db"

def init_skill_db():
    """初始化技能数据库"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS skills (
            skill_id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_name TEXT UNIQUE,
            description TEXT,
            code_snippet TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_all_skills():
    """获取当前所有已学会的技能简述，供大模型挑选"""
    with sqlite3.connect(DB_PATH) as conn: # 使用 with，即使报错也会自动关闭
        cursor = conn.cursor()
        cursor.execute("SELECT skill_name, description FROM skills")
        rows = cursor.fetchall()
        return [{"name": r[0], "description": r[1]} for r in rows]

def get_skill_code(skill_name: str) -> str:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT code_snippet FROM skills WHERE skill_name=?", (skill_name,))
        row = cursor.fetchone()
        return row[0] if row else None

def save_new_skill(name: str, description: str, code: str):
    """保存大模型新学会的技能"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO skills (skill_name, description, code_snippet) VALUES (?, ?, ?)",
                       (name, description, code))
        conn.commit()
    except sqlite3.IntegrityError:
        print(f"⚠️ 技能 {name} 已存在，跳过保存。")
    finally:
        conn.close()

# 初始化建表
init_skill_db()