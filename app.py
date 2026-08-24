import streamlit as st
import os
from dotenv import load_dotenv
import google.generativeai as genai

# 1. הגדרות דף האינטרנט
st.set_page_config(
    page_title="סוגיה בעיון - AI תורני",
    page_icon="📜",
    layout="centered"
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

SYSTEM_PROMPT = """
אתה מודול AI תורני מומחה, המנתח סוגיות הלכתיות, מחשבתיות ואקטואליות במתודולוגיה של בית מדרש ("סוגיה בעיון").
תפקידך להציג ניתוח יסודי, מעמיק ומדויק מפי המקורות ועד לפסיקת ההלכה למעשה, ללא שגיאות או המצאות.

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

כללי ברזל:
- אל תמציא ציטוטים או מקורות שלא קיימים.
- שמור על שפה תורנית, מכובדת ולמדנית.
"""

def analyze_sugya(question: str):
    try:
        # שימוש במודל gemini-3.6-flash הנדרש ע"י ה-API
        model = genai.GenerativeModel('models/gemini-3.6-flash')
        response = model.generate_content(f"{SYSTEM_PROMPT}\n\nשאלה לניתוח: {question}")
        return response.text
    except Exception as e:
        st.error(f"שגיאה בהפעלת המודל: {str(e)}")
        return None

# 3. עיצוב הממשק
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
