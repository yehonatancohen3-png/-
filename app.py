# 1. ייבוא ספריות נדרשות
import streamlit as st  # ייבוא ספריית Streamlit לבניית ממשק המשתמש
import os  # ייבוא ספרייה לעבודה עם מערכת הקבצים ונתיבים
import json  # ייבוא ספרייה לטיפול בקובצי JSON
import requests  # ייבוא ספרייה לביצוע בקשות HTTP לקריאה מ-APIs
import re  # ייבוא ספרייה לטיפול בביטויים רגולריים (Regex)
import time  # ייבוא ספרייה לעבודה עם זמנים והשהיות
import uuid  # ייבוא ספרייה לייצור מזהים ייחודיים
from concurrent.futures import ThreadPoolExecutor  # הרצת משימות ברקע
from dotenv import load_dotenv  # טעינת משתני סביבה
import google.generativeai as genai  # ה-SDK של Google Gemini

# 2. הגדרות דף האינטרנט
st.set_page_config(
    page_title="סוגיה בעיון - AI תורני",
    page_icon="📜",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# הוספת CSS מונע מריחת אותיות ותומך RTL
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
        word-break: keep-all !important;
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

# 4. מנגנון שליפת מקורות מ-Sefaria API
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
    
    sefaria_data = fetch_from_sefaria(query)
    if "לא נמצאו" not in sefaria_data and "לא ניתן" not in sefaria_data:
        context_parts.append(f"--- מקורות מדויקים מספריא (כולל ניקוד) ---\n{sefaria_data}")
        
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
            
            if masechet:
                source_info += f"מסכת {masechet} "
            if daf:
                source_info += f"דף {daf} "
            if siman:
                source_info += f"סימן {siman} "
            if seif:
                source_info += f"סעיף {seif} "
                
            source_info += f"\nתוכן המקור: \"{content}\""
            matched_local.append(source_info)
            
    if matched_local:
        context_parts.append(f"--- מקורות מהמאגר המקומי ---\n" + "\n\n".join(matched_local))
        
    if context_parts:
        return "\n\n".join(context_parts)
    return "לא נמצאו מקורות במאגרי המידע הזמינים."

# 6. יצירת System Prompt דינמי
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

כללי שפה: ענה בעברית תקנית, הירה ורהוטה, בצורה נגישה וקלה להבנה.
"""

def analyze_sugya(messages_history, style_mode):
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

        response = chat.send_message(prompt_with_context)
        return response.text

    except Exception as e:
        st.error(f"שגיאה בהפעלת המודל: {str(e)}")
        return None

# 7. ניהול פרויקטים ושיחות ב-Session State
if "projects" not in st.session_state:
    st.session_state.projects = {"פרויקט ראשי": []}

if "current_project" not in st.session_state:
    st.session_state.current_project = "פרויקט ראשי"

if "chats" not in st.session_state:
    st.session_state.chats = {}

if "current_chat_id" not in st.session_state:
    new_id = str(uuid.uuid4())
    st.session_state.chats[new_id] = {"title": "שיחה חדשה", "messages": [], "project": "פרויקט ראשי"}
    st.session_state.projects["פרויקט ראשי"].append(new_id)
    st.session_state.current_chat_id = new_id

def create_new_chat(project_name):
    new_id = str(uuid.uuid4())
    st.session_state.chats[new_id] = {"title": "שיחה חדשה", "messages": [], "project": project_name}
    st.session_state.projects[project_name].append(new_id)
    st.session_state.current_chat_id = new_id

# 8. סרגל צד (Sidebar) - ניהול פרויקטים ושיחות אחרונות
with st.sidebar:
    st.title("⚙️ הגדרות")
    
    style_mode = st.radio(
        "בחר סגנון ניתוח:",
        options=["פשוט ומונגש", "ישיבתי-למדני (סגנון שו\"ת)"],
        index=0
    )

    st.markdown("---")
    
    # --- ניהול פרויקטים ---
    st.subheader("📁 ניהול פרויקטים")
    
    # בחירת פרויקט פעיל
    project_list = list(st.session_state.projects.keys())
    selected_project = st.selectbox("בחר פרויקט:", project_list, index=project_list.index(st.session_state.current_project))
    if selected_project != st.session_state.current_project:
        st.session_state.current_project = selected_project
        st.rerun()

    # יצירת פרויקט חדש
    with st.expander("➕ הוסף פרויקט חדש"):
        new_proj_name = st.text_input("שם הפרויקט:")
        if st.button("צור פרויקט"):
            if new_proj_name and new_proj_name not in st.session_state.projects:
                st.session_state.projects[new_proj_name] = []
                st.session_state.current_project = new_proj_name
                create_new_chat(new_proj_name)
                st.success(f"הפרויקט '{new_proj_name}' נוצר בהצלחה!")
                st.rerun()

    # מחיקת פרויקט קיים
    if len(st.session_state.projects) > 1:
        with st.expander("🗑️ מחק פרויקט נוכחי"):
            st.warning(f"האם למחוק את '{st.session_state.current_project}'?")
            if st.button("אישור מחיקה"):
                proj_to_del = st.session_state.current_project
                # מחיקת השיחות המשוייכות לפרויקט
                for c_id in st.session_state.projects[proj_to_del]:
                    if c_id in st.session_state.chats:
                        del st.session_state.chats[c_id]
                del st.session_state.projects[proj_to_del]
                
                # מעבר לפרויקט הראשון ברשימה
                st.session_state.current_project = list(st.session_state.projects.keys())[0]
                if not st.session_state.projects[st.session_state.current_project]:
                    create_new_chat(st.session_state.current_project)
                else:
                    st.session_state.current_chat_id = st.session_state.projects[st.session_state.current_project][-1]
                st.rerun()

    st.markdown("---")

    # --- שיחה חדשה בפרויקט ---
    if st.button("➕ שיחה חדשה בפרויקט", use_container_width=True):
        create_new_chat(st.session_state.current_project)
        st.rerun()

    st.markdown("---")
    
    # --- שיחות אחרונות בפרויקט הנבחר ---
    st.subheader(f"📜 שיחות אחרונות ב-{st.session_state.current_project}")
    
    project_chat_ids = st.session_state.projects.get(st.session_state.current_project, [])
    active_chats = {
        c_id: st.session_state.chats[c_id]["title"]
        for c_id in project_chat_ids
        if c_id in st.session_state.chats
    }

    if active_chats:
        selected_id = st.selectbox(
            "בחר שיחה מהרשימה:",
            options=list(active_chats.keys()),
            format_func=lambda x: active_chats[x],
            index=list(active_chats.keys()).index(st.session_state.current_chat_id) if st.session_state.current_chat_id in active_chats else 0
        )
        
        if selected_id != st.session_state.current_chat_id:
            st.session_state.current_chat_id = selected_id
            st.rerun()

# 9. עיצוב הממשק והצגת השיחה הנוכחית
st.title("📜 סוגיה בעיון")
st.caption(f"פרויקט פעיל: **{st.session_state.current_project}** | מחובר בזמן אמת לספריא")

current_chat = st.session_state.chats[st.session_state.current_chat_id]

for message in current_chat["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("הכנס שאלה או סוגיה בעיון..."):
    if not current_chat["messages"]:
        current_chat["title"] = prompt[:25] + ("..." if len(prompt) > 25 else "")

    current_chat["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        status_placeholder = st.empty()

        messages_list = [
            "יהונתן חושב...",
            "יהונתן עומד לפתור את הסוגיה...",
            "יהונתן מריץ חיפוש בראש וכל התורה כולה לנגד עיניו...",
            "ליהונתן יש פיתרון, וחושב על כיוונים אחרים...",
            "יהונתן צריך ריכוז...",
            "יהונתן מקבץ כל מיני שו\"תים שנזכר בהם בהקשר לשאלה...",
            "יהונתן מבין שהשאלה מסובכת, אך אין שאלה שתישאר לא פתורה..."
        ]

        with ThreadPoolExecutor() as executor:
            future = executor.submit(analyze_sugya, current_chat["messages"], style_mode)
            
            idx = 0
            while not future.done():
                current_msg = messages_list[idx % len(messages_list)]
                status_placeholder.info(f"⏳ {current_msg}")
                time.sleep(2.5)
                idx += 1
            
            answer = future.result()

        status_placeholder.empty()

        if answer:
            st.markdown(answer)
            current_chat["messages"].append({"role": "assistant", "content": answer})
        else:
            st.error("התרחשה שגיאה בעת ניתוח הסוגיה.")
