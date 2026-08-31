# 1. ייבוא ספריות נדרשות
import streamlit as st  # ייבוא ספריית Streamlit לבניית ממשק המשתמש
import streamlit.components.v1 as components  # ייבוא רכיב JavaScript להסרת פוקוס מהמקלדת
import os  # ייבוא ספרייה לעבודה עם מערכת הקבצים ונתיבים
import json  # ייבוא ספרייה לטיפול בקובצי JSON
import requests  # ייבוא ספרייה לביצוע בקשות HTTP לקריאה מ-APIs
import re  # ייבוא ספרייה לטיפול בביטויים רגולריים (Regex)
import uuid  # ייבוא ספרייה לייצור מזהים ייחודיים לכל שיחה
from dotenv import load_dotenv  # ייבוא פונקציה לטעינת משתני סביבה מקובץ .env
import google.generativeai as genai  # ייבוא ה-SDK של Google Gemini

# 2. הגדרות דף האינטרנט
st.set_page_config(  # הגדרת תכונות הדף בדפדפן
    page_title="סוגיה בעיון - AI תורני",  # כותרת הדף בלשונית הדפדפן
    page_icon="📜",  # האייקון שיופיע בלשונית הדפדפן
    layout="centered",  # פריסת הדף בצורה ממורכזת
    initial_sidebar_state="collapsed"  # סרגל הצד מוסתר ברירת מחדל במובייל
)

# 3. עיצוב CSS יציב ותמיכה מלאה ב-RTL
st.markdown(
    """
    <style>
    /* איפוס גלישה כפויה למניעת קפיצות דף */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        scroll-behavior: smooth !important;
        overflow-anchor: none !important;
    }

    /* שמירה על פריסת LTR במעטפת המערכת למניעת עיוותים */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        direction: ltr !important;
    }

    /* החלת RTL אך ורק על אזורי תוכן וטקסט */
    [data-testid="stMainBlockContainer"], 
    [data-testid="stChatMessage"], 
    [data-testid="stChatInput"], 
    .stMarkdown, p, h1, h2, h3, h4, h5, h6, label, span {
        direction: rtl !important;
        text-align: right !important;
    }

    /* תיקון תצוגת סרגל הצד */
    [data-testid="stSidebar"] {
        direction: rtl !important;
        text-align: right !important;
    }
    
    [data-testid="stSidebarUserContent"] {
        direction: rtl !important;
        text-align: right !important;
        padding-top: 2rem !important;
    }

    [data-testid="stSidebar"] button, 
    [data-testid="stSidebar"] div[role="combobox"] {
        direction: rtl !important;
        text-align: right !important;
        width: 100% !important;
    }

    /* תיקון תצוגת רשימות */
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

# 4. טעינת מפתח ה-API
load_dotenv()  # טעינת המשתנים מקובץ .env במידה וקיים

api_key = None  # אתחול המשתנה למפתח ה-API

if "GEMINI_API_KEY" in st.secrets:  # בדיקה אם המפתח מוגדר ב-Secrets של Streamlit
    api_key = str(st.secrets["GEMINI_API_KEY"]).strip()  # חילוץ המפתח
elif "GOOGLE_API_KEY" in st.secrets:  # בדיקת שם מפתח חלופי
    api_key = str(st.secrets["GOOGLE_API_KEY"]).strip()  # חילוץ המפתח החלופי
else:  # ניסיון טעינה ממשתני הסביבה
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if not api_key:  # במידה ולא נמצא מפתח כלל
    st.error("לא נמצא מפתח API! אנא הגדר GEMINI_API_KEY ב-Secrets ב-Streamlit Cloud.")
    st.stop()

genai.configure(api_key=api_key)  # הגדרת המפתח עבור ספריית גוגל

# 5. מנגנון שליפת מקורות מ-Sefaria API
def fetch_from_sefaria(query: str) -> str:
    try:
        url = "https://www.sefaria.org/api/v2/search/text"
        payload = {
            "query": query,
            "type": "text",
            "field": "exact",
            "size": 5
        }
        response = requests.post(url, json=payload, timeout=8)
        
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
                    results.append(f"מקור מתוך ספריא [{title}]:\n\"{clean_text}\"")
            
            if results:
                return "\n\n".join(results)
                
    except Exception as e:
        return f"לא ניתן היה לשלוף מקורות מספריא: {str(e)}"
    
    return "לא נמצאו מקורות ספציפיים בספריא."

# 6. מנגנון שליפה משולב (מאגר מקומי + ספריא)
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
    
    # שליפה מספריא
    sefaria_data = fetch_from_sefaria(query)
    if "לא נמצאו" not in sefaria_data and "לא ניתן" not in sefaria_data:
        context_parts.append(f"--- מקורות מדויקים מספריא (כולל ניקוד) ---\n{sefaria_data}")
        
    # שליפה מהמאגר המקומי
    database = load_torah_database()
    query_words = [w for w in query.split() if len(w) > 2]
    matched_local = []
    
    for item in database:
        content = item.get("content", "")
        book = item.get("book", "")
        if any(word in content or word in book for word in query_words):
            source_info = f"מקור מקומי: {book} "
            
            masechet = item.get("masechet")
            daf = item.get("daf")
            siman = item.get("siman")
            seif = item.get("seif")
            
            if masechet: source_info += f"מסכת {masechet} "
            if daf: source_info += f"דף {daf} "
            if siman: source_info += f"סימן {siman} "
            if seif: source_info += f"סעיף {seif} "
                
            source_info += f"\nתוכן המקור: \"{content}\""
            matched_local.append(source_info)
            
    if matched_local:
        context_parts.append(f"--- מקורות מהמאגר המקומי ---\n" + "\n\n".join(matched_local))
        
    if context_parts:
        return "\n\n".join(context_parts)
    return "לא נמצאו מקורות במאגרי המידע הזמינים."

# 7. יצירת System Prompt דינמי לפי סגנון הנבחר
def get_system_prompt(style_mode: str) -> str:
    base_rules = """
כללי ברזל לציטוט ומקורות (חובה מוחלטת):
1. כאשר אתה מביא ציטוט מתוך המקורות שנשלפו מספריא או מהמאגר המקומי, חובה עליך להביא אותו מילה במילה בדיוק מוחלט כפי שהוא מופיע במקור!
2. שמור על הניקוד המקורי כפי שנשלף מספריא. אל תוריד ניקוד, אל תשנה אותיות ואל תשנה את משפטי המקור.
3. תחום כל ציטוט מדויק בתוך מירכאות ("...").
4. ציין תמיד בצמוד לכל ציטוט את מראה המקום המדויק שלו.
5. אסור להמציא מקורות, ציטוטים, ניקוד או שמות ספרים שלא קיימים!
6. בכל סוף תשובה, חובה לסיים במשפט הבא בדיוק: "והכל הוא רק לעיון ולמידה, ולהלכה למעשה יש לשאול רב מורה הוראה."
"""

    if style_mode == "ישיבתי-למדני (סגנון שו\"ת)":
        return f"""
אתה מודול AI תורני מומחה, הכותב בסגנון ישיבתי-למדני עמוק וססגוני, העשיר במטבעות לשון בארמית ובביטויי בית המדרש הקלאסיים.
תפקידך להציג משא ומתן למדני ברצף עיוני, המבוסס על דיוק בלשון המקורות, עמידה על קושיות וסתירות, הגדרת חקירות וסברות, וחילוקי דינים תוך שימוש נרחב בשפה תלמודית וארמית.

{base_rules}

הנחיות חובה לכתיבה בסגנון זה:
1. **שפה תלמודית וארמית:** עשה שימוש תדיר בביטויי בית המדרש ובארמית ("והנה באה לפנינו שאלה...", "ולכאורה יש לדון בזה מכמה צדדים...", "איכא למיחש טובא...", "ולפי זה יש לחלק בין...").
2. **מבנה רציף וזורם:** כתוב כמאמר עיוני למדני או שו"ת רציף (בלי כותרות מודרניות כגון "תשובה:", "סעיף 1").
3. **דיוק ופלפול:** התחל בדיוק לשון המקור, הקשה והקשה בין השיטות, והגדר את החקירה.
4. **חתומה וסיכום:** סיים בהכרעת הדין, בברכה תורנית, ולאחריה משפט הסיום המחייב.
"""
    else:
        return f"""
אתה מודול AI תורני מומחה, המנתח סוגיות הלכתיות ומחשבתיות בשפה ברורה, מופשטת ונגישה לכל לומד.
תפקידך להציג ניתוח בהיר ומסודר מפי המקורות ועד לפסיקת ההלכה למעשה.

{base_rules}

חובה עליך לבנות את התשובה לפי הסדר הבא:
1. **הגדרת המקרה והשאלה:** הסבר פשוט של השאלה והרקע.
2. **יסוד הסוגיה במקורות:** ציטוט המקורות המרכזיים ממקורם והסבר בשפה קלה.
3. **שיטות הראשונים והאחרונים:** הצגת השיטות השונות בשפה פשוטה.
4. **מסקנה הלכתית למעשה:** סיכום השורה התחתונה.
"""

# 8. פונקציית מחולל (Generator) להזרמת התשובה בזמן אמת (Streaming)
def stream_sugya_analysis(messages_history, style_mode):
    try:
        last_prompt = messages_history[-1]["content"]
        retrieved_context = retrieve_all_context(last_prompt)
        system_prompt = get_system_prompt(style_mode)
        
        generation_config = {
            "temperature": 0.0,
            "top_p": 0.8,
        }
        
        model = genai.GenerativeModel(
            model_name='models/gemini-3.6-flash',
            system_instruction=system_prompt,
            generation_config=generation_config
        )

        formatted_history = []
        for msg in messages_history[:-1]:
            role = "user" if msg["role"] == "user" else "model"
            formatted_history.append({"role": role, "parts": [msg["content"]]})

        chat = model.start_chat(history=formatted_history)

        prompt_with_context = f"""
מקורות מדויקים שנשלפו מספריא ומאגר הנתונים:
{retrieved_context}

שאלה לניתוח: {last_prompt}
"""
        # הפעלת הזרמה (stream=True) כדי לקבל חלקיקי תשובה בלייב
        response = chat.send_message(prompt_with_context, stream=True)
        
        for chunk in response:
            if chunk.text:
                yield chunk.text  # החזרת כל מילה/תו ברגע שהוא מיוצר
                
    except Exception as e:
        yield f"שגיאה בהפעלת המודל: {str(e)}"

# 9. ניהול היסטוריית השיחות ב-session_state
if "chats" not in st.session_state:
    st.session_state.chats = {}

if "current_chat_id" not in st.session_state:
    new_id = str(uuid.uuid4())
    st.session_state.chats[new_id] = {"title": "שיחה חדשה", "messages": []}
    st.session_state.current_chat_id = new_id

def create_new_chat():
    current_chat = st.session_state.chats.get(st.session_state.current_chat_id)
    if current_chat and not current_chat["messages"]:
        return
    new_id = str(uuid.uuid4())
    st.session_state.chats[new_id] = {"title": "שיחה חדשה", "messages": []}
    st.session_state.current_chat_id = new_id

# 10. סרגל צד (Sidebar)
with st.sidebar:
    st.title("⚙️ הגדרות")
    
    style_mode = st.radio(
        "בחר סגנון ניתוח:",
        options=["פשוט ומונגש", "ישיבתי-למדני (סגנון שו\"ת)"],
        index=0
    )

    st.markdown("---")
    
    if st.button("➕ שיחה חדשה", use_container_width=True):
        create_new_chat()
        st.rerun()

    st.markdown("---")
    st.title("📜 היסטוריית שיחות")

    active_chats = {
        c_id: c_data["title"]
        for c_id, c_data in st.session_state.chats.items()
        if c_data["messages"] or c_id == st.session_state.current_chat_id
    }

    if active_chats:
        selected_id = st.selectbox(
            "בחר שיחה מהרשימה:",
            options=list(active_chats.keys()),
            format_func=lambda x: active_chats[x],
            index=list(active_chats.keys()).index(st.session_state.current_chat_id)
        )
        
        if selected_id != st.session_state.current_chat_id:
            st.session_state.current_chat_id = selected_id
            st.rerun()

# 11. עיצוב הממשק והצגת השיחה
st.title("📜 סוגיה בעיון")
st.caption("מנוע בינה מלאכותית לניתוח סוגיות הלכתיות ולמדניות (מחובר בזמן אמת לספריא)")

current_chat = st.session_state.chats[st.session_state.current_chat_id]

# הצגת כל הודעות העבר
for message in current_chat["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# קלט מהמשתמש
if prompt := st.chat_input("הכנס שאלה או סוגיה בעיון..."):
    if not current_chat["messages"]:
        current_chat["title"] = prompt[:25] + ("..." if len(prompt) > 25 else "")

    # הוספת הודעת המשתמש להיסטוריה
    current_chat["messages"].append({"role": "user", "content": prompt})

    # הצגת הודעת המשתמש במסך
    with st.chat_message("user"):
        st.markdown(prompt)

    # הסרת הפוקוס מהמקלדת במובייל מיד בלחיצה כדי למנוע קפיצת מסך
    components.html(
        """
        <script>
            var inputs = window.parent.document.querySelectorAll('textarea, input');
            inputs.forEach(function(input) { input.blur(); });
        </script>
        """,
        height=0,
        width=0
    )

    # הצגת בועת ה-Assistant והזרמת התשובה בלייב כמו ב-Gemini
    with st.chat_message("assistant"):
        # st.write_stream מדפיס את המילים בלייב כפי שהן מגיעות ומחזיר את המחרוזת המלאה בסיום
        full_response = st.write_stream(
            stream_sugya_analysis(current_chat["messages"], style_mode)
        )
        
    # שמירת התשובה המלאה בזיכרון השיחה בסיום ההזרמה
    current_chat["messages"].append({"role": "assistant", "content": full_response})
