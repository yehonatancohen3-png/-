"""
=============================================================================
פרוייקט - מודול לסוגיה בעיון
=============================================================================
"""

import streamlit as st
import os
import json
import requests
import re
import time
import uuid
import google.generativeai as genai
from collections import Counter

# ==========================================
# 1. הגדרות בסיסיות (Page Config)
# ==========================================
st.set_page_config(
    page_title="סוגיה בעיון - עוזר תורני אישי",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. הזרקת CSS מותאם אישית (RTL, עיצוב וסרגל צד)
# ==========================================
st.markdown("""
<style>
    .stApp, .stSidebar, .stMarkdown, h1, h2, h3, p, div {
        direction: rtl;
        text-align: right;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    [data-testid="stToolbar"] {display: none;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stButton>button { border-radius: 8px; transition: all 0.3s ease; }
    .chat-row-container { display: flex; flex-direction: row; align-items: center; justify-content: space-between; width: 100%; margin-bottom: 5px; flex-wrap: nowrap; }
    .chat-btn-container { flex-grow: 1; min-width: 0; }
    .chat-btn-container .stButton>button { width: 100%; text-align: right; background-color: transparent; border: 1px solid #ddd; padding: 8px 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: block; }
    .chat-btn-container .stButton>button:hover { background-color: #f0f2f6; border-color: #c4c4c4; }
    .chat-del-container { flex-shrink: 0; margin-right: 5px; display: flex; align-items: center; }
    .chat-del-container [data-testid="stPopover"] > div > button { background-color: transparent; border: none; color: #ff4b4b; padding: 5px; width: auto !important; min-width: 0 !important; box-shadow: none; }
    .chat-del-container [data-testid="stPopover"] > div > button:hover { color: #ff0000; background-color: #ffeeee; }
    [data-testid="stPopoverBody"] { direction: rtl; text-align: right; min-width: 200px; }
    @media (max-width: 768px) { .chat-row-container { margin-bottom: 8px; } .chat-btn-container .stButton>button { padding: 10px 8px; font-size: 14px; } }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. טעינת משתני סביבה והגדרות API (מותאם לענן)
# ==========================================
# מנסה למשוך מפתח מההגדרות של סטרימליט ענן
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    api_key = None

# אם לא נמצא מפתח בענן, נבקש במסך
if not api_key:
    st.info("💡 המערכת מחוברת דרך GitHub! כדי להתחיל, הכנס את המפתח שלך כאן:")
    api_key = st.text_input("🔑 מפתח API של גוגל:", type="password")
    if not api_key:
        st.stop()

genai.configure(api_key=api_key)

generation_config = {
  "temperature": 0.4,
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 8192,
  "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
  model_name="gemini-1.5-flash",
  generation_config=generation_config,
)

# ==========================================
# 4. ניהול נתונים מקומיים (JSON)
# ==========================================
# בענן נשמור ב-Session State כדי למנוע קריסות של מערכת הקבצים
if 'user_data' not in st.session_state:
    st.session_state.user_data = {"projects": {"כללי": []}, "chats": {}}

# נגדיר מאגר מקומי ריק כדי שהקוד ירוץ גם ללא קבצים פיזיים
local_db = {}
local_index = {}

def rag_local_search(query, db, index, limit=3):
    return "מאגר מקומי לא זמין כרגע בענן."

# ==========================================
# 5. אינטגרציה עם API של ספריא (Sefaria)
# ==========================================
def clean_html_tags(text):
    return re.sub(re.compile('<.*?>'), '', text)

def search_sefaria(query, limit=3):
    search_url = f"https://www.sefaria.org/api/search-wrapper?query={query}&size={limit}"
    results_text = ""
    try:
        response = requests.get(search_url, timeout=10)
        if response.status_code == 200:
            hits = response.json().get("hits", {}).get("hits", [])
            for hit in hits:
                ref = hit.get("_source", {}).get("ref", "מקור לא ידוע")
                text_response = requests.get(f"https://www.sefaria.org/api/texts/{ref}?context=0", timeout=5)
                if text_response.status_code == 200:
                    he_text = text_response.json().get("he", "")
                    if isinstance(he_text, list): he_text = " ".join(he_text)
                    he_text = clean_html_tags(he_text)
                    if he_text: results_text += f"\nמקור: {ref}\nתוכן: {he_text}\n"
    except Exception:
        pass
    return results_text

# ==========================================
# 6. System Prompts
# ==========================================
PROMPTS = {
    "פשוט ומונגש": "אתה עוזר תורני חכם ונגיש...\n* עליך לענות בשפה פשוטה, מודרנית וברורה.\n* הסבר מושגים קשים.\n* חובה לסיים כל תשובה במשפט: 'הערה: אין לפסוק הלכה מתוך דברים אלו.'",
    "ישיבתי-למדני": "אתה תלמיד חכם העונה בסגנון ישיבתי למדני...\n* חלק את התשובה ל'קושיה', 'תירוץ', 'נפקא מינה'.\n* חובה לסיים כל תשובה במשפט: 'הערה: אין לפסוק הלכה מתוך דברים אלו.'",
    "הכנה לרבנות": "אתה בוחן ורב המכין תלמידים למבחני הרבנות...\n* התשובה צריכה להיות מובנית וממוספרת.\n* חובה לסיים כל תשובה במשפט: 'הערה: אין לפסוק הלכה מתוך דברים אלו.'"
}

# ==========================================
# 7. פונקציית תשאול ל-Gemini
# ==========================================
def get_gemini_response(prompt, context, style):
    system_instruction = PROMPTS.get(style, PROMPTS["פשוט ומונגש"])
    full_prompt = f"{system_instruction}\n\nהקשר שמצאנו:\n{context}\n\nשאלה:\n{prompt}"
    try:
        chat_session = model.start_chat(history=[])
        return chat_session.send_message(full_prompt).text
    except Exception as e:
        return f"אירעה שגיאה: {str(e)}"

# ==========================================
# 8. ניהול סרגל הצד (Sidebar)
# ==========================================
if 'current_project' not in st.session_state: st.session_state.current_project = "כללי"
if 'current_chat_id' not in st.session_state: st.session_state.current_chat_id = None
if 'search_query' not in st.session_state: st.session_state.search_query = ""

with st.sidebar:
    st.title("📚 סוגיה בעיון")
    with st.expander("➕ פרויקט חדש"):
        new_proj_name = st.text_input("שם הפרויקט:")
        if st.button("צור פרויקט") and new_proj_name and new_proj_name not in st.session_state.user_data["projects"]:
            st.session_state.user_data["projects"][new_proj_name] = []
            st.session_state.current_project = new_proj_name
            st.rerun()
    
    st.divider()
    project_names = list(st.session_state.user_data["projects"].keys())
    selected_project = st.selectbox("📂 בחר פרויקט", project_names, index=project_names.index(st.session_state.current_project))
    if selected_project != st.session_state.current_project:
        st.session_state.current_project = selected_project
        st.session_state.current_chat_id = None
        st.rerun()
        
    st.divider()
    if st.button("💬 שיחה חדשה", use_container_width=True):
        new_chat_id = str(uuid.uuid4())
        st.session_state.user_data["chats"][new_chat_id] = {"title": "שיחה חדשה", "messages": [], "project": st.session_state.current_project}
        st.session_state.user_data["projects"][st.session_state.current_project].insert(0, new_chat_id)
        st.session_state.current_chat_id = new_chat_id
        st.rerun()

    st.divider()
    st.markdown("### שיחות בפרויקט")
    chat_ids = st.session_state.user_data["projects"].get(st.session_state.current_project, [])
    if not chat_ids: st.info("אין שיחות בפרויקט זה.")
    for cid in chat_ids:
        if cid in st.session_state.user_data["chats"]:
            chat_title = st.session_state.user_data["chats"][cid].get("title", "שיחה")
            btn_type = "primary" if cid == st.session_state.current_chat_id else "secondary"
            if st.button(f"📄 {chat_title}", key=f"btn_{cid}", type=btn_type, use_container_width=True):
                st.session_state.current_chat_id = cid
                st.rerun()

# ==========================================
# 9. מסך ראשי - אזור השיחה
# ==========================================
if st.session_state.current_chat_id and st.session_state.current_chat_id in st.session_state.user_data["chats"]:
    current_chat = st.session_state.user_data["chats"][st.session_state.current_chat_id]
    st.header(current_chat["title"])
    
    col1, col2 = st.columns(2)
    with col1: selected_style = st.selectbox("סגנון לימוד", list(PROMPTS.keys()), index=0)
    with col2: search_mode = st.radio("חיפוש מקורות:", ["Sefaria (אונליין)", "ללא חיפוש"], horizontal=True)

    st.divider()
    for msg in current_chat["messages"]:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if prompt := st.chat_input("שאל קושיה או חפש מקור..."):
        if current_chat["title"] == "שיחה חדשה": current_chat["title"] = prompt[:30] + "..."
        current_chat["messages"].append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
            
        with st.chat_message("assistant"):
            with st.spinner("מעיין בספרים..."):
                context = search_sefaria(prompt) if search_mode == "Sefaria (אונליין)" else ""
                response_text = get_gemini_response(prompt, context, selected_style)
                st.markdown(response_text)
                if context:
                    with st.expander("📌 מקורות גולמיים שנמשכו (Sefaria)"): st.text(context)
        current_chat["messages"].append({"role": "assistant", "content": response_text})
        st.rerun()
else:
    st.title("ברוכים הבאים ל-AI סוגיה בעיון 📖")
    st.write("בחר שיחה מהתפריט או צור שיחה חדשה.")
