# 1. ייבוא ספריות נדרשות
import streamlit as st  # ייבוא ספריית Streamlit לבניית ממשק המשתמש והצ'אט[cite: 1]
import os  # ייבוא ספריית os לעבודה עם מערכת הקבצים ומשתני סביבה[cite: 1]
import json  # ייבוא ספריית json לקריאה ועיבוד של קובצי נתונים מסוג JSON[cite: 1]
import requests  # ייבוא ספריית requests לביצוע קריאות HTTP ל-API של ספריא[cite: 1]
import re  # ייבוא ספריית re (Regular Expressions) לניקוי תגיות HTML[cite: 1]
from dotenv import load_dotenv  # ייבוא הפונקציה load_dotenv שטוענת משתני סביבה מקובץ .env[cite: 1]
import google.generativeai as genai  # ייבוא הספרייה הרשמית של גוגל לתקשורת עם מודל ה-AI של Gemini[cite: 1]

# 2. הגדרות דף האינטרנט
st.set_page_config(  # הגדרת פרמטרים בסיסיים של העמוד בדפדפן[cite: 1]
    page_title="סוגיה בעיון - AI תורני",  # קביעת הכותרת שתופיע בתווית הלשונית של הדפדפן[cite: 1]
    page_icon="📜",  # קביעת האייקון שיעמוד לצד כותרת הלשונית[cite: 1]
    layout="centered"  # הגדרת פריסת העמוד להיות מרוכזת במרכז המסך[cite: 1]
)  # סגירת סוגריים של הפונקציה set_page_config[cite: 1]

# הוספת CSS מקיף ליישור מלא מימין לשמאל (RTL)
st.markdown(  # הזרקת קוד CSS מותאם אישית לתוך דף ה-Streamlit[cite: 1]
    """
    <style>
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
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
    """,  # סיום מחרוזת ה-CSS הרב-שורתית[cite: 1]
    unsafe_allow_html=True  # מאשר ל-Streamlit לרנדר את תגיות ה-HTML/CSS שהוכנסו[cite: 1]
)  # סגירת הרצת ה-markdown[cite: 1]

# 3. טעינת מפתח ה-API
load_dotenv()  # טעינת משתני הסביבה מתוך קובץ .env מקומי (אם קיים)[cite: 1]

api_key = None  # אתחול משתנה המפתח לערך ריק[cite: 1]

if "GEMINI_API_KEY" in st.secrets:  # בדיקה אם המפתח מוגדר תחת GEMINI_API_KEY ב-Secrets של ענן Streamlit[cite: 1]
    api_key = str(st.secrets["GEMINI_API_KEY"]).strip()  # שמירת המפתח כמחרוזת וניקוי רווחים מיותרים[cite: 1]
elif "GOOGLE_API_KEY" in st.secrets:  # בדיקה חלופית אם המפתח מוגדר תחת GOOGLE_API_KEY ב-Secrets[cite: 1]
    api_key = str(st.secrets["GOOGLE_API_KEY"]).strip()  # שמירת המפתח החלופי וניקוי רווחים[cite: 1]
else:  # אם המפתח לא נמצא ב-Secrets[cite: 1]
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")  # ניסיון לשלוף את המפתח משתני הסביבה במערכת המקומית[cite: 1]

if not api_key:  # בדיקה אם המפתח עדיין ריק (לא נמצא באף מקור)[cite: 1]
    st.error("לא נמצא מפתח API! אנא הגדר GEMINI_API_KEY ב-Secrets ב-Streamlit Cloud.")  # הצגת הודעת שגיאה אדומה למשתמש[cite: 1]
    st.stop()  # עצירת הרצת האפליקציה במידה ואין מפתח תקף[cite: 1]

genai.configure(api_key=api_key)  # הגדרת מפתח ה-API בספרייה הרשמית של גוגל[cite: 1]

# 4. מנגנון שליפת מקורות מדויקים כולל ניקוד מ-Sefaria API
def fetch_from_sefaria(query: str) -> str:  # הגדרת פונקציה המקבלת שאילתה ומחזירה מחרוזת עם המקורות[cite: 1]
    """חיפוש ושליפת מקורות מדויקים בעברית (כולל ניקוד) מתוך ספריא"""  # תיעוד הפונקציה (Docstring)[cite: 1]
    try:  # פתיחת בלוק ניסיון למניעת קריסות במקרה של שגיאת תקשורת[cite: 1]
        url = "https://www.sefaria.org/api/v2/search/text"  # כתובת ה-Endpoint של מנוע החיפוש ב-API של ספריא[cite: 1]
        payload = {  # יצירת המילון המכיל את הפרמטרים לשליחה בבקשה[cite: 1]
            "query": query,  # מילת/משפט החיפוש שהוזנו[cite: 1]
            "type": "text",  # הגדרת סוג החיפוש לטקסט[cite: 1]
            "field": "exact",  # הגדרת שדה החיפוש להתאמה מדויקת[cite: 1]
            "size": 5  # הגבלת מספר התוצאות המוחזרות ל-5 בלבד[cite: 1]
        }  # סגירת מילון ה-payload[cite: 1]
        response = requests.post(url, json=payload, timeout=5)  # שליחת בקשת POST ל-API עם מגבלת זמן של 5 שניות[cite: 1]
        
        if response.status_code == 200:  # בדיקה אם התקבלה תשובה תקינה מהשרת (קוד 200 OK)[cite: 1]
            data = response.json()  # המרת תשובת ה-JSON המוחזרת למילון ב-Python[cite: 1]
            hits = data.get("hits", {}).get("hits", [])  # חילוץ רשימת תוצאות החיפוש (hits) מתוך ה-JSON[cite: 1]
            
            if not hits:  # בדיקה אם רשימת התוצאות ריקה[cite: 1]
                return "לא נמצאו מקורות תואמים בספריא."  # החזרת הודעה שלא נמצאו תוצאות[cite: 1]
            
            results = []  # אתחול רשימה ריקה לאגרגציה של התוצאות המעובדות[cite: 1]
            for hit in hits:  # לולאה המעבדת כל תוצאה בנפרד[cite: 1]
                source = hit.get("_source", {})  # חילוץ אובייקט ה-source המכיל את פרטי המקור[cite: 1]
                title = source.get("ref", "")  # חילוץ מראה המקום (למשל: "Shabbat 103a")[cite: 1]
                he_text = source.get("he", "")  # חילוץ הטקסט בעברית[cite: 1]
                
                if isinstance(he_text, str) and he_text.strip():  # בדיקה שהטקסט הוא מחרוזת תקינה ואינו ריק[cite: 1]
                    clean_text = re.sub(r'<[^>]+>', '', he_text)  # הסרת תגיות HTML בלבד ושמירה מלאה על הניקוד[cite: 1]
                    results.append(f"מקור מתוך ספריא [{title}]:\n\"{clean_text}\"")  # הוספת המקור המעובד לרשימה[cite: 1]
            
            if results:  # בדיקה אם נאספו תוצאות תקינות[cite: 1]
                return "\n\n".join(results)  # חיבור כל התוצאות למחרוזת אחת המופרדת בשורות ריקות[cite: 1]
                
    except Exception as e:  # תפיסת שגיאות במידה והתרחשה תקלה במהלך החיפוש[cite: 1]
        return f"לא ניתן היה לשלוף מקורות מספריא: {str(e)}"  # החזרת הודעת השגיאה[cite: 1]
    
    return "לא נמצאו מקורות ספציפיים בספריא."  # החזרת ברירת מחדל אם לא התקבלו תוצאות[cite: 1]

# 5. מנגנון שליפה משולב (מאגר מקומי + ספריא)
def load_torah_database():  # הגדרת פונקציה לטעינת המאגר המקומי[cite: 1]
    db_path = os.path.join("data", "torah_database.json")  # בניית הנתיב לקובץ ה-JSON המקומי בתיקיית data[cite: 1]
    if os.path.exists(db_path):  # בדיקה אם קובץ המאגר המקומי קיים בדיסק[cite: 1]
        try:  # ניסיון לקרוא את הקובץ[cite: 1]
            with open(db_path, "r", encoding="utf-8") as f:  # פתיחת הקובץ לקריאה בקידוד UTF-8[cite: 1]
                return json.load(f)  # טעינת והחזרת נתוני ה-JSON כרשימה/מילון[cite: 1]
        except Exception:  # תפיסת שגיאות קריאה במידה וקיימות[cite: 1]
            pass  # התעלמות משגיאה והמשך הלאה[cite: 1]
    return []  # החזרת רשימה ריקה אם הקובץ לא קיים או שארעה שגיאה[cite: 1]

def retrieve_all_context(query: str) -> str:  # הגדרת פונקציה המאחדת מכלול מקורות מכל המאגרים[cite: 1]
    context_parts = []  # אתחול רשימה לאיסוף חלקי ההקשר[cite: 1]
    
    # 1. שליפה מספריא (עם הניקוד המקורי)
    sefaria_data = fetch_from_sefaria(query)  # קריאה לפונקציית השליפה מספריא[cite: 1]
    if "לא נמצאו" not in sefaria_data and "לא ניתן" not in sefaria_data:  # בדיקה שנשלפו נתונים תקינים מספריא[cite: 1]
        context_parts.append(f"--- מקורות מדויקים מספריא (כולל ניקוד) ---\n{sefaria_data}")  # הוספת הנתונים מספריא להקשר[cite: 1]
        
    # 2. שליפה מהמאגר המקומי (JSON)
    database = load_torah_database()  # טעינת הנתונים מהמאגר המקומי[cite: 1]
    query_words = [w for w in query.split() if len(w) > 2]  # פירוק השאילתה למילים באורך גדול מ-2 אותיות[cite: 1]
    matched_local = []  # אתחול רשימה לתוצאות שנמצאו במאגר המקומי[cite: 1]
    
    for item in database:  # לולאה שעוברת על כל פריט במאגר המקומי[cite: 1]
        content = item.get("content", "")  # חילוץ תוכן הפריט[cite: 1]
        book = item.get("book", "")  # חילוץ שם הספר[cite: 1]
        if any(word in content or word in book for word in query_words):  # בדיקה אם מילה מהשאילתה מופיעה בתוכן או בשם הספר[cite: 1]
            source_info = f"מקור מקומי: {book} "  # יצירת מחרוזת תיאור המקור[cite: 1]
            if "masechet" in item:  # בדיקה אם קיימת שדה מסכת[cite: 1]
                source_info += f"מסכת {item['masechet']} דף {item['daf']} "  # הוספת פרטי המסכת והדף[cite: 1]
            if "siman" in item:  # בדיקה אם קיים שדה סימן[cite: 1]
                source_info += f"סימן {item['siman']} סעיף {item['seif']} "  # הוספת פרטי הסימן והסעיף[cite: 1]
            source_info += f"\nתוכן המקור: \"{content}\""  # הוספת תוכן המקור[cite: 1]
            matched_local.append(source_info)  # הוספת הפריט המעובד לרשימת התוצאות המקומיות[cite: 1]
            
    if matched_local:  # בדיקה אם נמצאו תוצאות במאגר המקומי[cite: 1]
        context_parts.append(f"--- מקורות מהמאגר המקומי ---\n" + "\n\n".join(matched_local))  # הוספתן לחלקי ההקשר[cite: 1]
        
    if context_parts:  # בדיקה אם נאסף הקשר כלשהו[cite: 1]
        return "\n\n".join(context_parts)  # החזרת כל חלקי ההקשר מחוברים יחד[cite: 1]
    return "לא נמצאו מקורות במאגרי המידע הזמינים."  # החזרת הודעת ברירת מחדל[cite: 1]

# 6. System Prompt מוקשח לציטוט מילה במילה + ניקוד
SYSTEM_PROMPT = """
אתה מודול AI תורני מומחה, המנתח סוגיות הלכתיות, מחשבתיות ואקטואליות במתודולוגיה של בית מדרש ("סוגיה בעיון").
תפקידך להציג ניתוח יסודי, מעמיק ומדויק מפי המקורות ועד לפסיקת ההלכה למעשה.

כללי ברזל לציטוט ומקורות (חובה מוחלטת):
1. כאשר אתה מביא ציטוט מתוך המקורות שנשלפו מספריא או מהמאגר המקומי, חובה עליך להביא אותו מילה במילה בדיוק מוחלט כפי שהוא מופיע במקור!
2. שמור על הניקוד המקורי כפי שנשלף מספריא. אל תוריד ניקוד, אל תשנה אותיות ואל תסדר מחדש את משפטי המקור.
3. תחום כל ציטוט מדויק בתוך מירכאות ("...").
4. ציין תמיד בצמוד לכל ציטוט את מראה המקום המדויק שלו בספריא.
5. אסור להמציא מקורות, ציטוטים, ניקוד או שמות ספרים שלא קיימים!

חובה עליך לבנות את התשובה לפי הסדר הלמדני הבא:

1. **הגדרת המקרה והשאלה:**
   - פירוק השאלה למרכיבים ההלכתיים שלה.

2. **יסוד הסוגיה במקורות (תנ"ך, משנה, גמרא):**
   - הובאת המקורות המרכזיים בציטוט מילה במילה (כולל ניקוד אם קיים במקור) עם מראה מקום מדויק והסבר הסוגיה.

3. **שיטות הראשונים (מחלוקות הסוגיה):**
   - הצגת השיטות השונות (רש"י, תוספות, רמב"ם, רמב"ן, רא"ש וכו') והסברת הסברה הלמדנית.

4. **פסיקת השולחן ערוך והנושאי כלים:**
   - הצגת פסק המחבר והרמ"א, ודברי נושאי הכלים המרכזיים.

5. **שו"תים ופוסקי זמננו (אקטואליה והיקש הלכתי):**
   - דיון בפסיקות מאוחרות והשלכות למעשה.

6. **מסקנה הלכתית למעשה:**
   - סיכום ברור של השורה התחתונה לפי מנהג ספרד ואשכנז.
   - הדגשה: "תוכן זה מיועד לעיון ולמידה, ובמקרה מעשי יש להתייעץ עם רב מורה הוראה."

כללי שפה ודיוק:
- ענה בעברית תקנית, רהוטה ותורנית בלבד.
"""  # הגדרת המחרוזת המכילה את כל הנחיות ה-System Prompt המפורטות[cite: 1]

def analyze_sugya(messages_history):  # הגדרת פונקציית הניתוח המקבלת את היסטוריית השיחה המלאה[cite: 1]
    try:  # פתיחת בלוק ניסיון להרצת הניתוח[cite: 1]
        last_prompt = messages_history[-1]["content"]  # חילוץ השאלה האחרונה שהזין המשתמש[cite: 1]
        retrieved_context = retrieve_all_context(last_prompt)  # שליפת המקורות הרלוונטיים מספריא/המאגר המקומי עבור השאלה האחרונה[cite: 1]
        
        # Temperature 0.0 מונע אילתורים ומבטיח היצמדות מוחלטת לציטוטים ולניקוד[cite: 1]
        generation_config = {  # יצירת מילון ההגדרות ליצירת התוכן על ידי המודל[cite: 1]
            "temperature": 0.0,  # קביעת טמפרטורה אפס למניעת הזיות ושמירה על דיוק מוחלט[cite: 1]
            "top_p": 0.8,  # הגבלת סינון ההסתברויות לבחירת המילים[cite: 1]
        }  # סגירת מילון ה-generation_config[cite: 1]
        
        model = genai.GenerativeModel(  # אתחול אובייקט המודל של Gemini[cite: 1]
            model_name='models/gemini-3.6-flash',  # הגדרת שם המודל הנדרש[cite: 1]
            system_instruction=SYSTEM_PROMPT,  # הזרקת ה-System Prompt שהוגדר לעיל[cite: 1]
            generation_config=generation_config  # הזרקת קונפיגורציית הטמפרטורה[cite: 1]
        )  # סגירת אתחול המודל[cite: 1]

        # המרת היסטוריית ההודעות מ-Streamlit לפורמט המתאים למודל Gemini[cite: 1]
        formatted_history = []  # אתחול רשימת היסטוריית ההודעות המפורמטת[cite: 1]
        for msg in messages_history[:-1]:  # מעבר על כל ההודעות הקודמות (ללא ההודעה האחרונה)[cite: 1]
            role = "user" if msg["role"] == "user" else "model"  # תרגום התפקיד מ-Streamlit ל-Gemini (user/model)[cite: 1]
            formatted_history.append({"role": role, "parts": [msg["content"]]})  # הוספת ההודעה בפורמט המתאים לרשימה[cite: 1]

        # התחלת שיחה מתמשכת (Chat) עם ההיסטוריה המפורמטת[cite: 1]
        chat = model.start_chat(history=formatted_history)  # פתיחת אובייקט שיחה במודל מבוסס היסטוריה[cite: 1]

        # בניית הודעת הפנייה האחרונה בשילוב ההקשר שנשלף[cite: 1]
        prompt_with_context = f"""
מקורות מדויקים שנשלפו מספריא ומאגר הנתונים:
{retrieved_context}

שאלה לניתוח: {last_prompt}
"""  # הרכבת הטקסט הסופי לשליחה למודל[cite: 1]

        response = chat.send_message(prompt_with_context)  # שליחת ההודעה האחרונה וקבלת התשובה תוך שמירת הקשר השיחה[cite: 1]
        return response.text  # החזרת הטקסט של התשובה שיוצרה[cite: 1]

    except Exception as e:  # תפיסת שגיאות במהלך יצירת התשובה[cite: 1]
        st.error(f"שגיאה בהפעלת המודל: {str(e)}")  # הצגת הודעת שגיאה במידת הצורך[cite: 1]
        return None  # החזרת ערך ריק במקרה שגיאה[cite: 1]

# 7. עיצוב הממשק והצגת היסטוריית הצ'אט
st.title("📜 סוגיה בעיון")  # הצגת כותרת הראשית של האפליקציה בתוך הממשק[cite: 1]
st.caption("מנוע בינה מלאכותית לניתוח סוגיות הלכתיות ולמדניות (מחובר בזמן אמת לספריא)")  # הצגת כותרת משנה תיאורית[cite: 1]

# אתחול היסטוריית ההודעות ב-st.session_state במידה ואינה קיימת עדיין[cite: 1]
if "messages" not in st.session_state:  # בדיקה אם הסטוריית ההודעות עוד לא אותחלה[cite: 1]
    st.session_state.messages = []  # אתחול רשימה ריקה לשמירת הסטוריית השיחה[cite: 1]

# הצגת כל הודעות הצ'אט הקודמות מתוך st.session_state[cite: 1]
for message in st.session_state.messages:  # לולאה שעוברת על כל הודעה בהיסטוריה[cite: 1]
    with st.chat_message(message["role"]):  # פתיחת בלוק הודעת צ'אט לפי ה-role (user/assistant)[cite: 1]
        st.markdown(message["content"])  # הצגת תוכן ההודעה בפורמט Markdown[cite: 1]

# קבלת קלט חדש מהמשתמש דרך תיבת הצ'אט[cite: 1]
if prompt := st.chat_input("הכנס שאלה או סוגיה בעיון..."):  # יצירת תיבת קלט למשתמש ובדיקה אם הוזנה שאלה[cite: 1]
    st.session_state.messages.append({"role": "user", "content": prompt})  # הוספת שאלת המשתמש להיסטוריה[cite: 1]
    with st.chat_message("user"):  # פתיחת בלוק הודעה עבור המשתמש[cite: 1]
        st.markdown(prompt)  # הצגת שאלת המשתמש במסך[cite: 1]

    with st.chat_message("assistant"):  # פתיחת בלוק הודעה עבור תשובת ה-AI[cite: 1]
        with st.spinner("שולף מקורות מדויקים ומנוקדים מספריא ומנתח את הסוגיה..."):  # הצגת הודעת טעינה מסתובבת[cite: 1]
            answer = analyze_sugya(st.session_state.messages)  # קריאה לפונקציית הניתוח עם כל היסטוריית השיחה[cite: 1]
            if answer:  # בדיקה שהתקבלה תשובה תקינה[cite: 1]
                st.markdown(answer)  # הצגת תשובת המודל במסך[cite: 1]
                st.session_state.messages.append({"role": "assistant", "content": answer})  # הוספת התשובה להיסטוריית השיחה[cite: 1]
