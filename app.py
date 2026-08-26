# 1. ייבוא ספריות נדרשות
import streamlit as st
import os
import json
import requests
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import google.generativeai as genai

# 2. הגדרות דף האינטרנט
st.set_page_config(
    page_title="סוגיה בעיון - AI תורני",
    page_icon="📜",
    layout="centered"
)

# הוספת CSS מקיף ליישור מלא מימין לשמאל (RTL) وتמיכה בעיצוב נקי
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

    h1, h2, h3, h4, h5, h6, p, div, span, label, .stMarkdownContainer, .stMarkdown {
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

    [data-testid="stSidebar"] button {
        user-select: none;
        -webkit-user-select: none;
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
    
    # 1. שליפה מספריא
    sefaria_data = fetch_from_sefaria(query)
    if "לא נמצאו" not in sefaria_data and "לא ניתן" not in sefaria_data:
        context_parts.append(f"--- מקורות מדויקים מספריא (כולל ניקוד) ---\n{sefaria_data}")
        
    # 2. שליפה מהמאגר המקומי
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

# 6. יצירת System Prompt דינמי לפי סגנון הנבחר
def get_system_prompt(style_mode: str) -> str:
    base_rules = """
כללי ברזל לציטוט ומקורות (חובה מוחלטת):
1. כאשר אתה מביא ציטוט מתוך המקורות שנשלפו מספריא או מהמאגר המקומי, חובה עליך להביא אותו מילה במילה בדיוק מוחלט כפי שהוא מופיע במקור!
2. שמור על הניקוד המקורי כפי שנשלף מספריא. אל תוריד ניקוד, אל תשנה אותיות ואל תסדר מחדש את משפטי המקור.
3. תחום כל ציטוט מדויק בתוך מירכאות ("...").
4. ציין תמיד בצמוד לכל ציטוט את מראה המקום המדויק שלו בספריא.
5. אסור להמציא מקורות, ציטוטים, ניקוד או שמות ספרים שלא קיימים!
"""

    if style_mode == "ישיבתי-למדני (סגנון שו\"ת)":
        return f"""
אתה מודול AI תורני מומחה, המנתח סוגיות בסגנון ישיבתי-למדני עמוק ("סוגיה בעיון") בדומה לתשובות שו"ת למדניות.
תפקידך להציג ניתוח יסודי, מעמיק ומחודד, תוך דגש על סברות, קושיות, תירוצים, חילוקים בין שיטות וגדרים הלכתיים.

{base_rules}

חובה עליך לבנות את התשובה לפי הסדר הלמדני הבא:

1. **הגדרת הסוגיה והנידון:**
   - פירוק הגדרים ההלכתיים והסתפקות הדין.

2. **יסוד הסוגיה במקורות (גמרא וסוגיות מקבילות):**
   - הובאת המקורות המרכזיים בציטוט מילה במילה (כולל ניקוד אם קיים במקור) עם מראה מקום מדויק והסבר מהלך הגמרא.

3. **שיטות הראשונים והגדרת הסברות:**
   - הצגת השיטות השונות (רש"י, תוספות, רמב"ם, רמב"ן, רא"ש וכו'), עמידה על החילוקים ביניהם והגדרת ה"חקירה" או הסברה הלמדנית.

4. **פסיקת השולחן ערוך והנושאי כלים:**
   - דיוק בלשון המחבר והרמ"א, ודברי נושאי הכלים (ש"ך, ט"ז, פתחי תשובה וכו').

5. **שו"תים ופוסקי זמננו:**
   - הובאת תשובות אחרונים ופוסקי זמננו, היקשים למקרים אקטואליים והעמקה בסברות הפוסקים.

6. **סדר הדין ומסקנה להלכה:**
   - סיכום הדין להלכה ולמעשה לפי מנהג ספרד ואשכנז.
   - הדגשה: "תוכן זה מיועד לעיון ולמידה, ובמקרה מעשי יש להתייעץ עם רב מורה הוראה."

כללי שפה:
- ענה בשפה תורנית-ישיבתית גבוהה, תוך שימוש במושגים למדניים מקובלים.
"""
    else:  # סגנון פשוט ומונגש
        return f"""
אתה מודול AI תורני מומחה, המנתח סוגיות הלכתיות ומחשבתיות בשפה ברורה, מופשטת ונגישה לכל לומד.
תפקידך להציג ניתוח בהיר ומסודר מפי המקורות ועד לפסיקת ההלכה למעשה.

{base_rules}

חובה עליך לבנות את התשובה לפי הסדר הבא:

1. **הגדרת המקרה והשאלה:**
   - הסבר פשוט וברור של השאלה והרקע שלה.

2. **יסוד הסוגיה במקורות (תנ"ך, משנה, גמרא):**
   - הובאת המקורות המרכזיים בציטוט מילה במילה (כולל ניקוד אם קיים במקור) עם מראה מקום מדויק והסבר בשפה קלה.

3. **שיטות הראשונים (מחלוקות הסוגיה):**
   - הצגת השיטות השונות בשפה פשוטה והסברת מוקד המחלוקת.

4. **פסיקת השולחן ערוך והרמ"א:**
   - הצגת הפסק בשולחן ערוך וברמ"א.

5. **פוסקי זמננו (אקטואליה):**
   - דיון קצר בפסיקות של פוסקי זמננו הנוגעות לימינו.

6. **מסקנה הלכתית למעשה:**
   - סיכום ברור של השורה התחתונה לפי מנהג ספרד ואשכנז.
   - הדגשה: "תוכן זה מיועד לעיון ולמידה, ובמקרה מעשי יש להתייעץ עם רב מורה הוראה."

כללי שפה:
- ענה בעברית תקנית, הירה ורהוטה, בצורה נגישה וקל להבנה.
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

# 7. ניהול היסטוריית השיחות ב-session_state
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

# 8. סרגל צד (Sidebar)
with st.sidebar:
    st.title("⚙️ הגדרות וסגנון")
    
    # בחירת סגנון תשובה
    style_mode = st.radio(
        "בחר סגנון ניתוח:",
        options=["פשוט ומונגש", "ישיבתי-למדני (סגנון שו\"ת)"],
        index=0
    )

    st.markdown("---")
    st.title("📜 היסטוריית שיחות")
    
    if st.button("➕ שיחה חדשה", use_container_width=True, type="secondary"):
        create_new_chat()
        st.rerun()

    st.markdown("---")

    archived_chats = {
        c_id: c_data for c_id, c_data in st.session_state.chats.items()
        if c_data["messages"] or c_id == st.session_state.current_chat_id
    }

    for c_id, c_data in list(archived_chats.items()):
        if not c_data["messages"] and c_id != st.session_state.current_chat_id:
            continue

        is_active = (c_id == st.session_state.current_chat_id)
        btn_label = f"💬 {c_data['title']}"
        
        if st.button(btn_label, key=f"select_{c_id}", use_container_width=True, type="primary" if is_active else "secondary"):
            st.session_state.current_chat_id = c_id
            st.rerun()

# JavaScript למחיקה
st.components.v1.html(
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
    height=0,
)

# 9. עיצוב הממשק והצגת השיחה הנוכחית
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
