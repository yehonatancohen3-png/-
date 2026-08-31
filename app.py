# 1. ייבוא ספריות נדרשות
import streamlit as st  # ייבוא ספריית Streamlit לבניית ממשק המשתמש
import os  # ייבוא ספרייה לעבודה עם מערכת הקבצים ונתיבים
import json  # ייבוא ספרייה לטיפול בקובצי JSON
import requests  # ייבוא ספרייה לביצוע בקשות HTTP לקריאה מ-APIs
import re  # ייבוא ספרייה לטיפול בביטויים רגולריים (Regex)
import time  # ייבוא ספרייה לעבודה עם זמנים והשהיות
import uuid  # ייבוא ספרייה לייצור מזהים ייחודיים לכל שיחה
from concurrent.futures import ThreadPoolExecutor  # ייבוא מחלקה להרצת משימות ברקע באופן מקבילי
from dotenv import load_dotenv  # ייבוא פונקציה לטעינת משתני סביבה מקובץ .env
import google.generativeai as genai  # ייבוא ה-SDK של Google Gemini

# 2. הגדרות דף האינטרנט
st.set_page_config(  # הגדרת תכונות הדף בדפדפן
    page_title="סוגיה בעיון - AI תורני",  # כותרת הדף בלשונית הדפדפן
    page_icon="📜",  # האייקון שיופיע בלשונית הדפדפן
    layout="centered"  # פריסת הדף בצורה ממורכזת
)

# הוספת CSS מתוקן: מונע מעיכה במובייל ושומר על RTL מלא במחשב
st.markdown(
    """
    <style>
    /* 1. הגדרת RTL מלאה לכל אזור התוכן הראשי */
    .stApp, .stAppHeader, [data-testid="stAppViewContainer"] {
        direction: rtl !important;
        text-align: right !important;
    }

    /* 2. הגדרת RTL פנימית בסרגל הצד מבלי לשבור את מבנה ה-Flex/Grid בנייד */
    [data-testid="stSidebar"] {
        text-align: right !important;
    }
    
    [data-testid="stSidebarContent"] {
        direction: rtl !important;
        text-align: right !important;
    }

    /* 3. שמירה על כיווניות ניווט סרגל הצד */
    [data-testid="stSidebarNav"] {
        direction: rtl !important;
    }

    /* 4. יישור טקסט, כותרות והודעות צ'אט */
    [data-testid="stChatMessage"], [data-testid="stChatInput"], .stMarkdown, p, h1, h2, h3, h4, label {
        direction: rtl !important;
        text-align: right !important;
    }

    /* 5. תיקון תצוגת רשימות (נקודות/מספרים) ב-RTL */
    ul, ol {
        direction: rtl !important;
        text-align: right !important;
        padding-right: 1.5rem !important;
        padding-left: 0rem !important;
    }

    /* 6. תיקון כפתורים בסרגל הצד: מניעת מעיכת אותיות ואיפוס גלישה בנייד */
    [data-testid="stSidebar"] button {
        white-space: normal !important;
        word-wrap: break-word !important;
        word-break: break-word !important;
        user-select: none;
        -webkit-user-select: none;
    }

    [data-testid="stSidebar"] button p {
        word-break: break-word !important;
        white-space: normal !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 3. טעינת מפתח ה-API
load_dotenv()  # טעינת המשתנים מקובץ .env במידה וקיים

api_key = None  # אתחול המשתנה למפתח ה-API

if "GEMINI_API_KEY" in st.secrets:  # בדיקה אם המפתח מוגדר ב-Secrets של Streamlit
    api_key = str(st.secrets["GEMINI_API_KEY"]).strip()  # חילוץ המפתח ואיפוס רווחים
elif "GOOGLE_API_KEY" in st.secrets:  # בדיקת שם מפתח חלופי ב-Secrets
    api_key = str(st.secrets["GOOGLE_API_KEY"]).strip()  # חילוץ המפתח החלופי
else:  # אם לא נמצא ב-Secrets, ניסיון טעינה ממשתני הסביבה
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")  # חילוץ ממשתני סביבה

if not api_key:  # במידה ולא נמצא מפתח כלל
    st.error("לא נמצא מפתח API! אנא הגדר GEMINI_API_KEY ב-Secrets ב-Streamlit Cloud.")  # הצגת הודעת שגיאה
    st.stop()  # עצירת הרצת האפליקציה

genai.configure(api_key=api_key)  # הגדרת המפתח עבור ספריית גוגל

# 4. מנגנון שליפת מקורות מ-Sefaria API
def fetch_from_sefaria(query: str) -> str:  # הגדרת פונקציה לשליפת מקורות מספריא
    try:  # תחילת בלוק טיפול בשגיאות
        url = "https://www.sefaria.org/api/v2/search/text"  # כתובת ה-API של ספריא לחיפוש טקסט
        payload = {  # הגדרת הנתונים שנשלחים בבקשה
            "query": query,  # שאילתת החיפוש
            "type": "text",  # סוג החיפוש
            "field": "exact",  # חיפוש מדויק
            "size": 5  # כמות התוצאות המרבית להחזרה
        }
        response = requests.post(url, json=payload, timeout=8)  # שליחת הבקשה ל-API עם מגבלת זמן של 8 שניות
        
        if response.status_code == 200:  # בדיקה אם הבקשה הצליחה (קוד 200)
            data = response.json()  # המרת התשובה מ-JSON למילון פייתון
            hits = data.get("hits", {}).get("hits", [])  # חילוץ רשימת התוצאות
            
            if not hits:  # אם לא נתקבלו תוצאות
                return "לא נמצאו מקורות תואמים בספריא."  # החזרת הודעה על חוסר תוצאות
            
            results = []  # רשימה לאחסון המקורות המעובדים
            for hit in hits:  # לולאה על התוצאות שנמצאו
                source = hit.get("_source", {})  # חילוץ אובייקט המקור
                title = source.get("ref", "")  # חילוץ מראה המקום (כותרת הספר/מסכת)
                he_text = source.get("he", "")  # חילוץ הטקסט בעברית
                
                if isinstance(he_text, str) and he_text.strip():  # בדיקה שהטקסט תקין ואינו ריק
                    clean_text = re.sub(r'<[^>]+>', '', he_text)  # ניקוי תגיות HTML מהטקסט
                    results.append(f"מקור מתוך ספריא [{title}]:\n\"{clean_text}\"")  # הוספת המקור לרשימה
            
            if results:  # אם נאספו מקורות מעובדים
                return "\n\n".join(results)  # חיבור כל המקורות לטקסט אחד עם מרווחים
                
    except Exception as e:  # תפיסת שגיאה במידה והתרחשה
        return f"לא ניתן היה לשלוף מקורות מספריא: {str(e)}"  # החזרת הודעת השגיאה
    
    return "לא נמצאו מקורות ספציפיים בספריא."  # ברירת מחדל במידה ולא הוחזר טקסט

# 5. מנגנון שליפה משולב (מאגר מקומי + ספריא)
def load_torah_database():  # פונקציה שטוענת את מאגר הנתונים המקומי
    db_path = os.path.join("data", "torah_database.json")  # בניה של נתיב הקובץ
    if os.path.exists(db_path):  # בדיקה אם הקובץ קיים
        try:  # ניסיון לקרוא את הקובץ
            with open(db_path, "r", encoding="utf-8") as f:  # פתיחת הקובץ בקידוד UTF-8
                return json.load(f)  # טעינת והחזרת נתוני ה-JSON
        except Exception:  # במקרה של שגיאה בטעינה
            pass  # התעלמות והמשך
    return []  # החזרת רשימה ריקה אם הקובץ לא קיים או שנכשל

def retrieve_all_context(query: str) -> str:  # פונקציה לרכז את כל התוכן והמקורות
    context_parts = []  # רשימה שתכיל את חלקי התוכן
    
    # 1. שליפה מספריא
    sefaria_data = fetch_from_sefaria(query)  # קריאה לפונקציית השליפה מספריא
    if "לא נמצאו" not in sefaria_data and "לא ניתן" not in sefaria_data:  # אם נמצאו מקורות תקינים
        context_parts.append(f"--- מקורות מדויקים מספריא (כולל ניקוד) ---\n{sefaria_data}")  # הוספה לרשימת התוכן
        
    # 2. שליפה מהמאגר המקומי
    database = load_torah_database()  # טעינת המאגר המקומי
    query_words = [w for w in query.split() if len(w) > 2]  # פירוק השאילתה למילים מעל 2 אותיות
    matched_local = []  # רשימה לתוצאות מהמאגר המקומי
    
    for item in database:  # מעבר על כל פריט במאגר המקומי
        content = item.get("content", "")  # חילוץ התוכן
        book = item.get("book", "")  # חילוץ שם הספר
        if any(word in content or word in book for word in query_words):  # בדיקה אם אחת המילים מופיעה בתוכן או בספר
            source_info = f"מקור מקומי: {book} "  # יצירת מראה מקום מקומי
            
            masechet = item.get("masechet")  # חילוץ מסכת
            daf = item.get("daf")  # חילוץ דף
            siman = item.get("siman")  # חילוץ סימן
            seif = item.get("seif")  # חילוץ סעיף
            
            if masechet:  # אם קיימת מסכת
                source_info += f"מסכת {masechet} "  # הוספה לתיאור
            if daf:  # אם קיים דף
                source_info += f"דף {daf} "  # הוספה לתיאור
            if siman:  # אם קיים סימן
                source_info += f"סימן {siman} "  # הוספה לתיאור
            if seif:  # אם קיים סעיף
                source_info += f"סעיף {seif} "  # הוספה לתיאור
                
            source_info += f"\nתוכן המקור: \"{content}\""  # הוספת התוכן של המקור
            matched_local.append(source_info)  # הוספה לרשימת ההתאמות
            
    if matched_local:  # אם נמצאו התאמות במאגר המקומי
        context_parts.append(f"--- מקורות מהמאגר המקומי ---\n" + "\n\n".join(matched_local))  # הוספה לטקסט הכולל
        
    if context_parts:  # אם ישנם מקורות כלשהם
        return "\n\n".join(context_parts)  # החזרת המקורות כטקסט מאוחד
    return "לא נמצאו מקורות במאגרי המידע הזמינים."  # החזרה במידה ולא נמצא דבר

# 6. יצירת System Prompt דינמי לפי סגנון הנבחר
def get_system_prompt(style_mode: str) -> str:  # פונקציה המייצרת את ה-Prompt בהתאם לסגנון הנבחר
    base_rules = """
כללי ברזל לציטוט ומקורות (חובה מוחלטת):
1. כאשר אתה מביא ציטוט מתוך המקורות שנשלפו מספריא או מהמאגר המקומי, חובה עליך להביא אותו מילה במילה בדיוק מוחלט כפי שהוא מופיע במקור!
2. שמור על הניקוד המקורי כפי שנשלף מספריא. אל תוריד ניקוד, אל תשנה אותיות ואל תסדר מחדש את משפטי המקור.
3. תחום כל ציטוט מדויק בתוך מירכאות ("...").
4. ציין תמיד בצמוד לכל ציטוט את מראה המקום המדויק שלו.
5. אסור להמציא מקורות, ציטוטים, ניקוד או שמות ספרים שלא קיימים!
6. בכל סוף תשובה, חובה לסיים במשפט הבא בדיוק: "והכל הוא רק לעיון ולמידה, ולהלכה למעשה יש לשאול רב מורה הוראה."
"""  # כללי היסוד הלמדניים המשותפים לכל הסגנונות, כולל תוספת סיום חובה

    if style_mode == "ישיבתי-למדני (סגנון שו\"ת)":  # התאמה לפי בחירת המשתמש לסגנון הישיבתי
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
"""  # ה-Prompt המעודכן לסגנון למדני-ארמי עמוק
    else:  # סגנון פשוט ומונגש
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
"""  # ה-Prompt לסגנון מונגש ופשוט

def analyze_sugya(messages_history, style_mode):  # פונקציית הניתוח המרכזית
    try:  # בלוק טיפול בשגיאות
        last_prompt = messages_history[-1]["content"]  # חילוץ ההודעה האחרונה שנשלחה
        retrieved_context = retrieve_all_context(last_prompt)  # שליפת כל המקורות הרלוונטיים
        
        system_prompt = get_system_prompt(style_mode)  # קבלת ה-System Prompt בהתאם לסגנון הנבחר
        
        generation_config = {  # הגדרות התנהגות המודל
            "temperature": 0.0,  # אפס יצירתיות לשמירה על דיוק מרבי
            "top_p": 0.8,  # הגבלת מדגם המילים
        }
        
        model = genai.GenerativeModel(  # יצירת אובייקט המודל
            model_name='models/gemini-3.6-flash',  # שם המודל של גוגל
            system_instruction=system_prompt,  # הזרקת הנחיות המערכת
            generation_config=generation_config  # הזרקת הגדרות היצירה
        )

        formatted_history = []  # רשימה לעיצוב ההיסטוריה המותאמת ל-API
        for msg in messages_history[:-1]:  # מעבר על הודעות העבר למעט האחרונה
            role = "user" if msg["role"] == "user" else "model"  # התאמת שמות התפקידים
            formatted_history.append({"role": role, "parts": [msg["content"]]})  # הוספה במבנה הנדרש

        chat = model.start_chat(history=formatted_history)  # פתיחת שיחה רציפה עם ההיסטוריה

        prompt_with_context = f"""
מקורות מדויקים שנשלפו מספריא ומאגר הנתונים:
{retrieved_context}

שאלה לניתוח: {last_prompt}
"""  # הרכבת ה-Prompt המלא הכולל את השאלה והמקורות

        response = chat.send_message(prompt_with_context)  # שליחת ההודעה למודל לקבלת תשובה
        return response.text  # החזרת הטקסט מתוך תשובת המודל

    except Exception as e:  # טיפול בשגיאה
        st.error(f"שגיאה בהפעלת המודל: {str(e)}")  # הצגת שגיאה למשתמש
        return None  # החזרת None

# 7. ניהול היסטוריית השיחות ב-session_state
if "chats" not in st.session_state:  # אם מילון השיחות לא קיים בזיכרון ה-Session
    st.session_state.chats = {}  # אתחול מילון שיחות ריק

if "current_chat_id" not in st.session_state:  # אם מזהה השיחה הנוכחית אינו מוגדר
    new_id = str(uuid.uuid4())  # יצירת מזהה ייחודי חדש
    st.session_state.chats[new_id] = {"title": "שיחה חדשה", "messages": []}  # הגדרת שיחה חדשה במילון
    st.session_state.current_chat_id = new_id  # קביעת מזהה השיחה הנוכחית

def create_new_chat():  # פונקציה ליצירת שיחה חדשה
    current_chat = st.session_state.chats.get(st.session_state.current_chat_id)  # חילוץ השיחה הנוכחית
    if current_chat and not current_chat["messages"]:  # אם השיחה הנוכחית כבר ריקה
        return  # מניעת יצירת שיחה ריקה נוספת
    new_id = str(uuid.uuid4())  # יצירת מזהה ייחודי חדש
    st.session_state.chats[new_id] = {"title": "שיחה חדשה", "messages": []}  # שמירת השיחה הריקה
    st.session_state.current_chat_id = new_id  # מעבר לשיחה החדשה

# 8. סרגל צד (Sidebar)
with st.sidebar:  # פתיחת אזור סרגל הצד
    st.title("⚙️ הגדרות וסגנון")  # כותרת הגדרות בסרגל הצד
    
    # בחירת סגנון תשובה
    style_mode = st.radio(  # רכיב רדיו לבחירת סגנון
        "בחר סגנון ניתוח:",  # תוית הרכיב
        options=["פשוט ומונגש", "ישיבתי-למדני (סגנון שו\"ת)"],  # אפשרויות הבחירה
        index=0  # ברירת מחדל: פשוט ומונגש
    )

    st.markdown("---")  # קו מפריד עיצובי
    st.title("📜 היסטוריית שיחות")  # כותרת היסטוריה בסרגל הצד
    
    if st.button("➕ שיחה חדשה", use_container_width=True, type="secondary"):  # כפתור שיחה חדשה לא מודגש
        create_new_chat()  # קריאה לפונקציית יצירת שיחה
        st.rerun()  # רענון הדף

    st.markdown("---")  # קו מפריד עיצובי

    archived_chats = {  # סינון השיחות כך שיוצגו רק שיחות עם הודעות או השיחה הנוכחית
        c_id: c_data for c_id, c_data in st.session_state.chats.items()
        if c_data["messages"] or c_id == st.session_state.current_chat_id
    }

    for c_id, c_data in list(archived_chats.items()):  # מעבר על רשימת השיחות בארכיון
        if not c_data["messages"] and c_id != st.session_state.current_chat_id:  # אם השיחה ריקה ואינה הפעילה
            continue  # דילוג על הצגתה

        is_active = (c_id == st.session_state.current_chat_id)  # בדיקה אם זו השיחה הנידונה כעת
        btn_label = f"💬 {c_data['title']}"  # יצירת תווית הכפתור עם כותרת השיחה
        
        if st.button(btn_label, key=f"select_{c_id}", use_container_width=True, type="primary" if is_active else "secondary"):  # כפתור לבחירת השיחה
            st.session_state.current_chat_id = c_id  # עדכון המזהה הפעיל
            st.rerun()  # רענון המסך להצגת השיחה הנבחרת

# JavaScript למחיקת שיחות בלחיצה ארוכה / מקש ימני
st.components.v1.html(  # הזרקת רכיב ה-JavaScript המותאם אישית
    """
    <script>
    const parentDoc = window.parent.document;
    
    parentDoc.addEventListener('contextmenu', function(e) {
        let btn = e.target.closest('button');
        if (btn && btn.innerText.includes('💬')) {
            e.preventDefault();
            if (confirm("האם ברצונך למחוק שיחה זו?")) {
                btn.click();
                let deleteEvt = new CustomEvent('delete_chat', { detail: btn.innerText });
                window.parent.dispatchEvent(deleteEvt);
            }
        }
    });

    let pressTimer;
    parentDoc.addEventListener('touchstart', function(e) {
        let btn = e.target.closest('button');
        if (btn && btn.innerText.includes('💬')) {
            pressTimer = setTimeout(function() {
                if (confirm("האם ברצונך למחוק שיחה זו?")) {
                    btn.click();
                    let deleteEvt = new CustomEvent('delete_chat', { detail: btn.innerText });
                    window.parent.dispatchEvent(deleteEvt);
                }
            }, 800);
        }
    });

    parentDoc.addEventListener('touchend', function(e) {
        clearTimeout(pressTimer);
    });
    </script>
    """,
    height=0,  # גובה הרכיב נקבע ל-0 כדי שלא תפספס מקום במסך
)

# 9. עיצוב הממשק והצגת השיחה הנוכחית
st.title("📜 סוגיה בעיון")  # הכותרת הראשית בדף
st.caption("מנוע בינה מלאכותית לניתוח סוגיות הלכתיות ולמדניות (מחובר בזמן אמת לספריא)")  # תיאור משנה

current_chat = st.session_state.chats[st.session_state.current_chat_id]  # חילוץ נתוני השיחה הנוכחית

for message in current_chat["messages"]:  # מעבר על כל הודעות השיחה הנוכחית
    with st.chat_message(message["role"]):  # יצירת בועת צ'אט לפי התפקיד (משתמש/עוזר)
        st.markdown(message["content"])  # הצגת התוכן של ההודעה

if prompt := st.chat_input("הכנס שאלה או סוגיה בעיון..."):  # קליטת קלט חדש מהמשתמש
    if not current_chat["messages"]:  # אם זו ההודעה הראשונה בשיחה
        current_chat["title"] = prompt[:25] + ("..." if len(prompt) > 25 else "")  # קביעת כותרת השיחה לפי 25 התווים הראשונים

    current_chat["messages"].append({"role": "user", "content": prompt})  # הוספת הודעת המשתמש לזיכרון
    with st.chat_message("user"):  # יצירת בועת הודעה של המשתמש
        st.markdown(prompt)  # הצגת הודעת המשתמש במסך

    with st.chat_message("assistant"):  # יצירת בועת הודעה של העוזר
        status_placeholder = st.empty()  # יצירת אזור דינמי שניתן לעדכן או לנקות

        messages_list = [  # רשימת המשפטים המתחלפים בזמן ההמתנה
            "יהונתן חושב...",
            "יהונתן עומד לפתור את הסוגיה...",
            "יהונתן מריץ חיפוש בראש וכל התורה כולה לנגד עיניו...",
            "ליהונתן יש פיתרון, וחושב על כיוונים אחרים...",
            "יהונתן צריך ריכוז...",
            "יהונתן מקבץ כל מיני שו\"תים שנזכר בהם בהקשר לשאלה...",
            "יהונתן מבין שהשאלה מסובכת, אך אין שאלה שתישאר לא פתורה..."
        ]

        with ThreadPoolExecutor() as executor:  # הפעלת מנגנון הרצה מקבילית
            future = executor.submit(analyze_sugya, current_chat["messages"], style_mode)  # הרצת חישוב התשובה ברקע
            
            idx = 0  # אינדקס למעבר על המשפטים המתחלפים
            while not future.done():  # כל עוד המודל לא סיים להחזיר תשובה
                current_msg = messages_list[idx % len(messages_list)]  # בחירת המשפט המתאים לפי התור
                status_placeholder.info(f"⏳ {current_msg}")  # הצגת המשפט בתוך תיבת מידע
                time.sleep(2.5)  # השהיה של 2.5 שניות לפני העדכון הבא
                idx += 1  # קידום האינדקס
            
            answer = future.result()  # קבלת התשובה הסופית שנזקקה ברקע

        status_placeholder.empty()  # מחיקת הודעת הטעינה מהמסך

        if answer:  # אם הוחזרה תשובה תקינה מהמודל
            st.markdown(answer)  # הצגת התשובה על המסך
            current_chat["messages"].append({"role": "assistant", "content": answer})  # שמירת תשובת העוזר בהיסטוריה
        else:  # במידה וארעה שגיאה ולא התקבלה תשובה
            st.error("התרחשה שגיאה בעת ניתוח הסוגיה.")  # הצגת הודעת שגיאה
