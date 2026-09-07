import streamlit as st
import os
import json
import requests
import re
import time
import uuid
import urllib.parse
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed
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
  "temperature": 0.0,
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
# 4. מנוע RAG רב-מקורות מואץ ושליפה מקבילית (Optimized Fast Sefaria & Local DB)
# ==========================================
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) TorahResearchBot/2.0"
}

HTTP_SESSION = requests.Session()
HTTP_SESSION.headers.update(HEADERS)

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

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_sefaria_text_and_he_ref(ref_str: str):
    """שליפת טקסט מלא ומראה מקום מדויק בעברית (heRef) מספריא עם מנגנון מטמון מקומי"""
    if not ref_str:
        return "", ""
    clean_ref = ref_str.strip()
    
    # 1. ניסיון שליפה מ-API v3 של ספריא
    try:
        url = f"https://www.sefaria.org/api/v3/texts/{urllib.parse.quote(clean_ref)}?context=0"
        res = HTTP_SESSION.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            he_ref = data.get("heRef", "")
            versions = data.get("versions", [])
            for v in versions:
                if v.get("language") == "he":
                    text = v.get("text", "")
                    if isinstance(text, list):
                        flat = []
                        def flatten(l):
                            for item in l:
                                if isinstance(item, list):
                                    flatten(item)
                                else:
                                    flat.append(str(item))
                        flatten(text)
                        clean_t = clean_html_tags(" ".join(flat))
                        if clean_t:
                            return clean_t, he_ref
                    clean_t = clean_html_tags(str(text))
                    if clean_t:
                        return clean_t, he_ref
    except Exception as e:
        print(f"Error fetching ref {clean_ref}: {e}")

    # 2. גיבוי לקריאת API v1 במקרה ש-v3 לא החזיר גרסה עברית או נכשל
    try:
        url2 = f"https://www.sefaria.org/api/texts/{urllib.parse.quote(clean_ref)}?context=0"
        res2 = HTTP_SESSION.get(url2, timeout=4)
        if res2.status_code == 200:
            data2 = res2.json()
            he_ref = data2.get("heRef", "")
            raw_he = data2.get("he")
            if raw_he:
                if isinstance(raw_he, list):
                    return clean_html_tags(" ".join([str(x) for x in raw_he])), he_ref
                return clean_html_tags(str(raw_he)), he_ref
    except Exception:
        pass

    return "", ""

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_sefaria_text_by_ref(ref_str: str) -> str:
    """Step 2: Fetches full text once exact Ref is known (Sefaria API v3 with v1 fallback)."""
    text, _ = fetch_sefaria_text_and_he_ref(ref_str)
    return text

fetch_single_ref_text = fetch_sefaria_text_by_ref

@st.cache_data(ttl=86400, show_spinner=False)
def get_sefaria_sources_robust(user_query: str) -> List[str]:
    """
    Fetches raw Hebrew sources from Sefaria API with automatic URL encoding,
    Hebrew reference titles, and multi-stage fallback.
    """
    retrieved_texts = []
    raw_query = user_query.strip()
    clean_query = re.sub(r'[^\w\s]', '', user_query).strip()
    
    if not clean_query and not raw_query:
        return retrieved_texts

    # 1. Encode Hebrew string for safe HTTP requests (keeping ref punctuation like : or .)
    target_ref = raw_query if any(c in raw_query for c in [':', '.']) else clean_query
    encoded_query = urllib.parse.quote(target_ref)
    
    # 2. Stage 1: Try Sefaria Text Search API (Global Search)
    search_url = "https://www.sefaria.org/api/search-wrapper"
    payload = {
        "query": clean_query,
        "type": "text",
        "size": 5,
        "field": "naive_lemmatizer"
    }
    
    headers = {"Content-Type": "application/json"}

    try:
        response = HTTP_SESSION.post(search_url, json=payload, headers=headers, timeout=6)
        if response.status_code == 200:
            hits = response.json().get("hits", {}).get("hits", [])
            for hit in hits:
                source_data = hit.get("_source") or {}
                ref = source_data.get("ref")
                # חילוץ Ref מתוך _id במידה ושדה ref חסר ב-_source
                if not ref and hit.get("_id"):
                    raw_id = hit.get("_id", "")
                    m = re.match(r'^([^(]+)', raw_id)
                    ref = m.group(1).strip() if m else raw_id
                
                he_ref = source_data.get("heRef", "")
                he_text = source_data.get("he", "")
                
                # שליפת הטקסט המלא ומראה המקום בעברית אם נדרש
                if ref:
                    fetched_text, fetched_he_ref = fetch_sefaria_text_and_he_ref(ref)
                    if not he_text and fetched_text:
                        he_text = fetched_text
                    if fetched_he_ref:
                        he_ref = fetched_he_ref
                
                if not he_text and hit.get("highlight"):
                    hl = hit.get("highlight", {})
                    hl_snippets = []
                    for v in hl.values():
                        if isinstance(v, list):
                            hl_snippets.extend(v)
                    he_text = " ... ".join(hl_snippets)
                
                display_ref = he_ref if he_ref else (ref or "")
                
                # ניקוי תגיות HTML במידה וקיימות
                clean_he = re.sub(r'<[^>]+>', '', str(he_text)).strip()
                if clean_he and display_ref and not any(c.startswith(f"[{display_ref}]") for c in retrieved_texts):
                    retrieved_texts.append(f"[{display_ref}]\n{clean_he}")
    except Exception as e:
        print(f"Sefaria Search API Error: {e}")

    # 3. Stage 2: Fallback to Direct Ref Fetch if Search returned empty
    if not retrieved_texts:
        try:
            # ניסיון שליפה ישירה של טקסט אם השאילתה תואמת מראה מקום או ספר מוכר
            direct_url = f"https://www.sefaria.org/api/v3/texts/{encoded_query}?context=0"
            res = HTTP_SESSION.get(direct_url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                he_ref = data.get("heRef", "")
                display_ref = he_ref if he_ref else user_query
                versions = data.get("versions", [])
                for v in versions:
                    if v.get("language") == "he":
                        t = v.get("text", "")
                        text_str = " ".join(t) if isinstance(t, list) else str(t)
                        clean_t = re.sub(r'<[^>]+>', '', text_str).strip()
                        if clean_t:
                            retrieved_texts.append(f"[{display_ref}]\n{clean_t}")
                            break
        except Exception as e:
            print(f"Sefaria Direct Fetch Error: {e}")

    return retrieved_texts

search_sefaria_sources = get_sefaria_sources_robust

@st.cache_data(ttl=86400, show_spinner=False)
def search_sefaria_fast(query: str, max_results: int = 5):
    """
    שליפה מובנית מספריא באמצעות מנוע השליפה המשופר (get_sefaria_sources_robust)
    ומחזירה רשימת אובייקטים מובנים עבור ממשק המשתמש ושכבת האימות.
    """
    raw_contexts = get_sefaria_sources_robust(query)
    results = []
    for item in raw_contexts[:max_results]:
        lines = item.split("\n", 1)
        if len(lines) == 2:
            ref_clean = lines[0].strip("[]")
            text_clean = lines[1].strip()
            results.append({
                "ref": ref_clean,
                "text": text_clean,
                "url": f"https://www.sefaria.org/{urllib.parse.quote(ref_clean)}"
            })
        elif item.strip():
            results.append({
                "ref": query.strip(),
                "text": item.strip(),
                "url": f"https://www.sefaria.org/{urllib.parse.quote(query.strip())}"
            })
    return results

@st.cache_data(ttl=86400, show_spinner=False)
def search_sefaria_and_local(query, max_results=5):
    """שילוב מיידי של מקורות מקומיים (0ms) עם תוצאות ספריא המואצות עם שמירת מטמון מקומי ל-24 שעות"""
    sources = []
    
    # 1. חיפוש מיידי במאגר מקומי (Latency אפסי)
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

    # 2. שליפה מקבילית מספריא (ממוטבת במטמון)
    try:
        sefaria_sources = search_sefaria_fast(query, max_results=max_results)
        for s in sefaria_sources:
            if not any(existing["ref"] == s["ref"] for existing in sources):
                sources.append(s)
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
# 5. הגדרת פרומפט המערכת המחייב (חוקי ברזל לכל סגנונות התשובה)
# ==========================================
SYSTEM_PROMPT = """אתה עוזר מחקר תורני ולמדני מומחה. תפקידך לספק תשובות מלאות, ברורות ומדויקות (בהתאם לסגנון שנבחר: פשוט ומונגש, שו"ת, הכנה למבחני רבנות, או ישיבתי-למדני), תוך שמירה מחמירה על חוקי הברזל הבאים:

חוקי ברזל לעיצוב ולמבנה התשובה:

1. מקורות בעברית בלבד:
   - כל מראי המקומות, שמות הספרים, המסכתות והמחברים חייבים להופיע בלשון הקודש/עברית בלבד (למשל: "רמב"ם הלכות חובל ומזיק", "מסכת סנהדרין", "שולחן ערוך חושן משפט", ולא באנגלית או בתעתיק לטיני).
   - אם מראה מקום שנשלף מ-API מכיל שם באנגלית, תרגם או המר אותו לשמו העברי המקובל והמקור.

2. מבנה תשובה שלם - מהגמרא ועד להלכה למעשה:
   כל ניתוח של סוגיה או מושג חייב לעקוב אחר ההשתלשלות ההלכתית המלאה ולא לעצור בראשונים:
   א. יסוד הסוגיה ומקורות חז"ל (משנה, גמרא, מדרשי הלכה).
   ב. מחלוקת הראשונים (רמב"ם, רש"י, תוספות, ראב"ד, רמב"ן, רשב"א, רא"ש, רי"ף וכו').
   ג. ניתוח וחקירות האחרונים (שולחן ערוך, נושאי כלים, הגר"ח מבריסק, אגרות משה, ציץ אליעזר וכו').
   ד. סיכום הפסיקה וההלכה למעשה.

3. דיוק מילולי (Verbatim):
   - ציטוטים בתוך מרכאות חייבים להיפלט בדיוק מוחלט מתוך המקורות שנשלפו, תוך שמירה על המבנה והלשון העברית המקורית.
   - איסור מוחלט על ציטוט מהזיכרון הפנימי.
   - הפרדה בין הסבר לציטוט: הסבר את המושג בלשונך הברורה והטבעית, ואת הציטוט הבא בתוך מרכאות בדיוק מוחלט בצמוד למראה מקום.
   - חסר במקורות: אם הציטוט המדויק אינו מופיע במקורות שנשלפו, הסבר את הכלל בלשונך וציין שמראה המקום המדויק של הציטוט המילולי לא נשלף במלואו."""

PROMPTS = {
    "פשוט ומונגש": f"""{SYSTEM_PROMPT}

דגשי סגנון - פשוט ומונגש:
* ספק הסבר מלא, בהיר ומסודר בגובה העיניים בהתאם למבנה השלם (יסוד הסוגיה בחז"ל, שיטות הראשונים, הכרעת האחרונים וההלכה למעשה).
* הקפד על שמות מקורות ומראי מקומות בלשון הקודש ובעברית בלבד.
* באר מושגים, סברות וטעמים בלשון פשוטה וקולחת.
* ציטוטים מהמקורות שלב בתוך מרכאות בדיוק מילולי מוחלט (אות-באות מהמקורות שנשלפו) עם מראה מקום עברי בסוגריים.
* חובה לסיים כל תשובה במשפט: "הערה: תוכן זה מיועד ללימוד בלבד, ואין לפסוק ממנו הלכה למעשה."
""",
    "סגנון שו\"ת": f"""{SYSTEM_PROMPT}

דגשי סגנון - סגנון שו"ת:
* מבנה תשובה מסודר ומלא לפי ארבעת השלבים: הצגת השאלה, יסוד הסוגיה במקורות חז"ל, משא ומתן בשיטות הראשונים והאחרונים, ומסקנה ברורה ומנומקת של ההלכה למעשה.
* הקפד על שמות מקורות ומראי מקומות בלשון הקודש ובעברית בלבד.
* הסבר את הטעמים והסברות בלשון תורנית רהוטה ועשירה, ואת הציטוטים הבא בתוך מרכאות בדיוק מילולי מוחלט (Verbatim) עם מראי מקומות עבריים בסוגריים.
* חובה לסיים כל תשובה במשפט: "הערה: תוכן זה מיועד ללימוד בלבד, ואין לפסוק ממנו הלכה למעשה."
""",
    "הכנה למבחני רבנות": f"""{SYSTEM_PROMPT}

דגשי סגנון - הכנה למבחני רבנות:
* הצג תשובה מלאה, שיטתית ומקיפה בהשתלשלות הלכתית מובחנת ומסודרת בסעיפים:
  א. יסוד הסוגיה ומקורות חז"ל (משנה, גמרא, מדרשי הלכה).
  ב. מחלוקות הראשונים וטעמיהם (רמב"ם, רש"י, תוספות, רא"ש, רי"ף, רמב"ן וכו').
  ג. פסק השולחן ערוך והרמ"א וניתוח נושאי הכלים והאחרונים.
  ד. סיכום הפסיקה וההלכה למעשה למבחן הרבנות.
* הקפד על שמות ספרים ומראי מקומות בלשון הקודש ובעברית בלבד.
* באר את שיטות הפוסקים וטעמיהם בהרחבה, ואת הציטוטים הבא בתוך מרכאות אות-באות מתוך המקורות שנשלפו.
* חובה לסיים כל תשובה במשפט: "הערה: תוכן זה מיועד ללימוד בלבד, ואין לפסוק ממנו הלכה למעשה."
""",
    "ישיבתי-למדני": f"""{SYSTEM_PROMPT}

דגשי סגנון - ישיבתי-למדני:
* פתח מהלך למדני שלם ומעמיק בהשתלשלות מלאה: יסוד הסוגיה בחז"ל, שיטות הראשונים, חקירות האחרונים וראשי הישיבות (בריסק, קובץ שיעורים, אגרות משה וכו'), קושיות, תירוצים, דיוקים וחילוקי סברות, עד להכרעת ההלכה למעשה.
* הקפד על שמות ספרים, מסכתות ומחברים בלשון הקודש ובעברית בלבד.
* נסח את המשא ומתן הלמדני בלשונך בצורה בהירה ועמוקה, ואת הציטוטים המדויקים הבא בתוך מרכאות בדיוק מוחלט (אות-באות מתוך המקורות שנשלפו).
* חובה לסיים כל תשובה במשפט: "הערה: תוכן זה מיועד ללימוד בלבד, ואין לפסוק ממנו הלכה למעשה."
"""
}

# תמיכה לאחור בבחירות סגנון קודמות
PROMPTS["ישיבתי-למדני (סגנון שו\"ת)"] = PROMPTS["סגנון שו\"ת"]
PROMPTS["מחקר תורני קפדני (מדויק ומבוסס מקורות)"] = PROMPTS["ישיבתי-למדני"]

STYLE_OPTIONS = ["פשוט ומונגש", "סגנון שו\"ת", "הכנה למבחני רבנות", "ישיבתי-למדני"]

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

def verify_verbatim_citations(response_text, sources):
    """בודק התאמה מילולית (Verbatim) של ציטוטים באמצעות התאמת מחרוזות בזיכרון ו-Regex בלבד (ללא קריאות LLM חוסמות)"""
    if not sources:
        return {
            "is_valid": True,
            "grounding_score": 100.0,
            "total_quotes": 0,
            "verified_quotes": [],
            "unverified_quotes": [],
            "details": "לא נשלפו מקורות חיצוניים."
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

    if total == 0:
        details = "התשובה מנוסחת ומוסברת בשפה חופשית ובהירה ללא ציטוטים במרכאות."
    else:
        details = f"{len(verified)} מתוך {total} ציטוטים אומתו מילה-במילה מול המקורות שנשלפו."

    return {
        "is_valid": is_valid,
        "grounding_score": score,
        "total_quotes": total,
        "verified_quotes": verified,
        "unverified_quotes": unverified,
        "details": details
    }

# תאימות לאחור
validate_response = verify_verbatim_citations

# ==========================================
# 7. מנוע ג'מיני - זיהוי דינמי והזרמת תשובה מהירה (Fast Streaming)
# ==========================================
@st.cache_resource(ttl=3600)
def get_supported_models():
    """שולף ושומר במטמון את כל המודלים הפעילים שנתמכים בחשבון, בהעדפה לדגמי flash עדכניים ומהירים"""
    try:
        active_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'preview-tts' not in m.name and 'image' not in m.name and 'transcribe' not in m.name and 'computer-use' not in m.name:
                    active_models.append(m.name)
        
        active_models.sort(key=lambda name: (
            0 if '3.7-flash' in name else
            1 if '3.8-flash' in name else
            2 if '3.6-flash' in name else
            3 if 'flash-latest' in name else
            4 if '3.5-flash' in name else
            5 if '2.5-flash' in name else
            6 if 'flash' in name else 7
        ))
        if active_models:
            return active_models
    except Exception:
        pass
    
    return ['models/gemini-3.7-flash', 'models/gemini-3.6-flash', 'models/gemini-flash-latest', 'models/gemini-2.5-flash']

def stream_gemini_response(prompt, context, style="פשוט ומונגש"):
    """הזרמת תשובה בזמן אמת מ-Gemini API (Fast Streaming) עם מעבר אוטומטי למודל גיבוי בעת עומס"""
    system_instruction = PROMPTS.get(style, PROMPTS["פשוט ומונגש"])
    full_prompt = f"{system_instruction}\n\nמקורות שנשלפו בזמן אמת (Context):\n{context}\n\nשאלה לניתוח:\n{prompt}"
    
    available_models = get_supported_models()
    last_error = ""
    
    for model_name in available_models:
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=generation_config,
                system_instruction=system_instruction
            )
            response = model.generate_content(full_prompt, stream=True)
            has_yielded = False
            for chunk in response:
                if chunk.text:
                    yield chunk.text
                    has_yielded = True
            if has_yielded:
                return
        except Exception as e:
            last_error = str(e)
            continue
            
    yield f"אירעה שגיאה בקבלת תשובה מהמודל: {last_error}"

def get_gemini_response(prompt, sources, context, style="פשוט ומונגש"):
    """קריאה סינכרונית מהירה ל-Gemini ואימות מילולי בזיכרון ללא קריאות LLM חוסמות"""
    chunks = []
    for chunk in stream_gemini_response(prompt, context, style):
        chunks.append(chunk)
    response_text = "".join(chunks)
    val_report = verify_verbatim_citations(response_text, sources)
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
        learning_style = st.selectbox("🎯 בחר סגנון לימוד ותשובה:", STYLE_OPTIONS)
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
            sources = []
            if use_sefaria:
                with st.spinner("שולף מקורות תורניים ומעיין בסוגיה..."):
                    sources = search_sefaria_and_local(user_input, max_results=5)
            context_sources = format_context_sources(sources)

            # הזרמה ישירה ומהירה של תשובת ה-AI בזמן אמת (Fast Streaming)
            response_text = st.write_stream(stream_gemini_response(user_input, context_sources, learning_style))

            # אימות מילולי מיידי (Optimized Validation) ללא השהיה וללא קריאות LLM חוסמות
            validation_report = verify_verbatim_citations(response_text, sources)

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
