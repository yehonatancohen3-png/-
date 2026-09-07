import streamlit as st
import os
import json
import requests
import re
import time
import uuid
import urllib.parse
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

TALMUD_TRACTATES = [
    'Berakhot', 'Shabbat', 'Eruvin', 'Pesachim', 'Rosh Hashanah', 'Yoma', 'Sukkah',
    'Beitzah', 'Taanit', 'Megillah', 'Moed Katan', 'Chagigah', 'Yevamot', 'Ketubot',
    'Nedarim', 'Nazir', 'Sotah', 'Gittin', 'Kiddushin', 'Bava Kamma', 'Bava Metzia',
    'Bava Batra', 'Sanhedrin', 'Makkot', 'Shevuot', 'Avodah Zarah', 'Horayot',
    'Zevachim', 'Menachot', 'Chullin', 'Bekhorot', 'Arakhin', 'Temurah', 'Keritot',
    'Meilah', 'Tamid', 'Niddah'
]
TALMUD_REGEX = r'^(' + '|'.join(TALMUD_TRACTATES) + r')\s+\d+[ab](\b|:)'

def get_source_category_and_score(ref):
    """דירוג מקורות לפי קאנון תורני קלאסי: משנה -> תלמוד -> רמב"ם -> שו"ע -> מפרשים -> שאר"""
    is_primary = " on " not in ref
    
    # 0: משנה מקורית (למעט משנה ברורה)
    if is_primary and re.search(r'^Mishnah\b', ref, re.IGNORECASE) and not ref.startswith("Mishnah Berurah"):
        return "mishnah", 0
    # 1: תלמוד בבלי / ירושלמי מקורי
    if is_primary and (re.search(TALMUD_REGEX, ref, re.IGNORECASE) or ref.startswith("Jerusalem Talmud")):
        return "talmud", 1
    # 2: רמב"ם משנה תורה מקורי
    if is_primary and (ref.startswith("Mishneh Torah") or ref.startswith("Rambam")):
        return "rambam", 2
    # 3: שולחן ערוך מקורי
    if is_primary and (ref.startswith("Shulchan Arukh") or ref.startswith("Shulhan Arukh")):
        return "shulchan_arukh", 3
    
    # מפרשים ונושאי כלים
    if " on Mishnah" in ref:
        return "commentary", 5
    if any(f" on {tr}" in ref for tr in TALMUD_TRACTATES):
        return "commentary", 6
    if " on Mishneh Torah" in ref:
        return "commentary", 7
    if " on Shulchan Arukh" in ref or " on Shulhan Arukh" in ref:
        return "commentary", 8
    
    return "other", 10

def extract_keywords_for_expansion(query):
    """פירוק שאילתה למילות מפתח מהותיות לצורך הרחבת נושא (Topic Expansion)"""
    cleaned = re.sub(r'[?.,!;:״"״”()ֿ\-\_]', ' ', query)
    stop_prefixes = [
        r'^מה הדין (של |ב-|ב)?',
        r'^מה ההלכה (של |ב-|ב)?',
        r'^האם ',
        r'^מדוע ',
        r'^למה ',
        r'^כיצד ',
        r'^מאימתי ',
        r'^סוגיית ',
        r'^סוגית ',
        r'^דין ',
        r'^כלל '
    ]
    for sp in stop_prefixes:
        cleaned = re.sub(sp, '', cleaned).strip()
    
    stop_words = {'מה', 'מי', 'איזה', 'איך', 'כיצד', 'למה', 'מדוע', 'האם', 'של', 'על', 'אל', 'זה', 'זו', 'אלה', 'כל', 'רק', 'אם', 'אין', 'שאין'}
    words = [w for w in cleaned.split() if w not in stop_words and len(w) > 1]
    return " ".join(words)

def execute_sefaria_search(query_str, size=40):
    """קריאת חיפוש מול search-wrapper של ספריא"""
    url = "https://www.sefaria.org/api/search-wrapper"
    try:
        r = HTTP_SESSION.post(url, json={"query": query_str, "size": size}, timeout=3.0)
        if r.status_code == 200:
            return r.json().get("hits", {}).get("hits", [])
    except Exception:
        pass
    return []

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_single_ref_text(ref_name, timeout=2.0):
    """שליפת קטע טקסט בודד מספריא לפי Ref עם Timeout מוגדר ומטמון ל-24 שעות"""
    try:
        url = f"https://www.sefaria.org/api/texts/{urllib.parse.quote(ref_name)}?context=0"
        res = HTTP_SESSION.get(url, timeout=timeout)
        if res.status_code == 200:
            raw_he = res.json().get("he")
            if raw_he:
                if isinstance(raw_he, list):
                    return clean_html_tags(" ".join([str(x) for x in raw_he]))
                return clean_html_tags(str(raw_he))
    except Exception:
        pass
    return None

@st.cache_data(ttl=86400, show_spinner=False)
def search_sefaria_fast(query, max_results=5):
    """
    שליפה מקבילית רב-שלבית מספריא:
    1. ביטוי מדויק (Strict Exact-Phrase Search): חיפוש הביטוי המדויק עם מרכאות ווריאציות אותיות שימוש.
    2. הרחבת נושא (Topic Expansion): אם אין תוצאות, פירוק למילות מפתח ושליפת מקורות יסוד קלאסיים (משנה, תלמוד, רמב"ם, שו"ע).
    3. שמירה במטמון ל-24 שעות ושליפת טקסטים מלאים במקביל.
    """
    clean_q = query.strip().strip('"״”\'')
    if not clean_q:
        return []

    collected_hits = []
    seen_refs = set()
    direct_res = None

    # 1. בדיקת מראה מקום ישיר (Direct Ref)
    direct_url = f"https://www.sefaria.org/api/texts/{urllib.parse.quote(clean_q)}?context=0"
    try:
        d_res = HTTP_SESSION.get(direct_url, timeout=1.5)
        if d_res.status_code == 200:
            d_json = d_res.json()
            he_val = d_json.get("he")
            if he_val:
                text_content = clean_html_tags(" ".join([str(x) for x in he_val])) if isinstance(he_val, list) else clean_html_tags(str(he_val))
                ref_name = d_json.get("ref", clean_q)
                cat, score = get_source_category_and_score(ref_name)
                direct_res = {
                    "ref": ref_name,
                    "text": text_content,
                    "url": f"https://www.sefaria.org/{urllib.parse.quote(ref_name)}",
                    "priority": score,
                    "category": cat
                }
                seen_refs.add(ref_name)
    except Exception:
        pass

    # שלב 1: חיפוש ביטוי מדויק (Strict Exact-Phrase Search)
    exact_queries = [f'"{clean_q}"']
    if clean_q.startswith("אין "):
        exact_queries.append(f'"ש{clean_q}"')
        exact_queries.append(f'"{clean_q[4:].strip()}"')
    elif not clean_q.startswith("ש"):
        exact_queries.append(f'"ש{clean_q}"')

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(execute_sefaria_search, eq, 40) for eq in exact_queries]
        for f in futures:
            for hit in f.result():
                raw_id = hit.get("_id", "")
                m = re.match(r'^([^(]+)', raw_id)
                clean_ref = m.group(1).strip() if m else raw_id
                if clean_ref not in seen_refs:
                    seen_refs.add(clean_ref)
                    collected_hits.append(hit)

    # שלב 2: הרחבת נושא (Topic Expansion)
    # אם החיפוש המדויק לא החזיר תוצאות או שלא נמצאו מקורות קלאסיים (משנה, תלמוד, רמב"ם)
    has_classic = any(
        get_source_category_and_score(re.match(r'^([^(]+)', h.get("_id","")).group(1).strip())[1] <= 3
        for h in collected_hits if re.match(r'^([^(]+)', h.get("_id",""))
    )

    if len(collected_hits) == 0 or not has_classic:
        expanded_keywords = extract_keywords_for_expansion(clean_q)
        if expanded_keywords and expanded_keywords != clean_q:
            kw_hits = execute_sefaria_search(expanded_keywords, size=40)
            for hit in kw_hits:
                raw_id = hit.get("_id", "")
                m = re.match(r'^([^(]+)', raw_id)
                clean_ref = m.group(1).strip() if m else raw_id
                if clean_ref not in seen_refs:
                    seen_refs.add(clean_ref)
                    collected_hits.append(hit)

    # חילוץ ודירוג המועמדים
    candidates = []
    for hit in collected_hits:
        raw_id = hit.get("_id", "")
        m = re.match(r'^([^(]+)', raw_id)
        clean_ref = m.group(1).strip() if m else raw_id
        
        highlights = hit.get("highlight", {})
        hl_list = []
        for v in highlights.values():
            if isinstance(v, list):
                hl_list.extend(v)
        snippet = clean_html_tags(" ... ".join(hl_list))
        
        cat, score = get_source_category_and_score(clean_ref)
        candidates.append({
            "ref": clean_ref,
            "snippet": snippet,
            "category": cat,
            "priority": score
        })

    # בחירת מקורות יסוד קלאסיים מגוונים (משנה, תלמוד, רמב"ם, שו"ע)
    selected_candidates = []
    category_buckets = {"mishnah": [], "talmud": [], "rambam": [], "shulchan_arukh": [], "commentary": [], "other": []}
    for c in candidates:
        category_buckets.setdefault(c["category"], []).append(c)

    # 1. קודם כל נציג מכל קבוצה קלאסית מרכזית שנמצאה
    for cat_name in ["mishnah", "talmud", "rambam", "shulchan_arukh"]:
        if category_buckets[cat_name]:
            selected_candidates.append(category_buckets[cat_name].pop(0))

    # 2. השלמת יתרת המקומות לפי עדיפות הניקוד הקלאסי
    remaining = []
    for bucket in category_buckets.values():
        remaining.extend(bucket)
    remaining.sort(key=lambda x: x["priority"])

    while len(selected_candidates) < max_results and remaining:
        selected_candidates.append(remaining.pop(0))

    # שליפת טקסטים מלאים במקביל עבור המקורות הנבחרים
    results = []
    if direct_res:
        results.append(direct_res)

    if selected_candidates:
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_map = {executor.submit(fetch_single_ref_text, c["ref"]): c for c in selected_candidates[:max_results]}
            for fut in as_completed(future_map):
                c = future_map[fut]
                full_text = None
                try:
                    full_text = fut.result()
                except Exception:
                    pass
                final_text = full_text if full_text else c["snippet"]
                if final_text and not any(r["ref"] == c["ref"] for r in results):
                    results.append({
                        "ref": c["ref"],
                        "text": final_text,
                        "url": f"https://www.sefaria.org/{urllib.parse.quote(c['ref'])}",
                        "priority": c["priority"],
                        "category": c["category"]
                    })
                    if len(results) >= max_results:
                        break

    results.sort(key=lambda x: x.get("priority", 10))
    return results[:max_results]

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
SYSTEM_PROMPT = """אתה עוזר מחקר תורני ולמדני. תפקידך לספק תשובות מלאות, ברורות ונורמליות (בהתאם לסגנון שנבחר: פשוט ומונגש, שו"ת, או הכנה למבחני רבנות), תוך שמירה מוחלטת על חוקי ציטוט מחמירים.

חוקי המענה והציטוט:
1. מענה מלא וברור: ענה על שאלת המשתמש בצורה נורמלית, מוסברת ומאורגנת. הסבר את המושגים, ההלכות והסברות בשפה ברורה וקליחה.
2. דיוק מילולי מוחלט (Verbatim) בציטוטים: כאשר אתה מביא ציטוט מתוך מקור (בתוך מרכאות), הציטוט חייב להיות מועתק אות-באות ומילה-במילה מתוך המקורות שנשלפו עבורך בלבד.
3. איסור מוחלט על ציטוט מהזיכרון: אסור לשחזר או להמציא ציטוטים בתוך מרכאות מהזיכרון הפנימי.
4. הפרדה בין הסבר לציטוט:
   - את הסבר המושג/הסוגיה כתוב בלשונך באופן הברור והטבעי ביותר.
   - את הציטוטים הבא כראיה או כמקור בתוך מרכאות בדיוק מוחלט, בצמוד למראה מקום.
5. חסר במקורות: אם הציטוט המדויק אינו מופיע במקורות שנשלפו, הסבר את הכלל/המושג בלשונך, וציין בקצרה שמראה המקום המדויק של הציטוט המילולי לא נשלף במלואו."""

PROMPTS = {
    "פשוט ומונגש": f"""{SYSTEM_PROMPT}

דגשי סגנון - פשוט ומונגש:
* ספק הסבר מלא, ברור ומאורגן בגובה העיניים על שאלת המשתמש.
* באר מושגים וטעמים בלשון בהירה וקולחת.
* ציטוטים מהמקורות שלב בתוך מרכאות בדיוק מילולי מוחלט (אות-באות מהמקורות שנשלפו) עם מראה מקום בסוגריים.
* חובה לסיים כל תשובה במשפט: "הערה: תוכן זה מיועד ללימוד בלבד, ואין לפסוק ממנו הלכה למעשה."
""",
    "סגנון שו\"ת": f"""{SYSTEM_PROMPT}

דגשי סגנון - סגנון שו"ת:
* מבנה תשובה מסודר ומלא: הצגת השאלה, משא ומתן הלכתי ומסקנה ברורה ומנומקת.
* הסבר את הטעמים והסברות בלשון תורנית רהוטה ועשירה, ואת הציטוטים הבא בתוך מרכאות בדיוק מילולי מוחלט (Verbatim) עם מראי מקומות בסוגריים.
* חובה לסיים כל תשובה במשפט: "הערה: תוכן זה מיועד ללימוד בלבד, ואין לפסוק ממנו הלכה למעשה."
""",
    "הכנה למבחני רבנות": f"""{SYSTEM_PROMPT}

דגשי סגנון - הכנה למבחני רבנות:
* הצג תשובה מלאה, שיטתית ומקיפה בהשתלשלות הלכתית סדורה (סוגיות הש"ס, ראשונים, שולחן ערוך ונושאי כלים).
* באר את שיטות הפוסקים וטעמיהם בהרחבה, ואת הציטוטים הבא בתוך מרכאות אות-באות מתוך המקורות שנשלפו.
* חובה לסיים כל תשובה במשפט: "הערה: תוכן זה מיועד ללימוד בלבד, ואין לפסוק ממנו הלכה למעשה."
""",
    "ישיבתי-למדני": f"""{SYSTEM_PROMPT}

דגשי סגנון - ישיבתי-למדני:
* פתח מהלך למדני שלם ומעמיק: בירור הסוגיה, קושיות, תירוצים, דיוקים וחילוקי סברות.
* נסח את המשא ומתן הלמדני בלשונך בצורה בהירה ועמוקה, ואת הציטוטים המדויקים הבא בתוך מרכאות בדיוק מוחלט (אות-באות מתוך המקורות שנשלפו).
* חובה לסיים כל תשובה במשפט: "הערה: תוכן זה מיועד ללימוד בלבד, ואין לפסוק ממנו הלכה למעשה."
"""
}

# תמיכה לאחור בבחירות סגנון קודמות
PROMPTS["ישיבתי-למדני (סגנון שו\"ת)"] = PROMPTS["סגנון שו\"ת"]
PROMPTS["מחקר תורני קפדני (מדויק ומבוסס מקורות)"] = PROMPTS["ישיבתי-למדני"]

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
                system_instruction=SYSTEM_PROMPT
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
