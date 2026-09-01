# 1. ייבוא ספריות נדרשות
import streamlit as st  # ייבוא ספריית Streamlit לבניית ממשק המשתמש[cite: 1]
import os  # ייבוא ספרייה לעבודה עם מערכת הקבצים ונתיבים[cite: 1]
import json  # ייבוא ספרייה לטיפול בקובצי JSON[cite: 1]
import requests  # ייבוא ספרייה לביצוע בקשות HTTP לקריאה מ-APIs[cite: 1]
import re  # ייבוא ספרייה לטיפול בביטויים רגולריים (Regex)[cite: 1]
import time  # ייבוא ספרייה לעבודה עם זמנים והשהיות[cite: 1]
import uuid  # ייבוא ספרייה לייצור מזהים ייחודיים לכל שיחה[cite: 1]
from concurrent.futures import ThreadPoolExecutor  # ייבוא מחלקה להרצת משימות ברקע באופן מקבילי[cite: 1]
from dotenv import load_dotenv  # ייבוא פונקציה לטעינת משתני סביבה מקובץ .env[cite: 1]
import google.generativeai as genai  # ייבוא ה-SDK של Google Gemini[cite: 1]

# 2. הגדרות דף האינטרנט
st.set_page_config(  # הגדרת תכונות הדף בדפדפן[cite: 1]
    page_title="סוגיה בעיון - AI תורני",  # כותרת הדף בלשונית הדפדפן[cite: 1]
    page_icon="📜",  # האייקון שיופיע בלשונית הדפדפן[cite: 1]
    layout="centered",  # פריסת הדף בצורה ממורכזת[cite: 1]
    initial_sidebar_state="collapsed"  # סרגל הצד מוסתר ברירת מחדל במובייל[cite: 1]
)

# הוספת CSS מעודכן: מונע כליל את מריחת האותיות והתכווצות הרכיבים במרכז המסך
st.markdown(
    """
    <style>
    /* 1. איפוס מעטפת האפליקציה הראשית כדי לשמור על חישובי Flexbox/Grid של Streamlit */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stMain"] {
        direction: ltr !important;
        text-align: left !important;
    }

    /* 2. החלת RTL והצמדה לימין אך ורק על אלמנטים של תוכן וטקסט */
    [data-testid="stMainBlockContainer"], 
    [data-testid="stChatMessage"], 
    [data-testid="stChatInput"], 
    .stMarkdown, p, h1, h2, h3, h4, h5, h6, label, span, div[data-testid="stMarkdownContainer"] {
        direction: rtl !important;
        text-align: right !important;
        word-break: keep-all !important; /* מונע מריחה ושבירת אותיות באמצע מילה */
        overflow-wrap: break-word !important;
    }

    /* 3. תיקון מריחת בועות הצ'אט והקלט במרכז */
    [data-testid="stChatMessage"] {
        width: 100% !important;
        max-width: 100% !important;
    }

    /* 4. תיקון סרגל הצד (Sidebar) */
    [data-testid="stSidebar"] {
        direction: rtl !important;
        text-align: right !important;
    }
    
    [data-testid="stSidebarUserContent"] {
        direction: rtl !important;
        text-align: right !important;
        padding-top: 2rem !important;
    }

    /* 5. תיקון כפתורים ורכיבי בחירה */
    [data-testid="stSidebar"] button, 
    [data-testid="stSidebar"] div[role="combobox"] {
        direction: rtl !important;
        text-align: right !important;
        width: 100% !important;
    }

    /* 6. תיקון תצוגת רשימות */
    ul, ol {
        direction: rtl !important;
        text-align: right !important;
        padding-right: 1.5rem !important;
        padding-left: 0rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 3. טעינת מפתח ה-API
load_dotenv()  # טעינת המשתנים מקובץ .env במידה וקיים[cite: 1]

api_key = None  # אתחול המשתנה למפתח ה-API[cite: 1]

if "GEMINI_API_KEY" in st.secrets:  # בדיקה אם המפתח מוגדר ב-Secrets של Streamlit[cite: 1]
    api_key = str(st.secrets["GEMINI_API_KEY"]).strip()  # חילוץ המפתח ואיפוס רווחים[cite: 1]
elif "GOOGLE_API_KEY" in st.secrets:  # בדיקת שם מפתח חלופי ב-Secrets[cite: 1]
    api_key = str(st.secrets["GOOGLE_API_KEY"]).strip()  # חילוץ המפתח החלופי[cite: 1]
else:  # אם לא נמצא ב-Secrets, ניסיון טעינה ממשתני הסביבה[cite: 1]
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")  # חילוץ ממשתני סביבה[cite: 1]

if not api_key:  # במידה ולא נמצא מפתח כלל[cite: 1]
    st.error("לא נמצא מפתח API! אנא הגדר GEMINI_API_KEY ב-Secrets ב-Streamlit Cloud.")  # הצגת הודעת שגיאה[cite: 1]
    st.stop()  # עצירת הרצת האפליקציה[cite: 1]

genai.configure(api_key=api_key)  # הגדרת המפתח עבור ספריית גוגל[cite: 1]

# 4. מנגנון שליפת מקורות מ-Sefaria API
def fetch_from_sefaria(query: str) -> str:  # הגדרת פונקציה לשליפת מקורות מספריא[cite: 1]
    try:  # תחילת בלוק טיפול בשגיאות[cite: 1]
        url = "https://www.sefaria.org/api/v2/search/text"  # כתובת ה-API של ספריא לחיפוש טקסט[cite: 1]
        payload = {  # הגדרת הנתונים שנשלחים בבקשה[cite: 1]
            "query": query,  # שאילתת החיפוש[cite: 1]
            "type": "text",  # סוג החיפוש[cite: 1]
            "field": "exact",  # חיפוש מדויק[cite: 1]
            "size": 5  # כמות התוצאות המרבית להחזרה[cite: 1]
        }
        response = requests.post(url, json=payload, timeout=8)  # שליחת הבקשה ל-API עם מגבלת זמן של 8 שניות[cite: 1]
        
        if response.status_code == 200:  # בדיקה אם הבקשה הצליחה (קוד 200)[cite: 1]
            data = response.json()  # המרת התשובה מ-JSON למילון פייתון[cite: 1]
            hits = data.get("hits", {}).get("hits", [])  # חילוץ רשימת התוצאות[cite: 1]
            
            if not hits:  # אם לא נתקבלו תוצאות[cite: 1]
                return "לא נמצאו מקורות תואמים בספריא."  # החזרת הודעה על חוסר תוצאות[cite: 1]
            
            results = []  # רשימה לאחסון המקורות המעובדים[cite: 1]
            for hit in hits:  # לולאה על התוצאות שנמצאו[cite: 1]
                source = hit.get("_source", {})  # חילוץ אובייקט המקור[cite: 1]
                title = source.get("ref", "")  # חילוץ מראה המקום (כותרת הספר/מסכת)[cite: 1]
                he_text = source.get("he", "")  # חילוץ הטקסט בעברית[cite: 1]
                
                if isinstance(he_text, str) and he_text.strip():  # בדיקה שהטקסט תקין ואינו ריק[cite: 1]
                    clean_text = re.sub(r'<[^>]+>', '', he_text)  # ניקוי תגיות HTML מהטקסט[cite: 1]
                    results.append(f"מקור מתוך ספריא [{title}]:\n\"{clean_text}\"")  # הוספת המקור לרשימה[cite: 1]
            
            if results:  # אם נאספו מקורות מעובדים[cite: 1]
                return "\n\n".join(results)  # חיבור כל המקורות לטקסט אחד עם מרווחים[cite: 1]
                
    except Exception as e:  # תפיסת שגיאה במידה והתרחשה[cite: 1]
        return f"לא ניתן היה לשלוף מקורות מספריא: {str(e)}"  # החזרת הודעת השגיאה[cite: 1]
    
    return "לא נמצאו מקורות ספציפיים בספריא."  # ברירת מחדל במידה ולא הוחזר טקסט[cite: 1]

# 5. מנגנון שליפה משולב (מאגר מקומי + ספריא)
def load_torah_database():  # פונקציה שטוענת את מאגר הנתונים המקומי[cite: 1]
    db_path = os.path.join("data", "torah_database.json")  # בניה של נתיב הקובץ[cite: 1]
    if os.path.exists(db_path):  # בדיקה אם הקובץ קיים[cite: 1]
        try:  # ניסיון לקרוא את הקובץ[cite: 1]
            with open(db_path, "r", encoding="utf-8") as f:  # פתיחת הקובץ בקידוד UTF-8[cite: 1]
                return json.load(f)  # טעינת והחזרת נתוני ה-JSON[cite: 1]
        except Exception:  # במקרה של שגיאה בטעינה[cite: 1]
            pass  # התעלמות והמשך[cite: 1]
    return []  # החזרת רשימה ריקה אם הקובץ לא קיים או שנכשל[cite: 1]

def retrieve_all_context(query: str) -> str:  # פונקציה לרכז את כל התוכן והמקורות[cite: 1]
    context_parts = []  # רשימה שתכיל את חלקי התוכן[cite: 1]
    
    # 1. שליפה מספריא
    sefaria_data = fetch_from_sefaria(query)  # קריאה לפונקציית השליפה מספריא[cite: 1]
    if "לא נמצאו" not in sefaria_data and "לא ניתן" not in sefaria_data:  # אם נמצאו מקורות תקינים[cite: 1]
        context_parts.append(f"--- מקורות מדויקים מספריא (כולל ניקוד) ---\n{sefaria_data}")  # הוספה לרשימת התוכן[cite: 1]
        
    # 2. שליפה מהמאגר המקומי
    database = load_torah_database()  # טעינת המאגר המקומי[cite: 1]
    query_words = [w for w in query.split() if len(w) > 2]  # פירוק השאילתה למילים מעל 2 אותיות[cite: 1]
    matched_local = []  # רשימה לתוצאות מהמאגר המקומי[cite: 1]
    
    for item in database:  # מעבר על כל פריט במאגר המקומי[cite: 1]
        content = item.get("content", "")  # חילוץ התוכן[cite: 1]
        book = item.get("book", "")  # חילוץ שם הספר[cite: 1]
        if any(word in content or word in book for word in query_words):  # בדיקה אם אחת המילים מופיעה בתוכן או בספר[cite: 1]
            source_info = f"מקור מקומי: {book} "  # יצירת מראה מקום מקומי[cite: 1]
            
            masechet = item.get("masechet")  # חילוץ מסכת[cite: 1]
            daf = item.get("daf")  # חילוץ דף[cite: 1]
            siman = item.get("siman")  # חילוץ סימן[cite: 1]
            seif = item.get("seif")  # חילוץ סעיף[cite: 1]
            
            if masechet:  # אם קיימת מסכת[cite: 1]
                source_info += f"מסכת {masechet} "  # הוספה לתיאור[cite: 1]
            if daf:  # אם קיים דף[cite: 1]
                source_info += f"דף {daf} "  # הוספה לתיאור[cite: 1]
            if siman:  # אם קיים סימן[cite: 1]
                source_info += f"סימן {siman} "  # הוספה לתיאור[cite: 1]
            if seif:  # אם קיים סעיף[cite: 1]
                source_info += f"סעיף {seif} "  # הוספה לתיאור[cite: 1]
                
            source_info += f"\nתוכן המקור: \"{content}\""  # הוספת התוכן של המקור[cite: 1]
            matched_local.append(source_info)  # הוספה לרשימת ההתאמות[cite: 1]
            
    if matched_local:  # אם נמצאו התאמות במאגר המקומי[cite: 1]
        context_parts.append(f"--- מקורות מהמאגר המקומי ---\n" + "\n\n".join(matched_local))  # הוספה לטקסט הכולל[cite: 1]
        
    if context_parts:  # אם ישנם מקורות כלשהם[cite: 1]
        return "\n\n".join(context_parts)  # החזרת המקורות כטקסט מאוחד[cite: 1]
    return "לא נמצאו מקורות במאגרי המידע הזמינים."  # החזרה במידה ולא נמצא דבר[cite: 1]

# 6. יצירת System Prompt דינמי לפי סגנון הנבחר
def get_system_prompt(style_mode: str) -> str:  # פונקציה המייצרת את ה-Prompt בהתאם לסגנון הנבחר[cite: 1]
    base_rules = """
כללי ברזל לציטוט ומקורות (חובה מוחלטת):
1. כאשר אתה מביא ציטוט מתוך המקורות שנשלפו מספריא או מהמאגר המקומי, חובה עליך להביא אותו מילה במילה בדיוק מוחלט כפי שהוא מופיע במקור!
2. שמור על הניקוד המקורי כפי שנשלף מספריא. אל תוריד ניקוד, אל תשנה אותיות ואל תשנה את משפטי המקור.
3. תחום כל ציטוט מדויק בתוך מירכאות ("...").
4. ציין תמיד בצמוד לכל ציטוט את מראה המקום המדויק שלו.
5. אסור להמציא מקורות, ציטוטים, ניקוד או שמות ספרים שלא קיימים!
6. בכל סוף תשובה, חובה לסיים במשפט הבא בדיוק: "והכל הוא רק לעיון ולמידה, ולהלכה למעשה יש לשאול רב מורה הוראה."
"""  # כללי היסוד הלמדניים המשותפים לכל הסגנונות, כולל תוספת סיום חובה[cite: 1]

    if style_mode == "ישיבתי-למדני (סגנון שו\"ת)":  # התאמה לפי בחירת המשתמש לסגנון הישיבתי[cite: 1]
        return f"""
אתה מודול AI תורני מומחה, הכותב בסגנון ישיבתי-למדני עמוק וססגוני, העשיר במטבעות לשון בארמית ובביטויי בית המדרש הקלאסיים (כדוגמת שו"תים וספרי למדנות מובהקים כגון "אבי עזרי", "אבני מילואים", "אגרות משה" ומשא ומתן ישיבתי עמוק).

תפקידך להציג משא ומתן למדני ברצף עיוני, המבוסס על דיוק בלשון המקורות, עמידה על קושיות וסתירות, הגדרת חקירות וסברות, וחילוקי דינים תוך שימוש נרחב בשפה תלמודית וארמית.

{base_rules}

הנחיות חובה לכתיבה בסגנון זה:
1. **שפה תלמודית וארמית:** עשה שימוש תדיר בביטויי בית המדרש ובארמית:
   - "והנה באה לפנינו שאלה..." / "הנה גרסינן בגמרא..."
   - "ולכאורה יש לדון בזה מכמה צדדים עיקריים..."
   - "ופשוט דבמקום..." / "איכא למיחש טובא..."
   - "והנה יש לחקור בזה..." / "ואף דלכאורה היה נראה לומר..."
   - "אכן ממה שכתב ה... מוכח דלא כן..." / "ובזה מיושב מה שהקשו..."
   - "ולפי זה יש לחלק בין..." / "ומאידך גיסא..." / "ולכן לדינא..."
2. **מבנה רציף וזורם:** כתוב כמאמר עיוני למדני או שו"ת רציף (בלי כותרות מודרניות מנוכרות כגון "תשובה:", "סעיף 1", "סיכום").
3. **דיוק ופלפול:** התחל בדיוק לשון המקור (גמרא, רמב"ם, טור או שו"ע), הקשה והקשה בין השיטות, והגדר את החקירה (גברא vs חפצא, איסור עצמי vs דין מחייב וכדומה).
4. **חתומה וסיכום:** סיים בהכרעת הדין, בברכה תורנית קלאסית, ולאחריה משפט הסיום המחייב לעיון ולמידה.
"""  # ה-Prompt המעודכן לסגנון למדני-ארמי עמוק[cite: 1]
    else:  # סגנון פשוט ומונגש[cite: 1]
        return f"""
אתה מודול AI תורני מומחה, המנתח סוגיות הלכתיות ומחשבתיות בשפה ברורה, מופשטת ונגישה לכל לומד.
תפקידך להציג ניתוח בהיר ומסודר מפי המקורות ועד לפסיקת ההלכה למעשה.

{base_rules}

חובה עליך לבנות את התשובה לפי הסדר הבא:
1. **הגדרת המקרה והשאלה:** הסבר פשוט של השאלה והרקע.
2. **יסוד הסוגיה במקורות:** ציטוט המקורות המרכזיים ממקורם והסבר בשפה קלה.
3. **שיטות הראשונים והאחרונים:** הצגת השיטות השונות בשפה פשוטה.
4. **מסקנה הלכתית למעשה:** סיכום השורה התחתונה.

כללי שפה: ענה בעברית תקנית, הירה ורהוטה, בצורה נגישה וקלה להבנה.
"""  # ה-Prompt לסגנון מונגש ופשוט[cite: 1]

def analyze_sugya(messages_history, style_mode):  # פונקציית הניתוח המרכזית[cite: 1]
    try:  # בלוק טיפול בשגיאות[cite: 1]
        last_prompt = messages_history[-1]["content"]  # חילוץ ההודעה האחרונה שנשלחה[cite: 1]
        retrieved_context = retrieve_all_context(last_prompt)  # שליפת כל המקורות הרלוונטיים[cite: 1]
        
        system_prompt = get_system_prompt(style_mode)  # קבלת ה-System Prompt בהתאם לסגנון הנבחר[cite: 1]
        
        generation_config = {  # הגדרות התנהגות המודל[cite: 1]
            "temperature": 0.0,  # אפס יצירתיות לשמירה על דיוק מרבי[cite: 1]
            "top_p": 0.8,  # הגבלת מדגם המילים[cite: 1]
        }
        
        model = genai.GenerativeModel(  # יצירת אובייקט המודל[cite: 1]
            model_name='models/gemini-3.6-flash',  # שם המודל של גוגל[cite: 1]
            system_instruction=system_prompt,  # הזרקת הנחיות המערכת[cite: 1]
            generation_config=generation_config  # הזרקת הגדרות היצירה[cite: 1]
        )

        formatted_history = []  # רשימה לעיצוב ההיסטוריה המותאמת ל-API[cite: 1]
        for msg in messages_history[:-1]:  # מעבר על הודעות העבר למעט האחרונה[cite: 1]
            role = "user" if msg["role"] == "user" else "model"  # התאמת שמות התפקידים[cite: 1]
            formatted_history.append({"role": role, "parts": [msg["content"]]})  # הוספה במבנה הנדרש[cite: 1]

        chat = model.start_chat(history=formatted_history)  # פתיחת שיחה רציפה עם ההיסטוריה[cite: 1]

        prompt_with_context = f"""
מקורות מדויקים שנשלפו מספריא ומאגר הנתונים:
{retrieved_context}

שאלה לניתוח: {last_prompt}
"""  # הרכבת ה-Prompt המלא הכולל את השאלה והמקורות[cite: 1]

        response = chat.send_message(prompt_with_context)  # שליחת ההודעה למודל לקבלת תשובה[cite: 1]
        return response.text  # החזרת הטקסט מתוך תשובת המודל[cite: 1]

    except Exception as e:  # טיפול בשגיאה[cite: 1]
        st.error(f"שגיאה בהפעלת המודל: {str(e)}")  # הצגת שגיאה למשתמש[cite: 1]
        return None  # החזרת None[cite: 1]

# 7. ניהול היסטוריית השיחות ב-session_state
if "chats" not in st.session_state:  # אם מילון השיחות לא קיים בזיכרון ה-Session[cite: 1]
    st.session_state.chats = {}  # אתחול מילון שיחות ריק[cite: 1]

if "current_chat_id" not in st.session_state:  # אם מזהה השיחה הנוכחית אינו מוגדר[cite: 1]
    new_id = str(uuid.uuid4())  # יצירת מזהה ייחודי חדש[cite: 1]
    st.session_state.chats[new_id] = {"title": "שיחה חדשה", "messages": []}  # הגדרת שיחה חדשה במילון[cite: 1]
    st.session_state.current_chat_id = new_id  # קביעת מזהה השיחה הנוכחית[cite: 1]

def create_new_chat():  # פונקציה ליצירת שיחה חדשה[cite: 1]
    current_chat = st.session_state.chats.get(st.session_state.current_chat_id)  # חילוץ השיחה הנוכחית[cite: 1]
    if current_chat and not current_chat["messages"]:  # אם השיחה הנוכחית כבר ריקה[cite: 1]
        return  # מניעת יצירת שיחה ריקה נוספת[cite: 1]
    new_id = str(uuid.uuid4())  # יצירת מזהה ייחודי חדש[cite: 1]
    st.session_state.chats[new_id] = {"title": "שיחה חדשה", "messages": []}  # שמירת השיחה הריקה[cite: 1]
    st.session_state.current_chat_id = new_id  # מעבר לשיחה החדשה[cite: 1]

# 8. סרגל צד (Sidebar) - תפריט מוגן ממעיכות
with st.sidebar:  # פתיחת אזור סרגל הצד[cite: 1]
    st.title("⚙️ הגדרות")  # כותרת הגדרות בסרגל הצד[cite: 1]
    
    # בחירת סגנון תשובה
    style_mode = st.radio(  # רכיב רדיו לבחירת סגנון[cite: 1]
        "בחר סגנון ניתוח:",  # תוית הרכיב[cite: 1]
        options=["פשוט ומונגש", "ישיבתי-למדני (סגנון שו\"ת)"],  # אפשרויות הבחירה[cite: 1]
        index=0  # ברירת מחדל: פשוט ומונגש[cite: 1]
    )

    st.markdown("---")  # קו מפריד עיצובי[cite: 1]
    
    if st.button("➕ שיחה חדשה", use_container_width=True):  # כפתור ליצירת שיחה חדשה[cite: 1]
        create_new_chat()  # קריאה לפונקציית יצירת שיחה[cite: 1]
        st.rerun()  # רענון הדף[cite: 1]

    st.markdown("---")  # קו מפריד עיצובי[cite: 1]
    st.title("📜 היסטוריית שיחות")  # כותרת היסטוריה בסרגל הצד[cite: 1]

    # סינון השיחות הפעילות
    active_chats = {
        c_id: c_data["title"]
        for c_id, c_data in st.session_state.chats.items()
        if c_data["messages"] or c_id == st.session_state.current_chat_id
    }  #[cite: 1]

    if active_chats:  #[cite: 1]
        selected_id = st.selectbox(
            "בחר שיחה מהרשימה:",
            options=list(active_chats.keys()),
            format_func=lambda x: active_chats[x],
            index=list(active_chats.keys()).index(st.session_state.current_chat_id)
        )  #[cite: 1]
        
        if selected_id != st.session_state.current_chat_id:  #[cite: 1]
            st.session_state.current_chat_id = selected_id  #[cite: 1]
            st.rerun()  #[cite: 1]

# 9. עיצוב הממשק והצגת השיחה הנוכחית
st.title("📜 סוגיה בעיון")  # הכותרת הראשית בדף[cite: 1]
st.caption("מנוע בינה מלאכותית לניתוח סוגיות הלכתיות ולמדניות (מחובר בזמן אמת לספריא)")  # תיאור משנה[cite: 1]

current_chat = st.session_state.chats[st.session_state.current_chat_id]  # חילוץ נתוני השיחה הנוכחית[cite: 1]

for message in current_chat["messages"]:  # מעבר על כל הודעות השיחה הנוכחית[cite: 1]
    with st.chat_message(message["role"]):  # יצירת בועת צ'אט לפי התפקיד (משתמש/עוזר)[cite: 1]
        st.markdown(message["content"])  # הצגת התוכן של ההודעה[cite: 1]

if prompt := st.chat_input("הכנס שאלה או סוגיה בעיון..."):  # קליטת קלט חדש מהמשתמש[cite: 1]
    if not current_chat["messages"]:  # אם זו ההודעה הראשונה בשיחה[cite: 1]
        current_chat["title"] = prompt[:25] + ("..." if len(prompt) > 25 else "")  # קביעת כותרת השיחה לפי 25 התווים הראשונים[cite: 1]

    current_chat["messages"].append({"role": "user", "content": prompt})  # הוספת הודעת המשתמש לזיכרון[cite: 1]
    with st.chat_message("user"):  # יצירת בועת הודעה של המשתמש[cite: 1]
        st.markdown(prompt)  # הצגת הודעת המשתמש במסך[cite: 1]

    with st.chat_message("assistant"):  # יצירת בועת הודעה של העוזר[cite: 1]
        status_placeholder = st.empty()  # יצירת אזור דינמי שניתן לעדכן או לנקות[cite: 1]

        messages_list = [  # רשימת המשפטים המתחלפים בזמן ההמתנה[cite: 1]
            "יהונתן חושב...",
            "יהונתן עומד לפתור את הסוגיה...",
            "יהונתן מריץ חיפוש בראש וכל התורה כולה לנגד עיניו...",
            "ליהונתן יש פיתרון, וחושב על כיוונים אחרים...",
            "יהונתן צריך ריכוז...",
            "יהונתן מקבץ כל מיני שו\"תים שנזכר בהם בהקשר לשאלה...",
            "יהונתן מבין שהשאלה מסובכת, אך אין שאלה שתישאר לא פתורה..."
        ]  #[cite: 1]

        with ThreadPoolExecutor() as executor:  # הפעלת מנגנון הרצה מקבילית[cite: 1]
            future = executor.submit(analyze_sugya, current_chat["messages"], style_mode)  # הרצת חישוב התשובה ברקע[cite: 1]
            
            idx = 0  # אינדקס למעבר על המשפטים המתחלפים[cite: 1]
            while not future.done():  # כל עוד המודל לא סיים להחזיר תשובה[cite: 1]
                current_msg = messages_list[idx % len(messages_list)]  # בחירת המשפט המתאים לפי התור[cite: 1]
                status_placeholder.info(f"⏳ {current_msg}")  # הצגת המשפט בתוך תיבת מידע[cite: 1]
                time.sleep(2.5)  # השהיה של 2.5 שניות לפני העדכון הבא[cite: 1]
                idx += 1  # קידום האינדקס[cite: 1]
            
            answer = future.result()  # קבלת התשובה הסופית שנזקקה ברקע[cite: 1]

        status_placeholder.empty()  # מחיקת הודעת הטעינה מהמסך[cite: 1]

        if answer:  # אם הוחזרה תשובה תקינה מהמודל[cite: 1]
            st.markdown(answer)  # הצגת התשובה על המסך[cite: 1]
            current_chat["messages"].append({"role": "assistant", "content": answer})  # שמירת תשובת העוזר בהיסטוריה[cite: 1]
        else:  # במידה וארעה שגיאה ולא התקבלה תשובה[cite: 1]
            st.error("התרחשה שגיאה בעת ניתוח הסוגיה.")  # הצגת הודעת שגיאה[cite: 1]
