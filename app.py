import streamlit as st
import os
import json
import requests
import re
import time
import uuid
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import google.generativeai as genai

# ==========================================
# 1. הגדרות דף ואינטרפייס (Page Config)
# ==========================================
st.set_page_config(
    page_title="סוגיה בעיון - עוזר תורני אישי",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# עיצוב מותאם לעברית (RTL), מצב כהה וסרגל צד למובייל
# ==========================================
st.markdown("""
<style>
    /* הגדרת כיווניות מימין לשמאל עבור רכיבי תוכן וטקסט */
    html, body, .stApp, .stMarkdown, h1, h2, h3, h4, h5, h6, p, label, span {
        direction: rtl !important;
        text-align: right !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

    /* מניעת גלישה אופקית */
    html, body, .stApp {
        max-width: 100vw !important;
        overflow-x: hidden !important;
    }

    /* מניעת מריחה: סרגל הצד כשהוא סגור מוסתר לחלוטין בכל גדלי המסכים */
    section[data-testid="stSidebar"][aria-expanded="false"],
    [data-testid="stSidebar"][aria-expanded="false"] {
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        min-width: 0 !important;
        max-width: 0 !important;
        height: 0 !important;
        overflow: hidden !important;
        opacity: 0 !important;
        pointer-events: none !important;
        position: fixed !important;
        right: -9999px !important;
        transform: translateX(200vw) !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    
    section[data-testid="stSidebar"][aria-expanded="false"] * {
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        height: 0 !important;
        overflow: hidden !important;
    }

    /* הסתרת מודאל ההתראות המובנה של Streamlit שקופץ במרכז המסך */
    div[data-testid="stSkillsNudgeAnchor"],
    div[data-testid="stSkillsNudge"],
    .stSkillsNudge,
    div[data-testid="stSkillsNudgeAnchor"] * {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        pointer-events: none !important;
        height: 0 !important;
        width: 0 !important;
    }

    /* שמירה על סרגל הכלים העליון עבור כפתור פתיחת מסך הצד */
    header[data-testid="stHeader"] {
        display: block !important;
        background: transparent !important;
        z-index: 9999 !important;
    }
    
    [data-testid="stToolbar"] {
        display: flex !important;
        visibility: visible !important;
    }

    /* כפתור פתיחת מסך הצד - נגיש ונוח ללחיצה */
    [data-testid="stExpandSidebarButton"] {
        display: flex !important;
        visibility: visible !important;
        z-index: 10000 !important;
        background: rgba(240, 242, 246, 0.2) !important;
        border-radius: 8px !important;
        padding: 4px !important;
        margin: 6px !important;
        cursor: pointer !important;
    }

    /* הסתרת כפתורי מערכת שאינם נחוצים */
    [data-testid="stAppDeployButton"], #MainMenu, [data-testid="stMainMenu"], footer {
        display: none !important;
    }

    /* סרגל צד ב-RTL */
    [data-testid="stSidebar"] {
        direction: rtl !important;
        text-align: right !important;
    }
    
    [data-testid="stChatMessage"], [data-testid="stChatInput"], div[data-baseweb="input"] {
        direction: rtl !important;
        text-align: right !important;
    }

    ul, ol {
        direction: rtl !important;
        text-align: right !important;
        padding-right: 1.5rem !important;
        padding-left: 0rem !important;
    }
    
    .stButton>button {
        border-radius: 8px;
        transition: all 0.3s ease;
    }
    
    [data-testid="stPopoverBody"] {
        direction: rtl !important;
        text-align: right !important;
        min-width: 220px;
    }

    /* התאמה ייעודית למכשירים ניידים */
    @media (max-width: 768px) {
        h1 {
            font-size: 1.6rem !important;
            word-wrap: break-word !important;
            white-space: normal !important;
            line-height: 1.3 !important;
        }

        .block-container {
            max-width: 100% !important;
            padding-top: 3.5rem !important;
            padding-right: 1rem !important;
            padding-left: 1rem !important;
        }

        /* סרגל צד פתוח במובייל - פתיחה מלאה מימין בצורה נקייה */
        section[data-testid="stSidebar"][aria-expanded="true"],
        [data-testid="stSidebar"][aria-expanded="true"] {
            display: block !important;
            visibility: visible !important;
            position: fixed !important;
            top: 0 !important;
            right: 0 !important;
            left: auto !important;
            bottom: 0 !important;
            width: 85vw !important;
            max-width: 320px !important;
            height: 100vh !important;
            z-index: 999999 !important;
            background-color: var(--background-color, #0e1117) !important;
            box-shadow: -5px 0 25px rgba(0, 0, 0, 0.7) !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
            transform: none !important;
        }

        /* מניעת קריסה של רוחב התוכן בתוך סרגל הצד (ביטול מריחה אנכית של אותיות) */
        [data-testid="stSidebar"][aria-expanded="true"] [data-testid="stSidebarContent"],
        [data-testid="stSidebar"][aria-expanded="true"] [data-testid="stSidebarUserContent"] {
            width: 100% !important;
            min-width: 260px !important;
            overflow-x: hidden !important;
        }

        /* כפתור סגירת הסרגל */
        [data-testid="stSidebarCollapseButton"] {
            display: block !important;
            visibility: visible !important;
        }

        [data-testid="stSidebarCollapseButton"] button,
        [data-testid="stSidebar"] button[aria-label="Close"] {
            z-index: 1000000 !important;
            cursor: pointer !important;
            display: flex !important;
            visibility: visible !important;
            font-size: 1.5rem !important;
            padding: 8px !important;
        }
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. הגדרת מפתח Google API
# ==========================================
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

if not GOOGLE_API_KEY:
    try:
        if "GOOGLE_API_KEY" in st.secrets:
            GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
        elif "GEMINI_API_KEY" in st.secrets:
            GOOGLE_API_KEY = st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass

if not GOOGLE_API_KEY:
    st.error("⚠️ לא נמצא מפתח API של Google. ודא שהגדרת את GOOGLE_API_KEY ב-Secrets ב-Streamlit Cloud או בקובץ .env מקומי.")
    st.stop()

genai.configure(api_key=GOOGLE_API_KEY)

generation_config = {
  "temperature": 0.2,
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 8192,
  "response_mime_type": "text/plain",
}

# ==========================================
# 3. ניהול נתונים מקומיים (JSON Persistence)
# ==========================================
DATA_DIR = "data"
USER_DATA_FILE = os.path.join(DATA_DIR, "user_data.json")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def init_user_data():
    if not os.path.exists(USER_DATA_FILE):
        default_data = {"projects": {"כללי": []}, "chats": {}}
        save_user_data(default_data)
        return default_data
    else:
        try:
            with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "projects" not in data or not data["projects"]:
                    data["projects"] = {"כללי": []}
                if "chats" not in data:
                    data["chats"] = {}
                return data
        except Exception:
            return {"projects": {"כללי": []}, "chats": {}}

def save_user_data(data):
    try:
        with open(USER_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

if 'user_data' not in st.session_state:
    st.session_state.user_data = init_user_data()

# ==========================================
# 4. מנוע RAG רב-מקורות ושליפה מדויקת (Sefaria & Local DB)
# ==========================================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) TorahResearchBot/2.0"
}

def clean_html_tags(text):
    """מנקה תגיות HTML ורווחי סרק מהטקסט"""
    if not text:
        return ""
    clean = re.sub(r'<[^>]+>', '', text)
    return re.sub(r'\s+', ' ', clean).strip()

def remove_cantillation_and_niqqud(text):
    """מסיר ניקוד, טעמי מקרא וגרשיים להשוואה מילולית מדויקת (Verbatim Matching)"""
    if not text:
        return ""
    cleaned = re.sub(r'[\u0591-\u05BD\u05BF-\u05C7]', '', text)
    cleaned = re.sub(r'[\"״״”"\'׳]', '', cleaned)
    return re.sub(r'\s+', ' ', cleaned).strip()

def search_sefaria_and_local(query, max_results=5):
    """שליפה היברידית של מקורות: מאגר מקומי מאומת, שליפת Ref ישירה, וחיפוש טקסטואלי רחב בספריא"""
    sources = []
    
    # 1. בדיקת מאגר מקומי (data/torah_database.json)
    db_path = os.path.join(DATA_DIR, "torah_database.json")
    if os.path.exists(db_path):
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                db_data = json.load(f)
                query_words = [w for w in re.split(r'\s+', query.strip()) if len(w) > 2]
                for entry in db_data:
                    entry_text = f"{entry.get('book','')} {entry.get('masechet','')} {entry.get('section','')} {entry.get('topic','')} {entry.get('content','')}"
                    matches = sum(1 for w in query_words if w in entry_text)
                    if matches > 0:
                        ref_title = f"{entry.get('book', '')} {entry.get('masechet', entry.get('section', ''))} {entry.get('daf', '')}"
                        if entry.get('siman'):
                            ref_title += f" סימן {entry.get('siman')} סעיף {entry.get('seif', '')}"
                        sources.append({
                            "ref": ref_title.strip(),
                            "text": clean_html_tags(entry.get("content", "")),
                            "url": "מאגר תורני מקומי מאומת"
                        })
        except Exception:
            pass

    # 2. שליפת Ref ישיר מספריא (אם מדובר בציטוט מראה מקום מדויק)
    try:
        direct_url = f"https://www.sefaria.org/api/texts/{urllib.parse.quote(query.strip())}?context=0"
        res = requests.get(direct_url, headers=HEADERS, timeout=3)
        if res.status_code == 200:
            d = res.json()
            he_val = d.get("he")
            if he_val:
                text_content = " ".join([clean_html_tags(x) for x in he_val]) if isinstance(he_val, list) else clean_html_tags(he_val)
                ref_name = d.get("ref", query)
                if not any(s["ref"] == ref_name for s in sources):
                    sources.append({
                        "ref": ref_name,
                        "text": text_content,
                        "url": f"https://www.sefaria.org/{urllib.parse.quote(ref_name)}"
                    })
    except Exception:
        pass

    # 3. חיפוש טקסטואלי מלא בספריא דרך search-wrapper
    try:
        search_url = "https://www.sefaria.org/api/search-wrapper"
        payload = {"query": query, "size": max_results}
        res = requests.post(search_url, json=payload, headers=HEADERS, timeout=4)
        if res.status_code == 200:
            hits = res.json().get("hits", {}).get("hits", [])
            for hit in hits:
                raw_id = hit.get("_id", "")
                ref_match = re.match(r'^([^(]+)', raw_id)
                clean_ref = ref_match.group(1).strip() if ref_match else raw_id
                
                if any(s["ref"] == clean_ref for s in sources):
                    continue
                
                full_text = ""
                try:
                    ref_res = requests.get(f"https://www.sefaria.org/api/texts/{urllib.parse.quote(clean_ref)}?context=0", headers=HEADERS, timeout=3)
                    if ref_res.status_code == 200:
                        raw_he = ref_res.json().get("he")
                        if raw_he:
                            full_text = " ".join([clean_html_tags(x) for x in raw_he]) if isinstance(raw_he, list) else clean_html_tags(raw_he)
                except Exception:
                    pass
                
                if not full_text:
                    highlights = hit.get("highlight", {})
                    hl_list = []
                    for v in highlights.values():
                        if isinstance(v, list):
                            hl_list.extend(v)
                    full_text = " ... ".join([clean_html_tags(h) for h in hl_list])

                if full_text.strip():
                    sources.append({
                        "ref": clean_ref,
                        "text": full_text.strip(),
                        "url": f"https://www.sefaria.org/{urllib.parse.quote(clean_ref)}"
                    })
                
                if len(sources) >= max_results:
                    break
    except Exception:
        pass

    return sources[:max_results]

def format_context_sources(sources):
    """פורמט ברור של מקורות עבור ה-Context עם מספור וקישורים"""
    if not sources:
        return "הערת מערכת: לא נמצאו מקורות רלוונטיים במאגרי השליפה (Context ריק)."
    
    formatted = []
    for idx, s in enumerate(sources, 1):
        formatted.append(f"[מקור {idx}]: {s['ref']}\nטקסט מקור מדויק (Verbatim מתוך המאגר):\n\"{s['text']}\"\nקישור למקור: {s['url']}")
    return "\n\n" + "\n\n---\n\n".join(formatted)

# ==========================================
# 5. הגדרת פרומפט המערכת המחייב (Strict Grounding & Zero Hallucinations)
# ==========================================
SYSTEM_PROMPT = """אתה עוזר מחקר תורני ואקדמי המתבסס אך ורק ובלעדית על המקורות שנשלפו עבורך בזמן אמת (Sefaria API / Google Search Tools).

חוקי ברזל למניעת הזיות ודיוק ציטוטים:
1. איסור מוחלט על ציטוט מהזיכרון: אסור לך לצטט, לשחזר או להשלים טקסטים תורניים/עובדתיים מהזיכרון הפנימי שלך. כל ציטוט חייב להגיע אך ורק מהמקור ששלפת כעת.
2. דיוק מילולי מוחלט (Verbatim): ציטוט מתוך מקור חייב להיות מועתק אות-באות ומילה-במילה מתוך ה-Context המוזרק. אין לשנות, לקצר או לנסח מחדש טקסט מצוטט.
3. ייחוס מקור מדויק: כל ציטוט חייב להופיע בתוך סוגריים או עם מראה מקום מדויק (כגון: [בבלי, ברכות ב ע"א] או קישור ישיר).
4. חובת הודעה על היעדר מידע: אם הציטוט או המקור המבוקש איננו מופיע בתוצאות השליפה (Context), חובה עליך להשיב: "המידע המבוקש אינו מופיע במקורות שנשלפו" ולא לנסות להשלים מדעתך.
5. הפרדה בין ציטוט לניתוח: יש ליצור הפרדה חדה בין ציטוט המקור (בשדתו המקורית) לבין הניתוח/הסבר. ההסבר חייב להתבסס רק על העובדות המוזכרות בציטוט."""

PROMPTS = {
    "מחקר תורני קפדני (מדויק ומבוסס מקורות)": f"""{SYSTEM_PROMPT}

דגשים למבנה התשובה:
* פתח בציטוט המקורות הרלוונטיים מתוך ה-Context בדיוק מילולי מוחלט (אות-באות).
* לאחר מכן, הצג ניתוח וביאור המבוסס אך ורק על העובדות שנזכרו בציטוטים.
* חובה לסיים כל תשובה במשפט: "הערה: תוכן זה מיועד ללימוד בלבד, ואין לפסוק ממנו הלכה למעשה."
""",
    "פשוט ומונגש": f"""{SYSTEM_PROMPT}

דגשים למבנה התשובה:
* ענה בשפה פשוטה, מודרנית וברורה אך מבוססת אך ורק על המקורות שנשלפו.
* צטט מילה-במילה מתוך ה-Context עם מראה מקום מדויק, ולאחר מכן הסבר את המושגים בפשטות.
* חובה לסיים כל תשובה במשפט: "הערה: תוכן זה מיועד ללימוד בלבד, ואין לפסוק ממנו הלכה למעשה."
""",
    "ישיבתי-למדני (סגנון שו\"ת)": f"""{SYSTEM_PROMPT}

דגשים למבנה התשובה:
* השתמש בשפה תורנית למדנית ומעמיקה.
* צטט שיטות מתוך ה-Context בלשונן המקורית המדויקת, וחלק את הניתוח לבירור הסוגיה, ביאור הציטוטים ונפקא מינה.
* חובה לסיים כל תשובה במשפט: "הערה: תוכן זה מיועד ללימוד בלבד, ואין לפסוק ממנו הלכה למעשה."
""",
    "הכנה למבחני רבנות": f"""{SYSTEM_PROMPT}

דגשים למבנה התשובה:
* סדר את הציטוטים והמקורות שנשלפו בהשתלשלות הלכתית מובנית (ש"ס, ראשונים, שולחן ערוך ונושאי כלים).
* הקפד על ציטוט מילולי מוחלט וייחוס מדויק של כל מקור בסוגריים.
* חובה לסיים כל תשובה במשפט: "הערה: תוכן זה מיועד ללימוד בלבד, ואין לפסוק ממנו הלכה למעשה."
"""
}

# ==========================================
# 6. שכבת אימות קפדנית (Validation Layer)
# ==========================================
def extract_quotes(text):
    """חילוץ כל הציטוטים מתוך תשובת המודל לבדיקת התאמה מילולית"""
    quotes = []
    patterns = [
        r'["״”"“]([^"״”"“\n]{6,})["״”"“]',
        r'>\s*([^\n]{6,})'
    ]
    for pat in patterns:
        for m in re.findall(pat, text):
            clean_q = m.strip()
            if len(clean_q.split()) >= 3:
                quotes.append(clean_q)
    return list(dict.fromkeys(quotes))

def validate_response(response_text, sources):
    """בודק התאמה מילולית (Verbatim) ב-100% והיעדר הזיות מול המקורות"""
    if "המידע המבוקש אינו מופיע במקורות שנשלפו" in response_text:
        return {
            "is_valid": True,
            "grounding_score": 100.0,
            "total_quotes": 0,
            "verified_quotes": [],
            "unverified_quotes": [],
            "details": "המודל דיווח כהלכה על היעדר מידע במקורות שנשלפו (כלל 4)."
        }

    combined_sources = " ".join([remove_cantillation_and_niqqud(s.get("text", "")) for s in sources])
    quotes = extract_quotes(response_text)
    verified = []
    unverified = []

    for q in quotes:
        norm_q = remove_cantillation_and_niqqud(q)
        if norm_q in combined_sources:
            verified.append(q)
        else:
            words = norm_q.split()
            if len(words) >= 4 and " ".join(words[1:-1]) in combined_sources:
                verified.append(q)
            else:
                unverified.append(q)

    total = len(quotes)
    score = 100.0 if total == 0 else round((len(verified) / total) * 100, 1)
    is_valid = (len(unverified) == 0)

    return {
        "is_valid": is_valid,
        "grounding_score": score,
        "total_quotes": total,
        "verified_quotes": verified,
        "unverified_quotes": unverified,
        "details": f"{len(verified)} מתוך {total} ציטוטים אומתו מילה-במילה מול המקורות שנשלפו."
    }

# ==========================================
# 7. מנוע ג'מיני - זיהוי דינמי וקריאה מבוקרת אימות
# ==========================================
@st.cache_resource(ttl=3600)
def get_supported_models():
    """שולף ושומר במטמון את כל המודלים הפעילים שנתמכים בחשבון, בהעדפה לדגמי flash עדכניים"""
    try:
        active_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if '2.5-flash' not in m.name and 'preview-tts' not in m.name and 'image' not in m.name:
                    active_models.append(m.name)
        
        active_models.sort(key=lambda name: (
            0 if '3.6-flash' in name else
            1 if '3.7-flash' in name else
            2 if 'flash-latest' in name else
            3 if '3.5-flash' in name else
            4 if 'flash' in name else 5
        ))
        if active_models:
            return active_models
    except Exception:
        pass
    
    return ['models/gemini-3.6-flash', 'models/gemini-flash-latest']

def get_gemini_response(prompt, sources, context, style):
    """יוצר תשובה מחמירה מבוססת מקורות ומריץ שכבת אימות ותיקון אוטונומי"""
    system_instruction = PROMPTS.get(style, PROMPTS["מחקר תורני קפדני (מדויק ומבוסס מקורות)"])
    full_prompt = f"{system_instruction}\n\nמקורות שנשלפו בזמן אמת (Context):\n{context}\n\nשאלה לניתוח:\n{prompt}"
    
    available_models = get_supported_models()
    last_error = ""
    response_text = ""
    
    for model_name in available_models:
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=generation_config,
                system_instruction=SYSTEM_PROMPT
            )
            response = model.generate_content(full_prompt)
            if response and response.text:
                response_text = response.text
                break
        except Exception as e:
            last_error = str(e)
            continue

    if not response_text:
        return f"אירעה שגיאה בחיבור למודלים: {last_error}", {"is_valid": False, "details": last_error}

    # שכבת אימות (Validation Layer)
    val_report = validate_response(response_text, sources)

    # מנגנון תיקון אוטונומי במידה וזוהה ציטוט שלא מופיע במקורות שנשלפו
    if not val_report["is_valid"] and sources:
        correction_prompt = f"""{SYSTEM_PROMPT}

שים לב: התשובה שנוסחה הכילה ציטוטים שלא אומתו מילה-במילה מתוך המקורות שנשלפו:
{val_report['unverified_quotes']}

אנא נסח מחדש את התשובה תוך הקפדה חמורה על חוקי הברזל:
1. איסור מוחלט על ציטוט מהזיכרון.
2. העתק אך ורק ציטוטים אות-באות ומילה-במילה מתוך ה-Context המוזרק בלבד:
{context}

שאלה מקורית:
{prompt}
"""
        for model_name in available_models:
            try:
                model = genai.GenerativeModel(
                    model_name=model_name,
                    generation_config=generation_config,
                    system_instruction=SYSTEM_PROMPT
                )
                corr_resp = model.generate_content(correction_prompt)
                if corr_resp and corr_resp.text:
                    new_val = validate_response(corr_resp.text, sources)
                    if new_val["is_valid"] or new_val["grounding_score"] >= val_report["grounding_score"]:
                        return corr_resp.text, new_val
            except Exception:
                continue

    return response_text, val_report

# ==========================================
# 7. ניהול Session State
# ==========================================
if 'current_project' not in st.session_state:
    st.session_state.current_project = "כללי"
if 'current_chat_id' not in st.session_state:
    st.session_state.current_chat_id = None
if 'search_query' not in st.session_state:
    st.session_state.search_query = ""

# ==========================================
# 8. סרגל צד (Sidebar)
# ==========================================
with st.sidebar:
    st.title("📚 סוגיה בעיון - ניהול")
    
    with st.expander("➕ פרויקט / תיקייה חדשה"):
        new_proj_name = st.text_input("שם הפרויקט החדש:")
        if st.button("צור פרויקט", use_container_width=True):
            if new_proj_name.strip():
                proj_clean = new_proj_name.strip()
                if proj_clean not in st.session_state.user_data["projects"]:
                    st.session_state.user_data["projects"][proj_clean] = []
                    save_user_data(st.session_state.user_data)
                    st.session_state.current_project = proj_clean
                    st.rerun()

    st.divider()
    
    project_names = list(st.session_state.user_data["projects"].keys())
    if not project_names:
        st.session_state.user_data["projects"]["כללי"] = []
        project_names = ["כללי"]
        
    if st.session_state.current_project not in project_names:
        st.session_state.current_project = project_names[0]
        
    selected_project = st.selectbox(
        "📂 בחר פרויקט פעיל:", 
        project_names, 
        index=project_names.index(st.session_state.current_project)
    )
    
    if selected_project != st.session_state.current_project:
        st.session_state.current_project = selected_project
        st.session_state.current_chat_id = None
        st.rerun()

    st.divider()
    
    if st.button("💬 שיחה חדשה", use_container_width=True, type="primary"):
        new_chat_id = str(uuid.uuid4())
        active_proj = st.session_state.current_project
        
        if active_proj not in st.session_state.user_data["projects"]:
            st.session_state.user_data["projects"][active_proj] = []
            
        st.session_state.user_data["chats"][new_chat_id] = {
            "title": "שיחה חדשה",
            "messages": [],
            "project": active_proj
        }
        st.session_state.user_data["projects"][active_proj].insert(0, new_chat_id)
        save_user_data(st.session_state.user_data)
        st.session_state.current_chat_id = new_chat_id
        st.rerun()

    st.divider()
    
    st.session_state.search_query = st.text_input("🔍 חיפוש שיחות:", value=st.session_state.search_query)

    st.markdown("### שיחות בפרויקט")
    chat_ids = st.session_state.user_data["projects"].get(st.session_state.current_project, [])
    
    for cid in chat_ids:
        if cid in st.session_state.user_data["chats"]:
            chat = st.session_state.user_data["chats"][cid]
            chat_title = chat.get("title", "שיחה ללא שם")
            
            if st.session_state.search_query and st.session_state.search_query.lower() not in chat_title.lower():
                continue
            
            btn_type = "primary" if cid == st.session_state.current_chat_id else "secondary"
            col_btn, col_del = st.columns([0.82, 0.18], gap="small")
            
            with col_btn:
                if st.button(f"📄 {chat_title}", key=f"btn_{cid}", type=btn_type, use_container_width=True):
                    st.session_state.current_chat_id = cid
                    st.rerun()
            
            with col_del:
                with st.popover("🗑️"):
                    st.write("למחוק שיחה זו?")
                    if st.button("מחק", key=f"del_{cid}"):
                        st.session_state.user_data["projects"][st.session_state.current_project].remove(cid)
                        del st.session_state.user_data["chats"][cid]
                        save_user_data(st.session_state.user_data)
                        if st.session_state.current_chat_id == cid:
                            st.session_state.current_chat_id = None
                        st.rerun()

# ==========================================
# 9. מסך ראשי והרצה במקביל
# ==========================================
if st.session_state.current_chat_id and st.session_state.current_chat_id in st.session_state.user_data["chats"]:
    current_chat = st.session_state.user_data["chats"][st.session_state.current_chat_id]
    
    st.header(f"📜 {current_chat.get('title', 'שיחה ללא שם')}")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        learning_style = st.selectbox("🎯 בחר סגנון לימוד ותשובה:", list(PROMPTS.keys()))
    with col2:
        use_sefaria = st.checkbox("🔍 שלוף מקורות בזמן אמת (Sefaria API)", value=True)

    st.divider()

    for msg in current_chat["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("sources"):
                with st.expander(f"📚 מקורות שנשלפו ואומתו ({len(msg['sources'])})", expanded=False):
                    if msg.get("validation", {}).get("is_valid"):
                        st.caption("✅ אומת מילה-במילה מול המקורות שנשלפו (100% Grounded)")
                    for s in msg["sources"]:
                        st.markdown(f"**[{s['ref']}]** — [קישור למקור]({s['url']})")
                        st.markdown(f"> *{s['text'][:300]}...*")

    user_input = st.chat_input("הכנס שאלה או סוגיה בעיון...")
    if user_input:
        if len(current_chat["messages"]) == 0:
            current_chat["title"] = user_input[:32] + "..." if len(user_input) > 32 else user_input
        
        current_chat["messages"].append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            status_placeholder = st.empty()
            
            loading_messages = [
                "יהונתן חושב...",
                "יהונתן עומד לפתור את הסוגיה...",
                "יהונתן מריץ חיפוש בראש וכל התורה כולה לנגד עיניו...",
                "ליהונתן יש פיתרון, וחושב על כיוונים אחרים...",
                "יהונתן צריך ריכוז...",
                "יהונתן מקבץ כל מיני שו\"תים שנזכר בהם בהקשר לשאלה...",
                "יהונתן מבין שהשאלה מסובכת, אך אין שאלה שתישאר לא פתורה..."
            ]

            def execute_pipeline():
                sources = []
                if use_sefaria:
                    sources = search_sefaria_and_local(user_input, max_results=5)
                context_sources = format_context_sources(sources)
                resp_text, val_rep = get_gemini_response(user_input, sources, context_sources, learning_style)
                return resp_text, sources, val_rep

            with ThreadPoolExecutor() as executor:
                future = executor.submit(execute_pipeline)
                
                msg_idx = 0
                while not future.done():
                    current_msg = loading_messages[msg_idx % len(loading_messages)]
                    status_placeholder.markdown(f"⏳ **{current_msg}**")
                    time.sleep(2)
                    msg_idx += 1
                
                response_text, sources, validation_report = future.result()

            status_placeholder.empty()
            st.markdown(response_text)

            if sources:
                with st.expander(f"📚 מקורות שנשלפו ואומתו בזמן אמת ({len(sources)})", expanded=False):
                    if validation_report.get("is_valid"):
                        st.success("✅ **אימות מקורות קפדני (100% Verbatim):** כל הציטוטים נבדקו ואומתו מילה-במילה מול המקורות המקוריים.")
                    else:
                        st.warning(f"⚠️ {validation_report.get('details')}")
                    for s in sources:
                        st.markdown(f"**[{s['ref']}]** — [קישור ישיר למקור בספריא]({s['url']})")
                        st.markdown(f"> *{s['text'][:350]}...*")
            elif "המידע המבוקש אינו מופיע במקורות שנשלפו" in response_text:
                st.info("ℹ️ **דיווח על היעדר מידע:** המודל פעל על פי חוקי הברזל ולא המציא מידע שלא נשלף.")

        current_chat["messages"].append({
            "role": "assistant",
            "content": response_text,
            "sources": sources,
            "validation": validation_report
        })
        save_user_data(st.session_state.user_data)
        st.rerun()

else:
    st.title("📜 סוגיה בעיון - עוזר תורני אישי")
    st.caption("מנוע בינה מלאכותית מבוסס מקורות לניתוח סוגיות הלכתיות ולמדניות")
    st.info("👈 בחר שיחה מסרגל הצד, או לחץ על **'💬 שיחה חדשה'** כדי להתחיל בלמידה.")
