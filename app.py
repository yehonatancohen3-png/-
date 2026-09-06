import streamlit as st
import os
import json
import requests
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import google.generativeai as genai

# ==========================================
# 1. הגדרות דף ואינטרפייס (Page Config)
# ==========================================
st.set_page_config(
    page_title="סוגיה בעיון - עוזר תורני אישי",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# עיצוב מותאם לעברית (RTL), מצב כהה וסרגל צד למובייל
# ==========================================
st.markdown("""
<style>
    /* הגדרת כיווניות מימין לשמאל עבור רכיבי תוכן וטקסט */
    html, body, .stApp, .stMarkdown, h1, h2, h3, h4, h5, h6, p, label, span {
        direction: rtl !important;
        text-align: right !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

    /* מניעת גלישה אופקית */
    html, body, .stApp {
        max-width: 100vw !important;
        overflow-x: hidden !important;
    }

    /* מניעת מריחה: סרגל הצד כשהוא סגור מוסתר לחלוטין בכל גדלי המסכים */
    section[data-testid="stSidebar"][aria-expanded="false"],
    [data-testid="stSidebar"][aria-expanded="false"] {
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        min-width: 0 !important;
        max-width: 0 !important;
        height: 0 !important;
        overflow: hidden !important;
        opacity: 0 !important;
        pointer-events: none !important;
        position: fixed !important;
        right: -9999px !important;
        transform: translateX(200vw) !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    
    section[data-testid="stSidebar"][aria-expanded="false"] * {
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        height: 0 !important;
        overflow: hidden !important;
    }

    /* הסתרת מודאל ההתראות המובנה של Streamlit שקופץ במרכז המסך */
    div[data-testid="stSkillsNudgeAnchor"],
    div[data-testid="stSkillsNudge"],
    .stSkillsNudge,
    div[data-testid="stSkillsNudgeAnchor"] * {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        pointer-events: none !important;
        height: 0 !important;
        width: 0 !important;
    }

    /* שמירה על סרגל הכלים העליון עבור כפתור פתיחת מסך הצד */
    header[data-testid="stHeader"] {
        display: block !important;
        background: transparent !important;
        z-index: 9999 !important;
    }
    
    [data-testid="stToolbar"] {
        display: flex !important;
        visibility: visible !important;
    }

    /* כפתור פתיחת מסך הצד - נגיש ונוח ללחיצה */
    [data-testid="stExpandSidebarButton"] {
        display: flex !important;
        visibility: visible !important;
        z-index: 10000 !important;
        background: rgba(240, 242, 246, 0.2) !important;
        border-radius: 8px !important;
        padding: 4px !important;
        margin: 6px !important;
        cursor: pointer !important;
    }

    /* הסתרת כפתורי מערכת שאינם נחוצים */
    [data-testid="stAppDeployButton"], #MainMenu, [data-testid="stMainMenu"], footer {
        display: none !important;
    }

    /* סרגל צד ב-RTL */
    [data-testid="stSidebar"] {
        direction: rtl !important;
        text-align: right !important;
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
    
    .stButton>button {
        border-radius: 8px;
        transition: all 0.3s ease;
    }
    
    [data-testid="stPopoverBody"] {
        direction: rtl !important;
        text-align: right !important;
        min-width: 220px;
    }

    /* התאמה ייעודית למכשירים ניידים */
    @media (max-width: 768px) {
        h1 {
            font-size: 1.6rem !important;
            word-wrap: break-word !important;
            white-space: normal !important;
            line-height: 1.3 !important;
        }

        .block-container {
            max-width: 100% !important;
            padding-top: 3.5rem !important;
            padding-right: 1rem !important;
            padding-left: 1rem !important;
        }

        /* סרגל צד פתוח במובייל - פתיחה מלאה מימין בצורה נקייה */
        section[data-testid="stSidebar"][aria-expanded="true"],
        [data-testid="stSidebar"][aria-expanded="true"] {
            display: block !important;
            visibility: visible !important;
            position: fixed !important;
            top: 0 !important;
            right: 0 !important;
            left: auto !important;
            bottom: 0 !important;
            width: 85vw !important;
            max-width: 320px !important;
            height: 100vh !important;
            z-index: 999999 !important;
            background-color: var(--background-color, #0e1117) !important;
            box-shadow: -5px 0 25px rgba(0, 0, 0, 0.7) !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
            transform: none !important;
        }

        /* מניעת קריסה של רוחב התוכן בתוך סרגל הצד (ביטול מריחה אנכית של אותיות) */
        [data-testid="stSidebar"][aria-expanded="true"] [data-testid="stSidebarContent"],
        [data-testid="stSidebar"][aria-expanded="true"] [data-testid="stSidebarUserContent"] {
            width: 100% !important;
            min-width: 260px !important;
            overflow-x: hidden !important;
        }

        /* כפתור סגירת הסרגל */
        [data-testid="stSidebarCollapseButton"] {
            display: block !important;
            visibility: visible !important;
        }

        [data-testid="stSidebarCollapseButton"] button,
        [data-testid="stSidebar"] button[aria-label="Close"] {
            z-index: 1000000 !important;
            cursor: pointer !important;
            display: flex !important;
            visibility: visible !important;
            font-size: 1.5rem !important;
            padding: 8px !important;
        }
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. הגדרת מפתח Google API
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
  "max_output_tokens": 4096,
  "response_mime_type": "text/plain",
}

# ==========================================
# 3. ניהול נתונים מקומיים (JSON Persistence)
# ==========================================
DATA_DIR = "data"
USER_DATA_FILE = os.path.join(DATA_DIR, "user_data.json")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def init_user_data():
    if not os.path.exists(USER_DATA_FILE):
        default_data = {"projects": {"כללי": []}, "chats": {}}
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

# ==========================================
# 4. שליפה מהירה מספריא
# ==========================================
def clean_html_tags(text):
    return re.sub(r'<[^>]+>', '', text)

def search_sefaria(query, limit=3):
    url = "https://www.sefaria.org/api/v2/search/text"
    payload = {
        "query": query,
        "type": "text",
        "field": "exact",
        "size": limit
    }
    results_text = ""
    try:
        response = requests.post(url, json=payload, timeout=3)
        if response.status_code == 200:
            hits = response.json().get("hits", {}).get("hits", [])
            for hit in hits:
                source = hit.get("_source", {})
                ref = source.get("ref", "מקור לא ידוע")
                he_text = source.get("he", "")
                if isinstance(he_text, str) and he_text.strip():
                    clean_text = clean_html_tags(he_text)
                    results_text += f"\nמקור מתוך ספריא [{ref}]:\n\"{clean_text}\"\n"
    except Exception:
        pass
    return results_text

# ==========================================
# 5. פרומפטים ותצורות לימוד
# ==========================================
PROMPTS = {
    "פשוט ומונגש": """אתה עוזר תורני חכם ונגיש המנתח סוגיות בבהירות.
* ענה בשפה פשוטה, מודרנית וברורה.
* המבנה הנדרש: הגדרת השאלה, יסוד הסוגיה, דעות מרכזיות, ומסקנה למעשה.
* חובה לסיים כל תשובה במשפט: "הערה: תוכן זה מיועד ללימוד בלבד, ואין לפסוק ממנו הלכה למעשה."
""",
    "ישיבתי-למדני (סגנון שו\"ת)": """אתה תלמיד חכם העונה בסגנון ישיבתי למדני ומעמיק.
* השתמש בשפה תורנית מסורתית, מונחי לומדות ומשא ומתן סוגיאתי.
* חלק את התשובה ל'קושיה', 'תירוץ', 'יסוד הסוגיה', 'נפקא מינה'.
* חובה לסיים כל תשובה במשפט: "הערה: תוכן זה מיועד ללימוד בלבד, ואין לפסוק ממנו הלכה למעשה."
""",
    "הכנה למבחני רבנות": """אתה בוחן ורב המכין תלמידים למבחני הרבנות הראשית.
* הצג השתלשלות הלכתית סדורה: מקורות מהתנ"ך והש"ס, ראשונים, שולחן ערוך, נושאי כלים ופוסקי זמננו.
* חובה לסיים כל תשובה במשפט: "הערה: תוכן זה מיועד ללימוד בלבד, ואין לפסוק ממנו הלכה למעשה."
"""
}

# ==========================================
# 6. מנוע ג'מיני - זיהוי דינמי ומטמון מהיר
# ==========================================
@st.cache_resource(ttl=3600)
def get_supported_models():
    """שולף ושומר במטמון את כל המודלים הפעילים שנתמכים בחשבון"""
    try:
        active_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                active_models.append(m.name)
        
        # מיון מודלים לפי עדיפות: 3.6-flash, 2.5-flash וכו'
        active_models.sort(key=lambda name: (
            0 if '3.6-flash' in name else
            1 if '2.5-flash' in name else
            2 if 'flash' in name else 3
        ))
        if active_models:
            return active_models
    except Exception:
        pass
    
    # ברירת מחדל מעודכנת למקרה שהשליפה נכשלה
    return ['models/gemini-3.6-flash', 'models/gemini-2.5-flash']

def get_gemini_response(prompt, context, style):
    system_instruction = PROMPTS.get(style, PROMPTS["פשוט ומונגש"])
    full_prompt = f"{system_instruction}\n\nמקורות שנשלפו מספריא:\n{context}\n\nשאלה לניתוח:\n{prompt}"
    
    available_models = get_supported_models()
    last_error = ""
    
    for model_name in available_models:
        try:
            model = genai.GenerativeModel(model_name=model_name, generation_config=generation_config)
            response = model.generate_content(full_prompt)
            if response and response.text:
                return response.text
        except Exception as e:
            last_error = str(e)
            continue

    return f"אירעה שגיאה בחיבור למודלים: {last_error}"

# ==========================================
# 7. ניהול Session State
# ==========================================
if 'current_project' not in st.session_state:
    st.session_state.current_project = "כללי"
if 'current_chat_id' not in st.session_state:
    st.session_state.current_chat_id = None
if 'search_query' not in st.session_state:
    st.session_state.search_query = ""

# ==========================================
# 8. סרגל צד (Sidebar)
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
# 9. מסך ראשי והרצה במקביל
# ==========================================
if st.session_state.current_chat_id and st.session_state.current_chat_id in st.session_state.user_data["chats"]:
    current_chat = st.session_state.user_data["chats"][st.session_state.current_chat_id]
    
    st.header(f"📜 {current_chat.get('title', 'שיחה ללא שם')}")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        learning_style = st.selectbox("🎯 בחר סגנון לימוד ותשובה:", list(PROMPTS.keys()))
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

        with st.chat_message("assistant"):
            status_placeholder = st.empty()
            
            loading_messages = [
                "יהונתן חושב...",
                "יהונתן עומד לפתור את הסוגיה...",
                "יהונתן מריץ חיפוש בראש וכל התורה כולה לנגד עיניו...",
                "ליהונתן יש פיתרון, וחושב על כיוונים אחרים...",
                "יהונתן צריך ריכוז...",
                "יהונתן מקבץ כל מיני שו\"תים שנזכר בהם בהקשר לשאלה...",
                "יהונתן מבין שהשאלה מסובכת, אך אין שאלה שתישאר לא פתורה..."
            ]

            def execute_pipeline():
                context_sources = ""
                if use_sefaria:
                    context_sources = search_sefaria(user_input)
                return get_gemini_response(user_input, context_sources, learning_style)

            with ThreadPoolExecutor() as executor:
                future = executor.submit(execute_pipeline)
                
                msg_idx = 0
                while not future.done():
                    current_msg = loading_messages[msg_idx % len(loading_messages)]
                    status_placeholder.markdown(f"⏳ **{current_msg}**")
                    time.sleep(2)
                    msg_idx += 1
                
                response_text = future.result()

            status_placeholder.empty()
            st.markdown(response_text)

        current_chat["messages"].append({"role": "assistant", "content": response_text})
        save_user_data(st.session_state.user_data)
        st.rerun()

else:
    st.title("📜 סוגיה בעיון - עוזר תורני אישי")
    st.caption("מנוע בינה מלאכותית מבוסס מקורות לניתוח סוגיות הלכתיות ולמדניות")
    st.info("👈 בחר שיחה מסרגל הצד, או לחץ על **'💬 שיחה חדשה'** כדי להתחיל בלמידה.")
