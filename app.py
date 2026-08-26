import streamlit as st
import os
import json
import requests
import re
from dotenv import load_dotenv
import google.generativeai as genai

# 1. הגדרות דף האינטרנט
st.set_page_config(
    page_title="סוגיה בעיון - AI תורני",
    page_icon="📜",
    layout="centered"
)

# הוספת CSS ליישור RTL
st.markdown(
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

    h1, h2, h3, h4, h5, h6, p, div, span, label, .stMarkdownContainer, .stMarkdown {
        direction: rtl !important;
        text-align: right !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 2. טעינת מפתח ה-API
load_dotenv()

api_key = None
if "GEMINI_API_KEY" in st.secrets:
    api_key = str(st.secrets["GEMINI_API_KEY"]).strip()
elif "GOOGLE_API_KEY" in st.secrets:
    api_key = str(st.secrets["GOOGLE_API_KEY"]).strip()
else:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if not api_key:
    st.error("לא נמצא מפתח API! אנא הגדר GEMINI_API_KEY ב-Secrets.")
    st.stop()

genai.configure(api_key=api_key)

# 3. מנגנון שליפת מקורות מספריא (כולל טיפול בשגיאות תקשורת)
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

# 4. מנגנון שליפה מורחב
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
            if "masechet" in item:
                source_info += f"מסכת {item['masechet']} דף {item['daf']} "
            if "siman" in item:
                source_info += f"סימן {item['siman']} סעיף {item['seif']} "
            source_info += f"\nתוכן המקור: \"{content}\""
            matched_local.append(source_info)
            
    if matched_local:
        context_parts.append(f"--- מקורות מהמאגר המקומי ---\n" + "\n\n".join(matched_local))
        
    if context_parts:
        return "\n\n".join(context_parts)
    return "לא נמצאו מקורות במאגרי המידע הזמינים."

# 5. System Prompt
SYSTEM_PROMPT = """
אתה מודול AI תורני מומחה, המנתח סוגיות הלכתיות, מחשבתיות ואקטואליות במתודולוגיה של בית מדרש ("סוגיה בעיון").
תפקידך להציג ניתוח יסודי, מעמיק ומדויק מפי המקורות ועד לפסיקת ההלכה למעשה.

כללי ברזל לציטוט ומקורות:
1. ציטוטים מספריא/מאגר מקומי יש להביא מילה במילה במירכאות ("...").
2. שמור על הניקוד המקורי כפי שנשלף מספריא.
3. ציין תמיד בצמוד לכל ציטוט את מראה המקום המדויק.

סדר התשובה:
1. הגדרת המקרה והשאלה
2. יסוד הסוגיה במקורות
3. שיטות הראשונים
4. פסיקת השולחן ערוך והנושאי כלים
5. שו"תים ופוסקי זמננו
6. מסקנה הלכתית למעשה
"""

def analyze_sugya(messages_history):
    try:
        last_prompt = messages_history[-1]["content"]
        retrieved_context = retrieve_all_context(last_prompt)
        
        generation_config = {
            "temperature": 0.0,
            "top_p": 0.8,
        }
        
        # שימוש במודל היציב
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash',
            system_instruction=SYSTEM_PROMPT,
            generation_config=generation_config
        )

        formatted_history = []
        for msg in messages_history[:-1]:
            role = "user" if msg["role"] == "user" else "model"
            formatted_history.append({"role": role, "parts": [msg["content"]]})

        chat = model.start_chat(history=formatted_history)

        prompt_with_context = f"""
מקורות שנשלפו:
{retrieved_context}

שאלה לניתוח: {last_prompt}
"""
        response = chat.send_message(prompt_with_context)
        return response.text

    except Exception as e:
        st.error(f"שגיאה בהפעלת המודל: {str(e)}")
        return None

# 6. ממשק המשתמש והצגת ההיסטוריה
st.title("📜 סוגיה בעיון")
st.caption("מנוע בינה מלאכותית לניתוח סוגיות הלכתיות ולמדניות")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("הכנס שאלה או סוגיה בעיון..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.status("יהונתן מעיין בסוגיה ומריץ חיפוש במקורות...", expanded=True) as status:
            st.write("🔍 מריץ חיפוש בראש וכל התורה כולה לנגד עיניו...")
            st.write("📚 מקבץ שו\"תים ומקורות מספריא...")
            answer = analyze_sugya(st.session_state.messages)
            if answer:
                status.update(label="יהונתן מצא פתרון!", state="complete", expanded=False)
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
            else:
                status.update(label="התרחשה שגיאה בעת ניתוח הסוגיה", state="error")
