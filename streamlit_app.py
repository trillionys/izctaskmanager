import streamlit as st
import sqlite3
from datetime import date, datetime
import random
import hashlib
import os

# =========================================================
# 기본 설정
# =========================================================
st.set_page_config(
    page_title="Yeonsu Task Manager",
    page_icon="👻",
    layout="wide"
)

DB_NAME = "workflow.db"

# =========================================================
# 디자인
# =========================================================
st.markdown("""
<style>
:root {
    --navy: #2B3A67;
    --mint: #5BC0BE;
    --cream: #F7F9FB;
    --coral: #FF8E72;
}
.stApp { background-color: var(--cream); }
h1, h2, h3 { color: var(--navy); font-weight: 800; }
section[data-testid="stSidebar"] {
    background-color: white;
    border-right: 1px solid #e8edf3;
}
.stButton > button {
    background-color: var(--navy);
    color: white;
    border-radius: 14px;
    border: none;
    padding: 0.6rem 1rem;
    font-weight: 700;
}
.stButton > button:hover {
    background-color: var(--mint);
    color: white;
}
.card {
    background-color: white;
    padding: 18px;
    border-radius: 20px;
    box-shadow: 0 4px 14px rgba(43,58,103,0.08);
    margin-bottom: 18px;
}
.small-note { color: #6b7280; font-size: 0.95rem; }
.badge {
    display: inline-block;
    padding: 6px 12px;
    border-radius: 999px;
    background-color: #E7F8F7;
    color: var(--navy);
    font-weight: 700;
}
[data-testid="stDataFrame"],
[data-testid="stDataEditor"] {
    background-color: white;
    border-radius: 18px;
    padding: 10px;
    box-shadow: 0 4px 14px rgba(43,58,103,0.05);
}
div[data-testid="stMetric"] {
    background-color: white;
    padding: 16px;
    border-radius: 18px;
    box-shadow: 0 4px 14px rgba(43,58,103,0.08);
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# DB 연결 및 초기화
# =========================================================
def get_conn():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

conn = get_conn()
cur = conn.cursor()


def init_db():
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password_hash TEXT,
        salt TEXT,
        reset_code TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        situation TEXT,
        step_order INTEGER,
        next_task TEXT,
        task_weekday TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS work_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        work_date TEXT,
        weekday TEXT,
        situation TEXT,
        task TEXT,
        is_done TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS important_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        task TEXT,
        is_done TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS manual_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        work_date TEXT,
        weekday TEXT,
        task TEXT,
        is_done TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        project_name TEXT,
        news_date TEXT,
        preorder_date TEXT,
        main_open_date TEXT,
        end_date TEXT,
        memo TEXT
    )
    """)

    conn.commit()


def add_column_if_missing(table, column, col_type):
    cur.execute(f"PRAGMA table_info({table})")
    columns = [c[1] for c in cur.fetchall()]
    if column not in columns:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        conn.commit()


init_db()
add_column_if_missing("users", "reset_code", "TEXT")
for table_name in ["rules", "work_logs", "important_tasks", "manual_tasks", "projects"]:
    add_column_if_missing(table_name, "user_id", "INTEGER")

# =========================================================
# 회원가입 / 로그인
# =========================================================
def make_salt():
    return os.urandom(16).hex()


def hash_password(password, salt):
    return hashlib.sha256((password + salt).encode()).hexdigest()


def create_user(username, password, reset_code):
    salt = make_salt()
    password_hash = hash_password(password, salt)
    try:
        cur.execute(
            """
            INSERT INTO users (username, password_hash, salt, reset_code)
            VALUES (?, ?, ?, ?)
            """,
            (username, password_hash, salt, reset_code)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def login_user(username, password):
    cur.execute(
        """
        SELECT id, username, password_hash, salt
        FROM users
        WHERE username = ?
        """,
        (username,)
    )
    user = cur.fetchone()
    if user is None:
        return None

    user_id, saved_username, saved_hash, salt = user
    if hash_password(password, salt) == saved_hash:
        return {"id": user_id, "username": saved_username}
    return None


if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None

if not st.session_state.logged_in:
    st.markdown(
        """
        <div class="card">
        <h1>👻 Yeonsu Task Manager</h1>
        <p class="small-note">회원가입 또는 로그인 후 사용할 수 있습니다.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    tab_login, tab_signup, tab_reset = st.tabs(["로그인", "회원가입", "비밀번호 재설정"])

    with tab_login:
        login_username = st.text_input("아이디", key="login_username")
        login_password = st.text_input("비밀번호", type="password", key="login_password")

        if st.button("로그인"):
            user = login_user(login_username, login_password)
            if user:
                st.session_state.logged_in = True
                st.session_state.user_id = user["id"]
                st.session_state.username = user["username"]
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호가 올바르지 않습니다.")

    with tab_signup:
        signup_username = st.text_input("새 아이디", key="signup_username")
        signup_password = st.text_input("새 비밀번호", type="password", key="signup_password")
        signup_password_confirm = st.text_input("비밀번호 확인", type="password", key="signup_password_confirm")
        signup_reset_code = st.text_input(
            "비밀번호 재설정 코드",
            key="signup_reset_code",
            placeholder="비밀번호를 잊었을 때 사용할 본인 확인 코드"
        )

        if st.button("회원가입"):
            if signup_username.strip() == "" or signup_password.strip() == "":
                st.warning("아이디와 비밀번호를 입력해주세요.")
            elif signup_password != signup_password_confirm:
                st.warning("비밀번호가 서로 다릅니다.")
            elif signup_reset_code.strip() == "":
                st.warning("비밀번호 재설정 코드를 입력해주세요.")
            else:
                if create_user(signup_username, signup_password, signup_reset_code):
                    st.success("회원가입이 완료되었습니다. 로그인해주세요.")
                else:
                    st.error("이미 존재하는 아이디입니다.")

    with tab_reset:
        reset_username = st.text_input("아이디", key="reset_username")
        input_reset_code = st.text_input("비밀번호 재설정 코드", key="input_reset_code")
        new_password = st.text_input("새 비밀번호", type="password", key="new_password")
        new_password_confirm = st.text_input("새 비밀번호 확인", type="password", key="new_password_confirm")

        if st.button("비밀번호 재설정"):
            if reset_username.strip() == "":
                st.warning("아이디를 입력해주세요.")
            elif new_password.strip() == "":
                st.warning("새 비밀번호를 입력해주세요.")
            elif new_password != new_password_confirm:
                st.warning("새 비밀번호가 서로 다릅니다.")
            else:
                cur.execute(
                    """
                    SELECT id, reset_code
                    FROM users
                    WHERE username = ?
                    """,
                    (reset_username,)
                )
                user = cur.fetchone()
                if user is None:
                    st.error("존재하지 않는 아이디입니다.")
                elif user[1] != input_reset_code:
                    st.error("재설정 코드가 올바르지 않습니다.")
                else:
                    new_salt = make_salt()
                    new_hash = hash_password(new_password, new_salt)
                    cur.execute(
                        """
                        UPDATE users
                        SET password_hash = ?, salt = ?
                        WHERE id = ?
                        """,
                        (new_hash, new_salt, user[0])
                    )
                    conn.commit()
                    st.success("비밀번호가 재설정되었습니다. 다시 로그인해주세요.")

    st.stop()

user_id = st.session_state.user_id

# =========================================================
# 공통 함수
# =========================================================
weekdays = ["월", "화", "수", "목", "금", "토", "일", "요일 무관"]
real_weekdays = ["월", "화", "수", "목", "금", "토", "일"]


def get_korean_weekday(selected_date):
    return real_weekdays[selected_date.weekday()]


def fetch_rules_by_weekday(weekday):
    cur.execute(
        """
        SELECT situation, step_order, next_task, task_weekday
        FROM rules
        WHERE user_id = ?
        AND (task_weekday = ? OR task_weekday = '요일 무관')
        ORDER BY situation, step_order, task_weekday
        """,
        (user_id, weekday)
    )
    return cur.fetchall()


def fetch_rules_by_situation(keyword):
    cur.execute(
        """
        SELECT situation, step_order, next_task, task_weekday
        FROM rules
        WHERE user_id = ?
        AND situation LIKE ?
        ORDER BY situation, step_order, task_weekday
        """,
        (user_id, f"%{keyword}%")
    )
    return cur.fetchall()


def auto_register_today_tasks(today, today_weekday):
    tasks = fetch_rules_by_weekday(today_weekday)
    seen = set()

    for situation, step_order, task, task_weekday in tasks:
        key = (situation, task)
        if key in seen:
            continue
        seen.add(key)

        cur.execute(
            """
            SELECT COUNT(*)
            FROM work_logs
            WHERE user_id = ?
            AND work_date = ?
            AND situation = ?
            AND task = ?
            """,
            (user_id, str(today), situation, task)
        )
        exists = cur.fetchone()[0]

        if exists == 0:
            cur.execute(
                """
                INSERT INTO work_logs
                (user_id, work_date, weekday, situation, task, is_done)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, str(today), today_weekday, situation, task, "미완료")
            )
    conn.commit()


def calc_project_progress(today, news_date, preorder_date, main_open_date, end_date):
    preorder = datetime.strptime(preorder_date, "%Y-%m-%d").date()
    main_open = datetime.strptime(main_open_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()

    if today < preorder:
        return 0, "소식 확인 단계"

    if preorder <= today < main_open:
        total = max((main_open - preorder).days, 1)
        passed = (today - preorder).days
        return min(int((passed / total) * 25), 24), "사전예약 진행 중"

    if main_open <= today <= end:
        total = max((end - main_open).days, 1)
        passed = (today - main_open).days
        return min(25 + int((passed / total) * 75), 100), "본청약 진행 중"

    return 100, "종료 / 후속절차 필요"


def save_status_or_delete(table_name, row, editable_task=False):
    if row["삭제"]:
        cur.execute(
            f"DELETE FROM {table_name} WHERE id = ? AND user_id = ?",
            (row["ID"], user_id)
        )
    else:
        if editable_task:
            cur.execute(
                f"UPDATE {table_name} SET task = ?, is_done = ? WHERE id = ? AND user_id = ?",
                (row["업무"], "완료" if row["완료"] else "미완료", row["ID"], user_id)
            )
        else:
            cur.execute(
                f"UPDATE {table_name} SET is_done = ? WHERE id = ? AND user_id = ?",
                ("완료" if row["완료"] else "미완료", row["ID"], user_id)
            )

# =========================================================
        if situation.strip() == "":
            st.warning("상황을 입력해주세요.")
        else:
            saved_count = 0
            for step_order, task, days in tasks_input:
                if task.strip() != "":
                    if len(days) == 0:
                        st.warning(f"{step_order}단계 업무의 요일을 선택해주세요.")
                    else:
                        for day in days:
                            cur.execute(
                                """
                                INSERT INTO rules (user_id, situation, step_order, next_task, task_weekday)
                                VALUES (?, ?, ?, ?, ?)
                                """,
                                (user_id, situation.strip(), step_order, task.strip(), day)
                            )
                            saved_count += 1
            conn.commit()
            if saved_count > 0:
                st.success("업무 상황이 저장되었습니다.")
                st.rerun()
            else:
                st.warning("저장된 업무가 없습니다.")

    st.subheader("등록된 업무 목록")
    cur.execute(
        """
        SELECT id, situation, step_order, next_task, task_weekday
        FROM rules
        WHERE user_id = ?
        ORDER BY situation, step_order, task_weekday
        """,
        (user_id,)
    )
    rules = cur.fetchall()
    if rules:
        grouped = {}
        for rid, sit, step, task, day in rules:
            key = (sit, step, task)
            if key not in grouped:
                grouped[key] = {"삭제": False, "ID목록": [], "상황": sit, "단계": step, "업무": task, "요일": []}
            grouped[key]["ID목록"].append(rid)
            grouped[key]["요일"].append(day)

        rows = []
        for item in grouped.values():
            rows.append({
                "삭제": False,
                "ID목록": ",".join(map(str, item["ID목록"])),
                "상황": item["상황"],
                "단계": item["단계"],
                "업무": item["업무"],
                "요일": ", ".join(item["요일"])
            })
        edited = st.data_editor(rows, hide_index=True, use_container_width=True, disabled=["ID목록", "상황", "단계", "업무", "요일"], key="rules_editor")
        if st.button("선택 업무 삭제"):
            delete_ids = []
            for row in edited:
                if row["삭제"]:
                    delete_ids.extend(row["ID목록"].split(","))
            for rid in delete_ids:
                cur.execute("DELETE FROM rules WHERE id = ? AND user_id = ?", (rid, user_id))
            conn.commit()
            st.success("삭제되었습니다.")
            st.rerun()
    else:
        st.info("등록된 업무가 없습니다.")
# =========================================================
        SELECT id, work_date, weekday, situation, task, is_done
        FROM work_logs
        WHERE user_id = ? AND work_date = ?
        ORDER BY id DESC
        """,
        (user_id, str(selected_date))
    )
    auto_logs = cur.fetchall()

    cur.execute(
        """
        SELECT id, work_date, weekday, task, is_done
        FROM manual_tasks
        WHERE user_id = ? AND work_date = ?
        ORDER BY id DESC
        """,
        (user_id, str(selected_date))
    )
    manual_logs = cur.fetchall()

    rows = []
    for log in auto_logs:
        rows.append({"구분": "자동", "삭제": False, "완료": log[5] == "완료", "ID": log[0], "날짜": log[1], "요일": log[2], "상황": log[3], "업무": log[4]})
    for log in manual_logs:
        rows.append({"구분": "직접", "삭제": False, "완료": log[4] == "완료", "ID": log[0], "날짜": log[1], "요일": log[2], "상황": "직접 추가", "업무": log[3]})

    if rows:
        edited = st.data_editor(rows, hide_index=True, use_container_width=True, disabled=["구분", "ID", "날짜", "요일", "상황"], key="date_log_editor")
        if st.button("기록 변경사항 저장"):
            for row in edited:
                if row["구분"] == "자동":
                    if row["삭제"]:
                        cur.execute("DELETE FROM work_logs WHERE id = ? AND user_id = ?", (row["ID"], user_id))
                    else:
                        cur.execute("UPDATE work_logs SET is_done = ? WHERE id = ? AND user_id = ?", ("완료" if row["완료"] else "미완료", row["ID"], user_id))
                else:
                    if row["삭제"]:
                        cur.execute("DELETE FROM manual_tasks WHERE id = ? AND user_id = ?", (row["ID"], user_id))
                    else:
                        cur.execute("UPDATE manual_tasks SET task = ?, is_done = ? WHERE id = ? AND user_id = ?", (row["업무"], "완료" if row["완료"] else "미완료", row["ID"], user_id))
            conn.commit()
            st.success("저장되었습니다.")
            st.rerun()
    else:
        st.info("해당 날짜 기록 없음")

# =========================================================
# 요일별 추천
# =========================================================
else:
    selected_weekday = menu
    st.header(f"{selected_weekday} 추천 업무")

    tasks = fetch_rules_by_weekday(selected_weekday)
    if tasks:
        rows = []
        seen = set()
        for situation, step_order, task, day in tasks:
            key = (situation, step_order, task)
            if key in seen:
                continue
            seen.add(key)
            rows.append({"완료": False, "상황": situation, "단계": step_order, "업무": task, "요일": day})

        edited = st.data_editor(rows, hide_index=True, use_container_width=True, disabled=["상황", "단계", "업무", "요일"], key="weekday_editor")
        save_date = st.date_input("기록 날짜", date.today())

        if st.button("요일 업무 저장"):
            for row in edited:
                cur.execute(
                    """
                    INSERT INTO work_logs (user_id, work_date, weekday, situation, task, is_done)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, str(save_date), selected_weekday, row["상황"], row["업무"], "완료" if row["완료"] else "미완료")
                )
            conn.commit()
            st.success("저장되었습니다.")
            st.rerun()
    else:
        st.info("등록된 업무 없음")

conn.close()