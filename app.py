# 1. ייבוא ספריות נדרשות
import streamlit as st
import os
import json
import requests
import re
import time
import uuid
from dotenv import load_dotenv
import google.generativeai as genai

# 2. הגדרות דף האינטרנט
st.set_page_config(
    page_title="סוגיה בעיון - AI תורני",
    page_icon="📜",
    layout="centered",
    initial_sidebar_state="expanded"
)

# הוספת CSS מונע מריחת אותיות, תומך RTL, ומגדיל את נראות כפתורי המחיקה
st.markdown(
    """
    <style>
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stMain"] {
        direction: ltr !important;
        text-align: left !important;
    }
    [data-testid="stMainBlockContainer"], 
    [data-testid="stChatMessage"], 
    [data-testid="stChatInput"], 
    [data-testid="stPopoverBody"],
    .stMarkdown, p, h1, h2, h3, h4, h5, h6, label, span, div[data-testid="stMarkdownContainer"] {
        direction: rtl !important;
        text-align: right !important;
        word-break: keep-all !important;
        overflow-wrap: break-word !important;
    }
    [data-testid="stChatMessage"] {
        width: 100% !important;
        max-width: 100% !important;
    }
    [data-testid="stSidebar"] {
        direction: rtl !important;
        text-align: right !important;
    }
    [data-testid="stSidebarUserContent"] {
        direction: rtl !important;
        text-align: right !important;
        padding-top: 2rem !important;
    }
    [data-testid="stSidebar"] div[role="combobox"] {
        direction: rtl !important;
        text-align: right !important;
        width: 100% !important;
    }
    ul, ol {
        direction: rtl !important;
        text-align: right !important;
        padding-right: 1.5rem !important;
        padding-left: 0rem !important;
    }
    /* התאמת גודל ומרכוז עבור כפתורי האשפה בסרגל הצד */
    [data-testid="stSidebar"] button[kind="secondary"] p {
        font-size: 16px !important;
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

# 4. מנגנון שליפת מקורות מ-Sefaria API (הקטנת כמות למהירות מרבית)
def fetch_from_sefaria(query: str) -> str:
    try:
        url = "https://www.sefaria.org/api/v2/search/text"
        payload = {
            "query": query,
            "type": "text",
            "field": "exact",
            "size": 3
        }
        response = requests.post(url, json=payload, timeout=5)
        
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

# 6. יצירת System Prompt דינמי (כולל מצב מבחני רבנות מורחב)
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

    if style_mode == "הכנה למבחני רבנות":
        return f"""
אתה מודול AI תורני מומחה, המותאם במיוחד לסייע ללומדים ולנבחנים במבחני ההסמכה לרבנות הראשית.
תפקידך להציג את השלשלת ההלכתית המלאה והמדויקת לפי הסדר הבא:
1. **מקורות מהתנ"ך ומדברי הש"ס (גמרא):** הבאת הפסוקים הרלוונטיים וסוגיית הגמרא עם ציטוטים מדויקים ומראי מקומות.
2. **שיטות הראשונים:** התמקדות מרכזית ברמב"ם, בתוספת שיטות הרא"ש והרי"ף ככל שהם קיימים על הסוגיה.
3. **שיטות האחרונים:** הצגת הדברים בטור, בבית יوسف על הטור, בשולחן ערוך, וכן בנושאי הכלים המרכזיים (כגון חלקת מחוקק, בית שמואל, פתחי תשובה וכדומה).
4. **פסיקה למעשה למנהגי בני ימינו:** סיכום ההלכה למעשה תוך הבחנה ברורה ומפורטת בין מנהגי אשכנז, ספרד ותימן.

{base_rules}
"""
    elif style_mode == "ישיבתי-למדני (סגנון שו\"ת)":
        return f"""
אתה מודול AI תורני מומחה, הכותב בסגנון ישיבתי-למדני עמוק וססגוני, העשיר במטבעות לשון בארמית ובביטויי בית המדרש הקלאסיים.
תפקידך להציג משא ומתן למדני ברצף עיוני, המבוסס על דיוק בלשון המקורות, עמידה על קושיות וסתירות, והגדרת חקירות וסברות.

{base_rules}
"""
    else:
        return f"""
אתה מודול AI תורני מומחה, המנתח סוגיות הלכתיות ומחשבתיות בשפה ברורה, מופשטת ונגישה לכל לומד.

{base_rules}

חובה עליך לבנות את התשובה לפי הסדר הבא:
1. **הגדרת המקרה והשאלה:** הסבר פשוט של השאלה והרקע.
2. **יסוד הסוגיה במקורות:** ציטוט המקורות המרכזיים ממקורם והסבר בשפה קלה.
3. **שיטות הראשונים והאחרונים:** הצגת השיטות השונות בשפה פשוטה.
4. **מסקנה הלכתית למעשה:** סיכום השורה התחתונה.
"""

def analyze_sugya(messages_history, style_mode):
    max_retries = 3
    retry_delay = 5

    for attempt in range(max_retries):
        try:
            last_prompt = messages_history[-1]["content"]
            retrieved_context = retrieve_all_context(last_prompt)
            
            system_prompt = get_system_prompt(style_mode)
            
            generation_config = {
                "temperature": 0.0,
                "top_p": 0.8,
            }
            
            model = genai.GenerativeModel(
                model_name='gemini-3.6-flash',
                system_instruction=system_prompt,
                generation_config=generation_config
            )

            recent_history = messages_history[-7:-1]
            formatted_history = []
            for msg in recent_history:
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
            err_str = str(e)
            if "429" in err_str or "ResourceExhausted" in err_str:
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
            import traceback
            error_details = traceback.format_exc()
            st.error(f"שגיאה מפורטת בהפעלת המודל: {err_str}")
            st.code(error_details)
            return None
    return "חרגת ממכסת הבקשות (Rate Limit). אנא המתן מספר שניות ונסה שוב."

# 7. מערכת שמירת נתונים מקומית (Persistence)
USER_DATA_FILE = os.path.join("data", "user_data.json")

def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        try:
            with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None

def save_user_data():
    os.makedirs("data", exist_ok=True)
    data = {
        "projects": st.session_state.projects,
        "chats": st.session_state.chats,
        "current_project": st.session_state.current_project,
        "current_chat_id": st.session_state.current_chat_id
    }
    with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

if "data_loaded" not in st.session_state:
    saved_data = load_user_data()
    if saved_data:
        st.session_state.projects = saved_data.get("projects", {"פרויקט ראשי": []})
        st.session_state.chats = saved_data.get("chats", {})
        st.session_state.current_project = saved_data.get("current_project", "פרויקט ראשי")
        st.session_state.current_chat_id = saved_data.get("current_chat_id", None)
    else:
        st.session_state.projects = {"פרויקט ראשי": []}
        st.session_state.chats = {}
        st.session_state.current_project = "פרויקט ראשי"
        st.session_state.current_chat_id = None
    
    if not st.session_state.current_chat_id or st.session_state.current_chat_id not in st.session_state.chats:
        new_id = str(uuid.uuid4())
        st.session_state.chats[new_id] = {"title": "שיחה חדשה", "messages": [], "project": "פרויקט ראשי"}
        st.session_state.projects["פרויקט ראשי"].append(new_id)
        st.session_state.current_chat_id = new_id
        save_user_data()
        
    st.session_state.data_loaded = True

if "search_input_box" not in st.session_state:
    st.session_state.search_input_box = ""

def create_new_chat(project_name):
    new_id = str(uuid.uuid4())
    st.session_state.chats[new_id] = {"title": "שיחה חדשה", "messages": [], "project": project_name}
    st.session_state.projects[project_name].append(new_id)
    st.session_state.current_chat_id = new_id
    save_user_data()

if "style_mode" not in st.session_state:
    st.session_state.style_mode = "פשוט ומונגש"

# 8. סרגל צד (Sidebar) - מעוצב, מונגש וכולל אישור כפול למניעת מחיקות שגויות
with st.sidebar:
    # --- מיתוג וכותרת ---
    st.markdown("<h2 style='text-align: center; color: #1f77b4; margin-bottom: 0;'>📜 סוגיה בעיון</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 14px; color: gray; margin-top: 0;'>העוזר התורני החכם שלך</p>", unsafe_allow_html=True)
    
    # --- הגדרות סגנון התשובה (בראש העמוד) ---
    st.markdown("### ⚙️ סגנון לימוד")
    st.session_state.style_mode = st.selectbox(
        "בחר את סגנון התשובה המועדף:",
        options=["פשוט ומונגש", "ישיבתי-למדני (סגנון שו\"ת)", "הכנה למבחני רבנות"],
        index=["פשוט ומונגש", "ישיבתי-למדני (סגנון שו\"ת)", "הכנה למבחני רבנות"].index(st.session_state.style_mode),
        label_visibility="collapsed"
    )
    
    st.divider()

    # --- פעולות מרכזיות (שיחה חדשה) ---
    if st.button("➕ שיחה חדשה", use_container_width=True, type="primary", key="global_new_chat_btn"):
        if not st.session_state.current_project or st.session_state.current_project not in st.session_state.projects:
            st.session_state.current_project = list(st.session_state.projects.keys())[0]
        create_new_chat(st.session_state.current_project)
        
        if hasattr(st, "rerun"):
            st.rerun()
        else:
            st.experimental_rerun()

    # --- חיפוש מהיר (בזמן אמת) ---
    st.session_state.search_input_box = st.text_input(
        "חיפוש",
        value=st.session_state.get("search_input_box", ""),
        placeholder="🔍 חפש שיחה בתיקיות...",
        label_visibility="collapsed"
    )
    
    st.divider()

    # --- ניהול תיקיות ---
    col_title, col_add_folder = st.columns([7, 3], gap="small")
    with col_title:
        st.markdown("<h4 style='margin-bottom: 0; padding-top: 5px;'>📂 התיקיות שלי</h4>", unsafe_allow_html=True)
    with col_add_folder:
        with st.popover("➕ חדש", use_container_width=True):
            new_proj_name = st.text_input("שם התיקייה החדשה:", key="new_proj_input")
            if st.button("💾 צור", use_container_width=True, type="primary", key="create_proj_btn"):
                if new_proj_name and new_proj_name not in st.session_state.projects:
                    st.session_state.projects[new_proj_name] = []
                    st.session_state.current_project = new_proj_name
                    create_new_chat(new_proj_name)
                    if hasattr(st, "rerun"):
                        st.rerun()
                    else:
                        st.experimental_rerun()

    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # --- הצגת התיקיות והשיחות ---
    for proj_name, chat_ids in list(st.session_state.projects.items()):
        
        current_search = st.session_state.search_input_box.lower()
        filtered_chats = [
            cid for cid in chat_ids 
            if cid in st.session_state.chats and 
            (current_search in st.session_state.chats[cid]["title"].lower() or current_search == "")
        ]
        
        if current_search and not filtered_chats:
            continue

        is_expanded = (proj_name == st.session_state.current_project) or bool(current_search)
        
        with st.expander(f"📁 {proj_name} ({len(filtered_chats)})", expanded=is_expanded):
            
            # כפתורי ניהול תיקייה פנימיים (כולל בטיחות למחיקת תיקייה באמצעות פופאפ)
            c_new, c_del = st.columns([7, 3])
            with c_new:
                if st.button("➕ שיחה", key=f"new_{proj_name}", use_container_width=True):
                    st.session_state.current_project = proj_name
                    create_new_chat(proj_name)
                    if hasattr(st, "rerun"):
                        st.rerun()
                    else:
                        st.experimental_rerun()
            with c_del:
                with st.popover("🗑️ מחיקה", use_container_width=True):
                    st.markdown(f"**למחוק את '{proj_name}'?**\nכל השיחות בתיקייה יימחקו לצמיתות.")
                    if st.button("אישור מחיקה סופית", key=f"del_proj_{proj_name}", type="primary", use_container_width=True):
                        for c_id in st.session_state.projects[proj_name]:
                            if c_id in st.session_state.chats:
                                del st.session_state.chats[c_id]
                        del st.session_state.projects[proj_name]
                        
                        if not st.session_state.projects:
                            st.session_state.projects["פרויקט ראשי"] = []
                        
                        st.session_state.current_project = list(st.session_state.projects.keys())[0]
                        if not st.session_state.projects[st.session_state.current_project]:
                            create_new_chat(st.session_state.current_project)
                        else:
                            st.session_state.current_chat_id = st.session_state.projects[st.session_state.current_project][-1]
                        save_user_data()
                        if hasattr(st, "rerun"):
                            st.rerun()
                        else:
                            st.experimental_rerun()
            
            st.markdown("<hr style='margin: 5px 0; border: none; border-top: 1px solid #eee;'>", unsafe_allow_html=True)
            
            # רשימת השיחות בתיקייה עם מנגנון אישור כפול (בטיחות) למחיקת שיחה
            for cid in reversed(filtered_chats):
                chat = st.session_state.chats[cid]
                chat_title = chat["title"]
                
                is_active = (cid == st.session_state.current_chat_id)
                btn_type = "primary" if is_active else "secondary"
                
                col_btn, col_del_chat = st.columns([82, 18])
                
                with col_btn:
                    if st.button(f"💬 {chat_title}", key=f"btn_{cid}", use_container_width=True, type=btn_type):
                        st.session_state.current_chat_id = cid
                        st.session_state.current_project = proj_name
                        save_user_data()
                        if hasattr(st, "rerun"):
                            st.rerun()
                        else:
                            st.experimental_rerun()
                        
                with col_del_chat:
                    # מנגנון בטיחות: שימוש ב-Popover שדורש לחיצה נוספת ולא מוחק מיד בלחיצה אחת
                    with st.popover("🗑️", help="מחק שיחה זו"):
                        st.markdown(f"**למחוק את השיחה?**\n'{chat_title}'")
                        if st.button("כן, מחק", key=f"confirm_del_{cid}", type="primary", use_container_width=True):
                            if cid in st.session_state.projects[proj_name]:
                                st.session_state.projects[proj_name].remove(cid)
                            if cid in st.session_state.chats:
                                del st.session_state.chats[cid]
                            
                            if cid == st.session_state.current_chat_id:
                                if st.session_state.projects[proj_name]:
                                    st.session_state.current_chat_id = st.session_state.projects[proj_name][-1]
                                else:
                                    create_new_chat(proj_name)
                            
                            save_user_data()
                            if hasattr(st, "rerun"):
                                st.rerun()
                            else:
                                st.experimental_rerun()

# 9. עיצוב הממשק המרכזי והצגת השיחה הנוכחית
st.title("📜 סוגיה בעיון")
st.caption(f"תיקייה פעילה: **{st.session_state.current_project}** | מחובר בזמן אמת לספריא")

current_chat = st.session_state.chats[st.session_state.current_chat_id]

for message in current_chat["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("הכנס שאלה או סוגיה בעיון..."):
    if not current_chat["messages"]:
        current_chat["title"] = prompt[:25] + ("..." if len(prompt) > 25 else "")
        save_user_data()

    current_chat["messages"].append({"role": "user", "content": prompt})
    save_user_data()
    
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("⏳ יהונתן חושב ומנתח את הסוגיה..."):
            answer = analyze_sugya(current_chat["messages"], st.session_state.style_mode)

        if answer:
            st.markdown(answer)
            current_chat["messages"].append({"role": "assistant", "content": answer})
            save_user_data()
