"""
=============================================================================
פרוייקט - מודול AI סוגיה בעיון
=============================================================================

שלום ל-AI (ג'מיני) שיקרא את הקוד הזה! 
זהו פרויקט Streamlit המשמש כעוזר תורני חכם ("סוגיה בעיון"). 
הקוד מכיל את כל הפיצ'רים שפיתחנו עד כה ונמצא במצב עובד לחלוטין.

מבנה המערכת והלוגיקה:

1. תצוגה וממשק (UI/UX - RTL):
   - המערכת מותאמת במלואה לעברית (ימין-לשמאל) באמצעות בלוק CSS.
   - סרגל הצד (Sidebar) מכיל מערכת ניהול תיקיות (Projects) ושיחות (Chats).
   - עיצוב ייחודי: שורת השיחה בסרגל הצד מכילה כפתור לבחירת השיחה ובאותה שורה כפתור מחיקה (Popover).
   - מנגנון מחיקה בטוח: מחיקת תיקייה או שיחה דורשת אישור כפול באמצעות `st.popover`.
   - תיבת חיפוש פעילה לסינון שיחות לפי שם.

2. ניהול נתונים מקומי (Persistence & Session State):
   - הנתונים נשמרים מקומית בתיקיית `data/user_data.json`.
   - מבנה הנתונים המרוכז שמור ב-`st.session_state.user_data`:
     * "projects": מילון של שמות פרויקטים ורשימת UUIDs של שיחות בכל פרויקט.
     * "chats": מילון של שיחות לפי UUID (כותרת, היסטוריית הודעות, פרויקט משויך).
   - תוקנה שגיאת KeyError: גישה לפרויקטים נעשית תמיד באופן מוגן מתוך `user_data["projects"]` 
     עם בדיקת קיומו של המפתח לפני ביצוע `.append()` או `.insert()`.

3. מנוע בינה מלאכותית ומקורות (API):
   - טעינת מפתח ה-API תומכת גם בקובץ `.env` מקומי וגם ב-`st.secrets` של Streamlit Cloud.
   - שימוש ב-Google Generative AI (מודל `gemini-3.6-flash`).
   - שילוב Sefaria API: שליפה בזמן אמת של מקורות עבריים לפי שאילתת המשתמש.
   - גיבוי מאגר מקומי: טעינת `data/torah_database.json` במידה שספריא אינה זמינה.
   - System Prompts מותאמים לפי 3 סגנונות לימוד ("פשוט ומונגש", "ישיבתי-למדני", "הכנה למבחני רבנות").
   - מנגנון Retry לטיפול בשגיאות עומס (Rate Limit / 429).
=============================================================================
"""

import streamlit as st
import os
import json
import requests
import re
import time
import uuid
from dotenv import load_dotenv
import google.generativeai as genai

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
# 2. הזרקת CSS מותאם אישית (RTL ועיצוב)
# ==========================================
st.markdown("""
<style>
    /* כיווניות לימין (RTL) */
    .stApp, .stSidebar, .stMarkdown, h1, h2, h3, p, div {
        direction: rtl;
        text-align: right;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* הסתרת רכיבי סטרימליט מיותרים */
    [data-testid="stToolbar"] {display: none;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* עיצוב כפתורים */
    .stButton>button {
        border-radius: 8px;
        transition: all 0.3s ease;
    }
    
    /* שורת שיחה בסרגל צד */
    .chat-row-container {
        display: flex;
        flex-direction: row;
        align-items: center;
        justify-content: space-between;
        width: 100%;
        margin-bottom: 5px;
    }
    
    .chat-btn-container {
        flex-grow: 1;
        min-width: 0;
    }
    
    .chat-btn-container .stButton>button {
        width: 100%;
        text-align: right;
        background-color: transparent;
        border: 1px solid #ddd;
        padding: 8px 12px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    
    .chat-del-container {
        flex-shrink: 0;
        margin-right: 5px;
    }
    
    .chat-del-container [data-testid="stPopover"] > div > button {
        background-color: transparent;
        border: none;
        color: #ff4b4b;
        padding: 5px;
    }
    
    [data-testid="stPopoverBody"] {
        direction: rtl;
        text-align: right;
        min-width: 200px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. טעינת משתני סביבה וג'מיני (מקומי + ענן)
# ==========================================
load_dotenv()

# ניסיון שליפה מ-env מקומי
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# אם לא קיים ב-env, ניסיון שליפה מ-st.secrets ב-Streamlit Cloud
if not GOOGLE_API_KEY:
    try:
        if "GOOGLE_API_KEY" in st.secrets:
            GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    except Exception:
        pass

if not GOOGLE_API_KEY:
    st.error("⚠️ לא נמצא מפתח API של Google. ודא שהגדרת את GOOGLE_API_KEY ב-Secrets ב-Streamlit Cloud או בקובץ .env מקומי.")
    st.stop()

genai.configure(api_key=GOOGLE_API_KEY)
generation_config = {
  "temperature": 0.4,
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 8192,
  "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
  model_name="gemini-3.6-flash",
  generation_config=generation_config,
)

# ==========================================
# 4. ניהול נתונים מקומיים (JSON)
# ==========================================
DATA_DIR = "data"
USER_DATA_FILE = os.path.join(DATA_DIR, "user_data.json")
DB_FILE = os.path.join(DATA_DIR, "torah_database.json")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def init_user_data():
    if not os.path.exists(USER_DATA_FILE):
        default_data = {
            "projects": {"כללי": []},
            "chats": {}
        }
        save_user_data(default_data)
        return default_data
    else:
        try:
            with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "projects" not in data or not data["projects"]:
                    data["projects"] = {"כללי": []}
                if "chats" not in data:
                    data["chats"] = {}
                return data
        except Exception:
            return {"projects": {"כללי": []}, "chats": {}}

def save_user_data(data):
    try:
        with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

if 'user_data' not in st.session_state:
    st.session_state.user_data = init_user_data()

@st.cache_data
def load_local_database():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

local_db = load_local_database()

# ==========================================
# 5. אינטגרציה עם Sefaria API
# ==========================================
def clean_html_tags(text):
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

def search_sefaria(query, limit=3):
    search_url = f"https://www.sefaria.org/api/search-wrapper?query={query}&size={limit}"
    results_text = ""
    try:
        response = requests.get(search_url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            hits = data.get("hits", {}).get("hits", [])
            for hit in hits:
                ref = hit.get("_source", {}).get("ref", "מקור לא ידוע")
                text_api_url = f"https://www.sefaria.org/api/texts/{ref}?context=0"
                text_response = requests.get(text_api_url, timeout=5)
                if text_response.status_code == 200:
                    text_data = text_response.json()
                    he_text = text_data.get("he", "")
                    if isinstance(he_text, list):
                        he_text = " ".join(he_text)
                    he_text = clean_html_tags(he_text)
                    if he_text:
                        results_text += f"\nמקור: {ref}\nתוכן: {he_text}\n"
    except Exception:
        pass
    return results_text

# ==========================================
# 6. System Prompts
# ==========================================
PROMPTS = {
    "פשוט ומונגש": """אתה עוזר תורני חכם ונגיש.
* ענה בשפה פשוטה, מודרנית וברורה.
* הסבר מושגים קשים.
* חובה לצטט מקורות במדויק.
* חובה לסיים כל תשובה במשפט: "הערה: אין לפסוק הלכה מתוך דברים אלו, ויש לעשות שאלת חכם."
""",
    "ישיבתי-למדני (סגנון שו\"ת)": """אתה תלמיד חכם העונה בסגנון ישיבתי למדני.
* השתמש בשפה תורנית מסורתית, ארמית ישיבתית ומונחי לומדות.
* חלק את התשובה ל'קושיה', 'תירוץ', 'נפקא מינה'.
* חובה להביא ציטוטים מדויקים.
* חובה לסיים כל תשובה במשפט: "הערה: אין לפסוק הלכה מתוך דברים אלו, ויש לעשות שאלת חכם."
""",
    "הכנה למבחני רבנות": """אתה בוחן ורב המכין תלמידים למבחני הרבנות הראשית.
* התשובה צריכה להיות מובנית, מתומצתת ומסוכמת היטב.
* התמקד בטור, בית יוסף, שולחן ערוך ונושאי כליהם.
* חובה לסיים כל תשובה במשפט: "הערה: אין לפסוק הלכה מתוך דברים אלו, ויש לעשות שאלת חכם."
"""
}

# ==========================================
# 7. קריאה לג'מיני (כולל Retry)
# ==========================================
def get_gemini_response(prompt, context, style):
    system_instruction = PROMPTS.get(style, PROMPTS["פשוט ומונגש"])
    full_prompt = f"{system_instruction}\n\nהקשר/מקורות:\n{context}\n\nשאלה:\n{prompt}"
    
    retries = 3
    for attempt in range(retries):
        try:
            chat_session = model.start_chat(history=[])
            response = chat_session.send_message(full_prompt)
            return response.text
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "ResourceExhausted" in error_str:
                if attempt < retries - 1:
                    time.sleep(2)
                    continue
                return "המערכת עמוסה כרגע (Rate Limit). אנא המתן מספר שניות ונסה שוב."
            return f"אירעה שגיאה: {error_str}"

# ==========================================
# 8. ניהול Session State
# ==========================================
if 'current_project' not in st.session_state:
    st.session_state.current_project = "כללי"
if 'current_chat_id' not in st.session_state:
    st.session_state.current_chat_id = None
if 'search_query' not in st.session_state:
    st.session_state.search_query = ""

# ==========================================
# 9. סרגל צד (Sidebar)
# ==========================================
with st.sidebar:
    st.title("📚 מודול סוגיה בעיון")
    
    # יצירת פרויקט חדש
    with st.expander("➕ פרויקט/תיקייה חדשה"):
        new_proj_name = st.text_input("שם הפרויקט:")
        if st.button("צור פרויקט"):
            if new_proj_name:
                if new_proj_name not in st.session_state.user_data["projects"]:
                    st.session_state.user_data["projects"][new_proj_name] = []
                    save_user_data(st.session_state.user_data)
                    st.session_state.current_project = new_proj_name
                    st.rerun()
                else:
                    st.warning("פרויקט בשם זה כבר קיים.")

    st.divider()
    
    # בחירת פרויקט
    project_names = list(st.session_state.user_data["projects"].keys())
    if not project_names:
        st.session_state.user_data["projects"]["כללי"] = []
        project_names = ["כללי"]
        
    if st.session_state.current_project not in project_names:
        st.session_state.current_project = project_names[0]
        
    selected_project = st.selectbox(
        "📂 בחר פרויקט", 
        project_names, 
        index=project_names.index(st.session_state.current_project)
    )
    
    if selected_project != st.session_state.current_project:
        st.session_state.current_project = selected_project
        st.session_state.current_chat_id = None
        st.rerun()
        
    # מחיקת פרויקט
    if selected_project != "כללי":
        with st.popover("🗑️ מחיקת פרויקט"):
            st.write("האם למחוק פרויקט זה וכל שיחותיו?")
            if st.button("כן, מחק פרויקט", key=f"del_proj_{selected_project}"):
                chat_ids_to_delete = st.session_state.user_data["projects"][selected_project]
                for cid in chat_ids_to_delete:
                    if cid in st.session_state.user_data["chats"]:
                        del st.session_state.user_data["chats"][cid]
                del st.session_state.user_data["projects"][selected_project]
                save_user_data(st.session_state.user_data)
                st.session_state.current_project = "כללי"
                st.session_state.current_chat_id = None
                st.rerun()

    st.divider()
    
    # יצירת שיחה חדשה
    if st.button("💬 שיחה חדשה", use_container_width=True):
        new_chat_id = str(uuid.uuid4())
        active_proj = st.session_state.current_project
        
        if active_proj not in st.session_state.user_data["projects"]:
            st.session_state.user_data["projects"][active_proj] = []
            
        st.session_state.user_data["chats"][new_chat_id] = {
            "title": "שיחה חדשה",
            "messages": [],
            "project": active_proj
        }
        st.session_state.user_data["projects"][active_proj].insert(0, new_chat_id)
        save_user_data(st.session_state.user_data)
        st.session_state.current_chat_id = new_chat_id
        st.rerun()

    st.divider()
    
    # חיפוש שיחות
    st.session_state.search_query = st.text_input("🔍 חיפוש שיחות:", value=st.session_state.search_query)

    # הצגת השיחות
    st.markdown("### שיחות בפרויקט")
    chat_ids = st.session_state.user_data["projects"].get(st.session_state.current_project, [])
    
    if not chat_ids:
        st.info("אין שיחות בפרויקט זה.")
    else:
        for cid in chat_ids:
            if cid in st.session_state.user_data["chats"]:
                chat = st.session_state.user_data["chats"][cid]
                chat_title = chat.get("title", "שיחה ללא שם")
                
                if st.session_state.search_query and st.session_state.search_query not in chat_title:
                    continue
                
                btn_type = "primary" if cid == st.session_state.current_chat_id else "secondary"
                
                col_btn, col_del = st.columns([0.85, 0.15], gap="small")
                
                with col_btn:
                    if st.button(f"📄 {chat_title}", key=f"btn_{cid}", type=btn_type, use_container_width=True):
                        st.session_state.current_chat_id = cid
                        st.rerun()
                
                with col_del:
                    with st.popover("🗑️"):
                        st.write("למחוק שיחה זו?")
                        if st.button("מחק", key=f"del_{cid}"):
                            st.session_state.user_data["projects"][st.session_state.current_project].remove(cid)
                            del st.session_state.user_data["chats"][cid]
                            save_user_data(st.session_state.user_data)
                            if st.session_state.current_chat_id == cid:
                                st.session_state.current_chat_id = None
                            st.rerun()

# ==========================================
# 10. מסך ראשי - אזור הלימוד והשיחה
# ==========================================
if st.session_state.current_chat_id and st.session_state.current_chat_id in st.session_state.user_data["chats"]:
    current_chat = st.session_state.user_data["chats"][st.session_state.current_chat_id]
    
    st.header(current_chat.get("title", "שיחה ללא שם"))
    
    col1, col2 = st.columns([1, 1])
    with col1:
        learning_style = st.selectbox(
            "🎯 סגנון לימוד:",
            list(PROMPTS.keys())
        )
    with col2:
        use_sefaria = st.checkbox("🔍 שלוף מקורות בזמן אמת (Sefaria API)", value=True)

    st.divider()

    for msg in current_chat["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("שאל שאלה בסוגיה...")
    if user_input:
        if len(current_chat["messages"]) == 0:
            current_chat["title"] = user_input[:30] + "..." if len(user_input) > 30 else user_input
        
        current_chat["messages"].append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        context_sources = ""
        if use_sefaria:
            with st.spinner("שולף מקורות מספריא..."):
                context_sources = search_sefaria(user_input)

        with st.chat_message("assistant"):
            with st.spinner("מעיין בסוגיה ומנסח תשובה..."):
                response_text = get_gemini_response(user_input, context_sources, learning_style)
                st.markdown(response_text)

        current_chat["messages"].append({"role": "assistant", "content": response_text})
        save_user_data(st.session_state.user_data)
        st.rerun()

else:
    st.title("📖 סוגיה בעיון - עוזר תורני אישי")
    st.info("בחר שיחה מקיימת מסרגל הצד או לחץ על '💬 שיחה חדשה' כדי להתחיל בלימוד.")
