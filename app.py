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

# 3. מנגנון שליפת מקורות מתוך מאגר ה-JSON (RAG Retrieval)
def load_torah_database():
    db_path = os.path.join("data", "torah_database.json")
    if os.path.exists(db_path):
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.warning(f"אזהרה: לא ניתן לקרוא את מאגר הנתונים: {e}")
    return []

def retrieve_relevant_context(query: str, database: list) -> str:
    if not database:
        return "אין מקורות במאגר המקומי."
    
    matched_sources = []
    # חיפוש גמיש יותר לפי תת-מחרוזות
    query_words = [w for w in query.split() if len(w) > 2]
    
    for item in database:
        content = item.get("content", "")
        book = item.get("book", "")
        if any(word in content or word in book for word in query_words):
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

כללי שפה ודיוק (חובה):
- ענה אך ורק בעברית תקנית, רהוטה ותורנית.
- אסור בהחלט לשלב מילים בשפות זרות (ערבית, אנגלית וכו'). הקפד על ניסוח עברי נקי.

כללי מקורות וציטוטים:
1. במידה וצורפו מקורות מהמאגר המקומי, התבסס עליהם וצטט אותם מילה במילה במירכאות ("...").
2. במידה והמאגר המקומי אינו מכיל את המקורות הנדרשים לסוגיה, עליך להביא מתוך הידע התורני שלך את המקורות המדויקים והמפורסמים (פסוקים, משניות, גמרות, ראשונים, שולחן ערוך ונושאי כלים) בציטוט מדויק ועם ציוני מקור מלאים (שם הספר, מסכת/סימן/סעיף).
3. אסור להמציא מקורות, ציטוטים או שמות ספרים שלא קיימים!

חובה עליך לבנות את התשובה לפי הסדר הלמדני הבא:

1. **הגדרת המקרה והשאלה:**
   - פירוק השאלה למרכיבים ההלכתיים שלה (לדוגמה: מוחזקות, ספק ממון, תקפו כהן, המוציא מחברו עליו הראיה וכדומה).

2. **יסוד הסוגיה במקורות (תנ"ך, משנה, גמרא):**
   - הובאת המקורות המרכזיים בציטוט מילה במילה עם ציון מקור מדויק והסבר הסוגיה.

3. **שיטות הראשונים (מחלוקות הסוגיה):**
   - הצגת השיטות השונות (רש"י, תוספות, רמב"ם, רמב"ן, רא"ש וכו') והסברת הסברה הלמדנית של כל שיטה.

4. **פסיקת השולחן ערוך והנושאי כלים:**
   - הצגת פסק המחבר והרמ"א, ודברי נושאי הכלים המרכזיים (ש"ך, ט"ז, משנה ברורה וכדומה).

5. **שו"תים ופוסקי זמננו (אקטואליה והיקש הלכתי):**
   - דיון בפסיקות מאוחרות והשלכות למעשה.

6. **מסקנה הלכתית למעשה:**
   - סיכום ברור של השורה התחתונה לפי מנהג ספרד ואשכנז.
   - הדגשה: "תוכן זה מיועד לעיון ולמידה, ובמקרה מעשי יש להתייעץ עם רב מורה הוראה."
"""

def analyze_sugya(question: str):
    try:
        database = load_torah_database()
        retrieved_context = retrieve_relevant_context(question, database)
        
        prompt_with_context = f"""
מקורות שנשלפו מתוך המאגר המקומי:
{retrieved_context}

שאלה לניתוח: {question}
"""
        
        generation_config = {
            "temperature": 0.1,  # טמפרטורה נמוכה המאפשרת שליפת מקורות אמינים תוך שמירה על דיוק
            "top_p": 0.8,
        }
        
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
