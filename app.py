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

# ==========================================
# 4. הגדרות סיווג מקורות, עדיפויות והרחבת שאילתות (Primary Sources First)
# ==========================================
TALMUD_TRACTATES = {
    'Berakhot', 'Shabbat', 'Eruvin', 'Pesachim', 'Shekalim', 'Yoma', 'Sukkah',
    'Beitzah', 'Rosh Hashanah', 'Ta\'anit', 'Megillah', 'Moed Katan', 'Chagigah',
    'Yevamot', 'Ketubot', 'Nedarim', 'Nazir', 'Sotah', 'Gittin', 'Kiddushin',
    'Bava Kamma', 'Bava Metzia', 'Bava Batra', 'Sanhedrin', 'Makkot', 'Shevuot',
    'Avodah Zarah', 'Horayot', 'Zevachim', 'Menachot', 'Chullin', 'Bekhorot',
    'Arakhin', 'Temurah', 'Keritot', 'Meilah', 'Tamid', 'Niddah'
}

HEBREW_TRACTATES = [
    'ברכות', 'שבת', 'עירובין', 'פסחים', 'שקלים', 'יומא', 'סוכה', 'ביצה',
    'ראש השנה', 'תענית', 'מגילה', 'מועד קטן', 'חגיגה', 'יבמות', 'כתובות',
    'נדרים', 'נזיר', 'סוטה', 'גיטין', 'קידושין', 'בבא קמא', 'בבא מציעא',
    'בבא בתרא', 'סנהדרין', 'מכות', 'שבועות', 'עבודה זרה', 'הוריות', 'זבחים',
    'מנחות', 'חולין', 'בכורות', 'ערכין', 'תמורה', 'כריתות', 'מעילה', 'תמיד', 'נדה',
    'אהלות', 'אוהלות', 'כלים', 'טהרות', 'מקואות', 'עוקצין'
]

TANAKH_BOOKS = {
    'Genesis', 'Exodus', 'Leviticus', 'Numbers', 'Deuteronomy', 'Joshua', 'Judges',
    'I Samuel', 'II Samuel', 'I Kings', 'II Kings', 'Isaiah', 'Jeremiah', 'Ezekiel',
    'Hosea', 'Joel', 'Amos', 'Obadiah', 'Jonah', 'Micah', 'Nahum', 'Habakkuk',
    'Zephaniah', 'Haggai', 'Zechariah', 'Malachi', 'Psalms', 'Proverbs', 'Job',
    'Song of Songs', 'Ruth', 'Lamentations', 'Ecclesiastes', 'Esther', 'Daniel',
    'Ezra', 'Nehemiah', 'I Chronicles', 'II Chronicles'
}

HEBREW_TANAKH = [
    'בראשית', 'שמות', 'ויקרא', 'במדבר', 'דברים', 'יהושע', 'שופטים', 'שמואל', 'מלכים',
    'ישעיהו', 'ירמיהו', 'יחזקאל', 'הושע', 'יואל', 'עמוס', 'עובדיה', 'יונה', 'מיכה',
    'נחום', 'חבקוק', 'צפניה', 'חגי', 'זכריה', 'מלאכי', 'תהילים', 'משלי', 'איוב',
    'שיר השירים', 'רות', 'איכה', 'קהלת', 'אסתר', 'דניאל', 'עזרא', 'נחמיה', 'דברי הימים'
]

CONCEPTUAL_EXPANSIONS = {
    "תפילין": {
        "refs": [
            "Shulchan Arukh, Orach Chayim 30:2",
            "Mishnah Berurah 30:2",
            "Biur Halacha 30:2",
            "Kaf HaChayim on Shulchan Arukh, Orach Chayim 30:2",
            "Shulchan Arukh, Orach Chayim 37:2",
            "Shulchan Arukh, Orach Chayim 38:10",
            "Menachot 36a",
            "Eruvin 96a",
            "Mishneh Torah, Tefillin, Mezuzah and the Priestly Blessing 4:10"
        ],
        "queries": ["הנחת תפילין", "זמן הנחת תפילין", "תפילין כל היום", "ברכת תפילין", "שקיעת החמה"]
    },
    "מוקצה": {
        "refs": [
            "Shabbat 123b",
            "Shabbat 124a",
            "Shabbat 142a",
            "Shulchan Arukh, Orach Chayim 308:3",
            "Mishnah Berurah 308:3",
            "Biur Halacha 308:3",
            "Kaf HaChayim on Shulchan Arukh, Orach Chayim 308:3",
            "Mishneh Torah, Sabbath 25:1"
        ],
        "queries": ["טלטול מוקצה", "לצורך גופו ומקומו", "כלי שמלאכתו לאיסור", "דבר שמלאכתו להיתר"]
    },
    "בישול בשבת": {
        "refs": [
            "Shabbat 18b",
            "Shabbat 36b",
            "Shabbat 38a",
            "Shulchan Arukh, Orach Chayim 253:1",
            "Mishnah Berurah 253:1",
            "Shulchan Arukh, Orach Chayim 318:1",
            "Mishnah Berurah 318:1",
            "Biur Halacha 318:1",
            "Mishneh Torah, Sabbath 3:1"
        ],
        "queries": ["חימום אוכל בשבת", "שהייה והחזרה", "פלטה של שבת", "בישול אחר בישול"]
    },
    "בשר בחלב": {
        "refs": [
            "Chullin 103b",
            "Chullin 104b",
            "Chullin 105a",
            "Shulchan Arukh, Yoreh De'ah 87:1",
            "Shulchan Arukh, Yoreh De'ah 89:1",
            "Siftei Kohen on Shulchan Arukh, Yoreh De'ah 89:1",
            "Turei Zahav on Shulchan Arukh, Yoreh De'ah 89:1",
            "Pithei Teshuva on Shulchan Arukh, Yoreh De'ah 89:1",
            "Mishneh Torah, Forbidden Foods 9:1"
        ],
        "queries": ["המתנה בין בשר לחלב", "בשר עוף בחלב", "אכילת גבינה אחר בשר"]
    },
    "שעות זמניות": {
        "refs": [
            "Pesachim 93b",
            "Pesachim 94a",
            "Berakhot 9b",
            "Berakhot 26b",
            "Mishnah Berakhot 1:2",
            "Mishnah Berakhot 4:1",
            "Shulchan Arukh, Orach Chayim 233:1",
            "Mishnah Berurah 233:3",
            "Biur Halacha 233:1",
            "Mishnah Berurah 58:4",
            "Mishneh Torah, Reading the Shema 1:9",
            "Mishneh Torah, Prayer and the Priestly Blessing 3:1"
        ],
        "queries": ["שעות ביום", "עד שלש שעות", "ארבע שעות", "שיעור שעות", "מעלות השחר ועד הנץ החמה", "עוביו של רקיע"]
    },
    "זמני היום": {
        "refs": [
            "Pesachim 93b",
            "Pesachim 94a",
            "Berakhot 2b",
            "Berakhot 9b",
            "Berakhot 26b",
            "Shulchan Arukh, Orach Chayim 233:1",
            "Mishneh Torah, Reading the Shema 1:9"
        ],
        "queries": ["זמני היום", "עלות השחר", "הנץ החמה", "שקיעת החמה", "צאת הכוכבים"]
    },
    "אין דוחין נפש מפני נפש": {
        "aliases": ["סומק טפי", "דדמא דידך", "מאי חזית", "מי יימר", "נפש מפני נפש", "ההוא דאתא לקמיה דרבא"],
        "refs": [
            "Sanhedrin 74a",
            "Yoma 82b",
            "Pesachim 25b",
            "Mishnah Oholot 7:6",
            "Sanhedrin 72b",
            "Mishneh Torah, Murderer and the Preservation of Life 1:9",
            "Shulchan Arukh, Choshen Mishpat 425:2"
        ],
        "queries": ["נפש מפני נפש", "מאי חזית דדמא דידך סומק", "מי יימר דדמא דידך סומק טפי", "יצא ראשו אין נוגעין בו", "ההוא דאתא לקמיה דרבא", "סומק טפי"]
    },
    "פיקוח נפש": {
        "refs": [
            "Yoma 85a",
            "Yoma 85b",
            "Shabbat 132a",
            "Mishneh Torah, Sabbath 2:1",
            "Shulchan Arukh, Orach Chayim 328:1"
        ],
        "queries": ["פיקוח נפש דוחה שבת", "וחי בהם ולא שימות בהם"]
    },
    "גרמא": {
        "refs": [
            "Bava Kamma 60a",
            "Bava Batra 22b",
            "Sanhedrin 76b",
            "Mishneh Torah, Wounding and Damaging 4:2",
            "Shulchan Arukh, Choshen Mishpat 386:1"
        ],
        "queries": ["גרם נזיקין", "גרמא בנזיקין פטור", "גרמי חייב"]
    },
    "ספק דאורייתא": {
        "refs": [
            "Pesachim 9a",
            "Ketubot 9a",
            "Beitzah 3b",
            "Mishneh Torah, Rebels 1:5",
            "Shulchan Arukh, Yoreh De'ah 110:1"
        ],
        "queries": ["ספק דאורייתא לחומרא", "ספק דרבנן לקולא"]
    },
    "ספק ברכות": {
        "refs": [
            "Berakhot 12a",
            "Berakhot 35a",
            "Mishneh Torah, Blessings 8:12",
            "Shulchan Arukh, Orach Chayim 209:3"
        ],
        "queries": ["ספק ברכות להקל", "סב״ל"]
    },
    "קים ליה בדרבה מיניה": {
        "refs": [
            "Ketubot 30a",
            "Sanhedrin 37a",
            "Bava Kamma 70b",
            "Mishneh Torah, Theft 3:1",
            "Shulchan Arukh, Choshen Mishpat 351:1"
        ],
        "queries": ["קלבד״מ", "אלא במיתה או בתשלומין"]
    },
    "המוציא מחברו עליו הראיה": {
        "refs": [
            "Bava Kamma 46a",
            "Bava Metzia 100a",
            "Mishneh Torah, Pleading 8:1",
            "Shulchan Arukh, Choshen Mishpat 399:1"
        ],
        "queries": ["המע״ה", "קרקע בחזקת בעליה עומדת"]
    },
    "יהרג ואל יעבור": {
        "refs": [
            "Sanhedrin 74a",
            "Pesachim 25a",
            "Yoma 82a",
            "Mishneh Torah, Foundations of the Torah 5:1",
            "Shulchan Arukh, Yoreh De'ah 157:1"
        ],
        "queries": ["שלוש עבירות חמורות", "עבודה זרה גילוי עריות ושפיכות דמים"]
    },
    "טבילת כלים": {
        "refs": [
            "Avodah Zarah 75b",
            "Mishneh Torah, Forbidden Foods 17:3",
            "Shulchan Arukh, Yoreh De'ah 120:1"
        ],
        "queries": ["כלי סעודה הנלקחים מן הגוי", "הטבלת כלים"]
    },
    "קידוש במקום סעודה": {
        "refs": [
            "Pesachim 101a",
            "Mishneh Torah, Sabbath 29:8",
            "Shulchan Arukh, Orach Chayim 273:1"
        ],
        "queries": ["אין קידוש אלא במקום סעודה"]
    },
    "שינוי מקום": {
        "refs": [
            "Pesachim 101b",
            "Berakhot 42a",
            "Mishneh Torah, Blessings 4:1",
            "Shulchan Arukh, Orach Chayim 178:1"
        ],
        "queries": ["שינוי מקום בברכות", "עקירת מקום"]
    },
    "פסיק רישיה": {
        "refs": [
            "Shabbat 75a",
            "Shabbat 103a",
            "Mishneh Torah, Sabbath 1:5",
            "Shulchan Arukh, Orach Chayim 320:18"
        ],
        "queries": ["פסיק רישא ולא ימות", "דבר שאינו מתכוון"]
    },
    "מצוות צריכות כוונה": {
        "refs": [
            "Rosh Hashanah 28a",
            "Berakhot 13a",
            "Pesachim 114a",
            "Mishneh Torah, Shofar, Sukkah and Lulav 2:4",
            "Shulchan Arukh, Orach Chayim 60:4"
        ],
        "queries": ["מצוות אין צריכות כוונה", "המתעסק"]
    },
    "ביטול ברוב": {
        "refs": [
            "Chullin 98a",
            "Zevachim 78a",
            "Mishneh Torah, Forbidden Foods 15:1",
            "Shulchan Arukh, Yoreh De'ah 98:1"
        ],
        "queries": ["ביטול בשישים", "אחרי רבים להטות"]
    },
    "דינא דמלכותא דינא": {
        "refs": [
            "Nedarim 28a",
            "Gittin 10b",
            "Bava Kamma 113a",
            "Mishneh Torah, Robbery and Lost Property 5:11",
            "Shulchan Arukh, Choshen Mishpat 369:6"
        ],
        "queries": ["דדמ״ד", "דינא דמלכותא"]
    },
    "חמץ שעבר עליו הפסח": {
        "refs": [
            "Pesachim 28a",
            "Mishneh Torah, Leavened and Unleavened Bread 1:4",
            "Shulchan Arukh, Orach Chayim 448:1"
        ],
        "queries": ["חמץ לאחר הפסח", "קנסו חכמים"]
    },
    "הבדלה": {
        "refs": [
            "Berakhot 33a",
            "Pesachim 102b",
            "Mishneh Torah, Sabbath 29:1",
            "Shulchan Arukh, Orach Chayim 296:1"
        ],
        "queries": ["הבדלה על הכוס", "זכרהו על היין", "מוצאי שבת"]
    },
    "תפילת מנחה": {
        "refs": [
            "Berakhot 26b",
            "Berakhot 27a",
            "Shulchan Arukh, Orach Chayim 233:1",
            "Mishnah Berurah 233:1",
            "Biur Halacha 233:1",
            "Mishneh Torah, Prayer and the Priestly Blessing 3:1"
        ],
        "queries": ["זמן תפילת מנחה", "מנחה גדולה", "מנחה קטנה", "פלג המנחה", "תפילת מנחה עד שקיעת החמה"]
    },
    "קריאת שמע": {
        "refs": [
            "Berakhot 2a",
            "Berakhot 9b",
            "Berakhot 10b",
            "Shulchan Arukh, Orach Chayim 58:1",
            "Mishnah Berurah 58:1",
            "Mishnah Berurah 58:4",
            "Biur Halacha 58:1",
            "Mishneh Torah, Reading the Shema 1:1"
        ],
        "queries": ["זמן קריאת שמע", "שמע של שחרית", "שלוש שעות", "הנץ החמה"]
    },
    "הדלקת נרות שבת": {
        "refs": [
            "Shabbat 25b",
            "Shabbat 35b",
            "Shulchan Arukh, Orach Chayim 261:1",
            "Mishnah Berurah 261:1",
            "Shulchan Arukh, Orach Chayim 263:1",
            "Mishnah Berurah 263:1",
            "Mishneh Torah, Sabbath 5:1"
        ],
        "queries": ["זמן הדלקת נרות שבת", "תוספת שבת", "בין השמשות", "ברכת הדלקת הנר"]
    },
    "ציצית": {
        "refs": [
            "Menachot 39b",
            "Menachot 41a",
            "Shulchan Arukh, Orach Chayim 8:1",
            "Mishnah Berurah 8:1",
            "Shulchan Arukh, Orach Chayim 11:1",
            "Mishnah Berurah 11:1",
            "Mishneh Torah, Fringes 1:1"
        ],
        "queries": ["הטלת ציצית", "טלית קטן", "ארבע כנפות", "ברכת הציצית"]
    },
    "עירובין": {
        "refs": [
            "Eruvin 2a",
            "Eruvin 59a",
            "Shulchan Arukh, Orach Chayim 345:1",
            "Mishnah Berurah 345:1",
            "Shulchan Arukh, Orach Chayim 366:1",
            "Mishnah Berurah 366:1",
            "Mishneh Torah, Eruv 1:1"
        ],
        "queries": ["עירוב חצרות", "טלטול בשבת", "רשות הרבים", "כרמלית"]
    }
}

def classify_source_priority(ref_str: str) -> int:
    """
    קביעת עדיפות המקור להרכבת הקונטקסט:
    1 - מקרא, משנה, תלמוד בבלי וירושלמי (Primary Texts)
    2 - רמב"ם (משנה תורה) ושולחן ערוך גופא (Primary Codes)
    3 - ראשונים (רש"י, תוספות, רמב"ן, רשב"א, רא"ש, רי"ף וכו')
    4 - נושאי כלי השו"ע ואחרונים קלאסיים (משנה ברורה, מגן אברהם וכו')
    5 - מפרשים מאוחרים, שו"תים ומחקר
    """
    if not ref_str:
        return 5
    ref = ref_str.strip()

    # זיהוי פירוש לפי תבניות מובהקות
    is_commentary = bool(
        re.search(r'\b(on|upon)\b', ref, re.IGNORECASE) or 
        ' על ' in ref or 
        ref.startswith('פירוש ') or 
        ref.startswith('ביאור ') or
        ref.startswith('חידושי ')
    )

    # 1. החרגות לאחרונים ששמם מתחיל במילים מטעות (כגון "משנה ברורה")
    if (
        ref.startswith('Mishnah Berurah') or 
        ref.startswith('משנה ברורה') or 
        'Mishnah Berurah' in ref or 
        'משנה ברורה' in ref or
        ref.startswith('Biur Halacha') or
        ref.startswith('ביאור הלכה')
    ):
        return 4

    # 2. רמב"ם גופא (Primary Code: Mishneh Torah) - נבדק לפני משנה בגלל הקידומת "משנה תורה"
    if not is_commentary:
        if (
            ref.startswith('Mishneh Torah') or 
            ref.startswith('משנה תורה') or 
            (ref.startswith('רמב"ם') and not any(k in ref for k in ['כסף משנה', 'מגיד משנה', 'לחם משנה']))
        ):
            return 2

    # 3. שולחן ערוך וטור גופא (Primary Code: Shulchan Arukh & Tur)
    if not is_commentary:
        if (
            ref.startswith('Shulchan Arukh') or 
            ref.startswith('שולחן ערוך') or
            ref.startswith('Tur, ') or
            ref.startswith('טור, ')
        ):
            return 2

    # 4. מקרא (Primary Tanakh)
    if not is_commentary:
        for b in TANAKH_BOOKS:
            if ref.startswith(b):
                return 1
        for hb in HEBREW_TANAKH:
            if ref.startswith(hb):
                return 1

    # 5. משנה (Primary Mishnah)
    if not is_commentary:
        if (ref.startswith('Mishnah ') or ref.startswith('משנה ')) and not ref.startswith('משנה תורה'):
            return 1

    # 6. תלמוד בבלי וירושלמי (Primary Talmud)
    if not is_commentary:
        for t in TALMUD_TRACTATES:
            if ref.startswith(t):
                return 1
        for ht in HEBREW_TRACTATES:
            if ref.startswith(ht) or ref.startswith(f"מסכת {ht}"):
                return 1
        if ref.startswith('Jerusalem Talmud') or ref.startswith('תלמוד ירושלמי'):
            return 1

    # 7. ראשונים (Rishonim)
    rishonim_markers = [
        'Rashi', 'Tosafot', 'Ramban', 'Rashba', 'Ritva', 'Ran', 'Rosh', 'Rif', 
        'Meiri', 'Sefer HaChinukh', 'Maggid Mishneh', 'Kesef Mishneh', 'Ra\'avad',
        'רש"י', 'תוספות', 'רמב"ן', 'רשב"א', 'ריטב"א', 'ר"ן', 'רא"ש', 'רי"ף', 
        'מאירי', 'ספר החינוך', 'מגיד משנה', 'כסף משנה', 'ראב"ד'
    ]
    if any(m in ref for m in rishonim_markers):
        return 3

    # 8. נושאי כלי השו"ע ואחרונים קלאסיים
    acharonim_markers = [
        'Magen Avraham', 'Turei Zahav', 'Taz', 'Siftei Kohen', 'Shach', 'Beur HaGra',
        'Gra', 'Kaf HaChayim', 'Arukh HaShulchan', 'Chayei Adam', 'Pitchei Teshuva',
        'Ba\'er Hetev', 'Ketzot HaChoshen', 'Netivot HaMishpat', 'Chatam Sofer',
        'Beit Shmuel', 'Chelkat Mechokek', 'בית שמואל', 'חלקת מחוקק',
        'מגן אברהם', 'ט"ז', 'טורי זהב', 'ש"ך', 'שפתי כהן', 'ביאור הגר"א', 'הגר"א',
        'כף החיים', 'ערוך השולחן', 'חיי אדם', 'פתחי תשובה', 'באר היטב', 'קצות החושן',
        'נתיבות המשפט', 'חתם סופר', 'פרי מגדים', 'Peri Megadim', 'משפטי עוזיאל', 'יביע אומר'
    ]
    if any(m in ref for m in acharonim_markers):
        return 4

    return 5

# מילוני עזר לזיקוק שאילתות הלכתיות והתאמת מושגים מדויקת
HALAKHIC_STOPWORDS = {
    'האם', 'מותר', 'אסור', 'אפשר', 'מהו', 'מהי', 'מה', 'מי', 'למה', 'מדוע', 'כיצד', 'איך',
    'הוא', 'היא', 'הם', 'הן', 'אשר', 'על', 'אל', 'את', 'זה', 'זו', 'אלה', 'אלו',
    'של', 'עם', 'כל', 'כך', 'רק', 'אם', 'או', 'כמו', 'שעה', 'הזה', 'הזאת', 'היו',
    'היה', 'תהיה', 'יהיה', 'ב2', 'ב3', 'ב4', 'ב12', 'בצהריים', 'בבוקר', 'בערב', 'בלילה',
    'אומרים', 'עושים', 'כשמניחים', 'שעושים', 'שאומרים', 'כזו', 'כזה', 'מאוחרת', 'מוקדמת',
    'המשפט', 'טוב', 'תודה', 'בבקשה', 'שלום', 'היי', 'אשמח', 'לדעת', 'להבין',
    'לשאול', 'שאלה', 'לגבי', 'בעניין', 'הלכה', 'למעשה', 'דין', 'הדין'
}

AMORA_OR_COMMON_WORDS = {
    'רבה', 'רבא', 'אביי', 'רב', 'שמואל', 'רבי', 'יוחנן', 'ריש לקיש', 'רב אשי', 'רבינא',
    'משפט', 'המשפט', 'פסוק', 'פסוקים', 'אמר', 'אמרו', 'שאמר', 'שאמרו', 'מימרא',
    'הלכה', 'דין', 'סברא', 'טפי', 'הזה', 'הזאת', 'ההוא', 'מאי'
}

MORPHOLOGY_MAP = {
    'להניח': ['הנחת', 'מניח', 'תפילין'],
    'לטלטל': ['טלטול', 'מוקצה'],
    'לחמם': ['חימום', 'בישול'],
    'לבשל': ['בישול', 'שבת'],
    'לאכול': ['אכילה'],
    'לברך': ['ברכת'],
    'לטבול': ['טבילת']
}

@st.cache_data(ttl=86400, show_spinner=False)
def get_sefaria_sources_robust(user_query: str, history=None) -> List[str]:
    """
    שליפת מקורות מספריא בעדיפות עליונה לקטגוריות ראשיות (תנ"ך, משנה, תלמוד, רמב"ם ושולחן ערוך)
    לפני פרשנים ואחרונים, כולל זיקוק שאילתה הלכתי, התחשבות בהקשר שיחה, הרחבת מושגים,
    שליפה מקבילית מסוננת לפי קטגוריות, ומראי מקומות בעברית בלבד.
    """
    raw_query = user_query.strip()
    clean_query = re.sub(r'[^\w\s]', ' ', user_query).strip()
    if not clean_query and not raw_query:
        return []

    collected_sources = []
    seen_refs = set()

    raw_words = clean_query.split()
    content_words = [w for w in raw_words if w not in HALAKHIC_STOPWORDS and len(w) > 1]

    # תמיכה בשאלות המשך שיחתיות: שילוב מילות תוכן מהודעות קודמות בשיחה
    combined_context_text = user_query
    if history and isinstance(history, list):
        for prev_msg in reversed(history):
            if isinstance(prev_msg, dict) and prev_msg.get("role") == "user":
                prev_text = prev_msg.get("content", "")
                if prev_text.strip() == user_query.strip():
                    continue  # דילוג על השאלה הנוכחית כדי לאתר את השאלה הקודמת
                combined_context_text += " " + prev_text
                prev_clean = re.sub(r'[^\w\s]', ' ', prev_text)
                prev_content = [w for w in prev_clean.split() if w not in HALAKHIC_STOPWORDS and len(w) > 1]
                if len(content_words) <= 2:
                    content_words = prev_content[:3] + content_words
                break

    # 1. הרחבת שאילתה (Query Expansion) למושגים תורניים והלכתיים עם התאמה מדויקת
    expanded_refs = []
    expanded_queries = []
    for concept, data in CONCEPTUAL_EXPANSIONS.items():
        matched = False
        if concept in combined_context_text:
            matched = True
        if not matched:
            for q in data.get("queries", []) + data.get("aliases", []):
                if q in combined_context_text:
                    matched = True
                    break
                q_words = [qw for qw in q.split() if qw not in HALAKHIC_STOPWORDS and qw not in AMORA_OR_COMMON_WORDS]
                if len(q_words) >= 2 and all(qw in combined_context_text for qw in q_words):
                    matched = True
                    break
        if not matched:
            concept_words = [cw for cw in re.findall(r'\b\w+\b', concept) if cw not in AMORA_OR_COMMON_WORDS and len(cw) >= 4]
            for cw in concept_words:
                if cw in content_words:
                    matched = True
                    break

        if matched:
            expanded_refs.extend(data.get("refs", []))
            expanded_queries.extend(data.get("queries", []))
            if len(expanded_refs) >= 10:
                break

    # שליפה ישירה ומקבילית של מראי מקומות מורחבים
    if expanded_refs:
        def fetch_direct_item(r):
            t, hr = fetch_sefaria_text_and_he_ref(r)
            return r, hr, t

        with ThreadPoolExecutor(max_workers=min(len(expanded_refs), 6)) as executor:
            for r, hr, t in executor.map(fetch_direct_item, expanded_refs):
                if t:
                    display_ref = hr if hr else r
                    if display_ref not in seen_refs:
                        seen_refs.add(display_ref)
                        prio = classify_source_priority(r)
                        collected_sources.append((prio, display_ref, t))

    # 2. שליפה מקבילית לפי קטגוריות ראשיות (Categorized Retrieval)
    primary_categories = [
        ("Mishnah", ["Mishnah"]),
        ("Talmud/Bavli", ["Talmud/Bavli"]),
        ("Halakhah/Mishneh Torah", ["Halakhah/Mishneh Torah"]),
        ("Halakhah/Shulchan Arukh", ["Halakhah/Shulchan Arukh"]),
        ("Acharonim/Commentary", ["Halakhah/Shulchan Arukh/Commentary"]),
        ("Responsa", ["Responsa"]),
        ("Tanakh", ["Tanakh"]),
        ("Global", None)
    ]

    # הכנת שאילתות מזוקקות להרצה: ביטויי מפתח, הטיות וביגרמות
    decomposed_subqueries = []
    if content_words:
        decomposed_subqueries.append(' '.join(content_words[:4]))
        for i in range(len(content_words) - 1):
            decomposed_subqueries.append(f"{content_words[i]} {content_words[i+1]}")
    for rw in raw_words:
        if rw in MORPHOLOGY_MAP:
            for m in MORPHOLOGY_MAP[rw]:
                if m not in decomposed_subqueries:
                    decomposed_subqueries.append(m)

    search_queries = []
    if content_words:
        search_queries.append(' '.join(content_words[:4]))
    if clean_query not in search_queries and len(clean_query.split()) <= 4:
        search_queries.append(clean_query)
    if expanded_queries:
        search_queries.extend(expanded_queries[:3])
    for dsq in decomposed_subqueries:
        if dsq not in search_queries:
            search_queries.append(dsq)

    def query_category(cat_info):
        cat_name, cat_filter = cat_info
        results = []
        # סריקת שאילתות מזוקקות להבטחת כיסוי גמרא, שו"ע, אחרונים ושו"תים
        queries_to_run = search_queries[:5] if cat_name in ["Talmud/Bavli", "Mishnah", "Acharonim/Commentary", "Responsa"] else search_queries[:2]
        for q in queries_to_run:
            payload = {
                "query": q,
                "type": "text",
                "size": 4,
                "field": "naive_lemmatizer"
            }
            if cat_filter:
                payload["filters"] = cat_filter
                payload["filter_fields"] = ["path"]
            try:
                res = HTTP_SESSION.post("https://www.sefaria.org/api/search-wrapper", json=payload, timeout=5)
                if res.status_code == 200:
                    hits = res.json().get("hits", {}).get("hits", [])
                    for h in hits:
                        raw_id = h.get("_id", "")
                        if "Introduction" in raw_id:
                            continue
                        results.append(h)
            except Exception:
                pass
            if len(results) >= 4:
                break
        return results

    with ThreadPoolExecutor(max_workers=8) as executor:
        cat_hits_lists = executor.map(query_category, primary_categories)
        all_hits = [hit for sublist in cat_hits_lists for hit in sublist]

    # שליפה מקבילית ומואצת של טקסט מלא ומראי מקומות בעברית מתוך התוצאות
    unique_hits_to_fetch = []
    seen_candidate_refs = set()
    for hit in all_hits:
        raw_id = hit.get("_id", "")
        m = re.match(r'^([^(]+)', raw_id)
        ref = m.group(1).strip() if m else raw_id
        if ref and ref not in seen_candidate_refs:
            seen_candidate_refs.add(ref)
            unique_hits_to_fetch.append((ref, hit))

    def fetch_hit_details(item):
        ref, hit = item
        t, hr = fetch_sefaria_text_and_he_ref(ref)
        if not t and hit.get("highlight"):
            hl = hit.get("highlight", {})
            hl_snippets = []
            for v in hl.values():
                if isinstance(v, list):
                    hl_snippets.extend(v)
            t = " ... ".join(hl_snippets)
        return ref, hr, t

    if unique_hits_to_fetch:
        with ThreadPoolExecutor(max_workers=8) as executor:
            for ref, hr, t in executor.map(fetch_hit_details, unique_hits_to_fetch):
                clean_he = clean_html_tags(str(t))
                if clean_he:
                    display_ref = hr if hr else ref
                    if display_ref not in seen_refs:
                        seen_refs.add(display_ref)
                        prio = classify_source_priority(ref)
                        collected_sources.append((prio, display_ref, clean_he))

    # 3. גיבוי: שליפה ישירה של השאילתה כ-Ref במידה ולא נשלפו מקורות
    if not collected_sources:
        try:
            target_ref = raw_query if any(c in raw_query for c in [':', '.']) else clean_query
            encoded_query = urllib.parse.quote(target_ref)
            direct_url = f"https://www.sefaria.org/api/v3/texts/{encoded_query}?context=0"
            res = HTTP_SESSION.get(direct_url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                he_ref = data.get("heRef", "")
                display_ref = he_ref if he_ref else user_query
                for v in data.get("versions", []):
                    if v.get("language") == "he":
                        t = v.get("text", "")
                        text_str = " ".join(t) if isinstance(t, list) else str(t)
                        clean_t = clean_html_tags(text_str)
                        if clean_t:
                            prio = classify_source_priority(target_ref)
                            collected_sources.append((prio, display_ref, clean_t))
                            break
        except Exception:
            pass

    # 4. הרכבת הקונטקסט בצורה מאוזנת המבטיחה מקורות בכל דרגי הפסיקה (כולל אחרונים ושו"תים)
    by_prio = {1: [], 2: [], 3: [], 4: [], 5: []}
    for s in collected_sources:
        prio = s[0]
        if prio in by_prio:
            by_prio[prio].append(s)
        else:
            by_prio[5].append(s)

    balanced_sources = []
    # מנות מובטחות: גמרא ומשנה (3), ראשונים (2), שו"ע ורמב"ם (3), אחרונים ונושאי כלים (4), שו"תים (2)
    tier_quotas = {1: 3, 3: 2, 2: 3, 4: 4, 5: 2}
    for prio in [1, 3, 2, 4, 5]:
        take = min(len(by_prio[prio]), tier_quotas[prio])
        balanced_sources.extend(by_prio[prio][:take])
        by_prio[prio] = by_prio[prio][take:]

    # השלמת מקומות עד 16 מקורות מתוך כלל המקורות שנותרו
    remaining_slots = 16 - len(balanced_sources)
    if remaining_slots > 0:
        leftover = []
        for prio in [1, 3, 2, 4, 5]:
            leftover.extend(by_prio[prio])
        balanced_sources.extend(leftover[:remaining_slots])

    # סידור במסלול פסיקה קנוני: גמרא (1) -> ראשונים (3) -> שו"ע (2) -> אחרונים (4) -> שו"תים (5)
    canonical_order = {1: 1, 3: 2, 2: 3, 4: 4, 5: 5}
    balanced_sources.sort(key=lambda item: canonical_order.get(item[0], 6))

    retrieved_texts = []
    for prio, disp_ref, text in balanced_sources:
        retrieved_texts.append(f"[{disp_ref}]\n{text}")

    return retrieved_texts

search_sefaria_sources = get_sefaria_sources_robust

@st.cache_data(ttl=86400, show_spinner=False)
def search_sefaria_fast(query: str, history=None, max_results: int = 14):
    """
    שליפה מובנית מספריא באמצעות מנוע השליפה המשופר והמתועדף (get_sefaria_sources_robust)
    ומחזירה רשימת אובייקטים מובנים עבור ממשק המשתמש ושכבת האימות,
    כאשר מקורות ראשוניים (חז"ל, רמב"ם, שו"ע) מופיעים בראש.
    """
    raw_contexts = get_sefaria_sources_robust(query, history=history)
    results = []
    for item in raw_contexts[:max_results]:
        lines = item.split("\n", 1)
        if len(lines) == 2:
            ref_clean = lines[0].strip("[]")
            text_clean = lines[1].strip()
            results.append({
                "ref": ref_clean,
                "text": text_clean,
                "url": f"https://www.sefaria.org/{urllib.parse.quote(ref_clean)}",
                "priority": classify_source_priority(ref_clean)
            })
        elif item.strip():
            results.append({
                "ref": query.strip(),
                "text": item.strip(),
                "url": f"https://www.sefaria.org/{urllib.parse.quote(query.strip())}",
                "priority": 5
            })
    return results

@st.cache_data(ttl=86400, show_spinner=False)
def search_sefaria_and_local(query, history=None, max_results=14):
    """שילוב מיידי של מקורות מקומיים עם תוצאות ספריא המתועדפות לפי קטגוריות ראשיות"""
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
                        ref_clean = ref_title.strip()
                        sources.append({
                            "ref": ref_clean,
                            "text": clean_html_tags(entry.get("content", "")),
                            "url": "מאגר תורני מקומי מאומת",
                            "priority": classify_source_priority(ref_clean)
                        })
        except Exception:
            pass

    # 2. שליפה מספריא בעדיפות למקורות ראשוניים, אחרונים ושו"תים
    try:
        sefaria_sources = search_sefaria_fast(query, history=history, max_results=max_results)
        for s in sefaria_sources:
            if not any(existing["ref"] == s["ref"] for existing in sources):
                sources.append(s)
            if len(sources) >= max_results:
                break
    except Exception:
        pass

    # סידור במסלול פסיקה קנוני: גמרא (1) -> ראשונים (3) -> שו"ע (2) -> אחרונים (4) -> שו"תים (5)
    canonical_order = {1: 1, 3: 2, 2: 3, 4: 4, 5: 5}
    sources.sort(key=lambda s: canonical_order.get(s.get("priority", 5), 6))
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
SYSTEM_PROMPT = """אתה עוזר מחקר תורני, הלכתי ולמדני. תפקידך להציג ניתוח מעמיק, ברור ומסודר של הסוגיה.

חובה עליך לבנות כל תשובה בדיוק לפי ההיררכיה הבאה (מימין לשמאל / מלמעלה למטה):

1. פסוקים (אם יש בסוגיה)
2. מקור בגמרא (ומדרשי הלכה הקשורים לסוגיה)
3. שיטות הראשונים (רש"י, תוספות, רמב"ם, ראב"ד, רמב"ן, רשב"א וכדומה)
4. פסק השולחן ערוך והרמ"א (אם יש בסוגיה)
5. אחרונים (נושאי כלי השו"ע, שו"תים, וגדולי האחרונים)
6. הלכה למעשה (חובה לפרט לפי מנהגי ופסיקות עדות: אשכנז, ספרד, ותימן)

חוקי ברזל למקורות באחרונים, ציטוטים ואמת תורנית:
- חובת הבאת מראי מקומות מדויקים באחרונים:
  בסעיף 5 ('אחרונים') ובסעיף 6 ('הלכה למעשה'), חובה מוחלטת לציין מראי מקומות מדויקים ומפורשים מגדולי האחרונים (משנה ברורה עם ציון סימן וסעיף קטן, ביאור הלכה, כף החיים, מגן אברהם, ט"ז, ש"ך, פתחי תשובה, ערוך השולחן, חזון איש, שו"ת יביע אומר, שו"ת אגרות משה, שו"ת ציץ אליעזר, שו"ת מנחת יצחק, ילקוט יוסף וכו').
  * אם המקור נשלף מהמאגר (מופיע ב-Context): צטט מתוכו ישירות במרכאות בדיוק מילולי מוחלט (Verbatim).
  * אם המקור באחרונים לא נשלף במלואו כציטוט ב-Context: אין להסתפק באמירה כללית, אלא חובה לציין את מראה המקום המדויק (שם הספר, חלק, סימן, סעיף קטן או סימן בשו"ת) ולבאר את שיטתו ופסיקתו בלשון תורנית מדויקת. לעולם אין להשאיר את סעיף האחרונים ללא מראי מקומות מפורשים!
- איסור מוחלט על המצאת מקורות (Zero Hallucination): כל ספר, סימן או שו"ת שמובא חייב להיות אמיתי וקיים בארון הספרים היהודי. חל איסור מוחלט להמציא ספרים או סימנים בדיוניים.
- דיוק מילולי מוחלט (Verbatim): שימוש במרכאות שמור אך ורק לטקסטים שהועתקו אות-באות מתוך המקורות שנשלפו בפועל מהמאגר. אין לשים במרכאות שום ביאור או מראה מקום שלא נשלף במאגר.
- אמת עובדתית ותורנית ללא משוא פנים (No Sycophancy): לעולם אל תסכים עם שגיאה עובדתית של המשתמש רק כדי לרצותו! אם המשתמש טועה בייחוס מימרא, שם אמורא או פסק (למשל: ייחוס דברי רבא לרבה וכדומה), העמד דברים על דיוקם בכבוד ובבהירות על פי המקורות האמיתיים של חז"ל.
- עברית בלבד: כל מראי המקומות, שמות הספרים והמחברים חייבים להופיע בלשון הקודש/עברית בלבד (ללא שמות באנגלית).
- חובת הבאת מקורות הש"ס: בסעיף 2 ('מקור בגמרא'), הבא תמיד את שם המסכת והדף האמיתי, וכאשר המקור נשלף מהמאגר - צטט מתוכו ישירות במרכאות."""

PROMPTS = {
    "פשוט ומונגש": f"""{SYSTEM_PROMPT}

דגשי סגנון - פשוט ומונגש:
* הצג את התשובה בדיוק לפי 6 השלבים ההיררכיים (פסוקים, גמרא, ראשונים, שו"ע ורמ"א, אחרונים, הלכה למעשה לעדות: אשכנז, ספרד ותימן) בשפה בהירה ומאירת עיניים.
* באר את המושגים והסברות בגובה העיניים.
* בסעיף 5 (אחרונים) ובסעיף 6 (הלכה למעשה) הבא תמיד מראי מקומות מדויקים (משנה ברורה סימן וס"ק, כף החיים, שו"תים וכו') עם הסבר בהיר.
* ציטוטים מהמקורות שלב בתוך מרכאות בדיוק מילולי מוחלט (אות-באות מהמקורות שנשלפו) עם מראה מקום עברי בלבד.
* חובה לסיים כל תשובה במשפט: "הערה: תוכן זה מיועד ללימוד בלבד, ואין לפסוק ממנו הלכה למעשה."
""",
    "סגנון שו\"ת": f"""{SYSTEM_PROMPT}

דגשי סגנון - סגנון שו"ת:
* מבנה תשובה מובהק של שאלות ותשובות העוקב בדיוק אחר 6 השלבים ההיררכיים (פסוקים, מקור בגמרא, ראשונים, שו"ע ורמ"א, אחרונים, הלכה למעשה עם פירוט מנהגי העדות: אשכנז, ספרד ותימן).
* לשון תורנית רהוטה ומנומקת היטב.
* סעיף 5 (אחרונים) יכלול דיון מנומק עם מראי מקומות מדויקים מנושאי הכלים, המשנה ברורה וספרי השו"ת המרכזיים.
* ציטוטים מהמקורות הבא בתוך מרכאות בדיוק מילולי מוחלט (Verbatim) עם מראי מקומות עבריים בלבד.
* חובה לסיים כל תשובה במשפט: "הערה: תוכן זה מיועד ללימוד בלבד, ואין לפסוק ממנו הלכה למעשה."
""",
    "הכנה למבחני רבנות": f"""{SYSTEM_PROMPT}

כאשר המצב שנבחר הוא "הכנה למבחני רבנות", עליך לנסח את התשובה בצורה יסודית, למדנית ומורחבת המותאמת לבחינות הרבנות הראשית, בדיוק לפי הסדר וההיררכיה הבאים:

1. תנ"ך (פסוקים ומקורות מן המקרא, אם יש בסוגיה)
2. גמרא (סוגיית הגמרא, מיקומה במסכת, ומדרשי הלכה הקשורים)
3. ראשונים:
   - דגש מרכזי על שיטת הרמב"ם (כולל נושאי כליו: מגיד משנה, כסף משנה, לחם משנה וכד')
   - הרי"ף והרא"ש (אם מופיעים בסוגיה)
   - ראשונים נוספים (רש"י, תוספות, רמב"ן, רשב"א, ר"ן, מאירי) - נא להרחיב בשיטותיהם!
4. טור ובית יוסף (הצגת דברי הטור ודיוני הבית יוסף המרכזיים בבירור יסודות המכלול)
5. שו"ע ונושאי הכלים:
   - פסק השולחן ערוך והרמ"א
   - הרחבה בנושאי הכלים והאחרונים המרכזיים: משנה ברורה עם סימנים וסעיפים קטנים, ביאור הלכה, שער הציון, כף החיים, ערוך השולחן, ט"ז, מגן אברהם (באורח חיים); ש"ך, ט"ז, פתחי תשובה (ביורה דעה); חלקת מחוקק, בית שמואל (באבן העזר); קצות החושן, נתיבות המשפט (בחושן משפט).
6. הלכה למעשה (סיכום השורה התחתונה לפסיקה, תוך חלוקה ברורה לפי מנהגי עדות: אשכנז, ספרד, ותימן, והבאת שו"תים כגון: יביע אומר, אגרות משה, ציץ אליעזר, ילקוט יוסף).

חוקי איכות וציטוט:
- הרחבה למדנית: הרחב ככל הניתן בביאור סברות הראשונים ונושאי הכלים של הרמב"ם והשו"ע - מודל זה מיועד לשינון וללימוד עיון לקראת מבחני רבנות.
- ציטוט מילולי (Verbatim): כל ציטוט מתוך המקורות חייב להיות מועתק בדיוק מוחלט אות-באות מתוך המקורות שנשלפו.
- עברית בלבד: כל שמות הספרים, המסכתות והמראי מקומות ייכתבו בלשון הקודש/עברית בלבד.
- חובה לסיים כל תשובה במשפט: "הערה: תוכן זה מיועד ללימוד בלבד, ואין לפסוק ממנו הלכה למעשה."
""",
    "ישיבתי-למדני": f"""{SYSTEM_PROMPT}

דגשי סגנון - ישיבתי-למדני:
* פתח מהלך למדני מעמיק המובנה לפי 6 השלבים: פסוקים, בירור יסוד הגמרא, שיטות הראשונים, פסק השו"ע והרמ"א, חקירות האחרונים וראשי הישיבות (קצות החושן, נתיבות המשפט, ר' שמעון שקופ, ברכת שמואל, אגרות משה, חזון איש, יביע אומר עם מראי מקומות מדויקים), ומסקנת ההלכה למעשה לפי מנהגי העדות (אשכנז, ספרד ותימן).
* קושיות, תירוצים, דיוקים וחילוקי סברות בעומק העיון.
* ציטוטים מדויקים הבא בתוך מרכאות בדיוק מוחלט (אות-באות מתוך המקורות שנשלפו).
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
    # אם המשתמש הזכיר במפורש בבקשה "הכנה למבחני רבנות" או "רבנות" - נחיל סגנון זה
    if any(keyword in prompt for keyword in ["רבנות", "מבחני רבנות", "הכנה למבחני רבנות", "בחינות הרבנות"]):
        style = "הכנה למבחני רבנות"
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

class SugyaAnswer(str):
    """מחלקת תשובה המרחיבה מחרוזת טקסט ומכילה גם מקורות ודוח אימות"""
    def __new__(cls, content, sources=None, validation=None):
        obj = super().__new__(cls, content)
        obj.content = content
        obj.sources = sources if sources is not None else []
        obj.validation = validation if validation is not None else {}
        return obj

    def get(self, key, default=None):
        if key == "content":
            return self.content
        elif key == "sources":
            return self.sources
        elif key == "validation":
            return self.validation
        return default

    def __getitem__(self, item):
        if item == "content":
            return self.content
        elif item == "sources":
            return self.sources
        elif item == "validation":
            return self.validation
        return super().__getitem__(item)

def analyze_sugya(messages, style_mode="פשוט ומונגש", use_sefaria=None):
    """
    מנתח סוגיה תורנית בצורה מעמיקה ומהירה:
    שולף מקורות תורניים מוסמכים (תנ\"ך, ש\"ס, רמב\"ם, שו\"ע ונושאי כלים),
    מרכיב את ההקשר ומפעיל את מודל השפה לקבלת פסק ומסקנות עם אימות מילולי מחמיר.
    """
    if isinstance(messages, list) and len(messages) > 0:
        last_msg = messages[-1]
        user_prompt = last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg)
        chat_history = messages
    else:
        user_prompt = str(messages)
        chat_history = None

    should_use_sefaria = use_sefaria if use_sefaria is not None else globals().get("use_sefaria", True)
    
    sources = []
    if should_use_sefaria:
        try:
            sources = search_sefaria_and_local(user_prompt, history=chat_history, max_results=10)
        except Exception:
            try:
                sources = search_sefaria_fast(user_prompt, history=chat_history, max_results=10)
            except Exception:
                sources = []

    context_sources = format_context_sources(sources)
    try:
        response_text, validation_report = get_gemini_response(user_prompt, sources, context_sources, style_mode)
    except Exception as e:
        response_text = f"אירעה שגיאה בניתוח הסוגיה: {str(e)}"
        validation_report = {"is_valid": False, "details": str(e)}

    return SugyaAnswer(response_text, sources=sources, validation=validation_report)


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

    style_mode = learning_style

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
            # רשימת המשפטים המעודכנת
            messages_list = [
                "יהונתן חושב...",
                "יהונתן עומד לפתור את הסוגיה...",
                "יהונתן מריץ חיפוש בראש וכל התורה כולה לנגד עיניו...",
                "ליהונתן יש פיתרון, וחושב על כיוונים אחרים...",
                "יהונתן צריך ריכוז...",
                "יהונתן מקבץ כל מיני שו\"תים שנזכר בהם בהקשר לשאלה...",
                "יהונתן מבין שהשאלה מסובכת, אך אין שאלה שתישאר לא פתורה...",
                "יהונתן מעיין בשיטות הראשונים...",
                "יהונתן מדייק בלשון השולחן ערוך והרמ\"א..."
            ]

            # שימוש ברכיב st.status עם דחיפת שינויים בלייב ובדיקת סיום מהירה
            with st.status(messages_list[0], expanded=False) as status:
                with ThreadPoolExecutor() as executor:
                    future = executor.submit(analyze_sugya, current_chat["messages"], style_mode)
                    
                    idx = 0
                    last_update = time.time()
                    
                    while not future.done():
                        # עדכון הטקסט בתיבה בלייב מדי 2.5 שניות
                        if time.time() - last_update >= 2.5:
                            idx += 1
                            current_msg = messages_list[idx % len(messages_list)]
                            status.update(label=current_msg)
                            last_update = time.time()
                        
                        time.sleep(0.1)
                    
                    answer = future.result()
                    status.update(label="יהונתן סיים לפתור את הסוגיה בהצלחה!", state="complete", expanded=False)

            st.markdown(str(answer))

            sources = getattr(answer, "sources", [])
            validation_report = getattr(answer, "validation", {})
            if sources:
                with st.expander(f"📚 מקורות שנשלפו ואומתו בזמן אמת ({len(sources)})", expanded=False):
                    if validation_report.get("is_valid"):
                        st.success("✅ **אימות מקורות קפדני (100% Verbatim):** כל הציטוטים נבדקו ואומתו מילה-במילה מול המקורות המקוריים.")
                    else:
                        st.warning(f"⚠️ {validation_report.get('details')}")
                    for s in sources:
                        st.markdown(f"**[{s['ref']}]** — [קישור ישיר למקור בספריא]({s['url']})")
                        st.markdown(f"> *{s['text'][:350]}...*")
            elif "המידע המבוקש אינו מופיע במקורות שנשלפו" in str(answer):
                st.info("ℹ️ **דיווח על היעדר מידע:** המודל פעל על פי חוקי הברזל ולא המציא מידע שלא נשלף.")

        current_chat["messages"].append({
            "role": "assistant",
            "content": str(answer),
            "sources": sources,
            "validation": validation_report
        })
        save_user_data(st.session_state.user_data)
        st.rerun()

else:
    st.title("📜 סוגיה בעיון - עוזר תורני אישי")
    st.caption("מנוע בינה מלאכותית מבוסס מקורות לניתוח סוגיות הלכתיות ולמדניות")
    st.info("👈 בחר שיחה מסרגל הצד, או לחץ על **'💬 שיחה חדשה'** כדי להתחיל בלמידה.")
