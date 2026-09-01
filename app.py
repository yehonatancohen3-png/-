# 1. ייבוא ספריות נדרשות
import streamlit as st  # ייבוא ספריית Streamlit לבניית ממשק המשתמש[cite: 1]
import os  # ייבוא ספרייה לעבודה עם מערכת הקבצים ונתיבים[cite: 1]
import json  # ייבוא ספרייה לטיפול בקובצי JSON[cite: 1]
import requests  # ייבוא ספרייה לביצוע בקשות HTTP לקריאה מ-APIs[cite: 1]
import re  # ייבוא ספרייה לטיפול בביטויים רגולריים (Regex)[cite: 1]
import time  # ייבוא ספרייה לעבודה עם זמנים והשהיות[cite: 1]
import uuid  # ייבוא ספרייה לייצור מזהים ייחודיים[cite: 1]
from concurrent.futures import ThreadPoolExecutor  # הרצת משימות ברקע[cite: 1]
from dotenv import load_dotenv  # טעינת משתני סביבה[cite: 1]
import google.generativeai as genai  # ה-SDK של Google Gemini[cite: 1]

# 2. הגדרות דף האינטרנט
st.set_page_config( [cite: 1]
    page_title="סוגיה בעיון - AI תורני", [cite: 1]
    page_icon="📜", [cite: 1]
    layout="centered", [cite: 1]
    initial_sidebar_state="collapsed" [cite: 1]
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
load_dotenv() [cite: 1]

api_key = None [cite: 1]

if "GEMINI_API_KEY" in st.secrets: [cite: 1]
    api_key = str(st.secrets["GEMINI_API_KEY"]).strip() [cite: 1]
elif "GOOGLE_API_KEY" in st.secrets: [cite: 1]
    api_key = str(st.secrets["GOOGLE_API_KEY"]).strip() [cite: 1]
else: [cite: 1]
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") [cite: 1]

if not api_key: [cite: 1]
    st.error("לא נמצא מפתח API! אנא הגדר GEMINI_API_KEY ב-Secrets ב-Streamlit Cloud.") [cite: 1]
    st.stop() [cite: 1]

genai.configure(api_key=api_key) [cite: 1]

# 4. מנגנון שליפת מקורות מ-Sefaria API
def fetch_from_sefaria(query: str) -> str: [cite: 1]
    try: [cite: 1]
        url = "https://www.sefaria.org/api/v2/search/text"  [cite: 1]
        payload = { [cite: 1]
            "query": query, [cite: 1]
            "type": "text", [cite: 1]
            "field": "exact", [cite: 1]
            "size": 5 [cite: 1]
        }
        response = requests.post(url, json=payload, timeout=8) [cite: 1]
        
        if response.status_code == 200: [cite: 1]
            data = response.json() [cite: 1]
            hits = data.get("hits", {}).get("hits", []) [cite: 1]
            
            if not hits: [cite: 1]
                return "לא נמצאו מקורות תואמים בספריא." [cite: 1]
            
            results = [] [cite: 1]
            for hit in hits: [cite: 1]
                source = hit.get("_source", {}) [cite: 1]
                title = source.get("ref", "") [cite: 1]
                he_text = source.get("he", "") [cite: 1]
                
                if isinstance(he_text, str) and he_text.strip(): [cite: 1]
                    clean_text = re.sub(r'<[^>]+>', '', he_text) [cite: 1]
                    results.append(f"מקור מתוך ספריא [{title}]:\n\"{clean_text}\"") [cite: 1]
            
            if results: [cite: 1]
                return "\n\n".join(results) [cite: 1]
                
    except Exception as e: [cite: 1]
        return f"לא ניתן היה לשלוף מקורות מספריא: {str(e)}" [cite: 1]
    
    return "לא נמצאו מקורות ספציפיים בספריא."  [cite: 1]

# 5. מנגנון שליפה משולב (מאגר מקומי + ספריא)
def load_torah_database(): [cite: 1]
    db_path = os.path.join("data", "torah_database.json") [cite: 1]
    if os.path.exists(db_path): [cite: 1]
        try: [cite: 1]
            with open(db_path, "r", encoding="utf-8") as f: [cite: 1]
                return json.load(f) [cite: 1]
        except Exception: [cite: 1]
            pass [cite: 1]
    return [] [cite: 1]

def retrieve_all_context(query: str) -> str: [cite: 1]
    context_parts = [] [cite: 1]
    
    sefaria_data = fetch_from_sefaria(query) [cite: 1]
    if "לא נמצאו" not in sefaria_data and "לא ניתן" not in sefaria_data: [cite: 1]
        context_parts.append(f"--- מקורות מדויקים מספריא (כולל ניקוד) ---\n{sefaria_data}") [cite: 1]
        
    database = load_torah_database() [cite: 1]
    query_words = [w for w in query.split() if len(w) > 2] [cite: 1]
    matched_local = [] [cite: 1]
    
    for item in database: [cite: 1]
        content = item.get("content", "") [cite: 1]
        book = item.get("book", "")  [cite: 1]
        if any(word in content or word in book for word in query_words): [cite: 1]
            source_info = f"מקור מקומי: {book} " [cite: 1]
            
            masechet = item.get("masechet") [cite: 1]
            daf = item.get("daf") [cite: 1]
            siman = item.get("siman") [cite: 1]
            seif = item.get("seif") [cite: 1]
            
            if masechet:  [cite: 1]
                source_info += f"מסכת {masechet} " [cite: 1]
            if daf: [cite: 1]
                source_info += f"דף {daf} " [cite: 1]
            if siman: [cite: 1]
                source_info += f"סימן {siman} " [cite: 1]
            if seif: [cite: 1]
                source_info += f"סעיף {seif} " [cite: 1]
                
            source_info += f"\nתוכן המקור: \"{content}\"" [cite: 1]
            matched_local.append(source_info) [cite: 1]
            
    if matched_local: [cite: 1]
        context_parts.append(f"--- מקורות מהמאגר המקומי ---\n" + "\n\n".join(matched_local)) [cite: 1]
        
    if context_parts: [cite: 1]
        return "\n\n".join(context_parts) [cite: 1]
    return "לא נמצאו מקורות במאגרי המידע הזמינים." [cite: 1]

# 6. יצירת System Prompt דינמי
def get_system_prompt(style_mode: str) -> str:  [cite: 1]
    base_rules = """
כללי ברזל לציטוט ומקורות (חובה מוחלטת):
1. כאשר אתה מביא ציטוט מתוך המקורות שנשלפו מספריא או מהמאגר המקומי, חובה עליך להביא אותו מילה במילה בדיוק מוחלט כפי שהוא מופיע במקור!
2. שמור על הניקוד המקורי כפי שנשלף מספריא. אל תוריד ניקוד, אל תשנה אותיות ואל תשנה את משפטי המקור.
3. תחום כל ציטוט מדויק בתוך מירכאות ("...").
4. ציין תמיד בצמוד לכל ציטוט את מראה המקום המדויק שלו.
5. אסור להמציא מקורות, ציטוטים, ניקוד או שמות ספרים שלא קיימים!
6. בכל סוף תשובה, חובה לסיים במשפט הבא בדיוק: "והכל הוא רק לעיון ולמידה, ולהלכה למעשה יש לשאול רב מורה הוראה."
""" [cite: 1]

    if style_mode == "ישיבתי-למדני (סגנון שו\"ת)": [cite: 1]
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
""" [cite: 1]
    else: [cite: 1]
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
""" [cite: 1]

def analyze_sugya(messages_history, style_mode): [cite: 1]
    try: [cite: 1]
        last_prompt = messages_history[-1]["content"] [cite: 1]
        retrieved_context = retrieve_all_context(last_prompt) [cite: 1]
        
        system_prompt = get_system_prompt(style_mode) [cite: 1]
        
        generation_config = { [cite: 1]
            "temperature": 0.0, [cite: 1]
            "top_p": 0.8, [cite: 1]
        }
        
        model = genai.GenerativeModel( [cite: 1]
            model_name='models/gemini-3.6-flash', [cite: 1]
            system_instruction=system_prompt, [cite: 1]
            generation_config=generation_config [cite: 1]
        )

        formatted_history = [] [cite: 1]
        for msg in messages_history[:-1]: [cite: 1]
            role = "user" if msg["role"] == "user" else "model" [cite: 1]
            formatted_history.append({"role": role, "parts": [msg["content"]]}) [cite: 1]

        chat = model.start_chat(history=formatted_history) [cite: 1]

        prompt_with_context = f"""
מקורות מדויקים שנשלפו מספריא ומאגר הנתונים:
{retrieved_context}

שאלה לניתוח: {last_prompt}
""" [cite: 1]

        response = chat.send_message(prompt_with_context) [cite: 1]
        return response.text [cite: 1]

    except Exception as e: [cite: 1]
        st.error(f"שגיאה בהפעלת המודל: {str(e)}") [cite: 1]
        return None [cite: 1]

# 7. ניהול פרויקטים ושיחות ב-Session State
if "projects" not in st.session_state:
    st.session_state.projects = {"פרויקט ראשי": []}  # מילון שבו המפתח הוא שם הפרויקט והערך הוא רשימת מזהי שיחות

if "current_project" not in st.session_state:
    st.session_state.current_project = "פרויקט ראשי"

if "chats" not in st.session_state: [cite: 1]
    st.session_state.chats = {} [cite: 1]

if "current_chat_id" not in st.session_state: [cite: 1]
    new_id = str(uuid.uuid4()) [cite: 1]
    st.session_state.chats[new_id] = {"title": "שיחה חדשה", "messages": [], "project": "פרויקט ראשי"} [cite: 1]
    st.session_state.projects["פרויקט ראשי"].append(new_id)
    st.session_state.current_chat_id = new_id [cite: 1]

def create_new_chat(project_name): [cite: 1]
    new_id = str(uuid.uuid4()) [cite: 1]
    st.session_state.chats[new_id] = {"title": "שיחה חדשה", "messages": [], "project": project_name} [cite: 1]
    st.session_state.projects[project_name].append(new_id)
    st.session_state.current_chat_id = new_id [cite: 1]

# 8. סרגל צד (Sidebar) - ניהול פרויקטים ושיחות אחרונות
with st.sidebar: [cite: 1]
    st.title("⚙️ הגדרות") [cite: 1]
    
    style_mode = st.radio( [cite: 1]
        "בחר סגנון ניתוח:", [cite: 1]
        options=["פשוט ומונגש", "ישיבתי-למדני (סגנון שו\"ת)"], [cite: 1]
        index=0 [cite: 1]
    )

    st.markdown("---") [cite: 1]
    
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

    st.markdown("---") [cite: 1]

    # --- שיחה חדשה בפרויקט ---
    if st.button("➕ שיחה חדשה בפרויקט", use_container_width=True): [cite: 1]
        create_new_chat(st.session_state.current_project) [cite: 1]
        st.rerun() [cite: 1]

    st.markdown("---") [cite: 1]
    
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
st.title("📜 סוגיה בעיון") [cite: 1]
st.caption(f"פרויקט פעיל: **{st.session_state.current_project}** | מחובר בזמן אמת לספריא")

current_chat = st.session_state.chats[st.session_state.current_chat_id] [cite: 1]

for message in current_chat["messages"]:  [cite: 1]
    with st.chat_message(message["role"]): [cite: 1]
        st.markdown(message["content"]) [cite: 1]

if prompt := st.chat_input("הכנס שאלה או סוגיה בעיון..."): [cite: 1]
    if not current_chat["messages"]: [cite: 1]
        current_chat["title"] = prompt[:25] + ("..." if len(prompt) > 25 else "") [cite: 1]

    current_chat["messages"].append({"role": "user", "content": prompt}) [cite: 1]
    with st.chat_message("user"): [cite: 1]
        st.markdown(prompt) [cite: 1]

    with st.chat_message("assistant"): [cite: 1]
        status_placeholder = st.empty() [cite: 1]

        messages_list = [ [cite: 1]
            "יהונתן חושב...",
            "יהונתן עומד לפתור את הסוגיה...",
            "יהונתן מריץ חיפוש בראש וכל התורה כולה לנגד עיניו...",
            "ליהונתן יש פיתרון, וחושב על כיוונים אחרים...",
            "יהונתן צריך ריכוז...",
            "יהונתן מקבץ כל מיני שו\"תים שנזכר בהם בהקשר לשאלה...",
            "יהונתן מבין שהשאלה מסובכת, אך אין שאלה שתישאר לא פתורה..."
        ] [cite: 1]

        with ThreadPoolExecutor() as executor: [cite: 1]
            future = executor.submit(analyze_sugya, current_chat["messages"], style_mode) [cite: 1]
            
            idx = 0 [cite: 1]
            while not future.done(): [cite: 1]
                current_msg = messages_list[idx % len(messages_list)] [cite: 1]
                status_placeholder.info(f"⏳ {current_msg}") [cite: 1]
                time.sleep(2.5) [cite: 1]
                idx += 1 [cite: 1]
            
            answer = future.result() [cite: 1]

        status_placeholder.empty() [cite: 1]

        if answer: [cite: 1]
            st.markdown(answer) [cite: 1]
            current_chat["messages"].append({"role": "assistant", "content": answer}) [cite: 1]
        else: [cite: 1]
            st.error("התרחשה שגיאה בעת ניתוח הסוגיה.") [cite: 1]
