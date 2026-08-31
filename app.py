# 1. ייבוא ספריות נדרשות
import streamlit as st  # ייבוא ספריית Streamlit לבניית ממשק המשתמש
import streamlit.components.v1 as components  # ייבוא הרכיב להרצת JavaScript פעיל ב-DOM
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
st.set_page_config(
    page_title="סוגיה בעיון - AI תורני",
    page_icon="📜",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 3. CSS חריף המנטרל לחלוטין את ה-Auto Scroll של Streamlit
st.markdown(
    """
    <style>
    /* 1. איפוס הגלישה הכפויה של Streamlit */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        scroll-behavior: auto !important;
        overflow-anchor: none !important;
    }

    /* 2. שמירה על פריסת LTR במעטפת המערכת למניעת עיוותים */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        direction: ltr !important;
    }

    /* 3. החלת RTL אך ורק על אזורי תוכן וטקסט */
    [data-testid="stMainBlockContainer"], 
    [data-testid="stChatMessage"], 
    [data-testid="stChatInput"], 
    .stMarkdown, p, h1, h2, h3, h4, h5, h6, label, span {
        direction: rtl !important;
        text-align: right !important;
    }

    /* 4. תיקון סרגל הצד */
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

    /* 5. תיקון תצוגת רשימות */
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

# 5. טעינת המאגר ויצירת אינדקס מילים מראש (Inverted Index) בזיכרון לחיפוש מיידי
@st.cache_data
def load_and_index_database():
    db_path = os.path.join("data", "torah_database.json")
    if not os.path.exists(db_path):
        return [], {}
    try:
        with open(db_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        word_index = {}
        for idx, item in enumerate(data):
            content = item.get("content", "") + " " + item.get("book", "")
            words = set(re.findall(r'\w+', content))
            for w in words:
                if len(w) > 2:
                    word_index.setdefault(w, set()).add(idx)
        return data, word_index
    except Exception:
        return [], {}

# 6. חיפוש מקומי מהיר במאגר מבוסס אינדקס
def search_local_database_fast(query: str) -> str:
    database, word_index = load_and_index_database()
    if not database or not word_index:
        return ""
        
    query_words = [w for w in re.findall(r'\w+', query) if len(w) > 2]
    if not query_words:
        return ""
        
    matching_indices = set()
    for w in query_words:
        if w in word_index:
            matching_indices.update(word_index[w])
            
    if not matching_indices:
        return ""

    matched_local = []
    for idx in list(matching_indices)[:3]:  # הגבלה ל-3 תוצאות הרלוונטיות ביותר
        item = database[idx]
        source_info = f"מקור מקומי: {item.get('book', '')} "
        if item.get("masechet"): source_info += f"מסכת {item.get('masechet')} "
        if item.get("daf"): source_info += f"דף {item.get('daf')} "
        if item.get("siman"): source_info += f"סימן {item.get('siman')} "
        if item.get("seif"): source_info += f"סעיף {item.get('seif')} "
        
        content = item.get('content', '')
        source_info += f"\nתוכן: \"{content[:300]}...\"" if len(content) > 300 else f"\nתוכן: \"{content}\""
        matched_local.append(source_info)
        
    return "\n\n".join(matched_local)

# 7. פנייה לספריא API עם Timeout מקוצר (1.5 שניות בלבד מונע תקיעות רשת)
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_from_sefaria_fast(query: str) -> str:
    try:
        url = "https://www.sefaria.org/api/v2/search/text"
        payload = {
            "query": query,
            "type": "text",
            "field": "exact",
            "size": 3
        }
        response = requests.post(url, json=payload, timeout=1.5)
        
        if response.status_code == 200:
            hits = response.json().get("hits", {}).get("hits", [])
            results = []
            for hit in hits[:3]:
                source = hit.get("_source", {})
                title = source.get("ref", "")
                he_text = source.get("he", "")
                
                if isinstance(he_text, str) and he_text.strip():
                    clean_text = re.sub(r'<[^>]+>', '', he_text)
                    results.append(f"מקור מתוך ספריא [{title}]:\n\"{clean_text}\"")
            
            if results:
                return "\n\n".join(results)
    except Exception:
        pass  # במידה וחרג מפרק הזמן או נכשל - ממשיכים הלאה מיד ללא תקיעה
    return ""

# 8. שליפת מקורות מקבילית ומהירה
def retrieve_all_context(query: str) -> str:
    context_parts = []
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_sefaria = executor.submit(fetch_from_sefaria_fast, query)
        future_local = executor.submit(search_local_database_fast, query)
        
        sefaria_data = future_sefaria.result()
        local_data = future_local.result()
        
    if sefaria_data:
        context_parts.append(f"--- מקורות מדויקים מספריא (כולל ניקוד) ---\n{sefaria_data}")
        
    if local_data:
        context_parts.append(f"--- מקורות מהמאגר המקומי ---\n{local_data}")
        
    if context_parts:
        return "\n\n".join(context_parts)
    return "לא נמצאו מקורות במאגרי המידע הזמינים."

# 9. יצירת System Prompt דינמי לפי סגנון הנבחר
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

        # שילוב 4 ההודעות האחרונות בלבד למניעת העמסת היסטוריה איטית על המודל
        formatted_history = []
        recent_history = messages_history[-5:-1] if len(messages_history) > 5 else messages_history[:-1]
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
        st.error(f"שגיאה בהפעלת המודל: {str(e)}")
        return None

# 10. ניהול היסטוריית השיחות ב-session_state
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

# 11. סרגל צד (Sidebar)
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

# 12. עיצוב הממשק והצגת השיחה הנוכחית
st.title("📜 סוגיה בעיון")
st.caption("מנוע בינה מלאכותית לניתוח סוגיות הלכתיות ולמדניות (מחובר בזמן אמת לספריא)")

current_chat = st.session_state.chats[st.session_state.current_chat_id]

for message in current_chat["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("הכנס שאלה או סוגיה בעיון..."):
    if not current_chat["messages"]:
        current_chat["title"] = prompt[:25] + ("..." if len(prompt) > 25 else "")

    current_chat["messages"].append({"role": "user", "content": prompt})
    
    components.html(
        """
        <script>
            (function() {
                var parentDoc = window.parent.document;
                var container = parentDoc.querySelector('[data-testid="stAppViewContainer"]') || parentDoc.querySelector('.main') || parentDoc.documentElement;
                
                var userMessages = parentDoc.querySelectorAll('[data-testid="stChatMessage"]');
                var lastUserMsg = userMessages[userMessages.length - 1];
                
                if (lastUserMsg) {
                    var targetTop = lastUserMsg.offsetTop - 20;
                    
                    var forceScroll = function() {
                        container.scrollTop = targetTop;
                    };
                    
                    forceScroll();
                    
                    var intervalId = setInterval(forceScroll, 50);
                    setTimeout(function() {
                        clearInterval(intervalId);
                    }, 4000);
                }
            })();
        </script>
        """,
        height=0,
        width=0
    )

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        messages_list = [
            "יהונתן חושב...",
            "יהונתן עומד לפתור את הסוגיה...",
            "יהונתן מריץ חיפוש בראש וכל התורה כולה לנגד עיניו...",
            "ליהונתן יש פיתרון, וחושב על כיוונים אחרים...",
            "יהונתן צריך ריכוז...",
            "יהונתן מקבץ כל מיני שו\"תים שנזכר בהם בהקשר לשאלה...",
            "יהונתן מבין שהשאלה מסובכת, אך אין שאלה שתישאר לא פתורה..."
        ]

        with st.status(messages_list[0], expanded=False) as status:
            with ThreadPoolExecutor() as executor:
                future = executor.submit(analyze_sugya, current_chat["messages"], style_mode)
                
                idx = 0
                last_update = time.time()
                
                while not future.done():
                    if time.time() - last_update >= 2.5:
                        idx += 1
                        current_msg = messages_list[idx % len(messages_list)]
                        status.update(label=current_msg)
                        last_update = time.time()
                    
                    time.sleep(0.1)  # בדיקת דופק קצרה לזיהוי סיום מיידי
                
                answer = future.result()

        if answer:
            st.markdown(answer)
            current_chat["messages"].append({"role": "assistant", "content": answer})
        else:
            st.error("התרחשה שגיאה בעת ניתוח הסוגיה.")
