# 1. ייבוא ספריות נדרשות
import streamlit as st  # ייבוא ספריית Streamlit לבניית ממשק המשתמש והצ'אט[cite: 1]
import os  # ייבוא ספריית os לעבודה עם מערכת הקבצים ומענה על משתני סביבה[cite: 1]
import json  # ייבוא ספריית json לקריאה ועיבוד של קובצי נתונים[cite: 1]
import requests  # ייבוא ספריית requests לביצוע קריאות HTTP ל-API[cite: 1]
import re  # ייבוא ספריית re לניקוי תגיות HTML[cite: 1]
import time  # ייבוא ספריית time לניהול הנגן/המתנה בין הודעה להודעה
from concurrent.futures import ThreadPoolExecutor  # ייבוא מנהל משימות ברקע לקבלת תשובה במקביל
from dotenv import load_dotenv  # ייבוא הפונקציה load_dotenv שטוענת משתני סביבה מקובץ .env[cite: 1]
import google.generativeai as genai  # ייבוא הספרייה הרשמית של גוגל לתקשורת עם Gemini[cite: 1]

# 2. הגדרות דף האינטרנט
st.set_page_config(  # הגדרת פרמטרים בסיסיים של העמוד בדפדפן[cite: 1]
    page_title="סוגיה בעיון - AI תורני",  # קביעת הכותרת שתופיע בתווית הלשונית[cite: 1]
    page_icon="📜",  # קביעת האייקון שיעמוד לצד כותרת הלשונית[cite: 1]
    layout="centered"  # הגדרת פריסת העמוד להיות מרוכזת במרכז המסך[cite: 1]
)

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
    """,
    unsafe_allow_html=True  # מאשר לרנדר את ה-CSS[cite: 1]
)

# 3. טעינת מפתח ה-API
load_dotenv()  # טעינת משתני הסביבה מתוך קובץ .env[cite: 1]

api_key = None  # אתחול משתנה המפתח[cite: 1]

if "GEMINI_API_KEY" in st.secrets:  # בדיקה ב-Secrets של Streamlit Cloud[cite: 1]
    api_key = str(st.secrets["GEMINI_API_KEY"]).strip()  # שמירת המפתח[cite: 1]
elif "GOOGLE_API_KEY" in st.secrets:  # בדיקה חלופית[cite: 1]
    api_key = str(st.secrets["GOOGLE_API_KEY"]).strip()  # שמירת המפתח החלופי[cite: 1]
else:  # ניסיון משתני סביבה במערכת המקומית[cite: 1]
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")  # שליפת המפתח[cite: 1]

if not api_key:  # בדיקה אם לא נמצא מפתח[cite: 1]
    st.error("לא נמצא מפתח API! אנא הגדר GEMINI_API_KEY ב-Secrets ב-Streamlit Cloud.")  # הודעת שגיאה[cite: 1]
    st.stop()  # עצירת האפליקציה[cite: 1]

genai.configure(api_key=api_key)  # הגדרת המפתח במודל[cite: 1]

# 4. מנגנון שליפת מקורות מדויקים כולל ניקוד מ-Sefaria API
def fetch_from_sefaria(query: str) -> str:  # פונקציה לשליפת מקורות[cite: 1]
    try:
        url = "https://www.sefaria.org/api/v2/search/text"  # Endpoint מנוע החיפוש[cite: 1]
        payload = {  # פרמטרי הבקשה[cite: 1]
            "query": query,
            "type": "text",
            "field": "exact",
            "size": 5
        }
        response = requests.post(url, json=payload, timeout=5)  # ביצוע הבקשה[cite: 1]
        
        if response.status_code == 200:  # בדיקת תקינות התשובה[cite: 1]
            data = response.json()  # פענוח JSON[cite: 1]
            hits = data.get("hits", {}).get("hits", [])  # חילוץ התוצאות[cite: 1]
            
            if not hits:
                return "לא נמצאו מקורות תואמים בספריא."  # הודעה ללא תוצאות[cite: 1]
            
            results = []
            for hit in hits:
                source = hit.get("_source", {})
                title = source.get("ref", "")
                he_text = source.get("he", "")
                
                if isinstance(he_text, str) and he_text.strip():
                    clean_text = re.sub(r'<[^>]+>', '', he_text)  # הסרת תגיות HTML לשמירה על ניקוד[cite: 1]
                    results.append(f"מקור מתוך ספריא [{title}]:\n\"{clean_text}\"")
            
            if results:
                return "\n\n".join(results)  # חיבור כל התוצאות[cite: 1]
                
    except Exception as e:
        return f"לא ניתן היה לשלוף מקורות מספריא: {str(e)}"  # טיפול בשגיאה[cite: 1]
    
    return "לא נמצאו מקורות ספציפיים בספריא."

# 5. מנגנון שליפה משולב (מאגר מקומי + ספריא)
def load_torah_database():
    db_path = os.path.join("data", "torah_database.json")  # נתיב למאגר המקומי[cite: 1]
    if os.path.exists(db_path):
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                return json.load(f)  # טעינת המאגר המקומי[cite: 1]
        except Exception:
            pass
    return []

def retrieve_all_context(query: str) -> str:
    context_parts = []
    
    # שליפה מספריא
    sefaria_data = fetch_from_sefaria(query)  # שליפה[cite: 1]
    if "לא נמצאו" not in sefaria_data and "לא ניתן" not in sefaria_data:
        context_parts.append(f"--- מקורות מדויקים מספריא (כולל ניקוד) ---\n{sefaria_data}")  # הרכבת ההקשר[cite: 1]
        
    # שליפה מהמאגר המקומי
    database = load_torah_database()  # טעינת המאגר[cite: 1]
    query_words = [w for w in query.split() if len(w) > 2]  # סינון מילים[cite: 1]
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
        context_parts.append(f"--- מקורות מהמאגר המקומי ---\n" + "\n\n".join(matched_local))  # הוספה[cite: 1]
        
    if context_parts:
        return "\n\n".join(context_parts)  # החזרת ההקשר המלא[cite: 1]
    return "לא נמצאו מקורות במאגרי המידע הזמינים."

# 6. System Prompt מוקשח לציטוט מילה במילה + ניקוד
SYSTEM_PROMPT = """
אתה מודול AI תורני מומחה, המנתח סוגיות הלכתיות, מחשבתיות ואקטואליות במתודולוגיה של בית מדרש ("סוגיה בעיון").
תפקידך להציג ניתוח יסודי, מעמיק ומדויק מפי המקורות ועד לפסיקת ההלכה למעשה.

כללי ברזל לציטוט ומקורות (חובה מוחלטת):
1. כאשר אתה מביא ציטוט מתוך המקורות שנשלפו מספריא או מהמאגר המקומי, חובה עליך להביא אותו מילה במילה בדיוק מוחלט כפי שהוא מופיע במקור!
2. שמור על הניקוד המקורי כפי שנשלף מספריא. אל תוריד ניקוד, אל תשנה אותיות ואל תשנה את המבנה.
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
"""  # ה-Prompt הלמדני המוגדר[cite: 1]

def analyze_sugya(messages_history):  # פונקציית הניתוח[cite: 1]
    try:
        last_prompt = messages_history[-1]["content"]  # שליפת השאלה האחרונה[cite: 1]
        retrieved_context = retrieve_all_context(last_prompt)  # שליפת המקורות[cite: 1]
        
        generation_config = {
            "temperature": 0.0,  # אפס אילתורים[cite: 1]
            "top_p": 0.8,
        }
        
        model = genai.GenerativeModel(
            model_name='models/gemini-3.6-flash',  # שם המודל[cite: 1]
            system_instruction=SYSTEM_PROMPT,
            generation_config=generation_config
        )

        formatted_history = []  # פירמוט ההיסטוריה לערכים של Gemini[cite: 1]
        for msg in messages_history[:-1]:
            role = "user" if msg["role"] == "user" else "model"
            formatted_history.append({"role": role, "parts": [msg["content"]]})

        chat = model.start_chat(history=formatted_history)  # תחילת השרשור[cite: 1]

        prompt_with_context = f"""
מקורות מדויקים שנשלפו מספריא ומאגר הנתונים:
{retrieved_context}

שאלה לניתוח: {last_prompt}
"""
        response = chat.send_message(prompt_with_context)  # שליחת הבקשה המעובדת[cite: 1]
        return response.text

    except Exception as e:
        st.error(f"שגיאה בהפעלת המודל: {str(e)}")  # טיפול בשגיאות[cite: 1]
        return None

# 7. עיצוב הממשק והצגת היסטוריית הצ'אט
st.title("📜 סוגיה בעיון")  # כותרת הדף[cite: 1]
st.caption("מנוע בינה מלאכותית לניתוח סוגיות הלכתיות ולמדניות (מחובר בזמן אמת לספריא)")  # תיאור[cite: 1]

# אתחול היסטוריית ההודעות במידה ואינה קיימת[cite: 1]
if "messages" not in st.session_state:
    st.session_state.messages = []  # יצירת סשן הודעות ריק[cite: 1]

# הצגת כל הודעות הצ'אט הקודמות[cite: 1]
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])  # רינדור ההודעות[cite: 1]

# קבלת קלט חדש מהמשתמש[cite: 1]
if prompt := st.chat_input("הכנס שאלה או סוגיה בעיון..."):  # זיהוי השאלה מתיבת הצ'אט[cite: 1]
    st.session_state.messages.append({"role": "user", "content": prompt})  # שמירת השאלה[cite: 1]
    with st.chat_message("user"):
        st.markdown(prompt)  # הצגת השאלה בתוך הצ'אט[cite: 1]

    with st.chat_message("assistant"):
        status_placeholder = st.empty()  # יצירת מכולה דינמית שתתעדכן כל 3 שניות
        
        # רשימת ההודעות המתחלפות
        messages_list = [
            "יהונתן חושב...",
            "יהונתן מחייך, עלה לו חידוש עצום לראש...",
            "יהונתן מריץ חיפוש בראש וכל התורה כולה לנגד עיניו...",
            "ליהונתן יש פיתרון, וחושב על כיוונים אחרים...",
            "יהונתן צריך ריכוז...",
            "יהונתן מקבץ כל מיני שו\"תים שנזכר בהם בהקשר לשאלה...",
            "יהונתן מבין שהשאלה מסובכת, אך אין שאלה שתישאר לא פתורה..."
            "יהונתן עומד לפתור את הסוגיה..."
            "יהונתן כותב על דף הבנה חדשה בדברי הראשונים..."
            "יהונתן מקבץ את כל מה שחשב עליו בצורה מסודרת לנגד עיניו..."
            "יהונתן מוסיף עוד משהו קטן לסוגיה..."
            "יהונתן מסיים לכתוב את התשובה..."
        ]

        # הרצת פונקציית הניתוח ברקע במקביל כדי לא לעצור את התחלפות ההודעות
        with ThreadPoolExecutor() as executor:
            future = executor.submit(analyze_sugya, st.session_state.messages)
            
            msg_index = 0
            # כל עוד התשובה לא מוכנה מהמודל - החלף הודעה כל 3 שניות
            while not future.done():
                current_msg = messages_list[msg_index % len(messages_list)]
                status_placeholder.markdown(f"⏳ **{current_msg}**")
                time.sleep(3)  # המתנה של 3 שניות exact
                msg_index += 1
            
            answer = future.result()  # שליפת התשובה שהסתיימה

        status_placeholder.empty()  # מחיקת הודעות ההמתנה ברגע שהתשובה הגיעה
        
        if answer:
            st.markdown(answer)  # הצגת התשובה[cite: 1]
            st.session_state.messages.append({"role": "assistant", "content": answer})  # שמירה להיסטוריית הצ'אט[cite: 1]
