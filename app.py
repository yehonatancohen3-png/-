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
    /* כיווניות לימין (RTL) לכל האפליקציה */
    .stApp, .stSidebar, .stMarkdown, h1, h2, h3, p, div {
        direction: rtl;
        text-align: right;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* הסתרת כפתור פריסת עמוד, תפריט עליון ולוגו סטרימליט */
    [data-testid="stToolbar"] {display: none;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* עיצוב כפתורים כללי */
    .stButton>button {
        border-radius: 8px;
        transition: all 0.3s ease;
    }
    
    /* פלקסבוקס לשורת השיחה: כפתור שיחה בצד ימין, כפתור מחיקה בצד שמאל */
    .chat-row-container {
        display: flex;
        flex-direction: row;
        align-items: center;
        justify-content: space-between;
        width: 100%;
        margin-bottom: 5px;
        flex-wrap: nowrap;
    }
    
    /* קונטיינר לכפתור בחירת השיחה (תופס את רוב המקום) */
    .chat-btn-container {
        flex-grow: 1;
        min-width: 0; 
    }
    
    /* עיצוב ספציפי לכפתור בחירת השיחה */
    .chat-btn-container .stButton>button {
        width: 100%;
        text-align: right;
        background-color: transparent;
        border: 1px solid #ddd;
        padding: 8px 12px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        display: block;
    }
    .chat-btn-container .stButton>button:hover {
        background-color: #f0f2f6;
        border-color: #c4c4c4;
    }
    
    /* קונטיינר לכפתור המחיקה (Popover) - מיושר לשמאל */
    .chat-del-container {
        flex-shrink: 0;
        margin-right: 5px; /* מרווח מכפתור השיחה */
        display: flex;
        align-items: center;
    }
    
    /* עיצוב כפתור המחיקה עצמו - מינימליסטי וקומפקטי */
    .chat-del-container [data-testid="stPopover"] > div > button {
        background-color: transparent;
        border: none;
        color: #ff4b4b;
        padding: 5px;
        width: auto !important;
        min-width: 0 !important;
        box-shadow: none;
    }
    .chat-del-container [data-testid="stPopover"] > div > button:hover {
        color: #ff0000;
        background-color: #ffeeee;
    }
    
    /* תיקון תצוגת פופ-אובר לאישור מחיקה */
    [data-testid="stPopoverBody"] {
        direction: rtl;
        text-align: right;
        min-width: 200px;
    }
    
    /* התאמות למסכים קטנים (מובייל) */
    @media (max-width: 768px) {
        .chat-row-container {
            margin-bottom: 8px;
        }
        .chat-btn-container .stButton>button {
            padding: 10px 8px;
            font-size: 14px;
        }
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. טעינת משתני סביבה והגדרות API
# ==========================================
# מנסה למשוך מפתח מסודות הענן של סטרימליט
try:
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
    else:
        api_key = None
except Exception:
    api_key = None

# אם לא נמצא מפתח בענן, נבקש במסך
if not api_key:
    st.info("💡 לא נמצא מפתח API בהגדרות הענן. הכנס את המפתח שלך כאן כדי להתחיל:")
    api_key = st.text_input("🔑 מפתח API של גוגל:", type="password")
    if not api_key:
        st.stop()

# קונפיגורציה של מודל ג'מיני
genai.configure(api_key=api_key)
generation_config = {
  "temperature": 0.4,
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 8192,
  "response_mime_type": "text/plain",
}

# תיקון השגיאה: שימוש במודל היציב והנתמך ביותר לגרסאות השונות (gemini-pro)
model = genai.GenerativeModel(
  model_name="gemini-pro",
  generation_config=generation_config,
)

# ==========================================
# 4. ניהול נתונים מקומיים (JSON) - משתמש ותורה
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
                return json.load(f)
        except Exception:
            return {"projects": {"כללי": []}, "chats": {}}

def save_user_data(data):
    with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

if 'user_data' not in st.session_state:
    st.session_state.user_data = init_user_data()

@st.cache_data
def load_local_database():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            return {}
    return {}

local_db = load_local_database()

@st.cache_data
def build_fast_word_index(db):
    index = {}
    for title, text in db.items():
        words = re.findall(r'\b\w+\b', text)
        for w in set(words):
            if w not in index:
                index[w] = []
            index[w].append(title)
    return index

local_index = build_fast_word_index(local_db)

def rag_local_search(query, db, index, limit=3):
    if not db:
        return "לא נמצא מאגר מקומי."
    query_words = re.findall(r'\b\w+\b', query)
    scores = Counter()
    for word in query_words:
        if word in index:
            for title in index[word]:
                scores[title] += 1
    if not scores:
        return "לא נמצאו תוצאות רלוונטיות במאגר המקומי."
    top_results = scores.most_common(limit)
    results_text = ""
    for title, score in top_results:
        snippet = db[title][:500] + "..."
        results_text += f"\nמקור מקומי: {title}\nתוכן (חלק): {snippet}\n"
    return results_text

# ==========================================
# 5. אינטגרציה עם API של ספריא (Sefaria)
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
# 6. הגדרת System Prompts לסגנונות השונים
# ==========================================
PROMPTS = {
    "פשוט ומונגש": """אתה עוזר תורני חכם ונגיש...
* עליך לענות בשפה פשוטה, מודרנית וברורה.
* הסבר מושגים קשים.
* חובה לצטט את המקורות במדויק עם ניקוד אם קיים.
* חובה לסיים כל תשובה במשפט: "הערה: אין לפסוק הלכה מתוך דברים אלו, ויש לעשות שאלת חכם."
""",
    "ישיבתי-למדני (סגנון שו\"ת)": """אתה תלמיד חכם העונה בסגנון ישיבתי למדני...
* השתמש בשפה תורנית מסורתית, ארמית ישיבתית ומונחי לומדות.
* חלק את התשובה ל'קושיה', 'תירוץ', 'נפקא מינה'.
* חובה להביא ציטוטים מדויקים.
* חובה לסיים כל תשובה במשפט: "הערה: אין לפסוק הלכה מתוך דברים אלו, ויש לעשות שאלת חכם."
""",
    "הכנה למבחני רבנות": """אתה בוחן ורב המכין תלמידים למבחני ההסמכה של הרבנות הראשית...
* התשובה צריכה להיות מובנית, מתומצתת, ממוספרת ומסוכמת היטב לשם שינון.
* התמקד ב'טור', 'בית יוסף', ו'שולחן ערוך' ונושאי כליהם.
* חובה לסיים כל תשובה במשפט: "הערה: אין לפסוק הלכה מתוך דברים אלו, ויש לעשות שאלת חכם."
"""
}

# ==========================================
# 7. פונקציית תשאול ל-Gemini (כולל Retry)
# ==========================================
def get_gemini_response(prompt, context, style):
    system_instruction = PROMPTS.get(style, PROMPTS["פשוט ומונגש"])
    
    full_prompt = f"{system_instruction}\n\nהקשר/מקורות שנוספו באופן אוטומטי:\n{context}\n\nשאלה מהמשתמש:\n{prompt}"
    
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
                else:
                    return "המערכת עמוסה כרגע (Rate Limit). אנא המתן מספר שניות ונסה שוב."
            else:
                return f"אירעה שגיאה בגישה למודל: {error_str}"

# ==========================================
# 8. ניהול המצב ב-Session State
# ==========================================
if 'current_project' not in st.session_state:
    st.session_state.current_project = "כללי"
if 'current_chat_id' not in st.session_state:
    st.session_state.current_chat_id = None
if 'search_query' not in st.session_state:
    st.session_state.search_query = ""

# ==========================================
# 9. סרגל הצד (Sidebar) - ניהול תיקיות ושיחות
# ==========================================
with st.sidebar:
    st.title("📚 מודול סוגיה בעיון")
    
    with st.expander("➕ פרויקט/תיקייה חדשה"):
        new_proj_name = st.text_input("שם הפרויקט:")
        if st.button("צור פרויקט"):
            if new_proj_name and new_proj_name not in st.session_state.user_data["projects"]:
                st.session_state.user_data["projects"][new_proj_name] = []
                save_user_data(st.session_state.user_data)
                st.session_state.current_project = new_proj_name
                st.rerun()
            elif new_proj_name in st.session_state.user_data["projects"]:
                st.warning("פרויקט בשם זה כבר קיים.")
    
    st.divider()
    
    project_names = list(st.session_state.user_data["projects"].keys())
    if st.session_state.current_project not in project_names:
        st.session_state.current_project = project_names[0] if project_names else "כללי"
        
    selected_project = st.selectbox("📂 בחר פרויקט", project_names, 
                                    index=project_names.index(st.session_state.current_project))
    
    if selected_project != st.session_state.current_project:
        st.session_state.current_project = selected_project
        st.session_state.current_chat_id = None
        st.rerun()
        
    if selected_project != "כללי":
        with st.popover("🗑️ מחיקת פרויקט"):
            st.write("האם אתה בטוח שברצונך למחוק תיקייה זו?")
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
    
    if st.button("💬 שיחה חדשה", use_container_width=True):
        new_chat_id = str(uuid.uuid4())
        st.session_state.user_data["chats"][new_chat_id] = {
            "title": "שיחה חדשה",
            "messages": [],
            "project": st.session_state.current_project
        }
        st.session_state.user_data["projects"][st.session_state.current_project].insert(0, new_chat_id)
        save_user_data(st.session_state.user_data)
        st.session_state.current_chat_id = new_chat_id
        st.rerun()

    st.divider()
    
    st.session_state.search_query = st.text_input("🔍 חיפוש שיחות:", value=st.session_state.search_query)

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
                
                st.markdown(f'<div class="chat-row-container">', unsafe_allow_html=True)
                col_btn, col_del = st.columns([0.85, 0.15], gap="small")
                
                with col_btn:
                    st.markdown('<div class="chat-btn-container">', unsafe_allow_html=True)
                    if st.button(f"📄 {chat_title}", key=f"btn_{cid}", type=btn_type, use_container_width=True):
                        st.session_state.current_chat_id = cid
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                
                with col_del:
                    st.markdown('<div class="chat-del-container">', unsafe_allow_html=True)
                    with st.popover("🗑️"):
                        st.write("בטוח שברצונך למחוק?")
                        if st.button("מחק", key=f"del_{cid}"):
                            st.session_state.user_data["projects"][st.session_state.current_project].remove(cid)
                            del st.session_state.user_data["chats"][cid]
                            save_user_data(st.session_state.user_data)
                            if st.session_state.current_chat_id == cid:
                                st.session_state.current_chat_id = None
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 10. מסך ראשי - אזור השיחה (Chat Interface)
# ==========================================
if st.session_state.current_chat_id and st.session_state.current_chat_id in st.session_state.user_data["chats"]:
    current_chat = st.session_state.user_data["chats"][st.session_state.current_chat_id]
    
    st.header(current_chat["title"])
    
    # 10א. שורת הגדרות: בחירת סגנון לימוד ומצב חיפוש מקורות
    col1, col2 = st.columns(2)
    
    with col1:
        selected_style = st.selectbox(
            "סגנון לימוד", 
            options=list(PROMPTS.keys()), 
            index=0
        )
    with col2:
        search_mode = st.radio(
            "חיפוש מקורות אוטומטי דרך:",
            ["Sefaria (אונליין)", "RAG (מאגר מקומי)", "ללא חיפוש"],
            horizontal=True
        )

    st.divider()

    # 10ב. הצגת היסטוריית השיחה
    for msg in current_chat["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 10ג. קבלת קלט המשתמש ועיבוד התשובה
    if prompt := st.chat_input("שאל קושיה, בקש הסבר, או חפש מקור..."):
        
        # עדכון שם השיחה אם זו ההודעה הראשונה
        if current_chat["title"] == "שיחה חדשה":
            current_chat["title"] = prompt[:30] + "..." if len(prompt) > 30 else prompt
        
        # שמירת הודעת המשתמש והצגתה
        current_chat["messages"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        # יצירת תשובה מה-AI
        with st.chat_message("assistant"):
            with st.spinner("מעיין בספרים ומנסח תשובה..."):
                
                # משיכת הקשר (Context) לפי בחירת המשתמש
                context = ""
                if search_mode == "Sefaria (אונליין)":
                    context = search_sefaria(prompt)
                elif search_mode == "RAG (מאגר מקומי)":
                    context = rag_local_search(prompt, local_db, local_index)
                
                # קריאה ל-Gemini
                response_text = get_gemini_response(prompt, context, selected_style)
                
                # הצגת התשובה
                st.markdown(response_text)
                
                # אם נמצאו מקורות בחיפוש, נוסיף אותם כהערה מוסתרת (Expander) לנוחות הלומד
                if context and search_mode != "ללא חיפוש":
                    with st.expander("📌 מקורות גולמיים שנמשכו (RAG / Sefaria)"):
                        st.text(context)
        
        # שמירת התשובה במערכת ורינדור מחדש
        current_chat["messages"].append({"role": "assistant", "content": response_text})
        save_user_data(st.session_state.user_data)
        st.rerun()

else:
    # מסך פתיחה כאשר לא נבחרה שיחה
    st.title("ברוכים הבאים ל-AI סוגיה בעיון 📖")
    st.write("אנא בחר שיחה מהתפריט בצד ימין, או צור שיחה חדשה כדי להתחיל בלימוד.")
