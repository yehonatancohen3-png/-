import streamlit as st
import os
import json
from dotenv import load_dotenv
import google.generativeai as genai

# 1. הגדרות דף האינטרנט
st.set_page_config(
    page_title="סוגיה בעיון - AI תורני",
    page_icon="📜",
    layout="centered"
)

# הוספת CSS ליישור מלא מימין לשמאל (RTL) לכל רכיבי האתר
st.markdown(
    """
    <style>
    /* יישור כללי של הדף, הגוף, והמיכלים המרכזיים */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stSidebar"] {
        direction: rtl !important;
        text-align: right !important;
    }
    
    /* יישור הטרמינל/אזור הצ'אט, תיבות ההודעות והקלט */
    [data-testid="stChatMessage"], [data-testid="stChatInput"], div[data-baseweb="input"] {
        direction: rtl !important;
        text-align: right !important;
    }

    /* יישור כותרות, טקסט חופשי ופסקי דין */
    h1, h2, h3, h4, h5, h6, p, div, span, label {
        direction: rtl !important;
        text-align: right !important;
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

# הגדרת מפתח ה-API
genai.configure(api_key=api_key)

# 3. מנגנון שליפת מקורות מתוך מאגר ה-JSON (RAG Retrieval)
def load_torah_database():
    """טעינת מאגר הנתונים הסגור מתיקיית data"""
    db_path = os.path.join("data", "torah_database.json")
    if os.path.exists(db_path):
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.warning(f"אזהרה: לא ניתן לקרוא את מאגר הנתונים: {e}")
    return []

def retrieve_relevant_context(query: str, database: list) -> str:
    """חיפוש ושליפת מקורות מתאימים מתוך המאגר הסגור לפי מילות מפתח"""
    if not database:
        return "לא נמצאו מקורות במאגר המקומי."
    
    matched_sources = []
    query_words = set(query.split())
    
    for item in database:
        content = item.get("content", "")
        book = item.get("book", "")
        # בדיקת התאמת מילים פשוטה
        if any(word in content or word in book for word in query_words if len(word) > 2):
            source_info = f"מקור: {book} "
            if "masechet" in item:
                source_info += f"מסכת {item['masechet']} דף {item['daf']} "
            if "siman" in item:
                source_info += f"סימן {item['siman']} סעיף {item['seif']} "
            source_info += f"\nתוכן המקור: \"{content}\""
            matched_sources.append(source_info)
    
    if matched_sources:
        return "\n\n".join(matched_sources)
    return "לא נמצאו מקורות ספציפיים במאגר המקומי לשאלה זו."

SYSTEM_PROMPT = """
אתה מודול AI תורני מומחה, המנתח סוגיות הלכתיות, מחשבתיות ואקטואליות במתודולוגיה של בית מדרש ("סוגיה בעיון").
תפקידך להציג ניתוח יסודי, מעמיק ומדויק מפי המקורות ועד לפסיקת ההלכה למעשה.

חובה עליך להתבסס ראשית לכל על המקורות המצורפים מהמאגר הסגור! אסור להמציא ציטוטים, שמות ספרים או מקורות שלא קיימים.

חובה עליך לבנות את התשובה לפי הסדר הלמדני הבא:

1. **הגדרת המקרה והשאלה:**
   - פירוק השאלה למרכיבים ההלכתיים שלה (לדוגמה: איסור דאורייתא/דרבנן, ספק, גרמא, כבוד הבריות וכדומה).

2. **יסוד הסוגיה במקורות (תנ"ך, משנה, גמרא):**
   - הובאת המקורות המרכזיים עם הסבר מדויק של הנדון בגמרא.

3. **שיטות הראשונים (מחלוקות הסוגיה):**
   - הצגת השיטות השונות (רש"י, תוספות, רמב"ם, רמב"ן, רא"ש וכו') והסברת הסברה של כל שיטה.

4. **פסיקת השולחן ערוך והנושאי כלים:**
   - הצגת פסק המחבר (רבי יוסף קארו) והרמ"א, ודברי נושאי הכלים המרכזיים (משנה ברורה, ש"ך, ט"ז וכדומה).

5. **שו"תים ופוסקי זמננו (אקטואליה והיקש הלכתי):**
   - דיון בפסיקות המאה 20-21. במידה ומדובר בשאלה חדשה (טכנולוגיה, רפואה), עשה "דימוי מילתא למילתא" והסבר מאיזה יסוד עתיק נלמד המקרה החדש.

6. **מסקנה הלכתית למעשה:**
   - סיכום ברור של השורה התחתונה לפי מנהג ספרד ואשכנז.
   - הדגשה: "תוכן זה מיועד לעיון ולמידה, ובמקרה מעשי יש להתייעץ עם רב מורה הוראה."

כללי שפה, דיוק ואיות (חובה):
- ענה בעברית תקנית, רהוטה ומדויקת בלבד. אסור להמציא מילים, הטיות לא קיימות או מילים מומצאות!
- הקפד על דקדוק ואיות ללא שגיאות כתיב.
- אם אינך בטוח במקור מדויק, ציין זאת מפורשות ואל תנחש.
- שמור על שפה תורנית, מכובדת ולמדנית.
"""

def analyze_sugya(question: str):
    try:
        # שליפת מקורות מתוך מאגר ה-JSON
        database = load_torah_database()
        retrieved_context = retrieve_relevant_context(question, database)
        
        # בניית הפרומפט המשולב עם המקורות שנשלפו (Grounding)
        prompt_with_context = f"""
מקורות שנשלפו מתוך המאגר התורני הסגור:
{retrieved_context}

שאלה לניתוח: {question}
"""
        
        # הגדרת פרמטרים מוקשחים למניעת המצאות ושגיאות כתיב
        generation_config = {
            "temperature": 0.0,
            "top_p": 0.8,
        }
        
        # שימוש במודל gemini-3.6-flash עם הגדרות System Prompt ו-Temperature
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

# 4. עיצוב הממשק
st.title("📜 סוגיה בעיון")
st.caption("מנוע בינה מלאכותית לניתוח סוגיות הלכתיות ולמדניות")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("הכנס שאלה או סוגיה בעיון..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("מנתח את הסוגיה במקורות..."):
            answer = analyze_sugya(prompt)
            if answer:
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
