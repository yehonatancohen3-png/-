# ייבוא ספריית streamlit לבניית ממשק ה-Web והצ'אט
import streamlit as st
# ייבוא ספריית os לעבודה עם מערכת הקבצים ונתיבים
import os
# ייבוא ספריית json לקריאה ופענוח שלקבצי נתונים בפורמט JSON
import json
# ייבוא ספריית re לעבודה עם ביטויים רגולריים (Regular Expressions)
import re
# ייבוא ספריית requests לביצוע בקשות HTTP לרשת (כמו API של ספריא)
import requests
# ייבוא הפונקציה load_dotenv מתוך dotenv לטעינת משתני סביבה מקובץ .env
from dotenv import load_dotenv
# ייבוא ספריית Google Generative AI לעבודה עם מודלי Gemini
import google.generativeai as genai

# 1. הגדרות דף האינטרנט
# הגדרת הגדרות הדף הבסיסיות ב-Streamlit: כותרת הדף, האייקון שלו ופריסת העמוד
st.set_page_config(
    page_title="סוגיה בעיון - AI תורני",
    page_icon="📜",
    layout="centered"
)

# הוספת CSS מקיף ליישור מלא מימין לשמאל (RTL)
# הזרקת קוד CSS מותאם אישית לממשק כדי להבטיח שכל האלמנטים ייזחלו ויצופו מימין לשמאל (RTL)
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
# הפעלת הפונקציה שקוראת את משתני הסביבה מקובץ .env המקומי
load_dotenv()

# הגדרת משתנה ראשוני לאחסון מפתח ה-API
api_key = None

# בדיקה אם המפתח קיים באובייקט ה-Secrets של Streamlit Cloud תחת השם GEMINI_API_KEY
if "GEMINI_API_KEY" in st.secrets:
    # שמירת המפתח וניקוי רווחים מיותרים בקצוות
    api_key = str(st.secrets["GEMINI_API_KEY"]).strip()
# בדיקה אם המפתח קיים באובייקט ה-Secrets תחת השם החלופי GOOGLE_API_KEY
elif "GOOGLE_API_KEY" in st.secrets:
    # שמירת המפתח וניקוי רווחים מיותרים בקצוות
    api_key = str(st.secrets["GOOGLE_API_KEY"]).strip()
# במידה ולא נמצא ב-Secrets, ניסיון שליפת המפתח מתוך משתני הסביבה של מערכת ההפעלה או קובץ .env
else:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

# אם לא נמצא מפתח באף אחד מהמקורות, הצגת הודעת שגיאה ועצירת הרצת האפליקציה
if not api_key:
    st.error("לא נמצא מפתח API! אנא הגדר GEMINI_API_KEY ב-Secrets ב-Streamlit Cloud.")
    st.stop()

# הגדרת מפתח ה-API בספריית Google Generative AI לתקשורת מול השרתים
genai.configure(api_key=api_key)

# 3. מנגנון שליפת מקורות בזמן אמת מ-Sefaria API
# הגדרת פונקציה המקבלת מחרוזת חיפוש ומחזירה מקורות מתוך ה-API של ספריא
def fetch_from_sefaria(query: str) -> str:
    """חיפוש ושליפת מקורות מדויקים בעברית מתוך ספריא"""
    # בלוק try לטיפול בשגיאות תקשורת או שגיאות בבקשת ה-API
    try:
        # הגדרת כתובת ה-URL לשליפת הנתונים מ-Sefaria API
        url = "https://www.sefaria.org/api/v2/search/text"
        # הגדרת מכלול הנתונים (payload) שיישלחו בבקשת ה-POST
        payload = {
            "query": query,      # טקסט השאלה לחיפוש
            "type": "text",      # חיפוש בתוך טקסטים
            "field": "exact",    # חיפוש מדויק
            "size": 5            # החזרת עד 5 תוצאות ראשונות
        }
        # ביצוע בקשת POST לרשת עם הגדרת זמן קצוב (timeout) של 5 שניות
        response = requests.post(url, json=payload, timeout=5)
        
        # בדיקה אם השרת החזיר תשובה תקינה (קוד סטטוס 200 OK)
        if response.status_code == 200:
            # המרת תשובת השרת מפורמט JSON למילון פייתון
            data = response.json()
            # חילוץ רשימת הצירופים/התוצאות (hits) מתוך מבנה ה-JSON
            hits = data.get("hits", {}).get("hits", [])
            
            # אם לא חזרו תוצאות, החזרת הודעה מתאימה
            if not hits:
                return "לא נמצאו מקורות תואמים בספריא."
            
            # יצירת רשימה ריקה לאחסון המקורות המעובדים
            results = []
            # לולאה המעוברת על כל תוצאה שחזרה מחיפוש ספריא
            for hit in hits:
                # חילוץ אובייקט ה-source מתוך התוצאה
                source = hit.get("_source", {})
                # חילוץ שם המקור/האזכור (ref)
                title = source.get("ref", "")
                # חילוץ הטקסט בעברית (he)
                he_text = source.get("he", "")
                
                # בדיקה שהטקסט אינו ריק ושהוא מסוג מחרוזת
                if isinstance(he_text, str) and he_text.strip():
                    # ניקוי תגיות HTML מהטקסט של ספריא באמצעות ביטוי רגולרי
                    clean_text = re.sub(r'<[^>]+>', '', he_text)
                    # הוספת המקור המנוקה לרשימת התוצאות
                    results.append(f"מקור מתוך ספריא ({title}):\n\"{clean_text}\"")
            
            # אם נאספו תוצאות, חיבורן למחרוזת אחת עם שורות רווח ביניהן והחזרתן
            if results:
                return "\n\n".join(results)
                
    # תפיסת כל שגיאה שעלולה לקרות במהלך התקשורת והחזרת הודעת שגיאה מתאימה
    except Exception as e:
        return f"לא ניתן היה לשלוף מקורות מספריא: {str(e)}"
    
    # במידה ולא נאספו תוצאות תקינות, החזרת מחרוזת ברירת מחדל
    return "לא נמצאו מקורות ספציפיים בספריא."

# 4. מנגנון שליפה משולב (מאגר מקומי + ספריא)
# הגדרת פונקציה לטעינת מאגר הנתונים המקומי מקובץ JSON
def load_torah_database():
    # יצירת נתיב לקובץ torah_database.json בתוך תיקיית data
    db_path = os.path.join("data", "torah_database.json")
    # בדיקה האם הקובץ קיים בנתיב המבוקש
    if os.path.exists(db_path):
        # בלוק try לקריאה בטוחה של הקובץ
        try:
            # פתיחת הקובץ לקריאה בקידוד utf-8
            with open(db_path, "r", encoding="utf-8") as f:
                # טעינת תוכן ה-JSON והחזרתו כקובץ מילון/רשימה בפייתון
                return json.load(f)
        # התעלמות משגיאות במקרה של בעיה בקריאת הקובץ
        except Exception as e:
            pass
    # החזרת רשימה ריקה במידה והקובץ לא קיים או שנכשלה הקריאה
    return []

# הגדרת פונקציה המאחדת את השליפה מ-Sefaria וממהמאגר המקומי
def retrieve_all_context(query: str) -> str:
    # יצירת רשימה ריקה לאחסון חלקי המקורות השונים
    context_parts = []
    
    # 1. שליפה מספריא
    # קריאה לפונקציית החיפוש בספריא עם שאלת המשתמש
    sefaria_data = fetch_from_sefaria(query)
    # בדיקה אם חזרו תוצאות ממשיות (ולא הודעת חוסר תוצאות/שגיאה)
    if "לא נמצאו" not in sefaria_data and "לא ניתן" not in sefaria_data:
        # הוספת המקורות מספריא לרשימת חלקי המקורות
        context_parts.append(f"--- מקורות מדויקים מספריא ---\n{sefaria_data}")
        
    # 2. שליפה מהמאגר המקומי (JSON)
    # טעינת מאגר הנתונים המקומי
    database = load_torah_database()
    # פירוק שאלת המשתמש למילים וסינון מילים קצרות (פחות מ-3 אותיות)
    query_words = [w for w in query.split() if len(w) > 2]
    # יצירת רשימה ריקה למקורות תואמים מהמאגר המקומי
    matched_local = []
    
    # לולאה המעוברת על כל פריט במאגר הנתונים המקומי
    for item in database:
        # שליפת תוכן המקור ושם הספר
        content = item.get("content", "")
        book = item.get("book", "")
        # בדיקה אם אחת ממילות השאלה מופיעה בתוכן המקור או בשם הספר
        if any(word in content or word in book for word in query_words):
            # יצירת מחרוזת תיאור המקור
            source_info = f"מקור מקומי: {book} "
            # הוספת פרטי מסכת ודף במידה וקיימים
            if "masechet" in item:
                source_info += f"מסכת {item['masechet']} דף {item['daf']} "
            # הוספת פרטי סימן וסעיף במידה וקיימים
            if "siman" in item:
                source_info += f"סימן {item['siman']} סעיף {item['seif']} "
            # הוספת טקסט המקור
            source_info += f"\nתוכן המקור: \"{content}\""
            # הוספת המקור לרשימת המקורות המקומיים התואמים
            matched_local.append(source_info)
            
    # אם נמצאו מקורות במאגר המקומי, חיבורם והוספתם לרשימה הכללית
    if matched_local:
        context_parts.append(f"--- מקורות מהמאגר המקומי ---\n" + "\n\n".join(matched_local))
        
    # אם נאספו מקורות כלשהם (מספריא או מקומי), איחודם למחרוזת אחת והחזרתה
    if context_parts:
        return "\n\n".join(context_parts)
    # במידה ולא נמצאו מקורות באף מאגר, החזרת מחרוזת הודעה
    return "לא נמצאו מקורות במאגרי המידע הזמינים."

# הגדרת מחרוזת ה-System Prompt המכילה את הוראות המודל והמבנה הנדרש
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

# הגדרת הפונקציה הראשית לניתוח הסוגיה ושליחת הבקשה למודל
def analyze_sugya(question: str):
    # בלוק try לטיפול בשגיאות בזמן הפעלת המודל
    try:
        # קריאה לפונקציה לשליפת כל המקורות הרלוונטיים (מקומי + ספריא)
        retrieved_context = retrieve_all_context(question)
        
        # הרכבת הפרומפט המלא לשליחה למודל: חיבור המקורות שנשלפו יחד עם השאלה
        prompt_with_context = f"""
מקורות שנשלפו מספריא ומאגר הנתונים:
{retrieved_context}

שאלה לניתוח: {question}
"""
        
        # הגדרת פרמטרי היצירה של המודל (טמפרטורה נמוכה למניעת הזיות ודיוק גבוה)
        generation_config = {
            "temperature": 0.1,  # הגדרת יצירתיות נמוכה מאוד לטובת נאמנות למקורות
            "top_p": 0.8,        # הגבלת מגוון המילים שנבחרות
        }
        
        # יצירת אובייקט המודל של Gemini עם הדגם הספציפי, ה-System Prompt וההגדרות
        model = genai.GenerativeModel(
            model_name='models/gemini-3.6-flash',
            system_instruction=SYSTEM_PROMPT,
            generation_config=generation_config
        )
        # שליחת הפרומפט המשולב למודל וקבלת התשובה
        response = model.generate_content(prompt_with_context)
        # החזרת טקסט התשובה שהפיק המודל
        return response.text

    # תפיסת שגיאות בזמן הרצת המודל, הצגת הודעה בממשק והחזרת None
    except Exception as e:
        st.error(f"שגיאה בהפעלת המודל: {str(e)}")
        return None

# 5. עיצוב הממשק
# הצגת כותרת ראשית בדף האתר
st.title("📜 סוגיה בעיון")
# הצגת כותרת משנה / תיאור קצר מתחת לכותרת
st.caption("מנוע בינה מלאכותית לניתוח סוגיות הלכתיות ולמדניות (מחובר לספריא)")

# אתחול רשימת ההודעות ב-session_state במידה והיא עדיין לא קיימת
if "messages" not in st.session_state:
    st.session_state.messages = []

# הצגת היסטוריית השאלות בסרגל הצידי (Sidebar)
st.sidebar.title("💬 שאלות קודמות")
user_questions = [msg["content"] for msg in st.session_state.messages if msg["role"] == "user"]

if user_questions:
    for idx, q in enumerate(user_questions, 1):
        st.sidebar.markdown(f"**{idx}.** {q}")
else:
    st.sidebar.info("עדיין לא נשאלו שאלות בשיחה זו.")

# לולאה המציגה את כל הודעות העבר השמורות ב-session_state בתוך רכיבי צ'אט
for message in st.session_state.messages:
    # פתיחת בלוק הודעת צ'אט לפי התפקיד (user או assistant)
    with st.chat_message(message["role"]):
        # הצגת תוכן ההודעה בפורמט Markdown
        st.markdown(message["content"])

# קבלת קלט מהמשתמש מתוך תיבת הצ'אט (אם הוקלד טקסט)
if prompt := st.chat_input("הכנס שאלה או סוגיה בעיון..."):
    # הוספת שאלת המשתמש לרשימת ההודעות ב-session_state
    st.session_state.messages.append({"role": "user", "content": prompt})
    # הצגת הודעת המשתמש בממשק הצ'אט
    with st.chat_message("user"):
        st.markdown(prompt)

    # פתיחת בלוק תגובת עוזר ה-AI
    with st.chat_message("assistant"):
        # הצגת רכיב טעינה מסתובב בזמן שליפת המקורות והרצת המודל
        with st.spinner("שולף מקורות מדויקים מספריא ומנתח את הסוגיה..."):
            # קריאה לפונקציית הניתוח עם שאלת המשתמש
            answer = analyze_sugya(prompt)
            # אם התקבלה תשובה תקינה מהמודל
            if answer:
                # הצגת התשובה בממשק הצ'אט בפורמט Markdown
                st.markdown(answer)
                # שמירת תשובת העוזר ברשימת ההודעות ב-session_state
                st.session_state.messages.append({"role": "assistant", "content": answer})
                # רענון הממשק עדכון סרגל הצד באופן מיידי
                st.rerun()
