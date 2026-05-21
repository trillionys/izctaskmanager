import streamlit as st
import sqlite3
from datetime import date, datetime
import random
import hashlib

st.set_page_config(
    page_title="Yeonsu Task Manager",
    page_icon="👻",
    layout="wide"
)

# =============================
# 로그인 설정
# =============================
APP_USERNAME = "yeonsu"
APP_PASSWORD = "1234"

def check_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

PASSWORD_HASH = check_password(APP_PASSWORD)

if "login" not in st.session_state:
    st.session_state.login = False

if not st.session_state.login:
    st.title("👻 Yeonsu Task Manager")
    st.subheader("로그인")

    username = st.text_input("아이디")
    password = st.text_input("비밀번호", type="password")

    if st.button("로그인"):
        if username == APP_USERNAME and check_password(password) == PASSWORD_HASH:
            st.session_state.login = True
            st.rerun()
        else:
            st.error("아이디 또는 비밀번호가 틀렸습니다.")

    st.info("기본 아이디: yeonsu / 비밀번호: 1234")
    st.stop()

# =============================
# 디자인
# =============================
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
.badge {
    display: inline-block;
    padding: 6px 12px;
    border-radius: 999px;
    background-color: #E7F8F7;
    color: var(--navy);
    font-weight: 700;
    margin-bottom: 10px;
}
.small-note {
    color: #6b7280;
    font-size: 0.95rem;
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

# =============================
# DB
# =============================
conn = sqlite3.connect("workflow.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    situation TEXT,
    step_order INTEGER,
    next_task TEXT,
    task_weekday TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS work_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_date TEXT,
    weekday TEXT,
    situation TEXT,
    task TEXT,
    is_done TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS important_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task TEXT,
    is_done TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS manual_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_date TEXT,
    weekday TEXT,
    task TEXT,
    is_done TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_name TEXT,
    news_date TEXT,
    preorder_date TEXT,
    main_open_date TEXT,
    end_date TEXT,
    memo TEXT
)
""")

conn.commit()

weekdays = ["월", "화", "수", "목", "금", "토", "일", "요일 무관"]
real_weekdays = ["월", "화", "수", "목", "금", "토", "일"]

def get_korean_weekday(selected_date):
    return real_weekdays[selected_date.weekday()]

def fetch_rules_by_weekday(weekday):
    cursor.execute("""
    SELECT situation, step_order, next_task, task_weekday
    FROM rules
    WHERE task_weekday = ? OR task_weekday = '요일 무관'
    ORDER BY situation, step_order
    """, (weekday,))
    return cursor.fetchall()

def fetch_rules_by_situation(keyword):
    cursor.execute("""
    SELECT situation, step_order, next_task, task_weekday
    FROM rules
    WHERE situation LIKE ?
    ORDER BY situation, step_order, task_weekday
    """, (f"%{keyword}%",))
    return cursor.fetchall()

def auto_register_today_tasks(today, today_weekday):
    tasks = fetch_rules_by_weekday(today_weekday)
    seen = set()

    for situation, step_order, next_task, task_weekday in tasks:
        key = (situation, next_task)

        if key in seen:
            continue

        seen.add(key)

        cursor.execute("""
        SELECT COUNT(*)
        FROM work_logs
        WHERE work_date = ?
        AND situation = ?
        AND task = ?
        """, (str(today), situation, next_task))

        exists = cursor.fetchone()[0]

        if exists == 0:
            cursor.execute("""
            INSERT INTO work_logs
            (work_date, weekday, situation, task, is_done)
            VALUES (?, ?, ?, ?, ?)
            """, (
                str(today),
                today_weekday,
                situation,
                next_task,
                "미완료"
            ))

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
        progress = int((passed / total) * 25)
        return min(progress, 24), "사전예약 진행 중"

    if main_open <= today <= end:
        total = max((end - main_open).days, 1)
        passed = (today - main_open).days
        progress = 25 + int((passed / total) * 75)
        return min(progress, 100), "본청약 진행 중"

    return 100, "종료 / 후속절차 필요"

# =============================
# 타로
# =============================
tarot_cards = [
    ("The Fool", "새로운 시작, 가볍게 움직이면 좋은 날"),
    ("The Magician", "집중력과 실행력이 강한 날"),
    ("The High Priestess", "직감이 중요한 날"),
    ("The Empress", "성과가 자라나는 날"),
    ("The Emperor", "계획과 질서가 필요한 날"),
    ("The Lovers", "선택과 조율이 중요한 날"),
    ("The Chariot", "밀고 나가면 성과가 나는 날"),
    ("Strength", "부드러운 끈기가 필요한 날"),
    ("The Hermit", "혼자 정리하고 판단하기 좋은 날"),
    ("Wheel of Fortune", "변화의 흐름을 타야 하는 날"),
    ("Justice", "기준과 균형이 중요한 날"),
    ("The Hanged Man", "잠시 관점을 바꿔야 하는 날"),
    ("Death", "끝낼 것은 끝내야 하는 날"),
    ("Temperance", "속도 조절이 필요한 날"),
    ("The Devil", "집착이나 미루기를 조심할 날"),
    ("The Tower", "예상 밖 변동에 유연해야 하는 날"),
    ("The Star", "희망적인 방향이 보이는 날"),
    ("The Moon", "불확실한 정보는 확인이 필요한 날"),
    ("The Sun", "밝고 생산적인 흐름의 날"),
    ("Judgement", "결정과 정리가 필요한 날"),
    ("The World", "마무리와 완성에 좋은 날")
]

random.seed(str(date.today()))
card_name, card_meaning = random.choice(tarot_cards)
card_direction = random.choice(["정방향", "역방향"])

if card_direction == "역방향":
    card_meaning = "천천히 점검하세요. " + card_meaning

header_col1, header_col2 = st.columns([2.2, 1])

with header_col1:
    st.markdown("""
    <div class="card">
    <h1>👻 Yeonsu Task Manager</h1>
    <p class="small-note">
    상황별 업무 흐름과 요일별 할 일을 자동으로 정리하는 개인 업무 관리 시스템
    </p>
    </div>
    """, unsafe_allow_html=True)

with header_col2:
    st.markdown(f"""
    <div class="card">
    <h3>🔮 오늘의 타로</h3>
    <p><b>{card_name}</b></p>
    <p><span class="badge">{card_direction}</span></p>
    <p class="small-note">{card_meaning}</p>
    </div>
    """, unsafe_allow_html=True)

st.sidebar.write("👤 로그인됨")
if st.sidebar.button("로그아웃"):
    st.session_state.login = False
    st.rerun()

menu = st.sidebar.selectbox(
    "메뉴 선택",
    ["오늘 대시보드", "업무 상황 등록", "상황 입력 / 업무 추천", "날짜별 업무 기록", "프로젝트 관리"] + real_weekdays
)

# =============================
# 오늘 대시보드
# =============================
if menu == "오늘 대시보드":

    st.header("오늘 대시보드")

    today = date.today()
    today_weekday = get_korean_weekday(today)

    auto_register_today_tasks(today, today_weekday)

    col1, col2, col3 = st.columns(3)

    cursor.execute("SELECT COUNT(*) FROM work_logs WHERE work_date = ?", (str(today),))
    today_logs = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*)
    FROM work_logs
    WHERE work_date = ?
    AND is_done = '완료'
    """, (str(today),))
    today_done = cursor.fetchone()[0]

    col1.metric("오늘 날짜", str(today))
    col2.metric("오늘 요일", today_weekday)
    col3.metric("오늘 완료", f"{today_done}/{today_logs}")

    st.subheader("📌 진행 중 프로젝트")

    cursor.execute("""
    SELECT id, project_name, news_date, preorder_date, main_open_date, end_date, memo
    FROM projects
    ORDER BY end_date ASC
    """)
    projects = cursor.fetchall()

    if projects:
        for p in projects:
            progress, status = calc_project_progress(
                today,
                p[2],
                p[3],
                p[4],
                p[5]
            )

            st.markdown(f"### {p[1]}")
            st.progress(progress / 100)
            st.write(f"진행률: **{progress}%** / 상태: **{status}**")
            st.write(f"소식: {p[2]} | 사전예약: {p[3]} | 본청약: {p[4]} | 종료: {p[5]}")
            if p[6]:
                st.caption(p[6])
            st.divider()
    else:
        st.info("등록된 프로젝트가 없습니다.")

    st.subheader("⭐ 중요한 일")

    new_important = st.text_input(
        "특별히 중요한 일을 직접 입력하세요",
        placeholder="예: 오늘 대표님께 보고서 최종 전달"
    )

    if st.button("중요한 일 추가"):
        if new_important.strip() == "":
            st.warning("중요한 일을 입력해주세요.")
        else:
            cursor.execute("""
            INSERT INTO important_tasks
            (task, is_done)
            VALUES (?, ?)
            """, (new_important, "미완료"))
            conn.commit()
            st.rerun()

    cursor.execute("SELECT id, task, is_done FROM important_tasks ORDER BY id DESC")
    important_tasks = cursor.fetchall()

    if important_tasks:
        important_rows = []

        for item in important_tasks:
            important_rows.append({
                "삭제": False,
                "완료": True if item[2] == "완료" else False,
                "ID": item[0],
                "중요한 일": item[1]
            })

        edited_important = st.data_editor(
            important_rows,
            hide_index=True,
            use_container_width=True,
            disabled=["ID"],
            column_order=["삭제", "완료", "중요한 일", "ID"],
            key="important_editor"
        )

        if st.button("중요한 일 변경사항 저장"):
            for row in edited_important:
                if row["삭제"]:
                    cursor.execute("DELETE FROM important_tasks WHERE id = ?", (row["ID"],))
                else:
                    cursor.execute("""
                    UPDATE important_tasks
                    SET task = ?, is_done = ?
                    WHERE id = ?
                    """, (
                        row["중요한 일"],
                        "완료" if row["완료"] else "미완료",
                        row["ID"]
                    ))

            conn.commit()
            st.rerun()
    else:
        st.info("등록된 중요한 일이 없습니다.")

    st.subheader("➕ 오늘 새로 생긴 업무 추가")

    manual_task = st.text_input(
        "오늘 새로 생긴 업무",
        placeholder="예: 거래처에 추가 자료 보내기"
    )

    if st.button("오늘 업무에 직접 추가"):
        if manual_task.strip() == "":
            st.warning("추가할 업무를 입력해주세요.")
        else:
            cursor.execute("""
            INSERT INTO manual_tasks
            (work_date, weekday, task, is_done)
            VALUES (?, ?, ?, ?)
            """, (
                str(today),
                today_weekday,
                manual_task,
                "미완료"
            ))
            conn.commit()
            st.rerun()

    cursor.execute("""
    SELECT id, work_date, weekday, task, is_done
    FROM manual_tasks
    WHERE work_date = ?
    ORDER BY id DESC
    """, (str(today),))
    manual_logs = cursor.fetchall()

    if manual_logs:
        manual_rows = []

        for item in manual_logs:
            manual_rows.append({
                "삭제": False,
                "완료": True if item[4] == "완료" else False,
                "ID": item[0],
                "날짜": item[1],
                "요일": item[2],
                "업무": item[3]
            })

        edited_manual = st.data_editor(
            manual_rows,
            hide_index=True,
            use_container_width=True,
            disabled=["ID", "날짜", "요일"],
            column_order=["삭제", "완료", "날짜", "요일", "업무", "ID"],
            key="manual_today_editor"
        )

        if st.button("직접 추가 업무 저장"):
            for row in edited_manual:
                if row["삭제"]:
                    cursor.execute("DELETE FROM manual_tasks WHERE id = ?", (row["ID"],))
                else:
                    cursor.execute("""
                    UPDATE manual_tasks
                    SET task = ?, is_done = ?
                    WHERE id = ?
                    """, (
                        row["업무"],
                        "완료" if row["완료"] else "미완료",
                        row["ID"]
                    ))

            conn.commit()
            st.rerun()

    st.subheader("오늘 자동 등록된 업무")

    cursor.execute("""
    SELECT id, work_date, weekday, situation, task, is_done
    FROM work_logs
    WHERE work_date = ?
    ORDER BY situation, id
    """, (str(today),))

    logs = cursor.fetchall()

    if logs:
        rows = []

        for log in logs:
            rows.append({
                "삭제": False,
                "완료": True if log[5] == "완료" else False,
                "ID": log[0],
                "날짜": log[1],
                "요일": log[2],
                "상황": log[3],
                "업무": log[4]
            })

        edited_logs = st.data_editor(
            rows,
            hide_index=True,
            use_container_width=True,
            disabled=["ID", "날짜", "요일", "상황", "업무"],
            column_order=["삭제", "완료", "날짜", "요일", "상황", "업무", "ID"],
            key="today_logs_editor"
        )

        if st.button("오늘 업무 변경사항 저장"):
            for row in edited_logs:
                if row["삭제"]:
                    cursor.execute("DELETE FROM work_logs WHERE id = ?", (row["ID"],))
                else:
                    cursor.execute("""
                    UPDATE work_logs
                    SET is_done = ?
                    WHERE id = ?
                    """, (
                        "완료" if row["완료"] else "미완료",
                        row["ID"]
                    ))

            conn.commit()
            st.rerun()
    else:
        st.info("오늘 등록된 자동 업무가 없습니다.")

# =============================
# 프로젝트 관리
# =============================
elif menu == "프로젝트 관리":

    st.header("프로젝트 관리")

    project_name = st.text_input("프로젝트명")

    col1, col2 = st.columns(2)

    with col1:
        news_date = st.date_input("프로젝트 소식을 들은 시점", date.today())
        preorder_date = st.date_input("사전예약 오픈일자", date.today())

    with col2:
        main_open_date = st.date_input("본청약 오픈일자", date.today())
        end_date = st.date_input("마감일자", date.today())

    memo = st.text_area("메모")

    if st.button("프로젝트 등록"):
        if project_name.strip() == "":
            st.warning("프로젝트명을 입력해주세요.")
        elif not (news_date <= preorder_date <= main_open_date <= end_date):
            st.warning("날짜 순서는 소식일 ≤ 사전예약일 ≤ 본청약일 ≤ 마감일이어야 합니다.")
        else:
            cursor.execute("""
            INSERT INTO projects
            (project_name, news_date, preorder_date, main_open_date, end_date, memo)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (
                project_name,
                str(news_date),
                str(preorder_date),
                str(main_open_date),
                str(end_date),
                memo
            ))
            conn.commit()
            st.rerun()

    st.subheader("등록된 프로젝트")

    cursor.execute("""
    SELECT id, project_name, news_date, preorder_date, main_open_date, end_date, memo
    FROM projects
    ORDER BY end_date ASC
    """)
    projects = cursor.fetchall()

    if projects:
        rows = []

        for p in projects:
            progress, status = calc_project_progress(date.today(), p[2], p[3], p[4], p[5])

            rows.append({
                "삭제": False,
                "ID": p[0],
                "프로젝트": p[1],
                "상태": status,
                "진행률": f"{progress}%",
                "소식일": p[2],
                "사전예약": p[3],
                "본청약": p[4],
                "마감": p[5],
                "메모": p[6]
            })

        edited_projects = st.data_editor(
            rows,
            hide_index=True,
            use_container_width=True,
            disabled=["ID", "상태", "진행률"],
            column_order=["삭제", "프로젝트", "상태", "진행률", "소식일", "사전예약", "본청약", "마감", "메모", "ID"]
        )

        if st.button("프로젝트 변경사항 저장"):
            for row in edited_projects:
                if row["삭제"]:
                    cursor.execute("DELETE FROM projects WHERE id = ?", (row["ID"],))
                else:
                    cursor.execute("""
                    UPDATE projects
                    SET project_name = ?, news_date = ?, preorder_date = ?, main_open_date = ?, end_date = ?, memo = ?
                    WHERE id = ?
                    """, (
                        row["프로젝트"],
                        row["소식일"],
                        row["사전예약"],
                        row["본청약"],
                        row["마감"],
                        row["메모"],
                        row["ID"]
                    ))

            conn.commit()
            st.rerun()
    else:
        st.info("등록된 프로젝트가 없습니다.")

# =============================
# 업무 상황 등록
# =============================
elif menu == "업무 상황 등록":

    st.header("업무 상황 등록")

    situation = st.text_input("어떤 상황이 발생했을 때?")

    st.subheader("후속 업무 조치")

    tasks_input = []

    for i in range(1, 6):
        with st.expander(f"{i}단계 후속 업무", expanded=True):
            task = st.text_input(f"{i}단계 업무", key=f"task{i}")
            days = st.multiselect(f"{i}단계 실행 요일", weekdays, key=f"days{i}")
            tasks_input.append((i, task, days))

    if st.button("업무 상황 저장"):
        if situation.strip() == "":
            st.warning("상황을 입력해주세요.")
        else:
            for step_order, task, days in tasks_input:
                if task.strip() != "":
                    for day in days:
                        cursor.execute("""
                        INSERT INTO rules
                        (situation, step_order, next_task, task_weekday)
                        VALUES (?, ?, ?, ?)
                        """, (situation, step_order, task, day))

            conn.commit()
            st.rerun()

    st.subheader("등록된 업무 목록")

    cursor.execute("""
    SELECT id, situation, step_order, next_task, task_weekday
    FROM rules
    ORDER BY situation, step_order
    """)

    rules = cursor.fetchall()

    if rules:
        grouped = {}

        for rule_id, situation_name, step_order, next_task, task_weekday in rules:
            key = (situation_name, step_order, next_task)

            if key not in grouped:
                grouped[key] = {
                    "삭제": False,
                    "ID목록": [],
                    "상황": situation_name,
                    "단계": step_order,
                    "업무": next_task,
                    "요일": []
                }

            grouped[key]["ID목록"].append(rule_id)
            grouped[key]["요일"].append(task_weekday)

        table_rows = []

        for item in grouped.values():
            table_rows.append({
                "삭제": False,
                "ID목록": ",".join(map(str, item["ID목록"])),
                "상황": item["상황"],
                "단계": item["단계"],
                "업무": item["업무"],
                "요일": ", ".join(item["요일"])
            })

        edited_rules = st.data_editor(
            table_rows,
            hide_index=True,
            use_container_width=True,
            disabled=["ID목록", "상황", "단계", "업무", "요일"]
        )

        if st.button("선택 업무 삭제"):
            delete_ids = []

            for row in edited_rules:
                if row["삭제"]:
                    delete_ids.extend(row["ID목록"].split(","))

            for rule_id in delete_ids:
                cursor.execute("DELETE FROM rules WHERE id = ?", (rule_id,))

            conn.commit()
            st.rerun()
    else:
        st.info("등록된 업무가 없습니다.")

# =============================
# 상황 입력
# =============================
elif menu == "상황 입력 / 업무 추천":

    st.header("상황 입력 / 업무 추천")

    keyword = st.text_input("현재 상황 입력", placeholder="예: 계약서 수령")

    if keyword.strip() != "":
        results = fetch_rules_by_situation(keyword)

        if results:
            rows = []

            for r in results:
                rows.append({
                    "완료": False,
                    "상황": r[0],
                    "단계": r[1],
                    "업무": r[2],
                    "요일": r[3]
                })

            edited = st.data_editor(
                rows,
                hide_index=True,
                use_container_width=True,
                disabled=["상황", "단계", "업무", "요일"]
            )

            save_date = st.date_input("기록 날짜", date.today())

            if st.button("추천 업무 저장"):
                for row in edited:
                    cursor.execute("""
                    INSERT INTO work_logs
                    (work_date, weekday, situation, task, is_done)
                    VALUES (?, ?, ?, ?, ?)
                    """, (
                        str(save_date),
                        get_korean_weekday(save_date),
                        row["상황"],
                        row["업무"],
                        "완료" if row["완료"] else "미완료"
                    ))

                conn.commit()
                st.success("저장 완료")
        else:
            st.warning("등록된 업무가 없습니다.")

# =============================
# 날짜별 업무 기록
# =============================
elif menu == "날짜별 업무 기록":

    st.header("날짜별 업무 기록")

    selected_date = st.date_input("날짜 선택", date.today())

    cursor.execute("""
    SELECT id, work_date, weekday, situation, task, is_done
    FROM work_logs
    WHERE work_date = ?
    ORDER BY id DESC
    """, (str(selected_date),))
    logs = cursor.fetchall()

    cursor.execute("""
    SELECT id, work_date, weekday, task, is_done
    FROM manual_tasks
    WHERE work_date = ?
    ORDER BY id DESC
    """, (str(selected_date),))
    manual_logs = cursor.fetchall()

    rows = []

    for log in logs:
        rows.append({
            "구분": "자동",
            "삭제": False,
            "완료": True if log[5] == "완료" else False,
            "ID": log[0],
            "날짜": log[1],
            "요일": log[2],
            "상황": log[3],
            "업무": log[4]
        })

    for log in manual_logs:
        rows.append({
            "구분": "직접",
            "삭제": False,
            "완료": True if log[4] == "완료" else False,
            "ID": log[0],
            "날짜": log[1],
            "요일": log[2],
            "상황": "직접 추가",
            "업무": log[3]
        })

    if rows:
        edited_logs = st.data_editor(
            rows,
            hide_index=True,
            use_container_width=True,
            disabled=["구분", "ID", "날짜", "요일", "상황"]
        )

        if st.button("기록 변경사항 저장"):
            for row in edited_logs:
                table_name = "work_logs" if row["구분"] == "자동" else "manual_tasks"

                if row["삭제"]:
                    cursor.execute(f"DELETE FROM {table_name} WHERE id = ?", (row["ID"],))
                else:
                    cursor.execute(
                        f"UPDATE {table_name} SET is_done = ? WHERE id = ?",
                        ("완료" if row["완료"] else "미완료", row["ID"])
                    )

                    if row["구분"] == "직접":
                        cursor.execute(
                            "UPDATE manual_tasks SET task = ? WHERE id = ?",
                            (row["업무"], row["ID"])
                        )

            conn.commit()
            st.rerun()
    else:
        st.info("해당 날짜 기록 없음")

# =============================
# 요일별
# =============================
else:

    selected_weekday = menu

    st.header(f"{selected_weekday} 추천 업무")

    tasks = fetch_rules_by_weekday(selected_weekday)

    if tasks:
        rows = []
        seen = set()

        for situation, step_order, next_task, task_weekday in tasks:
            key = (situation, step_order, next_task)

            if key in seen:
                continue

            seen.add(key)

            rows.append({
                "완료": False,
                "상황": situation,
                "단계": step_order,
                "업무": next_task,
                "요일": task_weekday
            })

        edited = st.data_editor(
            rows,
            hide_index=True,
            use_container_width=True,
            disabled=["상황", "단계", "업무", "요일"]
        )

        save_date = st.date_input("기록 날짜", date.today())

        if st.button("요일 업무 저장"):
            for row in edited:
                cursor.execute("""
                INSERT INTO work_logs
                (work_date, weekday, situation, task, is_done)
                VALUES (?, ?, ?, ?, ?)
                """, (
                    str(save_date),
                    selected_weekday,
                    row["상황"],
                    row["업무"],
                    "완료" if row["완료"] else "미완료"
                ))

            conn.commit()
            st.success("저장 완료")
    else:
        st.info("등록된 업무 없음")

conn.close()
