import streamlit as st
import os
import json
import requests
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import google.generativeai as genai

# 1. הגדרות דף האינטרנט
st.set_page_config(
    page_title="Gemini - סוגיה בעיון",
    page_icon="✨",
    layout="centered"
)

# CSS ליישור RTL ועיצוב כפתורי הפרויקטים והשיחות בסגנון Gemini
st.markdown(
    """
    <style>
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stSidebar"] {
        direction: rtl !important;
        text-align: right !important;
    }
    
    [data-testid="stChatMessage"], [data-testid="stChatInput"], div[data-baseweb="input"] {
        direction: rtl !important;
        text-align: right !important;
    }

    h1, h2, h3, h4, h5, h6, p, div, span, label, .stMarkdownContainer, .stMarkdown {
        direction: rtl !important;
        text-align: right !important;
    }

    ul, ol {
        direction: rtl !important;
        text-align: right !important;
        padding-right: 1.5rem !important;
        padding-left: 0rem !important;
        margin-right: 0rem !important;
    }

    li {
        direction: rtl !important;
        text-align: right !important;
    }

    /* עיצוב כפתורי סרגל הצד */
    [data-testid="stSidebar"] button {
        border: none !important;
        background: transparent !important;
        text-align: right !important;
        justify-content: flex-start !important;
        padding: 6px 12px !important;
        box-shadow: none !important;
        width: 100% !important;
    }

    [data-testid="stSidebar"] button:hover {
        background-color: #f0f4f9 !important;
        border-radius: 20px !important;
    }

    /* הדגשת פרויקט פעיל */
    div[data-testid="stSidebar"] button[kind="primary"] {
        background-color: #e8f0fe !important;
        color: #1a73e8 !important;
        font-weight: bold !important;
        border-radius: 20px !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 2. ניהול Executor גלובלי להרצת משימות ברקע (גם בעת מעבר דפים)
if "executor" not in st.session_state:
    st.session_state.executor = ThreadPoolExecutor(max_workers=4)

# 3. טעינת מפתח ה-API
load_dotenv()

api_key = None
if "GEMINI_API_KEY" in st.secrets:
    api_key = str(st.secrets["GEMINI_API_KEY"]).strip()
elif "GOOGLE_API_KEY" in st.secrets:
    api_key = str(st.secrets["GOOGLE_API_KEY"]).strip()
else:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if not api_key:
    st.error("לא נמצא מפתח API! אנא הגדר GEMINI_API_KEY ב-Secrets.")
    st.stop()

genai.configure(api_key=api_key)

# 4. מנגנון שליפת מקורות מ-Sefaria API
def fetch_from_sefaria(query: str) -> str:
    try:
        url = "https://www.sefaria.org/api/v2/search/text"
        payload = {"query": query, "type": "text", "field": "exact", "size": 5}
        response = requests.post(url, json=payload, timeout=8)
        
        if response.status_code == 200:
            hits = response.json().get("hits", {}).get("hits", [])
            if not hits:
                return "לא נמצאו מקורות תואמים בספריא."
            results = []
            for hit in hits:
                source = hit.get("_source", {})
                title = source.get("ref", "")
                he_text = source.get("he", "")
                if isinstance(he_text, str) and he_text.strip():
                    clean_text = re.sub(r'<[^>]+>', '', he_text)
                    results.append(f"מקור מתוך ספריא [{title}]:\n\"{clean_text}\"")
            if results:
                return "\n\n".join(results)
    except Exception as e:
        return f"לא ניתן היה לשלוף מקורות מספריא: {str(e)}"
    return "לא נמצאו מקורות ספציפיים בספריא."

# 5. מנגנון שליפה משולב (מאגר מקומי + ספריא)
def load_torah_database():
    db_path = os.path.join("data", "torah_database.json")
    if os.path.exists(db_path):
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def retrieve_all_context(query: str) -> str:
    context_parts = []
    sefaria_data = fetch_from_sefaria(query)
    if "לא נמצאו" not in sefaria_data and "לא ניתן" not in sefaria_data:
        context_parts.append(f"--- מקורות מדויקים מספריא (כולל ניקוד) ---\n{sefaria_data}")
        
    database = load_torah_database()
    query_words = [w for w in query.split() if len(w) > 2]
    matched_local = []
    for item in database:
        content = item.get("content", "")
        book = item.get("book", "")
        if any(word in content or word in book for word in query_words):
            source_info = f"מקור מקומי: {book} "
            if item.get("masechet"): source_info += f"מסכת {item['masechet']} דף {item['daf']} "
            if item.get("siman"): source_info += f"סימן {item['siman']} סעיף {item['seif']} "
            source_info += f"\nתוכן המקור: \"{content}\""
            matched_local.append(source_info)
            
    if matched_local:
        context_parts.append(f"--- מקורות מהמאגר המקומי ---\n" + "\n\n".join(matched_local))
    return "\n\n".join(context_parts) if context_parts else "לא נמצאו מקורות במאגרי המידע הזמינים."

# 6. System Prompt
SYSTEM_PROMPT = """
אתה מודול AI תורני מומחה, המנתח סוגיות הלכתיות, מחשבתיות ואקטואליות במתודולוגיה של בית מדרש ("סוגיה בעיון").
תפקידך להציג ניתוח יסודי, מעמיק ומדויק מפי המקורות ועד לפסיקת ההלכה למעשה.

כללי ברזל לציטוט ומקורות:
1. ציטוטים מספריא/מאגר מקומי יש להביא מילה במילה במירכאות ("...").
2. שמור על הניקוד המקורי כפי שנשלף מספריא.
3. ציין תמיד בצמוד לכל ציטוט את מראה המקום המדויק.

סדר התשובה:
1. הגדרת המקרה והשאלה
2. יסוד הסוגיה במקורות
3. שיטות הראשונים
4. פסיקת השולחן ערוך והנושאי כלים
5. שו"תים ופוסקי זמננו
6. מסקנה הלכתית למעשה
"""

def analyze_sugya_worker(messages_history):
    """פונקציה עצמאית שמורצת בתוך ה-Thread ברקע"""
    try:
        last_prompt = messages_history[-1]["content"]
        retrieved_context = retrieve_all_context(last_prompt)
        
        generation_config = {"temperature": 0.0, "top_p": 0.8}
        model = genai.GenerativeModel(
            model_name='models/gemini-3.6-flash',
            system_instruction=SYSTEM_PROMPT,
            generation_config=generation_config
        )

        formatted_history = []
        for msg in messages_history[:-1]:
            role = "user" if msg["role"] == "user" else "model"
            formatted_history.append({"role": role, "parts": [msg["content"]]})

        chat = model.start_chat(history=formatted_history)
        prompt_with_context = f"מקורות שנשלפו:\n{retrieved_context}\n\nשאלה לניתוח: {last_prompt}"
        response = chat.send_message(prompt_with_context)
        return response.text
    except Exception as e:
        return f"שגיאה בהפעלת המודל: {str(e)}"

# 7. ניהול נתונים ב-Session State (פרויקטים -> שיחות)
if "projects" not in st.session_state:
    p_id = str(uuid.uuid4())
    c_id = str(uuid.uuid4())
    st.session_state.projects = {
        p_id: {
            "name": "פרוייקט - מודול AI סוגיה בעיון",
            "chats": {
                c_id: {
                    "title": "שיחה חדשה", 
                    "messages": [],
                    "running_future": None # שדה שמחזיק את המשימה שרצה ברקע
                }
            }
        }
    }
    st.session_state.current_project_id = p_id
    st.session_state.current_chat_id = c_id

if "search_term" not in st.session_state:
    st.session_state.search_term = ""

def create_new_project(name):
    p_id = str(uuid.uuid4())
    c_id = str(uuid.uuid4())
    st.session_state.projects[p_id] = {
        "name": name if name.strip() else "פרויקט חדש",
        "chats": {
            c_id: {
                "title": "שיחה חדשה", 
                "messages": [],
                "running_future": None
            }
        }
    }
    st.session_state.current_project_id = p_id
    st.session_state.current_chat_id = c_id

def create_new_chat():
    p_id = st.session_state.current_project_id
    c_id = str(uuid.uuid4())
    st.session_state.projects[p_id]["chats"][c_id] = {
        "title": "שיחה חדשה", 
        "messages": [],
        "running_future": None
    }
    st.session_state.current_chat_id = c_id

# 8. סרגל צד (Sidebar) אינטראקטיבי במבנה Gemini
with st.sidebar:
    st.markdown("## ✨ Gemini")
    st.write("")

    # מקטע 1: פעולות ראשיות
    if st.button("🖊️  שיחה חדשה", use_container_width=True):
        create_new_chat()
        st.rerun()

    with st.popover("🔍  חיפוש שיחות", use_container_width=True):
        st.session_state.search_term = st.text_input("חפש בשיחות:", value=st.session_state.search_term)

    if st.button("🎛️  ספרייה", use_container_width=True):
        st.info("ספריית המקורות פעילה ומחוברת לספריא בזמן אמת.")

    st.write("")

    # מקטע 2: תיקיות Notebook / פרויקטים בלחיצה
    st.caption("תיקיות Notebook")
    
    with st.popover("➕  תיקיית Notebook חדשה", use_container_width=True):
        new_proj_name = st.text_input("שם התיקייה / הפרויקט:")
        if st.button("צור פרויקט"):
            if new_proj_name:
                create_new_project(new_proj_name)
                st.rerun()

    for p_id, p_data in list(st.session_state.projects.items()):
        is_proj_active = (p_id == st.session_state.current_project_id)
        btn_type = "primary" if is_proj_active else "secondary"
        
        if st.button(f"📙  {p_data['name']}", key=f"proj_{p_id}", type=btn_type, use_container_width=True):
            st.session_state.current_project_id = p_id
            st.session_state.current_chat_id = list(p_data["chats"].keys())[0]
            st.rerun()

    st.write("")

    # מקטע 3: מהזמן האחרון (שיחות בתוך הפרויקט הנבחר כולל אינדיקציות טעינה)
    st.caption("מהזמן האחרון")

    current_proj = st.session_state.projects[st.session_state.current_project_id]
    
    filtered_chats = {
        c_id: c_data for c_id, c_data in current_proj["chats"].items()
        if st.session_state.search_term.lower() in c_data["title"].lower()
    }

    for c_id, c_data in list(filtered_chats.items()):
        is_chat_active = (c_id == st.session_state.current_chat_id)
        is_running = c_data.get("running_future") is not None and not c_data["running_future"].done()
        
        display_title = c_data["title"] + (" ⏳" if is_running else "")
        
        col1, col2 = st.columns([0.85, 0.15])
        with col1:
            if st.button(display_title, key=f"chat_{c_id}", use_container_width=True):
                st.session_state.current_chat_id = c_id
                st.rerun()
        with col2:
            if st.button("🗑️", key=f"del_{c_id}"):
                del current_proj["chats"][c_id]
                if not current_proj["chats"]:
                    create_new_chat()
                else:
                    st.session_state.current_chat_id = list(current_proj["chats"].keys())[0]
                st.rerun()

# 9. עיצוב הממשק והצגת השיחה הנוכחית
st.title("📜 סוגיה בעיון")

current_proj = st.session_state.projects[st.session_state.current_project_id]
current_chat = current_proj["chats"][st.session_state.current_chat_id]

st.caption(f"פרויקט: **{current_proj['name']}** | שיחה: **{current_chat['title']}**")

# בדיקת משימות שרצות ברקע בשיחה הנוכחית
if current_chat.get("running_future"):
    future = current_chat["running_future"]
    if future.done():
        answer = future.result()
        if answer:
            current_chat["messages"].append({"role": "assistant", "content": answer})
        current_chat["running_future"] = None
        st.rerun()
    else:
        st.info("⏳ יהונתן מעיין בסוגיה ומריץ חיפוש ברקע... ניתן לעבור לשיחות אחרות בינתיים.")

# הצגת כל הודעות השיחה
for message in current_chat["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# קבלת קלט חדש מהמשתמש
if prompt := st.chat_input("הכנס שאלה או סוגיה בעיון..."):
    if not current_chat["messages"] or current_chat["title"] == "שיחה חדשה":
        current_chat["title"] = prompt[:30] + ("..." if len(prompt) > 30 else "")

    current_chat["messages"].append({"role": "user", "content": prompt})
    
    # שליחת הבקשה ל-Worker ברקע ושמירת ה-Future בתוך השיחה
    future = st.session_state.executor.submit(analyze_sugya_worker, current_chat["messages"].copy())
    current_chat["running_future"] = future
    
    st.rerun()
