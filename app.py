# ייבוא ספריית streamlit לבניית ממשק ה-Web והצ'אט
import streamlit as st
# ייבוא ספריית os לעבודה עם מערכת הקבצים ונתיבים
import os
# ייבוא ספריית json לקריאה ופענוח של קבצי נתונים בפורמט JSON
import json
# ייבוא ספריית re לעבודה עם ביטויים רגולריים (Regular Expressions)
import re
# ייבוא ספריית requests לביצוע בקשות HTTP לרשת (כמו API של ספריא)
import requests
# ייבוא ספריית uuid ליצירת מזהים ייחודיים לכל שיחה
import uuid
# ייבוא הפונקציה load_dotenv מתוך dotenv לטעינת משתני סביבה מקובץ .env
from dotenv import load_dotenv
# ייבוא ספריית Google Generative AI לעבודה עם מודלי Gemini
import google.generativeai as genai

# 1. הגדרות דף האינטרנט
st.set_page_config(
    page_title="סוגיה בעיון - AI תורני",
    page_icon="📜",
    layout="centered"
)

# הוספת CSS מקיף ליישור מלא מימין לשמאל (RTL)
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

    h1, h2, h3, h4, h5, h6, p, div, span, label {
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

    .stMarkdownContainer, .stMarkdown {
        direction: rtl !important;
        text-align: right !important;
    }
    
    /* עיצוב כפתורי היסטוריה בסרגל הצד שייראו כמו קישורים/רשימה */
    div[data-testid="stSidebar"] button {
        text-align: right !important;
        justify-content: flex-start !important;
        width: 100% !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 2. טעינת מפתח ה-API
load_dotenv()

api_key = None

if "GEMINI_API_KEY" in st.secrets:
    api_key = str(st.secrets["GEMINI_API_KEY"]).strip()
elif "GOOGLE_API_KEY" in st.secrets:
    api_key = str(st.secrets["GOOGLE_API_KEY"]).strip()
else:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if not api_key:
    st.error("לא נמצא מפתח API! אנא הגדר GEMINI_API_KEY ב-Secrets ב-Streamlit Cloud.")
    st.stop()

genai.configure(api_key=api_key)

# 3. מנגנון לשמירה וטעינה של היסטוריית השיחות מקובץ JSON מקומי
HISTORY_FILE = "chat_history.json"

def load_all_sessions():
    """טעינת כל השיחות מקובץ ה-JSON המקומי בבטחה"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {}

def save_session(session_id, messages):
    """שמירת שיחה ספציפית לפי המזהה שלה בתוך קובץ ה-JSON"""
    sessions = load_all_sessions()
    if messages:
        first_question = next((m["content"] for m in messages if m["role"] == "user"), "שיחה ללא שם")
        sessions[session_id] = {
            "title": first_question,
            "messages": messages
        }
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(sessions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            st.error(f"שגיאה בשמירת היסטוריית השיחה: {e}")

# 4. מנגנון שליפת מקורות בזמן אמת מ-Sefaria API
def fetch_from_sefaria(query: str) -> str:
    """חיפוש ושליפת מקורות מדויקים בעברית מתוך ספריא"""
    try:
        url = "https://www.sefaria.org/api/v2/search/text"
        payload = {
            "query": query,
            "type": "text",
            "field": "exact",
            "size": 5
        }
        response = requests.post(url, json=payload, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            hits = data.get("hits", {}).get("hits", [])
            
            if not hits:
                return "לא נמצאו מקורות תואמים בספריא."
            
            results = []
            for hit in hits:
                source = hit.get("_source", {})
                title = source.get("ref", "")
                he_text = source.get("he", "")
                
                if isinstance(he_text, str) and he_text.strip():
                    clean_text = re.sub(r'<[^>]+>', '', he_text)
                    results.append(f"מקור מתוך ספריא ({title}):\n\"{clean_text}\"")
            
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
    
    # 1. שליפה מספריא
    sefaria_data = fetch_from_sefaria(query)
    if "לא נמצאו" not in sefaria_data and "לא ניתן" not in sefaria_data:
        context_parts.append(f"--- מקורות מדויקים מספריא ---\n{sefaria_data}")
        
    # 2. שליפה מהמאגר המקומי (JSON)
    database = load_torah_database()
    query_words = [w for w in query.split() if len(w) > 2]
    matched_local = []
    
    for item in database:
        content = item.get("content", "")
        book = item.get("book", "")
        if any(word in content or word in book for word in query_words):
            source_info = f"מקור מקומי: {book} "
            if "masechet" in item:
                source_info += f"מסכת {item['masechet']} דף {item['daf']} "
            if "siman" in item:
                source_info += f"סימן {item['siman']} סעיף {item['seif']} "
            source_info += f"\nתוכן המקור: \"{content}\""
            matched_local.append(source_info)
            
    if matched_local:
        context_parts.append(f"--- מקורות מהמאגר המקומי ---\n" + "\n\n".join(matched_local))
        
    if context_parts:
        return "\n\n".join(context_parts)
    return "לא נמצאו מקורות במאגרי המידע הזמינים."

SYSTEM_PROMPT = """
אתה מודול AI תורני מומחה, המנתח סוגיות הלכתיות, מחשבתיות ואקטואליות במתודולוגיה של בית מדרש ("סוגיה בעיון").
תפקידך להציג ניתוח יסודי, מעמיק ומדויק מפי המקורות ועד לפסיקת ההלכה למעשה.

כללי שפה ודיוק (חובה):
- ענה אך ורק בעברית תקנית, רהוטה ותורנית.
- אסור בהחלט לשלב מילים בשפות זרות (ערבית, אנגלית וכו'). הקפד על ניסוח עברי נקי.

כללי מקורות וציטוטים:
1. במידה וצורפו מקורות מספריא או מהמאגר המקומי, התבסס עליהם וצטט אותם מילה במילה במירכאות ("...").
2. במידה והמאגרים אינם מכילים את המקורות הנדרשים לסוגיה, עליך להביא מתוך הידע התורני שלך את המקורות המדויקים והמפורסמים (פסוקים, משניות, גמרות, ראשונים, שולחן ערוך ונושאי כלים) בציטוט מדויק ועם ציוני מקור מלאים.
3. אסור להמציא מקורות, ציטוטים או שמות ספרים שלא קיימים!

חובה עליך לבנות את התשובה לפי הסדר הלמדני הבא:

1. **הגדרת המקרה והשאלה:**
   - פירוק השאלה למרכיבים ההלכתיים שלה.

2. **יסוד הסוגיה במקורות (תנ"ך, משנה, גמרא):**
   - הובאת המקורות המרכזיים בציטוט מילה במילה עם ציון מקור מדויק והסבר הסוגיה.

3. **שיטות הראשונים (מחלוקות הסוגיה):**
   - הצגת השיטות השונות (רש"י, תוספות, רמב"ם, רמב"ן, רא"ש וכו') והסברת הסברה הלמדנית.

4. **פסיקת השולחן ערוך והנושאי כלים:**
   - הצגת פסק המחבר והרמ"א, ודברי נושאי הכלים המרכזיים.

5. **שו"תים ופוסקי זמננו (אקטואליה והיקש הלכתי):**
   - דיון בפסיקות מאוחרות והשלכות למעשה.

6. **מסקנה הלכתית למעשה:**
   - סיכום ברור של השורה התחתונה לפי מנהג ספרד ואשכנז.
   - הדגשה: "תוכן זה מיועד לעיון ולמידה, ובמקרה מעשי יש להתייעץ עם רב מורה הוראה."
"""

def analyze_sugya(question: str):
    try:
        retrieved_context = retrieve_all_context(question)
        
        prompt_with_context = f"""
מקורות שנשלפו מספריא ומאגר הנתונים:
{retrieved_context}

שאלה לניתוח: {question}
"""
        
        generation_config = {
            "temperature": 0.1,
            "top_p": 0.8,
        }
        
        # התאמה לדגם העדכני של גוגל
        model = genai.GenerativeModel(
            model_name='models/gemini-3.6-flash',
            system_instruction=SYSTEM_PROMPT,
            generation_config=generation_config
        )
        response = model.generate_content(prompt_with_context)
        return response.text

    except Exception as e:
        st.error(f"שגיאה בהפעלת המודל: {str(e)}")
        return None

# 6. עיצוב הממשק
st.title("📜 סוגיה בעיון")
st.caption("מנוע בינה מלאכותית לניתוח סוגיות הלכתיות ולמדניות (מחובר לספריא)")

if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = str(uuid.uuid4())
    st.session_state.messages = []

# הצגת היסטוריית השיחות בסרגל הצידי (Sidebar)
st.sidebar.title("💬 היסטוריית שיחות")

if st.sidebar.button("➕ שיחה חדשה"):
    st.session_state.current_session_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.rerun()

if st.sidebar.button("🗑️ מחיקת כל ההיסטוריה"):
    st.session_state.current_session_id = str(uuid.uuid4())
    st.session_state.messages = []
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)
    st.rerun()

st.sidebar.markdown("---")

all_sessions = load_all_sessions()

if isinstance(all_sessions, dict) and all_sessions:
    st.sidebar.caption("שיחות קודמות:")
    for s_id, s_data in all_sessions.items():
        if isinstance(s_data, dict):
            title = s_data.get("title", "שיחה ללא שם")
            display_title = title[:30] + "..." if len(title) > 30 else title
            if st.sidebar.button(display_title, key=f"session_{s_id}"):
                st.session_state.current_session_id = s_id
                st.session_state.messages = s_data.get("messages", [])
                st.rerun()
else:
    st.sidebar.info("אין שיחות קודמות שמורות.")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("הכנס שאלה או סוגיה בעיון..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("שולף מקורות מדויקים מספריא ומנתח את הסוגיה..."):
            answer = analyze_sugya(prompt)
            if answer:
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
                save_session(st.session_state.current_session_id, st.session_state.messages)
                st.rerun()
