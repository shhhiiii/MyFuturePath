import sqlite3

class DBManager:
    def __init__(self, db_path: str = "myfuturepath.db"):
        self.db_path = db_path
        self.create_tables()
        self.default_insert()

    def connect(self):
        return sqlite3.connect(self.db_path)

    def create_tables(self):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    chat_id INTEGER PRIMARY KEY,
                    telegram_id INTEGER UNIQUE,
                    name TEXT,
                    profession TEXT,
                    experience TEXT,
                    interests TEXT,
                    expert_mode INTEGER DEFAULT 0
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS faq (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT,
                    answer TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ai_questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    role TEXT,
                    content TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS career_questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS career_options (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question_id INTEGER,
                    option_text TEXT,
                    career_ids TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS careers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    linkedin_url TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS career_progress (
                    user_id INTEGER,
                    current_q INTEGER,
                    selected_careers TEXT DEFAULT '',
                    PRIMARY KEY(user_id)
                )
            """)

            conn.commit()

    def default_insert(self):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM faq")
            if cursor.fetchone()[0] == 0:
                faq_data = [
                    ("Do I have to pay to use the bot?", "No, the bot is free."),
                    ("Can I save professions I like?", "Yes, through the ⭐ My interests menu."),
                    ("What if I didn't find a suitable profession?",
                    "Try to describe yourself differently. For example: not 'I want IT', but 'I like dealing with computers and programming'."),
                    ("Who is this bot for?", "For teenagers, adults and anyone who is looking for new directions in their career.")
                ]
                cursor.executemany("INSERT INTO faq (question, answer) VALUES (?, ?)", faq_data)

            cursor.execute("SELECT COUNT(*) FROM ai_questions")
            if cursor.fetchone()[0] == 0:
                ai_qs = [
                    ("Which school subjects did you like the most?"),
                    ("Do you prefer working with people or with computers?"),
                    ("What suits you more: creative work or strict rules and structure?"),
                    ("Would you like to work in an office or remotely?"),
                    ("What is more important to you: a high salary or interesting work?"),
                    ("Imagine you have a lot of free time: what would you do?")
                ]
                cursor.executemany("INSERT INTO ai_questions (question) VALUES (?)", [(q,) for q in ai_qs])

            cursor.execute("SELECT COUNT(*) FROM career_questions")
            if cursor.fetchone()[0] == 0:
                questions = [
                    "Do you prefer working with people or with technology?",
                    "What is more important for you in a job?",
                    "Where would you like to work?",
                ]
                cursor.executemany("INSERT INTO career_questions (question) VALUES (?)", [(q,) for q in questions])

            cursor.execute("SELECT COUNT(*) FROM career_options")
            if cursor.fetchone()[0] == 0:
                options = [
                    (1, "👥 With people", "1,2"),        # HR, teacher
                    (1, "💻 With technology", "3,4"),    # Programmer, designer
                    (2, "💰 High salary", "3"),          # Programmer
                    (2, "✨ Creativity", "4"),           # Designer
                    (2, "📖 Helping people", "1,2"),     # HR, teacher
                    (3, "🏢 In an office", "1,3"),       # HR, programmer
                    (3, "🏠 Remote work", "3,4"),        # Programmer, designer
                    (3, "🏫 At school/university", "2"), # Teacher
                ]
                cursor.executemany("INSERT INTO career_options (question_id, option_text, career_ids) VALUES (?, ?, ?)", options)

            cursor.execute("SELECT COUNT(*) FROM careers")
            if cursor.fetchone()[0] == 0:
                careers = [
                    ("HR Specialist", "https://www.linkedin.com/jobs/hr/"),
                    ("Teacher", "https://www.linkedin.com/jobs/teacher/"),
                    ("Programmer", "https://www.linkedin.com/jobs/developer/"),
                    ("Designer", "https://www.linkedin.com/jobs/designer/"),
                ]
                cursor.executemany("INSERT INTO careers (name, linkedin_url) VALUES (?, ?)", careers)

            conn.commit()

    def init_career_progress(self, user_id: int):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("REPLACE INTO career_progress (user_id, current_q, selected_careers) VALUES (?, ?, ?)",
                        (user_id, 1, ""))
            conn.commit()

    def update_progress(self, user_id: int, current_q: int, selected_careers: list[int]):
        with self.connect() as conn:
            cursor = conn.cursor()
            career_str = ",".join(map(str, selected_careers))
            cursor.execute("UPDATE career_progress SET current_q = ?, selected_careers = ? WHERE user_id = ?",
                        (current_q, career_str, user_id))
            conn.commit()

    def get_progress(self, user_id: int):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT current_q, selected_careers FROM career_progress WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                return None
            current_q, selected = row
            ids = [int(x) for x in selected.split(",") if x.strip().isdigit()]
            return {"current_q": current_q, "selected_careers": ids}

    def clear_progress(self, user_id: int):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM career_progress WHERE user_id = ?", (user_id,))
            conn.commit()


    def get_career_question(self, qid: int):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT question FROM career_questions WHERE id = ?", (qid,))
            question = cursor.fetchone()
            if not question:
                return None
            cursor.execute("SELECT id, option_text FROM career_options WHERE question_id = ?", (qid,))
            options = cursor.fetchall()
            return {"id": qid, "question": question[0], "options": options}

    def get_career_by_ids(self, ids: list[int]):
        with self.connect() as conn:
            cursor = conn.cursor()
            qmarks = ",".join("?" * len(ids))
            cursor.execute(f"SELECT name, linkedin_url FROM careers WHERE id IN ({qmarks})", ids)
            return cursor.fetchall()

    def add_user(self, telegram_id: int, name: str, profession: str, experience: str, interests: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""INSERT OR REPLACE INTO users (chat_id, telegram_id, name, profession, experience, interests)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (telegram_id, telegram_id, name, profession, experience, interests))
            conn.commit()
    def add_message(self, user_id: int, role: str, content: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)", (user_id, role, content))
            conn.commit()

    def get_history(self, user_id: int, limit: int = 20):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT role, content FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit))
            rows = cursor.fetchall()
            return [{"role": r, "content": c} for r, c in rows[::-1]]

    def clear_history(self, user_id: int):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
            conn.commit()



    def get_user(self, chat_id):
        with self.connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE chat_id = ?", (chat_id,))
            row = cur.fetchone()
            if row:
                columns = [col[0] for col in cur.description]
                return dict(zip(columns, row))
            return None

    def set_expert_mode(self, telegram_id: int, status: bool):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET expert_mode = ? WHERE telegram_id = ?", (1 if status else 0, telegram_id))
            conn.commit()

    def get_expert_mode(self, telegram_id: int) -> bool:
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT expert_mode FROM users WHERE telegram_id = ?", (telegram_id,))
            result = cursor.fetchone()
            return bool(result[0]) if result else False


    def update_interests(self, telegram_id: int, interests: str):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET interests = ? WHERE telegram_id = ?", (interests, telegram_id))
            conn.commit()

    def get_interests(self, telegram_id: int) -> str:
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT interests FROM users WHERE telegram_id = ?", (telegram_id,))
            result = cursor.fetchone()
            return result[0] if result else ""
    def set_expert_mode(self, telegram_id: int, status: bool):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET expert_mode = ? WHERE telegram_id = ?", (1 if status else 0, telegram_id))
            conn.commit()

    def get_expert_mode(self, telegram_id: int) -> bool:
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT expert_mode FROM users WHERE telegram_id = ?", (telegram_id,))
            result = cursor.fetchone()
            return bool(result[0]) if result else False

    def get_faq(self):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT question, answer FROM faq")
            return cursor.fetchall()

    def get_ai_questions(self):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT question FROM ai_questions")
            return [row[0] for row in cursor.fetchall()]
