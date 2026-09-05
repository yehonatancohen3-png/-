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
    html, body, .stApp, .stSidebar, .stMarkdown, h1, h2, h3, h4, h5, h6, p, div, label, span {
        direction: rtl !important;
        text-align: right !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    [data-testid="stChatMessage"], [data-testid="stChatInput"], div[data-baseweb="input"] {
        direction: rtl !important;
        text-align: right !important;
    }

    ul, ol {
        direction: rtl !important;
        text-align: right !important;
        padding-right: 1.5rem !important;
        padding-left: 0rem !important;
    }
    
    [data-testid="stToolbar"] {display: none;}
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    .stButton>button {
        border-radius: 8px;
        transition: all 0.3s ease;
    }
    
    [data-testid="stPopoverBody"] {
        direction: rtl !important;
        text-align: right !important;
        min-width: 220px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. טעינת משתני סביבה והגדרת Google API
# ==========================================
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

if not GOOGLE_API_KEY:
    try:
        if "GOOGLE_API_KEY" in st.secrets:
            GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
        elif "GEMINI_API_KEY" in st.secrets:
            GOOGLE_API_KEY = st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass

if not GOOGLE_API_KEY:
    st.error("⚠️ לא נמצא מפתח API של Google. ודא שהגדרת את GOOGLE_API_KEY ב-Secrets ב-Streamlit Cloud או בקובץ .env מקומי.")
    st.stop()

genai.configure(api_key=GOOGLE_API_KEY)

generation_config = {
  "temperature": 0.2,
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 8192,
  "response_mime_type": "text/plain",
}

# ==========================================
# 4. ניהול נתונים מקומיים (JSON Persistence)
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

def search_sefaria(query, limit=4):
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
                        results_text += f"\nמקור מתוך ספריא [{ref}]:\n\"{he_text}\"\n"
    except Exception as e:
        results_text = f"שגיאה בשליפה מספריא: {str(e)}"
    return results_text

# ==========================================
# 6. פרומפטים לפי סגנונות לימוד
# ==========================================
PROMPTS = {
    "פשוט ומונגש": """אתה עוזר תורני חכם ונגיש המנתח סוגיות בבהירות.
* ענה בשפה פשוטה, מודרנית וברורה.
* הסבר מושגים קשים מבית המדרש.
* המבנה הנדרש: הגדרת השאלה, יסוד הסוגיה, דעות מרכזיות, ומסקנה למעשה.
* חובה לצטט מקורות במדויק.
* חובה לסיים כל תשובה במשפט: "הערה: תוכן זה מיועד ללימוד בלבד, ואין לפסוק ממנו הלכה למעשה."
""",
    "ישיבתי-למדני (סגנון שו\"ת)": """אתה תלמיד חכם העונה בסגנון ישיבתי למדני ומעמיק.
* השתמש בשפה תורנית מסורתית, מונחי לומדות ומשא ומתן סוגיאתי.
* חלק את התשובה ל'קושיה', 'תירוץ', 'יסוד הסוגיה', 'נפקא מינה'.
* הביא מחלוקות ראשונים ואחרונים בפירוט.
* חובה לסיים כל תשובה במשפט: "הערה: תוכן זה מיועד ללימוד בלבד, ואין לפסוק ממנו הלכה למעשה."
""",
    "הכנה למבחני רבנות": """אתה בוחן ורב המכין תלמידים למבחני הרבנות הראשית.
* הצג השתלשלות הלכתית סדורה: מקורות מהתנ"ך והש"ס, ראשונים (רמב"ם, רא"ש, רי"ף), טור, בית יוסף, שולחן ערוך, נושאי כלים ופוסקי זמננו.
* סכם בסוף בצורה תמציתית את השורה התחתונה למנהג אשכנז, ספרד ותימן.
* חובה לסיים כל תשובה במשפט: "הערה: תוכן זה מיועד ללימוד בלבד, ואין לפסוק ממנו הלכה למעשה."
"""
}

# ==========================================
# 7. מנוע ג'מיני דינמי - Dynamic Fallback
# ==========================================
def get_gemini_response(prompt, context, style):
    system_instruction = PROMPTS.get(style, PROMPTS["פשוט ומונגש"])
    full_prompt = f"{system_instruction}\n\nמקורות שנשלפו מספריא ומאגר הנתונים:\n{context}\n\nשאלה לניתוח:\n{prompt}"
    
    available_models = []
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
    except Exception:
        pass

    ordered_models = []
    for kw in ['flash', 'pro', 'gemini']:
        for m in available_models:
            if kw in m.lower() and m not in ordered_models:
                ordered_models.append(m)
    for m in available_models:
        if m not in ordered_models:
            ordered_models.append(m)

    fallback_defaults = [
        'gemini-1.5-flash',
        'gemini-2.0-flash',
        'models/gemini-1.5-flash',
        'models/gemini-2.0-flash'
    ]
    for fb in fallback_defaults:
        if fb not in ordered_models:
            ordered_models.append(fb)

    last_error = ""
    for model_name in ordered_models:
        try:
            model = genai.GenerativeModel(model_name=model_name, generation_config=generation_config)
            chat_session = model.start_chat(history=[])
            response = chat_session.send_message(full_prompt)
            if response and response.text:
                return response.text
        except Exception as e:
            last_error = str(e)
            continue

    return f"אירעה שגיאה בחיבור למודלים הזמינים בחשבונך: {last_error}"

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
    st.title("📚 סוגיה בעיון - ניהול")
    
    with st.expander("➕ פרויקט / תיקייה חדשה"):
        new_proj_name = st.text_input("שם הפרויקט החדש:")
        if st.button("צור פרויקט", use_container_width=True):
            if new_proj_name.strip():
                proj_clean = new_proj_name.strip()
                if proj_clean not in st.session_state.user_data["projects"]:
                    st.session_state.user_data["projects"][proj_clean] = []
                    save_user_data(st.session_state.user_data)
                    st.session_state.current_project = proj_clean
                    st.rerun()
                else:
                    st.warning("פרויקט בשם זה כבר קיים.")

    st.divider()
    
    project_names = list(st.session_state.user_data["projects"].keys())
    if not project_names:
        st.session_state.user_data["projects"]["כללי"] = []
        project_names = ["כללי"]
        
    if st.session_state.current_project not in project_names:
        st.session_state.current_project = project_names[0]
        
    selected_project = st.selectbox(
        "📂 בחר פרויקט פעיל:", 
        project_names, 
        index=project_names.index(st.session_state.current_project)
    )
    
    if selected_project != st.session_state.current_project:
        st.session_state.current_project = selected_project
        st.session_state.current_chat_id = None
        st.rerun()
        
    if selected_project != "כללי":
        with st.popover("🗑️ מחיקת פרויקט זה"):
            st.write(f"האם למחוק את הפרויקט **'{selected_project}'** וכל שיחותיו?")
            if st.button("אישור מחיקה", key=f"del_proj_{selected_project}"):
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
    
    if st.button("💬 שיחה חדשה", use_container_width=True, type="primary"):
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
    
    st.session_state.search_query = st.text_input("🔍 חיפוש שיחות:", value=st.session_state.search_query)

    st.markdown("### שיחות בפרויקט")
    chat_ids = st.session_state.user_data["projects"].get(st.session_state.current_project, [])
    
    if not chat_ids:
        st.info("אין שיחות בפרויקט זה. לחץ על 'שיחה חדשה' להתחלה.")
    else:
        for cid in chat_ids:
            if cid in st.session_state.user_data["chats"]:
                chat = st.session_state.user_data["chats"][cid]
                chat_title = chat.get("title", "שיחה ללא שם")
                
                if st.session_state.search_query and st.session_state.search_query.lower() not in chat_title.lower():
                    continue
                
                btn_type = "primary" if cid == st.session_state.current_chat_id else "secondary"
                col_btn, col_del = st.columns([0.82, 0.18], gap="small")
                
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
# 10. מסך ראשי
# ==========================================
if st.session_state.current_chat_id and st.session_state.current_chat_id in st.session_state.user_data["chats"]:
    current_chat = st.session_state.user_data["chats"][st.session_state.current_chat_id]
    
    st.header(f"📜 {current_chat.get('title', 'שיחה ללא שם')}")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        learning_style = st.selectbox(
            "🎯 בחר סגנון לימוד ותשובה:",
            list(PROMPTS.keys())
        )
    with col2:
        use_sefaria = st.checkbox("🔍 שלוף מקורות בזמן אמת (Sefaria API)", value=True)

    st.divider()

    for msg in current_chat["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("הכנס שאלה או סוגיה בעיון...")
    if user_input:
        if len(current_chat["messages"]) == 0:
            current_chat["title"] = user_input[:32] + "..." if len(user_input) > 32 else user_input
        
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
    st.title("📜 סוגיה בעיון - עוזר תורני אישי")
    st.caption("מנוע בינה מלאכותית מבוסס מקורות לניתוח סוגיות הלכתיות ולמדניות")
    
    st.info("👈 בחר שיחה מסרגל הצד, או לחץ על **'💬 שיחה חדשה'** כדי להתחיל בלמידה.")
    
    st.markdown("""
    ### 🌟 תכונות המערכת:
    * **איתור מקורות ב-Sefaria API:** שליפת מקורות, פסוקים ודפי גמרא בזמן אמת.
    * **סגנונות לימוד מותאמים:** בחירה בין הסבר מונגש, ניתוח ישיבתי-למדני, או הכנה למבחני רבנות.
    * **ניהול שיחות ותיקיות:** שמירת ההיסטוריה באופן מקומי וחלוקה לפי פרויקטים.
    """)
