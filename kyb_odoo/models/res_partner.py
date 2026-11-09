# -*- coding: utf-8 -*-
"""
KYB integration for res.partner — Real-time NIF auto-lookup, temporal audit, and contact autocomplete.

This module extends ``res.partner`` with:
    1. Custom fields for Algerian corporate identity (NIF, RC, NIS, Article d'Imposition, CNRC status).
    2. An ``onchange`` handler that auto-populates partner data from the KYB API (by Digidev)
       when a NIF or RC is entered.
    3. A ``_name_search`` override that queries the KYB fuzzy search endpoint
       for real-time autocomplete in many2one partner selector fields.
    4. Resilient multi-runtime support: seamlessly uses the official ``conforme`` SDK if installed,
       or falls back to native Python ``requests`` with zero external package requirements.
"""

import logging
import re
from typing import Optional, Tuple

import requests
from odoo import api, fields, models, _
from odoo.exceptions import UserError
try:
    from markupsafe import Markup
except ImportError:
    Markup = lambda s: s

_logger = logging.getLogger(__name__)

# ──────────────── Official Algerian RC (Décret 05-468 & 18-112) Utilities ────────────────
OFFICIAL_RC_REGEX = re.compile(r'^(0[0-9]|[1-6]\d|8[0-9]|9[0-9]|[0-9])/00-(\d{1,10})([ABCDabcd])(\d{2})?$')
COMPRESSED_RC_REGEX = re.compile(r'^(0[0-9]|[1-6]\d|8[0-9]|9[0-9]|[0-9])([ABCDabcd])(\d{1,10})$')
SPACED_RC_REGEX_1 = re.compile(r'^(0[0-9]|[1-6]\d|8[0-9]|9[0-9]|[0-9])\s*[-/ ]?\s*([ABCDabcd])\s*[-/ ]?\s*(\d{1,10})(?:\s*[-/ ]?\s*(\d{2}))?$')
SPACED_RC_REGEX_2 = re.compile(r'^(0[0-9]|[1-6]\d|8[0-9]|9[0-9]|[0-9])\s*[/ -]?\s*(?:00\s*[/ -]?\s*)?(\d{1,10})\s*[-/ ]?\s*([ABCDabcd])(?:\s*[-/ ]?\s*(\d{2}))?$')
ARABIC_RC_REGEX_1 = re.compile(r'^(0[0-9]|[1-6]\d|8[0-9]|9[0-9]|[0-9])\s*[-/ ]?\s*([أابجدABCDabcd])\s*[-/ ]?\s*(\d{1,10})(?:\s*[-/ ]?\s*(\d{2}))?$')
ARABIC_RC_REGEX_2 = re.compile(r'^(0[0-9]|[1-6]\d|8[0-9]|9[0-9]|[0-9])\s*[/ -]?\s*(?:00\s*[/ -]?\s*)?(\d{1,10})\s*[-/ ]?\s*([أابجدABCDabcd])(?:\s*[-/ ]?\s*(\d{2}))?$')
ARABIC_TO_LATIN_CATEGORY = {'أ': 'A', 'ا': 'A', 'ب': 'B', 'ج': 'C', 'د': 'D'}

def parse_algerian_rc(raw: Optional[str]) -> Optional[dict]:
    """Parse any Algerian RC format into canonical components (69 Wilayas + Wilaya 00 National, Loi 26-06 + 80-99 Pre-2000 Legacy)."""
    if not raw or not isinstance(raw, str):
        return None
    clean = raw.strip()
    if len(clean) < 5 or len(clean) > 30 or re.search(r'[a-zA-Z]{4,}', clean):
        return None
    wilaya, category, register_number, year = '', 'B', '', None
    m = OFFICIAL_RC_REGEX.match(clean)
    if m:
        wilaya, register_number, category, year = m.group(1).zfill(2), m.group(2), m.group(3).upper(), m.group(4)
    else:
        m = COMPRESSED_RC_REGEX.match(clean)
        if m:
            wilaya, category, register_number, year = m.group(1).zfill(2), m.group(2).upper(), m.group(3), m.group(1).zfill(2)
        else:
            m = SPACED_RC_REGEX_1.match(clean)
            if m:
                wilaya, category, register_number, year = m.group(1).zfill(2), m.group(2).upper(), m.group(3), m.group(4)
            else:
                m = SPACED_RC_REGEX_2.match(clean)
                if m:
                    wilaya, register_number, category, year = m.group(1).zfill(2), m.group(2), m.group(3).upper(), m.group(4)
                else:
                    m = ARABIC_RC_REGEX_1.match(clean)
                    if m:
                        wilaya, category, register_number, year = m.group(1).zfill(2), ARABIC_TO_LATIN_CATEGORY.get(m.group(2), 'B'), m.group(3), m.group(4)
                    else:
                        m = ARABIC_RC_REGEX_2.match(clean)
                        if m:
                            wilaya, register_number, category, year = m.group(1).zfill(2), m.group(2), ARABIC_TO_LATIN_CATEGORY.get(m.group(3), 'B'), m.group(4)

    if not wilaya or not register_number or not category:
        return None
    try:
        w_num = int(wilaya)
        if (w_num < 0 or w_num > 69) and (w_num < 80 or w_num > 99):
            return None
    except ValueError:
        return None


    padded_reg = register_number.zfill(7)
    return {
        'wilaya': wilaya,
        'category': category,
        'register_number': padded_reg,
        'year': year,
        'compressed': f'{wilaya}{category}{padded_reg}',
        'official': f'{wilaya}/00-{padded_reg}{category}{year}' if year else f'{wilaya}/00-{padded_reg}{category}'
    }

def format_official_rc(
    raw: Optional[str],
    fallback_year: Optional[str] = None,
    fallback_wilaya: Optional[str] = None,
) -> Optional[str]:
    """Format any Algerian RC into official Décret 05-468 format: WW/00-XXXXXXX[A|B|C|D]YY."""
    if not raw or not isinstance(raw, str):
        return None
    clean = raw.strip()
    # INVARIANT (certified 2026-11-06): the RC prefix is copied VERBATIM from the registry.
    # It must NEVER be rewritten from the NIF/address Wilaya. CNRC e-registrations use the
    # registration year as prefix (e.g. 24/00-1052733B24 for a company seated in Alger),
    # so any Wilaya-based "correction" fabricates an RC that does not exist.
    # `fallback_wilaya` is accepted for signature compatibility and intentionally ignored.
    if re.match(r'^(0[0-9]|[1-6]\d|8[0-9]|9[0-9]|[0-9])/00-(\d{7})([ABCDabcd])(\d{2})$', clean):
        return clean

    p = parse_algerian_rc(clean)
    if not p:
        return clean
    y = ''
    if fallback_year:
        s_yr = str(fallback_year).strip()
        m4 = re.search(r'(\d{4})', s_yr)
        m2 = re.match(r'^(\d{2})$', s_yr) if not m4 else None
        m = m4 or m2 or re.search(r'(\d{2})', s_yr)
        if m:
            y = m.group(1)[-2:]
    if not y and p.get('year'):
        y = str(p['year']).zfill(2)
    if not y:
        m_prefix = re.match(r'^(\d{2})[ABCDabcd]', clean)
        if m_prefix:
            y = m_prefix.group(1)

    final_w = p['wilaya']
    if y:
        return f"{final_w}/00-{p['register_number']}{p['category']}{y}"
    return f"{final_w}/00-{p['register_number']}{p['category']}"

def _clean_algerian_representant(raw: Optional[str]) -> Optional[str]:
    """
    Cleans representative / gérant string extracted from BOAL legal announcements or CNRC:
    - Strips leading action verbs: 'Désigner Mme X...', 'Nomination de M. Y...', 'Gérant: Z...'
    - Strips trailing roles and conjunctions: '...en qualité de gérant et', '... et', '... ou', trailing commas.
    """
    if not raw or not isinstance(raw, str):
        return False
    s = raw.strip()
    if not s or s.lower() in ("none", "null", "false", "-", "n/a"):
        return False

    # Strip leading BOAL publication verbs/markers
    s = re.sub(
        r"^(?:d[eé]signer|nommer|nomination\s+(?:de\s+|d['’])?|g[eé]rance\s+(?:par\s+|assur[eé]e\s+par\s+)?|renouvellement\s+(?:de\s+)?|confier\s+la\s+g[eé]rance\s+[aà]\s+|g[eé]rant\s*:?|repr[eé]sentant\s*:?)\s*",
        "",
        s,
        flags=re.IGNORECASE,
    )

    # Strip trailing role annotations (e.g. 'en qualité de gérant...', 'pour une durée...')
    s = re.sub(
        r"\s+(?:en\s+qualit[eé]\s+(?:de\s+|d['’]).*|en\s+tant\s+que.*|comme\s+g[eé]rant.*|pour\s+une\s+dur[eé]e.*|avec\s+(?:tous\s+)?les\s+pouvoirs.*)$",
        "",
        s,
        flags=re.IGNORECASE,
    )

    # Strip trailing conjunctions, commas, semicolons, dashes
    s = re.sub(r"\s+(?:et|ou|,|;|pour|avec|-|\/)\s*$", "", s, flags=re.IGNORECASE)
    s = s.strip(" ,.-;/")
    if len(s) < 2:
        return False
    return s

def _deduce_algerian_creation_date(nif: Optional[str] = None, rc: Optional[str] = None) -> Optional[str]:
    """
    Deterministically deduces the creation/immatriculation date ('YYYY-01-01')
    from Algerian corporate NIF (00YYWWXXXXXXXCC -> 20YY-01-01) or official RC.
    Guarantees 'Date d'Immatriculation' is never empty when year is known from identifiers.
    """
    if nif:
        clean_nif = re.sub(r"[^\d]", "", str(nif))
        if len(clean_nif) in (15, 20):
            if clean_nif.startswith("00"):
                yy_str = clean_nif[2:4]
            elif clean_nif.startswith("0"):
                yy_str = clean_nif[1:3]
            else:
                yy_str = ""
            if yy_str and yy_str.isdigit():
                yy = int(yy_str)
                full_y = 2000 + yy if yy <= 50 else 1900 + yy
                return f"{full_y}-01-01"
    if rc:
        clean_rc = str(rc).strip()
        m_official = re.search(r"[ABCDabcd](\d{2})$", clean_rc)
        if m_official:
            yy = int(m_official.group(1))
            full_y = 2000 + yy if yy <= 50 else 1900 + yy
            return f"{full_y}-01-01"
        m_comp = re.match(r"^(\d{2})[ABCDabcd]", clean_rc)
        if m_comp:
            yy = int(m_comp.group(1))
            full_y = 2000 + yy if yy <= 50 else 1900 + yy
            return f"{full_y}-01-01"
    return False

def _normalize_algerian_date(val: Optional[any]) -> Optional[str]:
    """
    Safely normalizes any date representation (ISO, slash DD/MM/YYYY, datetime, etc.)
    into canonical 'YYYY-MM-DD' for Odoo fields.Date. Returns False if missing or unparseable.
    """
    if not val:
        return False
    if hasattr(val, "strftime"):
        return val.strftime("%Y-%m-%d")
    s = str(val).strip()
    if not s or s.lower() in ("none", "null", "false", "n/a", "-"):
        return False
    m_iso = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})", s)
    if m_iso:
        y, m, d = m_iso.group(1), m_iso.group(2).zfill(2), m_iso.group(3).zfill(2)
        return f"{y}-{m}-{d}"
    m_fr = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})", s)
    if m_fr:
        d, m, y = m_fr.group(1).zfill(2), m_fr.group(2).zfill(2), m_fr.group(3)
        return f"{y}-{m}-{d}"
    m_year = re.match(r"^(\d{4})$", s)
    if m_year:
        return f"{m_year.group(1)}-01-01"
    return False
 
 
ALGERIAN_WILAYAS_69 = {
    "01": "Adrar", "02": "Chlef", "03": "Laghouat", "04": "Oum El Bouaghi",
    "05": "Batna", "06": "Béjaïa", "07": "Biskra", "08": "Béchar",
    "09": "Blida", "10": "Bouira", "11": "Tamanrasset", "12": "Tébessa",
    "13": "Tlemcen", "14": "Tiaret", "15": "Tizi Ouzou", "16": "Alger",
    "17": "Djelfa", "18": "Jijel", "19": "Sétif", "20": "Saïda",
    "21": "Skikda", "22": "Sidi Bel Abbès", "23": "Annaba", "24": "Guelma",
    "25": "Constantine", "26": "Médéa", "27": "Mostaganem", "28": "M'Sila",
    "29": "Mascara", "30": "Ouargla", "31": "Oran", "32": "El Bayadh",
    "33": "Illizi", "34": "Bordj Bou Arréridj", "35": "Boumerdès",
    "36": "El Tarf", "37": "Tindouf", "38": "Tissemsilt", "39": "El Oued",
    "40": "Khenchela", "41": "Souk Ahras", "42": "Tipaza", "43": "Mila",
    "44": "Aïn Defla", "45": "Naâma", "46": "Aïn Témouchent", "47": "Ghardaïa",
    "48": "Relizane", "49": "Timimoun", "50": "Bordj Badji Mokhtar",
    "51": "Ouled Djellal", "52": "Béni Abbès", "53": "In Salah",
    "54": "In Guezzam", "55": "Touggourt", "56": "Djanet",
    "57": "El M'Ghair", "58": "El Meniaa",
    "59": "Aflou", "60": "Barika", "61": "El Kantara", "62": "Bir El Ater",
    "63": "El Aricha", "64": "Ksar Chellala", "65": "Aïn Oussara",
    "66": "Messaad", "67": "Ksar El Boukhari", "68": "Bou Saâda",
    "69": "El Abiodh Sidi Cheikh",
}

_NORM_WILAYA_TO_CODE = {}
for code, name in ALGERIAN_WILAYAS_69.items():
    clean_k = re.sub(r"[^a-z0-9]", "", name.lower())
    _NORM_WILAYA_TO_CODE[clean_k] = code
    unaccented = (
        name.lower()
        .replace("é", "e")
        .replace("è", "e")
        .replace("ï", "i")
        .replace("â", "a")
    )
    _NORM_WILAYA_TO_CODE[re.sub(r"[^a-z0-9]", "", unaccented)] = code

# In-memory LRU/TTL cache for recent resolve/enrich results: {normalized_key: (timestamp, result_dict)}
# Used by create() and write() to backfill exact registry dates and prevent redundant billing.
_KYB_RECENT_RESOLVE_CACHE = {}

def _split_algerian_commune_wilaya(raw_str: Optional[str]) -> Tuple[str, str, str]:
    """
    Decomposes any Algerian administrative address or wilaya string into:
    (commune, wilaya, wilaya_code).
    Handles:
    - CNRC dual column format: 'IBN ZIAD/CONSTANTINE' -> ('Ibn Ziad', 'Constantine', '25')
    - Duplicate dual column: 'CONSTANTINE/CONSTANTINE' -> ('', 'Constantine', '25')
    - Code dash format: '25 - Constantine' -> ('', 'Constantine', '25')
    - Bare wilaya name: 'Constantine' -> ('', 'Constantine', '25')
    """
    if not raw_str or not isinstance(raw_str, str):
        return ("", "", "")
    s = raw_str.strip()
    if not s or s.lower() in ("none", "null", "false", "-", "n/a"):
        return ("", "", "")

    raw_commune = ""
    raw_wilaya = ""

    if "/" in s:
        parts = [p.strip() for p in s.split("/") if p.strip()]
        if len(parts) >= 2:
            raw_commune = parts[0]
            raw_wilaya = parts[-1]
        elif len(parts) == 1:
            raw_wilaya = parts[0]
    else:
        m_dash = re.match(r"^(\d{1,2})\s*[-:]\s*(.+)$", s)
        if m_dash:
            code_candidate = m_dash.group(1).zfill(2)
            name_candidate = m_dash.group(2).strip()
            if code_candidate in ALGERIAN_WILAYAS_69:
                return ("", ALGERIAN_WILAYAS_69[code_candidate], code_candidate)
            raw_wilaya = name_candidate
        else:
            raw_wilaya = s

    # Match raw_wilaya to canonical 69 Wilayas
    wilaya_clean = raw_wilaya.strip().title()
    wilaya_code = ""

    m_num = re.match(r"^(\d{1,2})\b", raw_wilaya.strip())
    if m_num and m_num.group(1).zfill(2) in ALGERIAN_WILAYAS_69:
        wilaya_code = m_num.group(1).zfill(2)
        wilaya_clean = ALGERIAN_WILAYAS_69[wilaya_code]
    else:
        norm_key = re.sub(r"[^a-z0-9]", "", raw_wilaya.lower())
        if norm_key in _NORM_WILAYA_TO_CODE:
            wilaya_code = _NORM_WILAYA_TO_CODE[norm_key]
            wilaya_clean = ALGERIAN_WILAYAS_69[wilaya_code]

    # Clean commune
    commune_clean = raw_commune.strip().title()
    if commune_clean.lower() == wilaya_clean.lower():
        commune_clean = ""

    return (commune_clean, wilaya_clean, wilaya_code)


def _unaccent_lower(text: str) -> str:
    return (
        (text or "")
        .lower()
        .replace("é", "e")
        .replace("è", "e")
        .replace("ê", "e")
        .replace("ë", "e")
        .replace("ï", "i")
        .replace("î", "i")
        .replace("â", "a")
        .replace("à", "a")
        .replace("ô", "o")
        .replace("û", "u")
    )


def _strip_trailing_locality(street_str: str, locality: str) -> str:
    """Strips a trailing city/commune/wilaya token from the end of a street string to avoid repetition."""
    if not street_str or not locality:
        return street_str
    s = street_str.strip()
    loc_norm = re.sub(r"[^a-z0-9]+", " ", _unaccent_lower(locality)).strip()
    if not loc_norm:
        return s
    # Match trailing locality (with optional leading comma/dash/space)
    words = s.split()
    loc_words = loc_norm.split()
    if len(words) > len(loc_words):
        tail = " ".join(words[-len(loc_words):]).strip(" ,.-/()")
        tail_norm = re.sub(r"[^a-z0-9]+", " ", _unaccent_lower(tail)).strip()
        if tail_norm == loc_norm:
            s = " ".join(words[:-len(loc_words)]).strip(" ,.-/")
    return s


ALGERIAN_COMMUNE_POSTAL_CODES = {
    "bab ezzouar": "16311", "dar el beida": "16100", "rouiba": "16039", "reghaia": "16043",
    "kouba": "16050", "cheraga": "16053", "hydra": "16035", "alger": "16000", "alger centre": "16000",
    "sidi m'hamed": "16014", "bir mourad rais": "16005", "birkhadem": "16029", "dely ibrahim": "16047",
    "ben aknoun": "16028", "el biar": "16030", "bouzareah": "16032", "draria": "16055",
    "ouled fayet": "16094", "saoula": "16093", "staoueli": "16062", "zeralda": "16063",
    "birtouta": "16086", "baraki": "16210", "el harrach": "16200", "hussein dey": "16040",
    "constantine": "25000", "sidi mabrouk": "25003", "ibn ziad": "25130", "el khroub": "25100",
    "ain smara": "25140", "hamma bouziane": "25230", "didouche mourad": "25210",
    "setif": "19000", "el eulma": "19600", "oran": "31000", "es senia": "31100", "bir el djir": "31130",
    "batna": "05000", "kechida": "05005", "barika": "05001", "blida": "09000", "boufarik": "09400",
    "ouled yaich": "09100", "guelma": "24000", "annaba": "23000", "el bouni": "23200",
    "tlemcen": "13000", "bejaia": "06000", "akbou": "06200", "tizi ouzou": "15000",
    "boumerdes": "35000", "khemis el khechna": "35310", "tipaza": "42000", "kolea": "42400",
    "bba": "34000", "bordj bou arreridj": "34000", "mostaganem": "27000", "chlef": "02000",
    "biskra": "07000", "skikda": "21000", "jijel": "18000", "medea": "26000",
}

_NORM_COMMUNE_TO_ZIP = {re.sub(r"[^a-z0-9]", "", k.lower()): v for k, v in ALGERIAN_COMMUNE_POSTAL_CODES.items()}


def _parse_algerian_address_components(
    raw_adresse: Optional[str],
    raw_wilaya: Optional[str],
    raw_code_postal: Optional[str] = None,
    raw_nif: Optional[str] = None,
) -> dict:
    """
    [ESTABLISHED INVARIANT - DO NOT MODIFY OR REINVENT]
    Parses CNRC/DGI Algerian address data into clean, non-redundant Odoo fields:
    1. street (Rue): Physical street / lot / cité / building ONLY.
       - Strips inline ', Commune X, Wilaya de Y' clauses.
       - Strips trailing Commune or Wilaya token from the end (e.g. '... CITÉ BOUAROUA SETIF' -> '... CITÉ BOUAROUA').
       - If raw_adresse is only the bare Wilaya/Commune name, sets street = False to prevent duplication.
    2. street2 (Rue 2...): ALWAYS False. NEVER put 'Commune de ...' in street2 (Commune is Ville/city, not a 2nd street line).
    3. city (Ville): Single canonical Commune name (or accented Wilaya chef-lieu when Commune == Wilaya).
       STRICTLY ISOLATED from the Wilaya — NEVER joins Commune to Wilaya.
    4. zip (Code postal): 5-digit Algerian postal code. If missing from CNRC, derives from commune or fallback Wilaya code (WW000).
    5. wilaya_name, wilaya_code: Pure canonical Wilaya name and 2-digit code for state_id (res.country.state).
       NEVER contains a slash '/' or a commune prefix (e.g. 'Constantine', NEVER 'Ibn Ziad/Constantine').
    """
    adresse_str = (raw_adresse or "").strip()
    wilaya_str = (raw_wilaya or "").strip()
    cp_str = (raw_code_postal or "").strip()

    # 1. Extract 5-digit postal code and postal locality from code_postal (e.g. 'BERRIANE (47100)' or 'SETIF RP (19000)')
    zip_code = ""
    cp_commune = ""
    if cp_str and cp_str.lower() not in ("none", "null", "false", "-", "n/a"):
        m_cp = re.search(r"\b(\d{5})\b", cp_str)
        if m_cp:
            zip_code = m_cp.group(1)
        cp_label = re.sub(r"\(\s*\d{5}\s*\)", "", cp_str).replace(zip_code, "").strip(" -/,()")
        cp_label = re.sub(r"\b(RP|WILAYA|PRINCIPAL|CENTRE)\b", "", cp_label, flags=re.I).strip(" -/,()")
        if cp_label and len(cp_label) >= 2:
            cp_commune = cp_label.title()

    # 2. Extract base commune/wilaya from raw_wilaya or slash-separated address
    if wilaya_str:
        commune_name, wilaya_name, wilaya_code = _split_algerian_commune_wilaya(wilaya_str)
    else:
        c_tmp, w_tmp, wc_tmp = _split_algerian_commune_wilaya(adresse_str)
        if wc_tmp:
            commune_name, wilaya_name, wilaya_code = c_tmp, w_tmp, wc_tmp
        else:
            commune_name, wilaya_name, wilaya_code = "", "", ""

    # 3. Extract inline 'Commune X' and 'Wilaya de Y' from adresse_str and strip from street
    clean_street = adresse_str
    inline_commune = ""
    inline_wilaya = ""

    m_inline_c = re.search(r"(?:,\s*|\b)Commune\s+(?:de\s+|d['’])?([^,/]+)", clean_street, flags=re.I)
    if m_inline_c:
        inline_commune = m_inline_c.group(1).strip(" ,.-").title()

    m_inline_w = re.search(r"(?:,\s*|\b)Wilaya\s+(?:de\s+|d['’])?([^,/]+)", clean_street, flags=re.I)
    if m_inline_w:
        inline_wilaya = m_inline_w.group(1).strip(" ,.-").title()

    # Remove trailing ', Commune ..., Wilaya de ...' from street so street only holds the physical street/lot/zone
    clean_street = re.sub(r",?\s*\bCommune\s+(?:de\s+|d['’])?[^,/]+", "", clean_street, flags=re.I)
    clean_street = re.sub(r",?\s*\bWilaya\s+(?:de\s+|d['’])?[^,/]+", "", clean_street, flags=re.I)
    clean_street = clean_street.strip(" ,.-/")

    # If clean_street ends with ', <Wilaya>' or ', <Commune> <Wilaya>', strip the trailing wilaya suffix
    m_trail = re.search(r",\s*([^,]+)$", clean_street)
    if m_trail:
        trail_part = m_trail.group(1).strip()
        _, w_tr, wc_tr = _split_algerian_commune_wilaya(trail_part)
        if wc_tr:
            if not inline_wilaya:
                inline_wilaya = w_tr
            clean_street = clean_street[:m_trail.start()].strip(" ,.-/")

    if "/" in clean_street:
        c_sl, w_sl, w_code_sl = _split_algerian_commune_wilaya(clean_street)
        if w_code_sl:
            if c_sl and not inline_commune:
                inline_commune = c_sl
            if w_sl and not inline_wilaya:
                inline_wilaya = w_sl
            clean_street = ""

    # Resolve final Wilaya (STRICT INVARIANT: must NEVER contain slash or commune join)
    if not wilaya_code and inline_wilaya:
        _, w_res, wc_res = _split_algerian_commune_wilaya(inline_wilaya)
        if wc_res:
            wilaya_name, wilaya_code = w_res, wc_res
        elif not wilaya_name:
            wilaya_name = inline_wilaya

    if wilaya_name and "/" in wilaya_name:
        _, w_pure, wc_pure = _split_algerian_commune_wilaya(wilaya_name)
        if w_pure:
            wilaya_name = w_pure
            if wc_pure:
                wilaya_code = wc_pure

    if not wilaya_code and zip_code and zip_code[:2] in ALGERIAN_WILAYAS_69:
        wilaya_code = zip_code[:2]
        wilaya_name = ALGERIAN_WILAYAS_69[wilaya_code]
    elif wilaya_code and wilaya_code in ALGERIAN_WILAYAS_69:
        wilaya_name = ALGERIAN_WILAYAS_69[wilaya_code]

    # Resolve final Commune (and normalize accented chef-lieu name if Commune matches Wilaya)
    final_commune = commune_name or inline_commune or cp_commune
    if final_commune and wilaya_name:
        if _unaccent_lower(final_commune) == _unaccent_lower(wilaya_name):
            final_commune = wilaya_name
        elif wilaya_name and _unaccent_lower(final_commune).startswith(_unaccent_lower(wilaya_name) + " "):
            sub_c = final_commune[len(wilaya_name):].strip(" -/,")
            if len(sub_c) >= 3:
                final_commune = sub_c.title()

    # Strip trailing Wilaya or Commune name from the end of clean_street
    if wilaya_name:
        clean_street = _strip_trailing_locality(clean_street, wilaya_name)
    if final_commune:
        clean_street = _strip_trailing_locality(clean_street, final_commune)
    if wilaya_name:
        clean_street = _strip_trailing_locality(clean_street, wilaya_name)

    # If clean_street is just the bare wilaya/commune name, leave street empty
    if clean_street and (
        (wilaya_name and _unaccent_lower(clean_street) == _unaccent_lower(wilaya_name))
        or (final_commune and _unaccent_lower(clean_street) == _unaccent_lower(final_commune))
    ):
        clean_street = ""

    city_val = final_commune or wilaya_name or ""

    # 4. Fallback 5-digit Postal Code Resolution (GUARANTEES NON-EMPTY POSTAL CODE)
    if not zip_code:
        if final_commune:
            fc_norm = re.sub(r"[^a-z0-9]", "", _unaccent_lower(final_commune))
            if fc_norm in _NORM_COMMUNE_TO_ZIP:
                zip_code = _NORM_COMMUNE_TO_ZIP[fc_norm]
        if not zip_code and adresse_str:
            adr_norm = re.sub(r"[^a-z0-9]", "", _unaccent_lower(adresse_str))
            for c_k, c_zip in _NORM_COMMUNE_TO_ZIP.items():
                if c_k in adr_norm:
                    zip_code = c_zip
                    break
        if not zip_code and wilaya_code:
            w_int = int(wilaya_code) if str(wilaya_code).isdigit() else 0
            if 1 <= w_int <= 58:
                zip_code = f"{w_int:02d}000"

    # Reconcile Geographical Wilaya with Postal Code & NIF (NEVER MIX COMMUNE & WRONG WILAYA)
    # The first 2 digits of an Algerian 5-digit postal code ALWAYS identify the official Wilaya.
    # If zip_code was deduced from the specific commune (e.g. Bab Ezzouar -> 16311),
    # override an erroneous registry Wilaya (e.g. Guelma 24) to keep address geographically pure.
    if zip_code and len(zip_code) == 5 and zip_code[:2] in ALGERIAN_WILAYAS_69:
        zip_wilaya_code = zip_code[:2]
        if wilaya_code != zip_wilaya_code:
            if final_commune:
                fc_norm = re.sub(r"[^a-z0-9]", "", _unaccent_lower(final_commune))
                if fc_norm in _NORM_COMMUNE_TO_ZIP:
                    wilaya_code = zip_wilaya_code
                    wilaya_name = ALGERIAN_WILAYAS_69[wilaya_code]
    if raw_nif:
        clean_n = re.sub(r"[^\d]", "", str(raw_nif))
        if len(clean_n) in (15, 20) and clean_n.startswith("00"):
            nif_w = clean_n[4:6]
            if nif_w in ALGERIAN_WILAYAS_69 and wilaya_code != nif_w:
                if (zip_code and zip_code[:2] == nif_w) or not zip_code:
                    wilaya_code = nif_w
                    wilaya_name = ALGERIAN_WILAYAS_69[wilaya_code]

    return {
        "street": clean_street or False,
        "street2": False,
        "city": city_val or False,
        "zip": zip_code or False,
        "commune_name": final_commune,
        "wilaya_name": wilaya_name,
        "wilaya_code": wilaya_code,
    }
 
 
class _NativeSearchNamespace:
    """Namespace mirroring the official SDK search capabilities."""

    def __init__(self, client: "_NativeKybClient"):
        self._client = client

    def autocomplete(self, query: str, poll: bool = False, live: bool = False) -> list:
        res = self._client.candidates(query, live=live)
        if isinstance(res, dict):
            return res.get("candidates") or res.get("results") or res.get("data") or []
        if isinstance(res, list):
            return res
        return []

def _get_config_param(env, key, default=""):
    """Universally get string config parameter across Odoo 16, 17, 18, 19, and 20."""
    try:
        icp = env["ir.config_parameter"].sudo()
        if hasattr(icp, "search"):
            try:
                rec = icp.search([("key", "=", key)], limit=1)
                if rec and getattr(rec, "value", None) is not None:
                    return rec.value
            except Exception:
                pass
        if hasattr(icp, "get_str"):
            val = icp.get_str(key, default=None)
            if val is not None:
                return val
        if hasattr(icp, "get_param"):
            val = icp.get_param(key, default=default)
            return val if val is not None else default
        if hasattr(icp, "_get"):
            val = icp._get(key)
            if val is not None:
                return val
        return default
    except Exception:
        return default


def _get_config_bool(env, key, default=True):
    """Universally get boolean config parameter across Odoo 16, 17, 18, 19, and 20."""
    try:
        icp = env["ir.config_parameter"].sudo()
        if hasattr(icp, "get_bool"):
            return icp.get_bool(key, default)
        if hasattr(icp, "get_param"):
            val = icp.get_param(key, default=str(default))
            return val == "True" if isinstance(val, str) else bool(val)
        if hasattr(icp, "_get"):
            val = icp._get(key)
            if val is None:
                return default
            return val in ("True", "1", True)
        return default
    except Exception:
        return default


def _set_config_param(env, key, value):
    """Universally set string config parameter across Odoo 16, 17, 18, 19, and 20."""
    try:
        icp = env["ir.config_parameter"].sudo()
        str_val = str(value) if value is not None else ""
        if hasattr(icp, "set_str"):
            return icp.set_str(key, str_val)
        if hasattr(icp, "set_param"):
            return icp.set_param(key, str_val)
        if hasattr(icp, "_set"):
            return icp._set(key, str_val)
        rec = icp.search([("key", "=", key)], limit=1)
        if rec:
            rec.value = str_val
        else:
            icp.create({"key": key, "value": str_val})
    except Exception:
        pass


class _NativeKybClient:
    """
    Zero-dependency Native KYB HTTP Client for Odoo.
    Uses standard Python 'requests' library bundled with all Odoo environments.
    Equipped with connection pooling, latency timing metrics, and sovereign audit logging.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://kyb.digidevagency.dz",
        timeout: float = 35.0,
        lang: str = "fr",
        env=None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.lang = lang
        self._session = requests.Session()
        try:
            import odoo.release
            odoo_ver = getattr(odoo.release, "version", "unknown")
        except Exception:
            odoo_ver = "unknown"

        mod_ver = "2.0.0"
        if env is not None:
            try:
                mod = env["ir.module.module"].sudo().search([("name", "=", "kyb_odoo")], limit=1)
                if mod and mod.installed_version:
                    mod_ver = mod.installed_version
            except Exception:
                pass

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Language": lang,
            "User-Agent": f"Odoo-KYB-Connector/{mod_ver} (Odoo {odoo_ver}; Sovereign)",
            "X-KYB-Client-Type": "odoo",
            "X-KYB-Client-Version": mod_ver,
            "X-KYB-Odoo-Version": str(odoo_ver),
        }
        if env is not None:
            try:
                db_uuid = _get_config_param(env, "database.uuid")
                db_name = env.cr.dbname
                web_url = _get_config_param(env, "web.base.url")
                if db_uuid:
                    headers["X-KYB-Database-UUID"] = str(db_uuid)
                if db_name:
                    headers["X-KYB-Database-Name"] = str(db_name)
                if web_url:
                    headers["X-KYB-Base-URL"] = str(web_url)
            except Exception:
                pass

        self._session.headers.update(headers)
        self.search = _NativeSearchNamespace(self)
        self._resolve_cache = {}  # {query_str: (timestamp, result_dict)}
        self._candidates_cache = {}  # {cache_key: (timestamp, result_dict)}

    def resolve(self, query: str) -> dict:
        """Resolve single Algerian identifier (NIF, RC, NIS, or Raison Sociale) with 60s in-memory deduplication."""
        import time
        clean_q = (query or "").strip()
        now = time.time()

        # 60-second In-Memory Deduplication: Prevents double/triple billing on immediate UI selections & onchange chains
        if clean_q in self._resolve_cache:
            ts, cached_val = self._resolve_cache[clean_q]
            if (now - ts) < 60.0:
                _logger.info("KYB resolve('%s') [In-Memory Cache Hit: 0.0ms, 0 Credits Deducted]", clean_q)
                return cached_val

        url = f"{self.base_url}/api/v1/entity/resolve"
        t0 = time.time()
        resp = self._session.get(url, params={"q": clean_q}, timeout=self.timeout)
        elapsed_ms = (time.time() - t0) * 1000.0
        _logger.info("KYB resolve('%s') completed in %.1fms [HTTP %d]", clean_q, elapsed_ms, resp.status_code)
        result = self._handle_response(resp)

        if isinstance(result, dict) and (result.get("entity") or result.get("data") or result.get("statut_cnrc")):
            self._resolve_cache[clean_q] = (now, result)
            ent = result.get("entity") or result.get("data") or result
            if isinstance(ent, dict):
                for ident in [ent.get("nif"), ent.get("rc_number"), ent.get("rcNumber"), ent.get("rc_number_official"), ent.get("nis")]:
                    if ident and isinstance(ident, str) and ident.strip():
                        self._resolve_cache[ident.strip()] = (now, result)

        return result

    def candidates(self, query: str, limit: int = 20, live: bool = False) -> dict:
        """Search entity candidates with in-memory keystroke storm deduplication (60s TTL)."""
        import time
        clean_q = (query or "").strip().lower()
        now = time.time()
        cache_key = f"{clean_q}:{limit}:{live}"

        # Keystroke Storm & Repetitive Typing Defense: 0.0ms memory hit
        if cache_key in self._candidates_cache:
            ts, cached_val = self._candidates_cache[cache_key]
            if (now - ts) < 60.0:
                _logger.info("KYB candidates('%s') [In-Memory Keystroke Cache Hit: 0.0ms, 0 Network Calls]", clean_q)
                return cached_val

        url = f"{self.base_url}/api/v1/entity/candidates"
        params = {"q": query, "limit": limit}
        if live:
            params["live"] = "true"
        t0 = time.time()
        resp = self._session.get(url, params=params, timeout=self.timeout)
        elapsed_ms = (time.time() - t0) * 1000.0
        _logger.info("KYB candidates('%s', live=%s) completed in %.1fms [HTTP %d]", query, live, elapsed_ms, resp.status_code)
        result = self._handle_response(resp)

        if isinstance(result, dict) and (result.get("candidates") or result.get("results")):
            self._candidates_cache[cache_key] = (now, result)

        return result

    def enrich(
        self,
        rc_number: str = "",
        raison_sociale: str = "",
        nif: str = "",
        nis: str = "",
        force_live: bool = False,
    ) -> dict:
        """
        Phase 2 Full Legal Profile Enrichment (Tier 1 Paid Detail View).
        Supports lookup and enrichment by RC Number, NIF, NIS, or Raison Sociale.
        Pulls authoritative NIF, NIS, Forme Juridique, Capital Social,
        Gérant / Représentant Légal, Codes NAE et Activités officielles.
        """
        import time
        url = f"{self.base_url}/api/v1/entity/enrich"
        payload = {}
        if rc_number:
            payload["rc_number"] = str(rc_number).strip()
        if raison_sociale:
            payload["raison_sociale"] = str(raison_sociale).strip()
        if nif:
            payload["nif"] = str(nif).strip()
        if nis:
            payload["nis"] = str(nis).strip()
        if force_live:
            payload["force_live"] = True
        t0 = time.time()
        resp = self._session.post(url, json=payload, timeout=self.timeout)
        elapsed_ms = (time.time() - t0) * 1000.0
        _logger.info("KYB enrich(rc='%s', nif='%s', live=%s) completed in %.1fms [HTTP %d]", rc_number, nif, force_live, elapsed_ms, resp.status_code)
        return self._handle_response(resp)

    def _handle_response(self, resp: requests.Response) -> dict:
        try:
            data = resp.json()
        except Exception:
            data = {}

        if not resp.ok:
            # Extract localized error from universal trilingual error envelope
            msg = (
                data.get("message")
                or data.get(f"message_{self.lang}")
                or data.get("error")
                or f"HTTP {resp.status_code} Error"
            )
            code = data.get("code", "API_ERROR")
            _logger.warning("KYB API error response [%s]: %s (HTTP %d)", code, msg, resp.status_code)
            raise UserError(f"[{code}] {msg}")
        return data

    def warmup(self) -> bool:
        """
        Preemptively establish and warm TLS/TCP connection to the sovereign gateway.
        Eliminates cold connection overhead before the user initiates form validation.
        """
        try:
            r = self._session.get(f"{self.base_url}/health", timeout=3.0)
            return r.status_code == 200
        except Exception:
            return False

    def close(self):
        self._session.close()


_CLIENT_CACHE: dict = {}




def _get_kyb_client(env):
    """
    Lazily initialise and return a persistent KYB client with connection reuse.

    Reads credentials from Odoo system parameters:
        - ``kyb.api_key`` (or legacy ``conforme.api_key``) — Bearer token for authentication.
        - ``kyb.base_url`` (or legacy ``conforme.base_url``) — API gateway URL (default: https://kyb.digidevagency.dz).

    Maintains a process-level session pool to eliminate redundant TCP/TLS handshakes,
    guaranteeing sub-100ms response times for onchange and autocomplete queries.
    """
    api_key = (
        _get_config_param(env, "kyb.api_key", default="")
        or _get_config_param(env, "conforme.api_key", default="")
    )
    base_url = (
        _get_config_param(env, "kyb.base_url", default="")
        or _get_config_param(env, "conforme.base_url", default="")
        or "https://kyb.digidevagency.dz"
    )
    if "githubusercontent.com" in base_url or "github.com" in base_url:
        base_url = "https://kyb.digidevagency.dz"
        _set_config_param(env, "kyb.base_url", base_url)

    if not api_key:
        raise UserError(
            _(
                "La clé API KYB n'est pas configurée.\n\n"
                "Veuillez vous rendre dans Paramètres → Vérification Fiscale KYB "
                "pour définir votre clé d'API (ou utiliser la clé sandbox 'sk_test_kyb_sandbox_key_001')."
            )
        )

    user_lang = getattr(getattr(env, "user", None), "lang", None) or "fr"
    lang_code = "ar" if "ar" in user_lang else ("en" if "en" in user_lang else "fr")

    cache_key = f"{api_key}:{base_url}:{lang_code}"
    cached = _CLIENT_CACHE.get(cache_key)
    if cached is not None:
        return cached

    timeout_param = _get_config_param(env, "kyb.timeout", default="35.0")
    try:
        timeout_val = float(timeout_param)
    except (ValueError, TypeError):
        timeout_val = 35.0

    client = _NativeKybClient(
        api_key=api_key, base_url=base_url, timeout=timeout_val, lang=lang_code, env=env
    )
    try:
        client.warmup()
    except Exception:
        pass

    _CLIENT_CACHE[cache_key] = client
    return client


class ResPartner(models.Model):
    _inherit = "res.partner"

    # ──────────────── Custom Algerian Fiscal Fields ────────────────

    kyb_nif = fields.Char(
        string="NIF (Numéro d'Identification Fiscale)",
        size=20,
        index=True,
        tracking=True,
        help="15 or 20-digit Algerian National Tax Identification Number.",
    )
    kyb_rc = fields.Char(
        string="Numéro RC",
        size=30,
        tracking=True,
        help="Numéro du Registre de Commerce (CNRC).",
    )
    kyb_article_imposition = fields.Char(
        string="Article d'Imposition (Numéro de Rôle)",
        size=30,
        tracking=True,
        help="Numéro d'Article d'Imposition (Art 114 CPF), crowd-cached via KYB.",
    )
    kyb_nis = fields.Char(
        string="NIS (Numéro d'Identification Statistique)",
        size=30,
        tracking=True,
        help="Numéro d'Identification Statistique délivré par l'ONS.",
    )
    kyb_statut_cnrc = fields.Selection(
        selection=[
            ("ACTIF", "Actif"),
            ("RADIE", "Radié"),
            ("SUSPENDU", "Suspendu"),
            ("INCONNU", "Inconnu"),
        ],
        string="Statut CNRC",
        default="INCONNU",
        tracking=True,
        help="Current CNRC registration standing from the KYB sovereign registry.",
    )
    kyb_date_radiation = fields.Date(
        string="Date de Radiation",
        tracking=True,
        help="Date officielle de radiation du registre de commerce (CNRC).",
    )
    kyb_date_creation = fields.Date(
        string="Date d'Immatriculation",
        tracking=True,
        help="Date officielle de première immatriculation au registre de commerce (CNRC).",
    )
    kyb_forme_juridique = fields.Char(
        string="Forme Juridique",
        tracking=True,
        help="Forme juridique officielle de l'entité (EURL, SARL, SPA, SNC, Personne Physique, etc.).",
    )
    kyb_capital_social = fields.Char(
        string="Capital Social",
        tracking=True,
        help="Capital social déclaré auprès du registre de commerce (CNRC).",
    )
    kyb_representant_legal = fields.Char(
        string="Représentant Légal / Gérant",
        tracking=True,
        help="Gérant ou représentant légal principal déclaré au CNRC.",
    )
    kyb_activite = fields.Char(
        string="Activité Principale Dominante",
        help="Activité principale dominante enregistrée au CNRC (avec code NAE).",
    )
    kyb_nae_codes = fields.Char(
        string="Codes NAE (Bruts)",
        help="Nomenclature Algérienne des Activités Économiques (Codes NAE officiels CNRC).",
    )
    kyb_activites_rc = fields.Text(
        string="Activités Secondaires RC (CNRC)",
        help="Ensemble des activités secondaires enregistrées au registre de commerce (avec codes NAE).",
    )
    kyb_last_verified = fields.Datetime(
        string="Dernière vérification KYB",
        readonly=True,
        help="Timestamp of the last successful KYB API verification.",
    )

    # ── Legacy Backward Compatibility Aliases ──
    conforme_nif = fields.Char(related="kyb_nif", readonly=False, string="NIF (Alias)", tracking=False)
    conforme_rc = fields.Char(related="kyb_rc", readonly=False, string="Numéro RC (Alias)", tracking=False)
    conforme_article_imposition = fields.Char(related="kyb_article_imposition", readonly=False, string="Article d'Imposition (Alias)", tracking=False)
    conforme_nis = fields.Char(related="kyb_nis", readonly=False, string="NIS (Alias)", tracking=False)
    conforme_statut_cnrc = fields.Selection(related="kyb_statut_cnrc", readonly=False, string="Statut CNRC (Alias)", tracking=False)
    conforme_activite = fields.Char(related="kyb_activite", readonly=False, string="Activité (Alias)", tracking=False)
    conforme_last_verified = fields.Datetime(related="kyb_last_verified", readonly=True, string="Dernière vérification (Alias)", tracking=False)
    kyb_date_immatriculation = fields.Date(related="kyb_date_creation", readonly=False, string="Date d'Immatriculation (Alias)", tracking=False)


    # ──────────────── Action Buttons & Onchange Handlers ───────────

    @api.model
    def _get_view(self, view_id=None, view_type="form", **options):
        """
        Relax client-side 'required' constraint on partner 'name' when a fiscal/registry
        identifier (kyb_nif, kyb_rc, vat, kyb_nis) is provided. Prevents Odoo OWL from
        blocking 'Vérifier Fiche KYB' or form save with 'Champs obligatoires manquants'
        when resolving a new partner solely by RC or NIF.
        """
        parent_meth = getattr(super(), "_get_view", None)
        if not callable(parent_meth):
            return None, None
        arch, view = parent_meth(view_id=view_id, view_type=view_type, **options)
        if view_type == "form" and arch is not None:
            try:
                for node in arch.xpath("//field[@name='name']"):
                    req = node.get("required")
                    if req and "type == 'contact'" in req and "kyb_nif" not in req:
                        node.set(
                            "required",
                            f"({req}) and not kyb_nif and not kyb_rc and not vat and not kyb_nis",
                        )
            except Exception as e_view:
                _logger.debug("KYB _get_view name required adjustment skipped: %s", e_view)
        return arch, view

    @api.model_create_multi
    def create(self, vals_list):
        raw_queries_by_idx = {}
        for idx, vals in enumerate(vals_list):
            if isinstance(vals.get("country_id"), dict):
                vals["country_id"] = vals["country_id"].get("id")
            if isinstance(vals.get("state_id"), dict):
                vals["state_id"] = vals["state_id"].get("id")

            # Detect if partner is being quick-created from a Supplier/Customer Invoice using a bare NIF or RC as 'name'
            raw_name = (vals.get("name") or "").strip()
            clean_name_id = re.sub(r"[\s\-_/.]", "", raw_name)
            if clean_name_id and re.match(r"^\d{15}(\d{5})?$", clean_name_id):
                if not vals.get("kyb_nif"):
                    vals["kyb_nif"] = clean_name_id
                if not vals.get("vat"):
                    vals["vat"] = clean_name_id
            elif raw_name and parse_algerian_rc(raw_name):
                if not vals.get("kyb_rc"):
                    vals["kyb_rc"] = raw_name

            raw_rc_in = (vals.get("kyb_rc") or vals.get("company_registry") or "").strip()
            raw_nif_in = (vals.get("kyb_nif") or vals.get("vat") or "").strip()
            raw_nis_in = (vals.get("kyb_nis") or "").strip()

            # Preserve the unformatted raw RC/NIF/NIS for post-create live resolution if record is not yet completely verified
            has_complete_governance = bool(
                vals.get("kyb_nif") and (vals.get("kyb_capital_social") or vals.get("kyb_representant_legal"))
            )
            is_already_verified = bool(
                has_complete_governance
                and (
                    vals.get("kyb_last_verified")
                    or (vals.get("kyb_statut_cnrc") in ("ACTIF", "RADIE", "SUSPENDU") and raw_name and raw_name not in (raw_rc_in, raw_nif_in, raw_nis_in))
                )
            )
            if not is_already_verified and (raw_nif_in or raw_rc_in or raw_nis_in):
                raw_queries_by_idx[idx] = raw_nif_in or raw_rc_in or raw_nis_in

            # Ensure 'name' is non-empty before DB insert when creating from NIF/RC only
            if not vals.get("name") and (raw_nif_in or raw_rc_in or raw_nis_in):
                vals["name"] = raw_nif_in or raw_rc_in or raw_nis_in

            if "kyb_rc" in vals or "company_registry" in vals:
                rc_in = vals.get("kyb_rc") or vals.get("company_registry")
                if rc_in:
                    fmt_rc = format_official_rc(rc_in, vals.get("kyb_date_creation")) or rc_in
                    vals["kyb_rc"] = fmt_rc
                    if "company_registry" in self._fields:
                        vals["company_registry"] = fmt_rc
            if (vals.get("kyb_nif") or vals.get("kyb_rc")) and vals.get("kyb_statut_cnrc") in ("ACTIF", "RADIE", "SUSPENDU") and not vals.get("kyb_last_verified"):
                vals["kyb_last_verified"] = fields.Datetime.now()

            # Backfill exact CNRC/DGI dates stripped by _AUTOCOMPLETE_DATE_EXCLUDE during client autocomplete RPC
            if (vals.get("kyb_nif") or vals.get("kyb_rc")) and (not vals.get("kyb_date_creation") or (vals.get("kyb_statut_cnrc") == "RADIE" and not vals.get("kyb_date_radiation"))):
                cached_ent = None
                for cand_key in (vals.get("kyb_nif"), vals.get("kyb_rc"), vals.get("vat"), vals.get("name")):
                    if not cand_key:
                        continue
                    ck = re.sub(r"[\s\-_/.]", "", str(cand_key).strip()).upper()
                    entry = _KYB_RECENT_RESOLVE_CACHE.get(ck)
                    if entry and isinstance(entry, tuple) and len(entry) == 2:
                        prof = entry[1]
                        if isinstance(prof, dict):
                            cached_ent = prof.get("entity") or prof.get("data") or prof
                            if isinstance(cached_ent, dict):
                                break
                if not vals.get("kyb_date_creation"):
                    if isinstance(cached_ent, dict):
                        dc = _normalize_algerian_date(
                            cached_ent.get("date_creation")
                            or cached_ent.get("date_immatriculation")
                            or cached_ent.get("dateImmatriculation")
                            or cached_ent.get("dateCreation")
                        )
                        if dc:
                            vals["kyb_date_creation"] = dc
                    if not vals.get("kyb_date_creation"):
                        ded = _deduce_algerian_creation_date(nif=vals.get("kyb_nif") or vals.get("vat"), rc=vals.get("kyb_rc"))
                        if ded:
                            vals["kyb_date_creation"] = ded
                if vals.get("kyb_statut_cnrc") == "RADIE" and not vals.get("kyb_date_radiation") and isinstance(cached_ent, dict):
                    dr = _normalize_algerian_date(
                        cached_ent.get("date_radiation")
                        or cached_ent.get("dateRadiation")
                        or cached_ent.get("radiation_date")
                        or cached_ent.get("date_rad")
                    )
                    if dr:
                        vals["kyb_date_radiation"] = dr
        # Determine if this batch has KYB-verified records or pending auto-resolve records before creation
        has_kyb = any(
            ((v.get("kyb_nif") or v.get("kyb_rc")) and v.get("kyb_statut_cnrc")) or (i in raw_queries_by_idx)
            for i, v in enumerate(vals_list)
        )

        if has_kyb:
            # mail_create_nolog=True: suppress Odoo's built-in "Contact créé" log message.
            # The institutional KYB card from _post_kyb_audit_log() is the sole chatter entry.
            # tracking_disable=True & mail_notrack=True: suppress all field tracking diffs on creation.
            records = super(ResPartner, self.with_context(
                mail_create_nolog=True, mail_notrack=True, tracking_disable=True
            )).create(vals_list)
        else:
            records = super().create(vals_list)

        for idx, record in enumerate(records):
            auto_q = raw_queries_by_idx.get(idx)
            if auto_q and not (getattr(self.env, "context", None) or {}).get("kyb_skip_resolve"):
                try:
                    record.with_context(tracking_disable=True, mail_notrack=True)._do_kyb_resolve(auto_q)
                except Exception as e_auto:
                    _logger.warning("KYB auto-resolve on partner create failed for '%s': %s", auto_q, e_auto)
            elif (record.kyb_nif or record.kyb_rc) and record.kyb_statut_cnrc:
                record._post_kyb_audit_log()
        return records

    def write(self, vals):
        if isinstance(vals.get("country_id"), dict):
            vals["country_id"] = vals["country_id"].get("id")
        if isinstance(vals.get("state_id"), dict):
            vals["state_id"] = vals["state_id"].get("id")
        if "kyb_rc" in vals or "company_registry" in vals:
            rc_in = vals.get("kyb_rc") or vals.get("company_registry")
            if rc_in:
                fmt_rc = format_official_rc(rc_in, vals.get("kyb_date_creation")) or rc_in
                vals["kyb_rc"] = fmt_rc
                if "company_registry" in self._fields:
                    vals["company_registry"] = fmt_rc
        if not vals.get("kyb_date_creation") and (vals.get("kyb_nif") or vals.get("kyb_rc") or vals.get("vat")):
            ded = _deduce_algerian_creation_date(nif=vals.get("kyb_nif") or vals.get("vat"), rc=vals.get("kyb_rc"))
            if ded:
                vals["kyb_date_creation"] = ded
        # Suppress ORM field-diff tracking chatter when saving KYB-enriched fields or updating company identity
        kyb_write_keys = {
            "kyb_nif", "kyb_rc", "kyb_nis", "kyb_statut_cnrc",
            "kyb_capital_social", "kyb_representant_legal", "kyb_forme_juridique",
            "kyb_activite", "kyb_nae_codes", "kyb_activites_rc",
            "kyb_date_creation", "kyb_date_radiation", "kyb_last_verified",
        }
        is_kyb_write = any(k in vals for k in kyb_write_keys) or (
            ("name" in vals or "vat" in vals) and any(bool(getattr(r, "kyb_nif", False) or getattr(r, "kyb_rc", False)) for r in self)
        )
        if is_kyb_write:
            res = super(ResPartner, self.with_context(tracking_disable=True, mail_notrack=True, mail_create_nolog=True)).write(vals)
            # If this write populated KYB verification data (e.g. when selecting from autocomplete on an existing draft),
            # ensure the green/red institutional KYB card is posted/updated in chatter.
            if not (getattr(self.env, "context", None) or {}).get("kyb_skip_audit_post"):
                for rec in self:
                    if (rec.kyb_nif or rec.kyb_rc) and rec.kyb_statut_cnrc in ("ACTIF", "RADIE", "SUSPENDU"):
                        rec.with_context(kyb_skip_audit_post=True)._post_kyb_audit_log()
            return res
        return super().write(vals)

    def _message_track(self, fields_iter, initial_values):
        if (
            self.env.context.get("mail_notrack")
            or self.env.context.get("tracking_disable")
            or any(bool(getattr(r, "kyb_nif", False) or getattr(r, "kyb_rc", False)) for r in self)
        ):
            fields_iter = ()
        return super()._message_track(fields_iter, initial_values)

    def message_track(self, tracked_fields, initial_values):
        """Odoo 14.0 & 15.0 MailThread field tracking entrypoint."""
        if (
            self.env.context.get("mail_notrack")
            or self.env.context.get("tracking_disable")
            or any(bool(getattr(r, "kyb_nif", False) or getattr(r, "kyb_rc", False)) for r in self)
        ):
            return {}
        parent_meth = getattr(super(), "message_track", None)
        if callable(parent_meth):
            res = parent_meth(tracked_fields, initial_values)
            return res if isinstance(res, dict) else {}
        return {}

    @api.constrains("kyb_nif", "vat")
    def _check_duplicate_nif(self):
        """Enforces duplicate NIF governance according to kyb.duplicate_nif_policy."""
        policy = _get_config_param(self.env, "kyb.duplicate_nif_policy", "warn")
        if policy == "allow":
            return

        for record in self:
            nif = (record.kyb_nif or record.vat or "").strip()
            # Ignore empty NIFs, non-digits, short strings, and sandbox deterministic test NIFs
            if not nif or len(nif) < 9 or nif.startswith("0000"):
                continue

            domain = [
                ("id", "!=", record.id),
                "|",
                ("kyb_nif", "=", nif),
                ("vat", "=", nif),
            ]
            duplicate = self.search(domain, limit=1)
            if duplicate:
                if policy == "block":
                    raise UserError(
                        _(
                            "Conformité Fiscale KYB : Un autre partenaire ('%(dup_name)s') possède déjà ce Numéro d'Identification Fiscale (NIF: %(nif)s). "
                            "La création ou modification de doublons fiscaux est strictement bloquée par votre politique d'entreprise."
                        )
                        % {"dup_name": duplicate.name, "nif": nif}
                    )
                elif policy == "warn":
                    msg = _(
                        "⚠️ Avertissement Doublon Fiscal : Le NIF '%(nif)s' est déjà attribué au partenaire '%(dup_name)s' (ID: %(dup_id)s)."
                    ) % {"nif": nif, "dup_name": duplicate.name, "dup_id": duplicate.id}
                    existing_warn = self.env["mail.message"].sudo().search([
                        ("model", "=", "res.partner"),
                        ("res_id", "=", record.id),
                        ("body", "ilike", f"%{nif}%"),
                        ("body", "ilike", "%Avertissement Doublon Fiscal%"),
                    ], limit=1)
                    if not existing_warn:
                        warn_author = self._get_session_author_partner(record)
                        record.message_post(
                            body=msg,
                            author_id=warn_author.id if warn_author else False,
                        )

    def _get_session_author_partner(self, partner=None):
        """
        Resolve the human session owner's res.partner record for Chatter traceability
        (showing who created/verified the contact), strictly avoiding OdooBot / System
        (SUPERUSER_ID=1 / base.user_root) when called inside a .sudo() context or CLI/cron.
        """
        try:
            root_user = self.env.ref("base.user_root", raise_if_not_found=False)
            root_uid = root_user.id if root_user else 1
        except Exception:
            root_uid = 1

        candidates = []
        # 1. Active env.user if it is a human user (not SUPERUSER_ID / OdooBot)
        cur_user = getattr(self.env, "user", None)
        if cur_user and getattr(cur_user, "id", None) and cur_user.id != root_uid:
            candidates.append(cur_user)

        # 2. HTTP session UID from context (preserved even when .sudo() switches env.uid to 1)
        ctx_uid = (getattr(self.env, "context", None) or {}).get("uid")
        if isinstance(ctx_uid, int) and ctx_uid > 0 and ctx_uid != root_uid:
            try:
                candidates.append(self.env["res.users"].sudo().browse(ctx_uid))
            except Exception:
                pass

        # 3. Contact creator / modifier (who created or last edited the partner record)
        if partner is not None:
            for u_field in ("write_uid", "create_uid"):
                u_rec = getattr(partner, u_field, None)
                if u_rec and getattr(u_rec, "id", None) and u_rec.id != root_uid:
                    candidates.append(u_rec)

        # 4. Fallback to Administrator (base.user_admin, uid=2) instead of OdooBot
        try:
            admin_user = self.env.ref("base.user_admin", raise_if_not_found=False)
            if admin_user:
                candidates.append(admin_user)
        except Exception:
            pass

        for usr in candidates:
            try:
                if usr and usr.exists() and usr.partner_id:
                    return usr.partner_id
            except Exception:
                continue

        return getattr(cur_user, "partner_id", None)

    def _post_kyb_audit_log(self):
        """
        [ESTABLISHED INVARIANT - DO NOT MODIFY OR REINVENT]
        Posts the single institutional KYB audit card to the record chatter:
        1. NEVER wrap the body in a styled inner <div> card (no background-color/border box inside the message).
           Always post with subtype_xmlid="mail.mt_note" so Odoo's native light-green note bubble is the sole card.
        2. NEVER use <code> tags for NIF, RC, NIS, NAE, or Article d'Imposition (Bootstrap renders <code> in red/crimson).
           Use plain <td style="font-family: monospace; color: #18181b;">. Red (#dc2626) is strictly for RADIÉ and Date de Radiation.
        3. ALWAYS render the header as a 2-column 100%-width <table> (left: 'Vérification KYB' with padding-right: 16px;
           right: status pill with text-align: right and margin-left: 16px) because Odoo's html_sanitize strips flexbox
           justify-content, which otherwise causes the ACTIF badge to collide with the title.
        4. Update existing 'Vérification KYB' message in-place and purge any 'Contact créé' or field-tracking diff noise.
        """
        for partner in self:
            if not hasattr(partner, "message_post"):
                continue
            # Flush any pending ORM / precommit field-tracking hooks first so no deferred
            # tracking message can be created after _post_kyb_audit_log finishes (Odoo 14-20).
            try:
                if hasattr(self.env, "flush_all"):
                    self.env.flush_all()
                elif hasattr(self, "flush"):
                    self.flush()
                if hasattr(self.env, "cr") and hasattr(self.env.cr, "precommit"):
                    self.env.cr.precommit.run()
            except Exception:
                pass
            # Strict Chatter Deduplication Guard: Remove generic creation/tracking noise & stale duplicate warnings
            try:
                cur_nif = (partner.kyb_nif or partner.vat or "").strip()
                all_msgs = self.env["mail.message"].sudo().search([
                    ("model", "=", "res.partner"),
                    ("res_id", "=", partner.id),
                ])
                for m in all_msgs:
                    b_str = str(m.body or "")
                    if "Vérification KYB" in b_str or "KYB Verification" in b_str or "التحقق الجبائي KYB" in b_str:
                        continue
                    if "Doublon" in b_str:
                        # If the partner's current NIF has changed or no longer matches the warning, purge stale warning
                        if not cur_nif or cur_nif not in b_str:
                            m.unlink()
                        continue
                    is_noise = (
                        "Contact créé" in b_str
                        or "Partner created" in b_str
                        or "Dénomination de la société" in b_str
                        or "Company Name" in b_str
                        or m.message_type == "tracking"
                        or bool(getattr(m, "tracking_value_ids", False))
                    )
                    if is_noise:
                        m.unlink()
            except Exception as e_dedup:
                _logger.warning("KYB chatter cleanup warning on partner #%s: %s", partner.id, e_dedup)

            statut = (partner.kyb_statut_cnrc or "ACTIF").upper()
            if "RAD" in statut or "مشطب" in statut:
                badge_text = "RADIÉ"
                badge_color = "#dc2626"
                card_bg = "#fef2f2"
                card_border = "#fecaca"
                div_border = "#fee2e2"
            elif "SUSP" in statut or "معلق" in statut:
                badge_text = "SUSPENDU"
                badge_color = "#d97706"
                card_bg = "#fffbeb"
                card_border = "#fde68a"
                div_border = "#fef3c7"
            elif "NON" in statut or "INTROUVABLE" in statut:
                badge_text = "NON TROUVÉ"
                badge_color = "#71717a"
                card_bg = "#f4f4f5"
                card_border = "#e4e4e7"
                div_border = "#e4e4e7"
            else:
                badge_text = "ACTIF"
                badge_color = "#10b981"
                card_bg = "#f0fdf4"
                card_border = "#bbf7d0"
                div_border = "#dcfce7"

            rows = []  # Statut row removed — badge in card header already conveys ACTIF/RADIÉ/SUSPENDU
            if partner.name:
                rows.append(f'<tr><td style="padding: 2px 10px 2px 0; color: #71717a; width: 38%; white-space: nowrap; vertical-align: top;">{_("Raison Sociale")} :</td><td style="padding: 2px 0; font-weight: 500; color: #18181b;">{partner.name}</td></tr>')
            if partner.kyb_nif:
                rows.append(f'<tr><td style="padding: 2px 10px 2px 0; color: #71717a; white-space: nowrap; vertical-align: top;">{_("NIF (Identifiant Fiscal)")} :</td><td style="padding: 2px 0; font-family: monospace; font-weight: 600; color: #18181b;">{partner.kyb_nif}</td></tr>')
            if partner.kyb_rc:
                rows.append(f'<tr><td style="padding: 2px 10px 2px 0; color: #71717a; white-space: nowrap; vertical-align: top;">{_("Numéro RC")} :</td><td style="padding: 2px 0; font-family: monospace; font-weight: 600; color: #18181b;">{partner.kyb_rc}</td></tr>')
            if partner.kyb_nis:
                rows.append(f'<tr><td style="padding: 2px 10px 2px 0; color: #71717a; white-space: nowrap; vertical-align: top;">{_("NIS (Statistique)")} :</td><td style="padding: 2px 0; font-family: monospace; color: #18181b;">{partner.kyb_nis}</td></tr>')
            if partner.kyb_forme_juridique:
                rows.append(f'<tr><td style="padding: 2px 10px 2px 0; color: #71717a; white-space: nowrap; vertical-align: top;">{_("Forme Juridique")} :</td><td style="padding: 2px 0; color: #18181b;">{partner.kyb_forme_juridique}</td></tr>')
            if partner.kyb_date_creation:
                label_immat = _("Date d'Immatriculation")
                d_crea_val = partner.kyb_date_creation.strftime("%d/%m/%Y") if hasattr(partner.kyb_date_creation, "strftime") else str(partner.kyb_date_creation)
                rows.append(f'<tr><td style="padding: 2px 10px 2px 0; color: #71717a; white-space: nowrap; vertical-align: top;">{label_immat} :</td><td style="padding: 2px 0; color: #18181b;">{d_crea_val}</td></tr>')
            else:
                # Exact date not published by the registry: show the year encoded in the NIF/RC, labelled as such.
                deduced = _deduce_algerian_creation_date(nif=partner.kyb_nif, rc=partner.kyb_rc)
                if deduced:
                    label_immat = _("Date d'Immatriculation")
                    yr_txt = _("Année %s (déduite du NIF — date exacte non publiée)") % deduced[:4]
                    rows.append(f'<tr><td style="padding: 2px 10px 2px 0; color: #71717a; white-space: nowrap; vertical-align: top;">{label_immat} :</td><td style="padding: 2px 0; color: #52525b;">{yr_txt}</td></tr>')
            if partner.kyb_date_radiation:
                d_rad_val = partner.kyb_date_radiation.strftime("%d/%m/%Y") if hasattr(partner.kyb_date_radiation, "strftime") else str(partner.kyb_date_radiation)
                rows.append(f'<tr><td style="padding: 2px 10px 2px 0; color: #71717a; white-space: nowrap; vertical-align: top;">{_("Date de Radiation")} :</td><td style="padding: 2px 0; font-weight: 600; color: #dc2626;">{d_rad_val}</td></tr>')
            if partner.kyb_capital_social:
                rows.append(f'<tr><td style="padding: 2px 10px 2px 0; color: #71717a; white-space: nowrap; vertical-align: top;">{_("Capital Social")} :</td><td style="padding: 2px 0; color: #18181b;">{partner.kyb_capital_social}</td></tr>')
            if partner.kyb_representant_legal:
                clean_rep = _clean_algerian_representant(partner.kyb_representant_legal) or partner.kyb_representant_legal
                rows.append(f'<tr><td style="padding: 2px 10px 2px 0; color: #71717a; white-space: nowrap; vertical-align: top;">{_("Gérant / Représentant")} :</td><td style="padding: 2px 0; color: #18181b;">{clean_rep}</td></tr>')
            if partner.kyb_activite:
                rows.append(f'<tr><td style="padding: 2px 10px 2px 0; color: #71717a; white-space: nowrap; vertical-align: top;">{_("Activité Principale")} :</td><td style="padding: 2px 0; color: #18181b;">{partner.kyb_activite}</td></tr>')
            if partner.kyb_nae_codes:
                rows.append(f'<tr><td style="padding: 2px 10px 2px 0; color: #71717a; white-space: nowrap; vertical-align: top;">{_("Codes NAE")} :</td><td style="padding: 2px 0; font-family: monospace; color: #18181b;">{partner.kyb_nae_codes}</td></tr>')
            if partner.kyb_activites_rc:
                acts_formatted = partner.kyb_activites_rc.replace("\n", "<br/>")
                rows.append(f'<tr><td style="padding: 2px 10px 2px 0; color: #71717a; white-space: nowrap; vertical-align: top;">{_("Activités Secondaires")} :</td><td style="padding: 2px 0; font-size: 11px; color: #3f3f46;">{acts_formatted}</td></tr>')
            if partner.kyb_article_imposition:
                lbl_art = _("Article d'Imposition")
                rows.append(f'<tr><td style="padding: 2px 10px 2px 0; color: #71717a; white-space: nowrap; vertical-align: top;">{lbl_art} :</td><td style="padding: 2px 0; font-family: monospace; color: #18181b;">{partner.kyb_article_imposition}</td></tr>')

            rows_html = "".join(rows)
            now_dt = fields.Datetime.now()
            now_str = now_dt.strftime("%d/%m/%Y %H:%M") if hasattr(now_dt, "strftime") else str(now_dt or "")
            body = (
                f'<div style="background-color: {card_bg} !important; border: 1px solid {card_border} !important; border-radius: 8px !important; padding: 12px 14px !important; margin: 4px 0 !important; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif;">'
                f'<table style="width: 100%; border-bottom: 1px solid {div_border} !important; margin-bottom: 8px; padding-bottom: 6px; border-collapse: collapse;">'
                '<tr>'
                f'<td style="text-align: left; vertical-align: middle; padding-right: 16px;"><strong style="color: #18181b; font-size: 13px; font-weight: 700;">{_("Vérification KYB")}</strong></td>'
                f'<td style="text-align: right; vertical-align: middle;"><span style="background-color: {badge_color} !important; color: #ffffff !important; padding: 3px 10px !important; border-radius: 9999px !important; font-size: 10px !important; font-weight: 700 !important; display: inline-block !important; text-transform: uppercase !important; letter-spacing: 0.05em !important; margin-left: 16px !important;">{badge_text}</span></td>'
                '</tr>'
                '</table>'
                f'<table style="width: 100%; font-size: 12px; border-collapse: collapse;">{rows_html}</table>'
                f'<div style="margin-top: 8px; font-size: 10px; color: #71717a; border-top: 1px solid {div_border} !important; padding-top: 4px;">'
                f'{_("Consultation Registre Officiel")} · {now_str}'
                f'</div>'
                '</div>'
            )
            # Chatter author attribution: assign message to the active human session owner (e.g. Administrator)
            # rather than OdooBot (SUPERUSER_ID=1) for full audit traceability of who created/verified the contact.
            # subtype_xmlid="mail.mt_note" renders Odoo's native light-green note bubble directly (zero nested card-inside-card)
            user_partner = self._get_session_author_partner(partner)
            author_id = user_partner.id if user_partner else False
            note_subtype = self.env.ref("mail.mt_note", raise_if_not_found=False)
            try:
                existing_cards = self.env["mail.message"].sudo().search([
                    ("model", "=", "res.partner"),
                    ("res_id", "=", partner.id),
                    "|", "|",
                    ("body", "ilike", "%Vérification KYB%"),
                    ("body", "ilike", "%KYB Verification%"),
                    ("body", "ilike", "%التحقق الجبائي KYB%"),
                ], order="id desc")
            except Exception:
                existing_cards = []
            # Strictly maintain a single card ID (zero double cards in DB or OWL Chatter):
            # Update existing_cards[0] in-place and broadcast the updated body over the bus.
            if existing_cards:
                card = existing_cards[0]
                if len(existing_cards) > 1:
                    extra_ids = existing_cards[1:].ids
                    try:
                        if user_partner and hasattr(user_partner, "_bus_send"):
                            user_partner._bus_send("mail.message/delete", {"message_ids": extra_ids})
                    except Exception:
                        pass
                    existing_cards[1:].unlink()
                update_vals = {"body": Markup(body), "date": fields.Datetime.now()}
                if author_id:
                    update_vals["author_id"] = author_id
                if note_subtype:
                    update_vals["subtype_id"] = note_subtype.id
                card.write(update_vals)
                try:
                    from odoo.addons.mail.tools.discuss import Store
                    if hasattr(card, "_bus_send_store"):
                        card._bus_send_store(card, {"body": card.body, "write_date": card.write_date})
                    elif hasattr(card, "_bus_channel"):
                        st = Store(bus_channel=card._bus_channel()).add(card, ["body", "write_date"])
                        if hasattr(st, "bus_send"):
                            st.bus_send()
                    else:
                        for chan in (card, self.env.user):
                            if chan:
                                Store(bus_channel=chan).add(
                                    card,
                                    lambda res: (res.attr("body"), res.attr("write_date")),
                                )
                except Exception:
                    try:
                        if user_partner and "bus.bus" in self.env:
                            bus_model = self.env["bus.bus"]
                            payload = {"Message": {"id": card.id, "body": card.body, "write_date": str(card.write_date)}}
                            if hasattr(bus_model, "_sendone"):
                                bus_model._sendone(user_partner, "mail.record/insert", payload)
                            elif hasattr(bus_model, "sendone"):
                                bus_model.sendone((self._cr.dbname, "res.partner", user_partner.id), {"type": "mail.record/insert", "payload": payload})
                    except Exception:
                        pass
            else:
                partner.with_context(kyb_skip_audit_post=True).message_post(
                    body=Markup(body),
                    author_id=author_id,
                    message_type="comment",
                    subtype_xmlid="mail.mt_note",
                )
        return True

    def enrich_company_message_post(self, data):
        """
        Post-enrichment callback triggered by partner_autocomplete after record.save().
        Sets sovereign verification timestamp, resolves strike-off date if radie,
        and posts an institutional chatter audit entry (Loi 25-11).
        """
        for partner in self:
            vals = {}
            if not partner.kyb_last_verified:
                vals["kyb_last_verified"] = fields.Datetime.now()

            # 1. Sync Date d'Immatriculation from incoming data or resolve fallback
            d_crea = False
            if isinstance(data, dict):
                d_crea = (
                    data.get("date_creation")
                    or data.get("date_immatriculation")
                    or data.get("dateImmatriculation")
                    or data.get("dateCreation")
                )
            norm_crea = _normalize_algerian_date(d_crea)
            if norm_crea and str(partner.kyb_date_creation or "")[:10] != norm_crea:
                vals["kyb_date_creation"] = norm_crea
            elif not partner.kyb_date_creation:
                query = partner.kyb_rc or partner.kyb_nif or partner.vat
                if query:
                    try:
                        client = _get_kyb_client(partner.env)
                        prof = client.resolve(query)
                        ent = prof.get("entity") or prof.get("data") or prof
                        d_crea = (
                            ent.get("date_creation")
                            or ent.get("date_immatriculation")
                            or ent.get("dateImmatriculation")
                            or ent.get("dateCreation")
                        )
                        norm_crea = _normalize_algerian_date(d_crea)
                        if norm_crea:
                            vals["kyb_date_creation"] = norm_crea
                    except Exception:
                        pass
                # Fallback: derive registration year from RC if exact date is still missing
                if not vals.get("kyb_date_creation") and partner.kyb_rc:
                    rc_clean = re.sub(r"\s+", "", str(partner.kyb_rc or ""))
                    m_suf = re.search(r"[A-Za-z](\d{2})$", rc_clean)
                    m_pref = re.match(r"^(\d{2})[A-Za-z]\d{4,8}$", rc_clean)
                    yr_2d = m_suf.group(1) if m_suf else (m_pref.group(1) if m_pref else None)
                    if yr_2d:
                        yr_full = int(yr_2d)
                        yr_4d = 1900 + yr_full if yr_full >= 50 else 2000 + yr_full
                        vals["kyb_date_creation"] = f"{yr_4d}-01-01"

            # 2. Sync Status and Date de Radiation
            incoming_statut = (data.get("statut_cnrc") or data.get("statutCnrc") or data.get("statut") or "") if isinstance(data, dict) else ""
            if incoming_statut:
                incoming_norm = incoming_statut.upper()
                statut_val = "RADIE" if ("RAD" in incoming_norm or "مشطب" in incoming_norm) else ("ACTIF" if ("ACT" in incoming_norm or "نشط" in incoming_norm) else incoming_norm)
                if partner.kyb_statut_cnrc != statut_val:
                    vals["kyb_statut_cnrc"] = statut_val

            effective_statut = (vals.get("kyb_statut_cnrc") or incoming_statut or partner.kyb_statut_cnrc or "").upper()
            is_radie = "RAD" in effective_statut or "مشطب" in effective_statut

            if is_radie:
                d_rad = False
                if isinstance(data, dict):
                    d_rad = data.get("date_radiation") or data.get("dateRadiation") or data.get("radiation_date")
                norm_rad = _normalize_algerian_date(d_rad)
                if norm_rad and str(partner.kyb_date_radiation or "")[:10] != norm_rad:
                    vals["kyb_date_radiation"] = norm_rad
                elif not partner.kyb_date_radiation:
                    query = partner.kyb_rc or partner.kyb_nif or partner.vat or partner.name
                    if query:
                        try:
                            client = _get_kyb_client(partner.env)
                            prof = client.resolve(query)
                            ent = prof.get("entity") or prof.get("data") or prof
                            d_rad = ent.get("date_radiation") or ent.get("dateRadiation")
                            norm_rad = _normalize_algerian_date(d_rad)
                            if norm_rad:
                                vals["kyb_date_radiation"] = norm_rad
                        except Exception:
                            pass
            else:
                # Active company must never retain a stale strike-off date
                if partner.kyb_date_radiation:
                    vals["kyb_date_radiation"] = False

            # 3. Defensive Invariant Gate: Date d'Immatriculation must be <= Date de Radiation
            eff_crea = vals.get("kyb_date_creation") or partner.kyb_date_creation
            eff_rad = vals.get("kyb_date_radiation") or partner.kyb_date_radiation
            if eff_crea and eff_rad and is_radie:
                str_crea = str(eff_crea)[:10]
                str_rad = str(eff_rad)[:10]
                if str_crea > str_rad:
                    _logger.warning(
                        "KYB date anomaly on partner #%s: immatriculation %s > radiation %s. Resolving official dates.",
                        partner.id, str_crea, str_rad
                    )
                    try:
                        client = _get_kyb_client(partner.env)
                        query = partner.kyb_rc or partner.kyb_nif or partner.vat
                        if query:
                            prof = client.resolve(query)
                            ent = prof.get("entity") or prof.get("data") or prof
                            real_crea = _normalize_algerian_date(ent.get("date_immatriculation") or ent.get("date_creation"))
                            real_rad = _normalize_algerian_date(ent.get("date_radiation"))
                            if real_crea:
                                vals["kyb_date_creation"] = real_crea
                            if real_rad:
                                vals["kyb_date_radiation"] = real_rad
                    except Exception as e_inv:
                        _logger.warning("Defensive date correction failed: %s", e_inv)

            if vals:
                # tracking_disable=True: suppress Odoo ORM field-diff chatter; the
                # institutional KYB card from _post_kyb_audit_log() is the sole audit trail.
                partner.with_context(tracking_disable=True, mail_notrack=True, kyb_skip_audit_post=True).write(vals)

            partner._post_kyb_audit_log()
        return True

    def action_verify_kyb(self):
        """Action button to trigger manual verification from partner form."""
        self.ensure_one()
        # If record was just auto-verified during create() within the last 10 seconds and is already complete, avoid redundant billing
        if (
            self.kyb_last_verified
            and self.kyb_statut_cnrc in ("ACTIF", "RADIE", "SUSPENDU")
            and self.name
            and self.kyb_nif
            and self.kyb_rc
            and (self.kyb_capital_social or self.kyb_representant_legal)
            and (fields.Datetime.now() - self.kyb_last_verified).total_seconds() < 10
        ):
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Vérification KYB Réussie"),
                    "message": _("L'entité '%(name)s' a été vérifiée avec succès (Statut: %(statut)s).") % {
                        "name": self.name,
                        "statut": self.kyb_statut_cnrc,
                    },
                    "sticky": False,
                    "type": "success",
                    "next": {"type": "ir.actions.client", "tag": "soft_reload"},
                },
            }
        query = (
            self.kyb_nif
            or self.conforme_nif
            or self.kyb_rc
            or (self.company_registry if "company_registry" in self._fields else False)
            or self.vat
            or self.kyb_nis
            or self.name
            or ""
        ).strip()
        if not query:
            raise UserError(_("Veuillez renseigner un NIF, un RC, un NIS ou une Raison Sociale pour lancer la vérification."))
        res = self._do_kyb_resolve(query)
        if isinstance(res, dict) and "warning" in res:
            warn = res["warning"]
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": warn.get("title", _("Vérification KYB")),
                    "message": warn.get("message", _("Aucune entité trouvée.")),
                    "sticky": False,
                    "type": "warning",
                    "next": {"type": "ir.actions.client", "tag": "soft_reload"},
                },
            }
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Vérification KYB Réussie"),
                "message": _("L'entité '%(name)s' a été vérifiée avec succès (Statut: %(statut)s).") % {
                    "name": self.name,
                    "statut": self.kyb_statut_cnrc,
                },
                "sticky": False,
                "type": "success",
                "next": {"type": "ir.actions.client", "tag": "soft_reload"},
            },
        }

    def action_verify_conforme(self):
        """Backward compatible action method alias."""
        return self.action_verify_kyb()

    @api.onchange("name")
    def _onchange_name_kyb_identifier(self):
        """
        When a user enters an exact 15/20-digit NIF or an Algerian RC number directly into
        the 'Nom' field (e.g. via 'Créer et modifier...' from a Supplier Invoice),
        automatically resolve and enrich the partner from the KYB registry.
        """
        if not self.name or (getattr(self.env, "context", None) or {}).get("kyb_skip_resolve"):
            return
        raw_name = self.name.strip()
        clean_num = re.sub(r"[\s\-_/.]", "", raw_name)
        if re.match(r"^\d{15}(\d{5})?$", clean_num):
            if self.kyb_last_verified and self.kyb_statut_cnrc in ("ACTIF", "RADIE", "SUSPENDU") and self.kyb_nif == clean_num:
                return
            self.kyb_nif = clean_num
            if not self.vat:
                self.vat = clean_num
            return self._do_kyb_resolve(clean_num)
        if parse_algerian_rc(raw_name):
            if self.kyb_last_verified and self.kyb_statut_cnrc in ("ACTIF", "RADIE", "SUSPENDU") and self.kyb_rc:
                return
            self.kyb_rc = raw_name
            return self._do_kyb_resolve(raw_name)

    @api.onchange("vat")
    def _onchange_vat(self):
        """Auto-populate when the standard Odoo VAT field is entered."""
        if self.vat:
            cleaned = re.sub(r"[\s\-_/.]", "", self.vat.strip())
            # Grille Tarifaire Guard: Skip API call if already verified with matching NIF (0 credits)
            if self.kyb_last_verified and self.kyb_statut_cnrc in ("ACTIF", "RADIE", "SUSPENDU") and (self.kyb_nif == cleaned or self.vat == cleaned):
                return
            if (getattr(self.env, "context", None) or {}).get("kyb_skip_resolve"):
                return
            if not self.kyb_nif:
                self.kyb_nif = cleaned
            return self._do_kyb_resolve(cleaned)

    @api.onchange("kyb_nif", "conforme_nif")
    def _onchange_kyb_nif(self):
        """
        When the user enters or modifies the NIF field, query the KYB API
        and auto-populate the partner form with the resolved entity data.
        """
        val = (self.kyb_nif or self.conforme_nif or "").strip()
        cleaned = re.sub(r"[\s\-_/.]", "", val)
        if not cleaned or len(cleaned) < 9:
            return
        # Grille Tarifaire Guard: Skip API call if already verified with matching NIF (0 credits)
        if self.kyb_last_verified and self.kyb_statut_cnrc in ("ACTIF", "RADIE", "SUSPENDU") and (self.kyb_nif == cleaned or self.conforme_nif == cleaned):
            return
        if (getattr(self.env, "context", None) or {}).get("kyb_skip_resolve"):
            return
        return self._do_kyb_resolve(cleaned)

    @api.onchange("kyb_rc", "conforme_rc")
    def _onchange_kyb_rc(self):
        """
        When the user enters or modifies the RC field, query the KYB API
        to resolve and enrich the entity (Personne Morale or Personne Physique).
        Auto-formats input to official Décret 05-468 invoicing format WW/00-XXXXXXX[A|B|C|D]YY.
        """
        raw_rc = (
            self.kyb_rc
            or self.conforme_rc
            or (self.company_registry if "company_registry" in self._fields else False)
            or ""
        ).strip()
        if not raw_rc or len(raw_rc) < 4:
            return

        fmt_rc = format_official_rc(raw_rc, self.kyb_date_creation)
        # Grille Tarifaire Guard: Skip API call if already verified with matching RC (0 credits)
        if (
            self.kyb_last_verified
            and self.kyb_statut_cnrc in ("ACTIF", "RADIE", "SUSPENDU")
            and self.name
            and self.name.strip() not in (raw_rc, fmt_rc or "")
            and (self.kyb_rc in (raw_rc, fmt_rc) or self.conforme_rc in (raw_rc, fmt_rc))
        ):
            return
        if (getattr(self.env, "context", None) or {}).get("kyb_skip_resolve"):
            return
        res = self._do_kyb_resolve(raw_rc)
        if not self.kyb_rc or self.kyb_rc == raw_rc:
            final_fmt = format_official_rc(self.kyb_rc or raw_rc, self.kyb_date_creation)
            if final_fmt:
                self.kyb_rc = final_fmt
                if "company_registry" in self._fields:
                    self.company_registry = final_fmt
        return res

    @api.onchange("kyb_nis")
    def _onchange_kyb_nis(self):
        """
        When the user enters or modifies the NIS field, query the KYB API
        to resolve and enrich the entity.
        """
        nis = (self.kyb_nis or "").strip()
        cleaned = re.sub(r"[\s\-_/.]", "", nis)
        if not cleaned or len(cleaned) < 9:
            return
        # Grille Tarifaire Guard: Skip API call if already verified with matching NIS (0 credits)
        if self.kyb_last_verified and self.kyb_statut_cnrc in ("ACTIF", "RADIE", "SUSPENDU") and self.kyb_nis == cleaned:
            return
        if (getattr(self.env, "context", None) or {}).get("kyb_skip_resolve"):
            return
        return self._do_kyb_resolve(cleaned)

    def _do_kyb_resolve(self, query: str):
        if isinstance(self.id, int) and self.id > 0:
            self = self.with_context(tracking_disable=True, mail_notrack=True)
        profile = None
        client = None
        try:
            client = _get_kyb_client(self.env)
        except Exception as e:
            _logger.warning("KYB client init error: %s", e)
            return {
                "warning": {
                    "title": _("Configuration KYB"),
                    "message": str(e),
                }
            }

        try:
            profile = client.resolve(query)
        except Exception as exc:
            _logger.info("KYB resolve by '%s' did not find immediate profile (%s), attempting live enrichment...", query, exc)
            # Automatic fallback: Attempt direct enrichment using whatever identifiers are available!
            try:
                rc_q = (
                    self.kyb_rc
                    or (self.company_registry if "company_registry" in self._fields else "")
                    or (query if any(c.isalpha() for c in query) and any(c.isdigit() for c in query) else "")
                )
                nif_q = (
                    self.kyb_nif
                    or self.vat
                    or (query if query.isdigit() and len(query) in (15, 20) else "")
                )
                nis_q = (
                    self.kyb_nis
                    or (query if query.isdigit() and len(query) == 15 else "")
                )
                name_q = self.name or (query if not any(c.isdigit() for c in query) else "")
                if rc_q or nif_q or nis_q or name_q:
                    enrich_resp = client.enrich(
                        rc_number=rc_q,
                        raison_sociale=name_q,
                        nif=nif_q,
                        nis=nis_q,
                    )
                    if isinstance(enrich_resp, dict) and enrich_resp.get("entity"):
                        profile = enrich_resp
            except Exception as e2:
                _logger.warning("KYB direct enrich fallback also failed for %s: %s", query, e2)

        if not profile or not (isinstance(profile, dict) and (profile.get("entity") or profile.get("data") or profile.get("raison_sociale"))):
            return {
                "warning": {
                    "title": _("Recherche Fiscale KYB"),
                    "message": _("Aucune entité trouvée pour l'identifiant '%s'. Vérifiez la saisie ou utilisez la recherche par Raison Sociale.") % query,
                }
            }

        # Map API response fields to Odoo partner fields (supports envelope unwrapping)
        if isinstance(profile, dict):
            data = profile.get("entity") or profile.get("data") or profile
            if not isinstance(data, dict):
                data = profile

            # Deep Enrichment Fallback: if resolve returned a partial skeleton without NIF or governance (capital/gerant), trigger live enrich
            if not data.get("nif") or not (data.get("capital_social") or data.get("representant_legal")):
                try:
                    rc_cand = (
                        data.get("rc_number")
                        or self.kyb_rc
                        or (self.company_registry if "company_registry" in self._fields else "")
                        or (query if any(c.isalpha() for c in query) and any(c.isdigit() for c in query) else "")
                    )
                    nif_cand = (
                        data.get("nif")
                        or self.kyb_nif
                        or self.vat
                        or (query if query.isdigit() and len(query) in (15, 20) else "")
                    )
                    nis_cand = (
                        data.get("nis")
                        or self.kyb_nis
                        or (query if query.isdigit() and len(query) == 15 else "")
                    )
                    name_cand = (
                        data.get("raison_sociale")
                        or self.name
                        or (query if not any(c.isdigit() for c in query) else "")
                    )
                    if rc_cand or nif_cand or nis_cand or name_cand:
                        enrich_resp = client.enrich(
                            rc_number=rc_cand,
                            raison_sociale=name_cand,
                            nif=nif_cand,
                            nis=nis_cand,
                            force_live=True,
                        )
                        if isinstance(enrich_resp, dict) and isinstance(enrich_resp.get("entity"), dict):
                            for k, v in enrich_resp["entity"].items():
                                if v is not None and v != "":
                                    data[k] = v
                except Exception as e_deep:
                    _logger.warning("KYB deep enrich fallback in _do_kyb_resolve failed for %s: %s", query, e_deep)

            # ── Strict Algerian CNRC Classification: Personne Morale (PM) vs Personne Physique (PP) ──
            rc_val = data.get("rc_number") or data.get("rcNumber") or data.get("rc") or data.get("numero_rc", "")
            forme_val = data.get("forme_juridique") or data.get("formeJuridique") or ""

            # Category 'B' (e.g. 15B0070815) = Personne Morale (société: SARL, EURL, SPA...).
            # Category 'A' (e.g. 16A0123456) = Personne Physique (commerçant individuel).
            # Category 'C' = Artisan / Coopérative.
            is_pm = False
            if rc_val and re.search(r'[0-9]+[B][0-9]+', rc_val, re.IGNORECASE):
                is_pm = True
            elif any(f in (forme_val or "").upper() for f in ("SARL", "EURL", "SPA", "SNC", "SCS", "SCA", "GIE", "EPE", "MORALE")):
                is_pm = True

            is_pp = False
            if rc_val and re.search(r'[0-9]+[AC][0-9]+', rc_val, re.IGNORECASE):
                is_pp = True
            elif "PHYSIQUE" in (forme_val or "").upper() or (forme_val or "").upper() == "PP":
                is_pp = True

            if is_pm:
                self.is_company = True
                if "company_type" in self._fields:
                    self.company_type = "company"
                if not forme_val:
                    forme_val = "Société (Personne Morale)"
                # Odoo Best Practice: A Personne Morale (PM) is a root commercial entity.
                # Never set parent_id (Employeur) to the company itself (prevents recursive hierarchy and duplicate partner records).
                if "parent_id" in self._fields and self.parent_id:
                    self.parent_id = False
            elif is_pp:
                self.is_company = False
                if "company_type" in self._fields:
                    self.company_type = "person"
                if not forme_val:
                    forme_val = "Personne Physique"
                # A Personne Physique (commerçant individuel) is self-employed, not an employee.
                if "parent_id" in self._fields and self.parent_id and not self.parent_id.is_company:
                    self.parent_id = False

            if forme_val:
                self.kyb_forme_juridique = forme_val
            capital = data.get("capital_social") or data.get("capitalSocial")
            if capital and is_pm:
                self.kyb_capital_social = str(capital)
            elif is_pp:
                self.kyb_capital_social = str(capital) if capital else "N/A (Patrimoine Individuel)"

            # Gérant / Représentant Légal:
            # - For PM (Personne Morale): Set to appointed corporate manager (Gérant / DG) from CNRC.
            # - For PP (Personne Physique): Set to titular individual owner / exploitant (Commerçant Titulaire).
            rep = data.get("representant_legal") or data.get("representantLegal")
            clean_rep = _clean_algerian_representant(rep) if rep else False
            if is_pm and clean_rep:
                self.kyb_representant_legal = clean_rep
            elif is_pp:
                self.kyb_representant_legal = clean_rep if clean_rep else (f"{self.name} (Titulaire)" if self.name else False)

            nif = data.get("nif") or ""
            if nif:
                self.kyb_nif = nif
                if not self.vat:
                    self.vat = nif
            elif self.vat and not self.kyb_nif:
                self.kyb_nif = self.vat
            elif self.kyb_nif and not self.vat:
                self.vat = self.kyb_nif

            if is_pp:
                self.is_company = False
                if "company_type" in self._fields:
                    self.company_type = "person"

            rc_official = data.get("rc_number_official") or data.get("rcNumberOfficial") or ""
            rc_raw = data.get("rc_number") or data.get("rcNumber") or data.get("rc") or data.get("numero_rc", "") or ""

            date_crea = data.get("date_creation") or data.get("date_immatriculation") or data.get("dateImmatriculation") or data.get("dateCreation")
            norm_crea = _normalize_algerian_date(date_crea)
            # Only an exact registry date is ever written to the Date field (never a deduced 01/01).
            if norm_crea:
                self.kyb_date_creation = norm_crea

            # ── Adresse & Wilaya Découplée: Résolution Géographique Cohérente ──
            adresse = data.get("adresse") or data.get("adresseSiegeSocial", "")
            wilaya_raw = data.get("wilaya", "")
            cp_raw = data.get("code_postal") or data.get("codePostal") or ""
            addr_parsed = _parse_algerian_address_components(adresse, wilaya_raw, cp_raw, raw_nif=self.kyb_nif or nif)
            wilaya_name = addr_parsed["wilaya_name"]
            wilaya_code = addr_parsed["wilaya_code"]

            self.street = addr_parsed["street"]
            self.street2 = addr_parsed["street2"]
            self.city = addr_parsed["city"]
            if addr_parsed["zip"]:
                self.zip = addr_parsed["zip"]
            if data.get("telephone") and not self.phone:
                self.phone = str(data.get("telephone")).strip()

            fallback_y = self.kyb_date_creation or (self.kyb_nif[2:4] if self.kyb_nif and len(self.kyb_nif) in (15, 20) and self.kyb_nif.isdigit() else None)
            rc = format_official_rc(rc_official or rc_raw, fallback_y, wilaya_code) or rc_official or rc_raw
            if rc:
                self.kyb_rc = rc
                if "company_registry" in self._fields:
                    self.company_registry = rc

            raison = data.get("raison_sociale") or data.get("raisonSociale") or data.get("name", "")
            if raison:
                self.name = raison

            statut = (data.get("statut_cnrc") or data.get("statutCnrc") or data.get("statut") or "INCONNU").upper()
            if "RAD" in statut or "مشطب" in statut:
                mapped_statut = "RADIE"
            elif "ACT" in statut or "نشط" in statut:
                mapped_statut = "ACTIF"
            elif "SUSP" in statut:
                mapped_statut = "SUSPENDU"
            else:
                mapped_statut = "INCONNU"

            if mapped_statut in dict(self._fields["kyb_statut_cnrc"].selection):
                self.kyb_statut_cnrc = mapped_statut

            date_rad = data.get("date_radiation") or data.get("dateRadiation") or data.get("date_rad")
            norm_rad = _normalize_algerian_date(date_rad)
            if norm_rad:
                self.kyb_date_radiation = norm_rad
            elif mapped_statut != "RADIE":
                self.kyb_date_radiation = False

            # ── Activités RC: Séparation Activité Principale & Activités Secondaires ──
            nae_raw = data.get("nae_codes") or data.get("naeCodes") or data.get("code_nae") or data.get("codeNae")
            if isinstance(nae_raw, list):
                self.kyb_nae_codes = ", ".join(str(c).strip() for c in nae_raw if c)
            elif isinstance(nae_raw, str):
                self.kyb_nae_codes = nae_raw.strip()

            acts_raw = data.get("activities") or data.get("activites") or []
            primary_act = data.get("activite_principale") or data.get("activitePrincipale") or data.get("activite") or ""
            primary_formatted = ""
            secondary_acts_lines = []

            if isinstance(acts_raw, list) and acts_raw:
                for idx, act in enumerate(acts_raw):
                    if isinstance(act, dict):
                        code = act.get("code") or ""
                        libelle = act.get("libelle") or act.get("name") or act.get("designation") or ""
                        formatted = f"[{code}] {libelle}".strip() if code else libelle.strip()
                        if idx == 0:
                            primary_formatted = formatted
                        elif formatted:
                            secondary_acts_lines.append(f"• {formatted}")
                    elif isinstance(act, str) and act.strip():
                        if idx == 0:
                            primary_formatted = act.strip()
                        else:
                            secondary_acts_lines.append(f"• {act.strip()}")
            elif isinstance(acts_raw, str) and acts_raw.strip():
                primary_formatted = acts_raw.strip()

            if not primary_formatted and primary_act:
                primary_formatted = str(primary_act).strip()

            if primary_formatted:
                self.kyb_activite = primary_formatted

            if secondary_acts_lines:
                self.kyb_activites_rc = "\n".join(secondary_acts_lines)
            else:
                self.kyb_activites_rc = False

            # Resolve Country & State
            dz_country = self.env.ref("base.dz", raise_if_not_found=False) or self.env["res.country"].search([("code", "=", "DZ")], limit=1)
            self.country_id = dz_country.id if dz_country else False
            if wilaya_name and dz_country:
                st = False
                # 1. Exact Wilaya code match (01..58)
                if wilaya_code and str(wilaya_code).isdigit():
                    st = self.env["res.country.state"].search([
                        ("country_id", "=", dz_country.id),
                        ("code", "=", str(wilaya_code).zfill(2))
                    ], limit=1)
                # 2. Exact case-insensitive name match (=ilike, strictly preventing substring joins like 'Ibn Ziad/Constantine')
                if not st:
                    st = self.env["res.country.state"].search([
                        ("country_id", "=", dz_country.id),
                        ("name", "=ilike", wilaya_name)
                    ], limit=1)
                if not st:
                    try:
                        w_code = str(wilaya_code).zfill(2) if (wilaya_code and str(wilaya_code).isdigit()) else wilaya_name[:2].upper()
                        st = self.env["res.country.state"].sudo().create({
                            "name": wilaya_name,
                            "code": w_code,
                            "country_id": dz_country.id,
                        })
                    except Exception:
                        st = False
                self.state_id = st.id if st else False
            else:
                self.state_id = False

            article = data.get("article_imposition") or data.get("articleImposition") or data.get("article_imp", "")
            if article:
                self.kyb_article_imposition = article

            nis = data.get("nis") or data.get("numero_nis", "")
            self.kyb_nis = nis or False
            self.kyb_last_verified = fields.Datetime.now()

            # If calling on an existing record, persist immediately to database
            if isinstance(self.id, int) and self.id > 0:
                write_vals = {
                    "name": self.name,
                    "kyb_nif": self.kyb_nif,
                    "vat": self.vat,
                    "kyb_rc": self.kyb_rc,
                    "kyb_forme_juridique": self.kyb_forme_juridique,
                    "kyb_capital_social": self.kyb_capital_social,
                    "kyb_representant_legal": self.kyb_representant_legal,
                    "kyb_statut_cnrc": self.kyb_statut_cnrc,
                    "kyb_date_radiation": self.kyb_date_radiation,
                    "kyb_date_creation": self.kyb_date_creation,
                    "kyb_activite": self.kyb_activite,
                    "kyb_nae_codes": self.kyb_nae_codes,
                    "kyb_activites_rc": self.kyb_activites_rc,
                    "kyb_article_imposition": self.kyb_article_imposition,
                    "kyb_nis": self.kyb_nis,
                    "is_company": self.is_company,
                    "street": self.street,
                    "street2": self.street2,
                    "city": self.city,
                    "zip": self.zip,
                    "country_id": self.country_id.id if self.country_id else False,
                    "state_id": self.state_id.id if self.state_id else False,
                    "kyb_last_verified": self.kyb_last_verified,
                }
                if self.phone:
                    write_vals["phone"] = self.phone
                if "company_registry" in self._fields and self.company_registry:
                    write_vals["company_registry"] = self.company_registry
                # tracking_disable=True: suppress Odoo ORM field-diff chatter; the
                # institutional KYB card from _post_kyb_audit_log() is the sole audit trail.
                self.with_context(tracking_disable=True, mail_notrack=True, kyb_skip_audit_post=True).write(write_vals)
                if is_pp:
                    pp_post = {"is_company": False}
                    if "company_type" in self._fields:
                        pp_post["company_type"] = "person"
                    self.with_context(tracking_disable=True, mail_notrack=True, kyb_skip_audit_post=True).write(pp_post)
                elif is_pm:
                    pm_post = {"is_company": True}
                    if "company_type" in self._fields:
                        pm_post["company_type"] = "company"
                    self.with_context(tracking_disable=True, mail_notrack=True, kyb_skip_audit_post=True).write(pm_post)
                self._post_kyb_audit_log()

            # ── Duplicate Fiscal Identifier (NIF) Guard ──
            if self.kyb_nif:
                clean_nif = str(self.kyb_nif).strip()
                dup_domain = [("kyb_nif", "=", clean_nif)]
                cur_id = self.id if (isinstance(self.id, int) and self.id > 0) else (self._origin.id if getattr(self, "_origin", None) else False)
                if cur_id:
                    dup_domain.append(("id", "!=", cur_id))
                existing_dup = self.env["res.partner"].sudo().search(dup_domain, limit=1)
                if existing_dup:
                    dup_mode = _get_config_param(self.env, "kyb.duplicate_nif_policy", default="warn")
                    msg = _(
                        "Doublon fiscal détecté : Le contact '%(exist_name)s' (ID: %(exist_id)s) possède déjà ce NIF (%(nif)s).\n"
                        "Veuillez vérifier les fiches pour éviter la duplication des tiers (utilisez Actions → Fusionner si nécessaire)."
                    ) % {
                        "exist_name": existing_dup.name,
                        "exist_id": existing_dup.id,
                        "nif": clean_nif,
                    }
                    if dup_mode == "block":
                        raise UserError(msg)
                    elif dup_mode == "warn":
                        return {
                            "warning": {
                                "title": _("Avertissement Doublon NIF"),
                                "message": msg,
                            }
                        }

    # ──────────────── _name_search Safe Override ───────────────────

    @api.model
    def _name_search(
        self,
        name: str = "",
        domain: Optional[list] = None,
        operator: str = "ilike",
        limit: int = 100,
        order: Optional[str] = None,
    ):
        """
        Safe local partner search compatible across Odoo 16 through 20.
        Delegates to parent _name_search in Odoo 16, or native name_search in Odoo 17+.
        Eliminates duplicate background entity creations during live dropdown keystrokes.
        """
        parent_meth = getattr(super(), "_name_search", None)
        if callable(parent_meth):
            try:
                return parent_meth(
                    name=name, args=domain, operator=operator, limit=limit
                )
            except TypeError:
                return parent_meth(
                    name=name, domain=domain, operator=operator, limit=limit
                )
        return self.name_search(
            name=name, args=domain, operator=operator, limit=limit
        )

    # ──────────────── Sovereign Autocomplete Overrides (Loi 25-11) ────────────────

    @api.model
    def autocomplete_by_name(self, query, query_country_id=False, timeout=15):
        """
        Sovereign Autocomplete Override (Loi 25-11 & Décret 05-468):
        Intercepts Odoo's native 'partner_autocomplete' dropdown (DnB / Clearbit).
        Routes company name searches to the Algerian KYB Sovereign Registry
        instead of transmitting queries offshore to Odoo IAP servers.
        """
        sovereign_enabled = _get_config_bool(self.env, "kyb.sovereign_autocomplete", default=True)
        allow_worldwide = _get_config_bool(self.env, "kyb.allow_worldwide_fallback", default=False)

        # If user explicitly requested worldwide search (query_country_id == 0) and fallback is allowed
        if query_country_id == 0 and allow_worldwide:
            if hasattr(super(), "autocomplete_by_name"):
                return super().autocomplete_by_name(query, query_country_id, timeout=timeout)

        if not sovereign_enabled:
            if hasattr(super(), "autocomplete_by_name"):
                return super().autocomplete_by_name(query, query_country_id, timeout=timeout)
            return []

        dz_country = self.env.ref("base.dz", raise_if_not_found=False) or self.env["res.country"].search([("code", "=", "DZ")], limit=1)
        dz_country_dict = {"id": dz_country.id, "display_name": dz_country.display_name or dz_country.name} if dz_country else False

        try:
            client = _get_kyb_client(self.env)
            clean_q = (query or "").strip()
            if len(clean_q) < 3:
                return []
            # If query looks like an exact NIF, NIS, or RC (e.g. 9-20 digits or Algerian RC)
            if re.match(r'^\d{9,20}$', clean_q) or re.search(r'[0-9]+[A-Z][0-9]+', clean_q, re.I):
                try:
                    res_prof = client.resolve(clean_q)
                    direct_data = res_prof.get("entity") or res_prof.get("data")
                    if isinstance(direct_data, dict):
                        raison = direct_data.get("raison_sociale") or clean_q
                        rc_official = direct_data.get("rc_number_official") or direct_data.get("rcNumberOfficial") or ""
                        rc_raw = direct_data.get("rc_number") or ""
                        rc = rc_official or format_official_rc(rc_raw) or rc_raw
                        nif = direct_data.get("nif") or (clean_q if clean_q.isdigit() else "")
                        c_dir, w_dir, _wcode = _split_algerian_commune_wilaya(direct_data.get("wilaya") or direct_data.get("adresse") or "")
                        wilaya_clean = w_dir or direct_data.get("wilaya") or ""
                        city_clean = c_dir if c_dir else wilaya_clean
                        statut = direct_data.get("statut_cnrc") or "ACTIF"
                        statut_badge = "🟢 Actif" if "ACT" in statut.upper() else ("🔴 Radié" if "RAD" in statut.upper() else "")
                        dir_sub = f"RC: {rc} · {wilaya_clean} · {statut_badge}".strip(" ·")
                        return [{
                            "name": raison,
                            "city": dir_sub,
                            "country_id": dz_country_dict,
                            "duns": nif or rc_raw or rc or clean_q,
                            "vat": nif,
                            "rc_number": rc_raw,
                            "rc_official": rc_official or rc,
                            "wilaya": wilaya_clean,
                            "description": dir_sub,
                        }]
                except Exception:
                    pass

            filter_mode = _get_config_param(self.env, "kyb.autocomplete_filter", default="all")
            limit_setting = _get_config_param(self.env, "kyb.autocomplete_limit", default="20")
            try:
                cand_limit = max(10, min(30, int(limit_setting)))
            except (ValueError, TypeError):
                cand_limit = 20

            res = client.candidates(query, limit=cand_limit)
        except Exception as exc:
            _logger.warning("KYB candidates search failed for '%s': %s", query, exc)
            if hasattr(super(), "autocomplete_by_name") and allow_worldwide:
                return super().autocomplete_by_name(query, query_country_id, timeout=timeout)
            return []

        raw_candidates = res.get("candidates") or res.get("results") or []
        if not raw_candidates and hasattr(super(), "autocomplete_by_name") and allow_worldwide:
            return super().autocomplete_by_name(query, query_country_id, timeout=timeout)

        results = []
        for cand in raw_candidates:
            if not isinstance(cand, dict):
                continue
            raison = cand.get("raison_sociale") or cand.get("name") or query
            nif = cand.get("nif") or ""
            rc_official = cand.get("rc_number_official") or cand.get("rcNumberOfficial") or ""
            rc_raw = cand.get("rc_number") or cand.get("rc") or ""

            # 1. Fallback Year Resolution for Official 16-Character RC (Décret 05-468: WW/00-XXXXXXXBYY)
            fallback_year = None
            if cand.get("date_immatriculation"):
                m_yr = re.search(r'(\d{4})', str(cand["date_immatriculation"]))
                if m_yr:
                    fallback_year = m_yr.group(1)[-2:]
            if not fallback_year and cand.get("date_creation"):
                m_yr = re.search(r'(\d{4})', str(cand["date_creation"]))
                if m_yr:
                    fallback_year = m_yr.group(1)[-2:]
            if not fallback_year and nif and len(nif) >= 4 and nif.startswith("00") and nif[2:4].isdigit():
                fallback_year = nif[2:4]
            if not fallback_year and rc_raw and len(rc_raw) >= 3 and rc_raw[:2].isdigit():
                fallback_year = rc_raw[:2]

            rc_formatted = format_official_rc(rc_official or rc_raw, fallback_year=fallback_year)
            rc = rc_formatted or rc_official or rc_raw
            c_name, w_name, _wcode = _split_algerian_commune_wilaya(cand.get("wilaya") or "")
            wilaya_clean = w_name or cand.get("wilaya") or ""
            city_clean = c_name if c_name else wilaya_clean
            statut = cand.get("statut_cnrc") or cand.get("statut") or "ACTIF"
            forme = cand.get("forme_juridique") or cand.get("forme") or ""

            is_radie = bool("RAD" in str(statut).upper() or "مشطب" in str(statut))
            is_suspendu = bool("SUSP" in str(statut).upper() or "معلق" in str(statut))

            # Apply user-configured status filter
            if filter_mode == "active_only" and is_radie:
                continue

            # Discrete legal status styling (No emoji circles, clean institutional text, discrete badge on far right)
            if is_radie:
                statut_label = "Radié"
                statut_badge_style = "color: #b91c1c; background-color: #fef2f2; border: 1px solid #fecaca; padding: 1px 8px; border-radius: 9999px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em; display: inline-block; white-space: nowrap;"
            elif is_suspendu:
                statut_label = "Suspendu"
                statut_badge_style = "color: #b45309; background-color: #fffbeb; border: 1px solid #fde68a; padding: 1px 8px; border-radius: 9999px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em; display: inline-block; white-space: nowrap;"
            else:
                statut_label = "Actif"
                statut_badge_style = "color: #15803d; background-color: #f0fdf4; border: 1px solid #bbf7d0; padding: 1px 8px; border-radius: 9999px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em; display: inline-block; white-space: nowrap;"

            # Check if this candidate already exists in the local database (by NIF, RC, or exact name)
            local_partner = False
            if nif:
                local_partner = self.env["res.partner"].sudo().search([("kyb_nif", "=", nif)], limit=1)
            if not local_partner and rc:
                rc_variants = list(filter(None, {rc, rc_raw, rc_official, format_official_rc(rc_raw)}))
                domain = [("kyb_rc", "in", rc_variants)]
                if "company_registry" in self.env["res.partner"]._fields:
                    domain = ["|", ("kyb_rc", "in", rc_variants), ("company_registry", "in", rc_variants)]
                local_partner = self.env["res.partner"].sudo().search(domain, limit=1)
            if not local_partner and raison:
                local_partner = self.env["res.partner"].sudo().search([("name", "=ilike", raison.strip())], limit=1)

            local_tag = f" • ⚠️ Existant (#{local_partner.id})" if local_partner else ""

            # Use most reliable identifier for duns lookup: nif > raw rc > official rc > raison
            chosen_duns = nif or rc_raw or rc or raison

            # Format spacious subtitle: RC · Wilaya · Forme (Status rendered discrete on far right)
            sub_parts = []
            if rc:
                sub_parts.append(f"RC: {rc}")
            if wilaya_clean:
                sub_parts.append(wilaya_clean)
            if forme:
                sub_parts.append(forme)
            subtitle = (" · ".join(sub_parts) + local_tag).strip(" ·")

            results.append({
                "name": raison,
                # In Odoo partner_autocomplete_core.js, suggestion.city is copied directly to suggestion.description
                # Formatting city as subtitle guarantees universal rich rendering across all Odoo versions (16 to 20)
                "city": subtitle,
                "country_id": dz_country_dict,
                "duns": chosen_duns,
                "vat": nif,
                "rc_number": rc_raw,
                "rc_official": rc,
                "wilaya": wilaya_clean,
                "statut_cnrc": "RADIE" if is_radie else ("SUSPENDU" if is_suspendu else "ACTIF"),
                "forme_juridique": forme,
                "description": subtitle,
                "statut_badge_clean": statut_label,
                "statut_badge_style": statut_badge_style,
                "statut_label": statut_label,
            })

        # When showing all entities, sort ACTIF first, followed by RADIÉ
        if filter_mode == "all":
            results.sort(key=lambda x: 1 if ("RAD" in str(x.get("statut_cnrc", "")).upper() or "مشطب" in str(x.get("statut_cnrc", ""))) else 0)

        return results

    @api.model
    def autocomplete_by_vat(self, vat, query_country_id=False, timeout=15):
        """
        Sovereign NIF Autocomplete Override:
        Resolves Algerian NIF directly from KYB API (by Digidev).
        """
        sovereign_enabled = _get_config_bool(self.env, "kyb.sovereign_autocomplete", default=True)
        if not sovereign_enabled:
            if hasattr(super(), "autocomplete_by_vat"):
                return super().autocomplete_by_vat(vat, query_country_id, timeout=timeout)
            return []

        try:
            client = _get_kyb_client(self.env)
            profile = client.resolve(vat)
            data = profile.get("entity") or profile.get("data") or profile
            if isinstance(data, dict):
                dz_country = self.env.ref("base.dz", raise_if_not_found=False) or self.env["res.country"].search([("code", "=", "DZ")], limit=1)
                dz_country_dict = {"id": dz_country.id, "display_name": dz_country.display_name or dz_country.name} if dz_country else False
                rc_official = data.get("rc_number_official") or data.get("rcNumberOfficial") or ""
                rc_raw = data.get("rc_number") or ""
                rc = rc_official or format_official_rc(rc_raw) or rc_raw
                c_vat, w_vat, _wcode = _split_algerian_commune_wilaya(data.get("wilaya") or data.get("adresse") or "")
                wilaya_clean = w_vat or data.get("wilaya") or ""
                city_clean = c_vat if c_vat else wilaya_clean
                return [{
                    "name": data.get("raison_sociale") or data.get("name") or vat,
                    "city": city_clean or "Algérie",
                    "country_id": dz_country_dict,
                    "duns": data.get("nif") or vat,
                    "vat": data.get("nif") or vat,
                    "rc_number": rc_raw,
                    "rc_official": rc_official or rc,
                    "wilaya": wilaya_clean,
                    "description": f"{wilaya_clean} • RC: {rc}".strip(" •"),
                }]
        except Exception as exc:
            _logger.warning("KYB VAT autocomplete failed for '%s': %s", vat, exc)

        if hasattr(super(), "autocomplete_by_vat"):
            return super().autocomplete_by_vat(vat, query_country_id, timeout=timeout)
        return []

    @api.model
    def enrich_by_duns(self, duns, timeout=15):
        """
        Sovereign Entity Enrichment:
        Triggered when a suggestion from the autocomplete dropdown is selected.
        Queries the KYB Sovereign Gateway and maps all official CNRC & DGI fields:
        Raison Sociale, NIF, RC, NIS, Article d'Imposition, Activité Principale,
        Codes NAE, Toutes les Activités RC, et Adresse.
        """
        sovereign_enabled = _get_config_bool(self.env, "kyb.sovereign_autocomplete", default=True)
        if not sovereign_enabled:
            if hasattr(super(), "enrich_by_duns"):
                return super().enrich_by_duns(duns, timeout=timeout)
            return {}

        # Extract contextual candidate metadata passed by Odoo's OWL autocomplete client
        candidate_ctx = self.env.context.get("enriched_company_data") or self.env.context.get("company") or {}

        clean_duns = (duns or "").strip()
        data = None
        client = None
        if clean_duns:
            try:
                client = _get_kyb_client(self.env)
                profile = client.resolve(clean_duns)
                data = profile.get("entity") or profile.get("data") or profile
            except Exception as exc:
                _logger.info("KYB resolve in enrich_by_duns for '%s' did not find immediate profile (%s), trying fallback enrich...", clean_duns, exc)

        # Fallback 1: If resolve misses or returned partial data without NIF or deep governance (capital/gerant), attempt targeted enrich
        if not data or not isinstance(data, dict) or not data.get("nif") or not (data.get("capital_social") or data.get("representant_legal")):
            try:
                if not client:
                    client = _get_kyb_client(self.env)
                rc_cand = (
                    (data.get("rc_number") if isinstance(data, dict) else "")
                    or candidate_ctx.get("rc_number")
                    or candidate_ctx.get("rc_official")
                    or candidate_ctx.get("rc")
                    or (clean_duns if any(c.isdigit() for c in clean_duns) and any(c.isalpha() for c in clean_duns) else "")
                )
                nif_cand = (
                    (data.get("nif") if isinstance(data, dict) else "")
                    or candidate_ctx.get("vat")
                    or candidate_ctx.get("nif")
                    or (clean_duns if clean_duns.isdigit() and len(clean_duns) in (15, 20) else "")
                )
                name_cand = (
                    (data.get("raison_sociale") if isinstance(data, dict) else "")
                    or candidate_ctx.get("name")
                    or (clean_duns if not rc_cand and not nif_cand else "")
                )
                if rc_cand or nif_cand or name_cand:
                    enrich_resp = client.enrich(
                        rc_number=rc_cand,
                        nif=nif_cand,
                        raison_sociale=name_cand,
                        force_live=True if (not data or not (data.get("capital_social") or data.get("representant_legal"))) else False,
                    )
                    if isinstance(enrich_resp, dict) and enrich_resp.get("entity"):
                        enriched_entity = enrich_resp["entity"]
                        if isinstance(enriched_entity, dict):
                            if data and isinstance(data, dict):
                                # Merge enriched fields into existing data
                                for k, v in enriched_entity.items():
                                    if v is not None and v != "":
                                        data[k] = v
                            else:
                                data = enriched_entity
            except Exception as e2:
                _logger.warning("KYB fallback enrich in enrich_by_duns failed for '%s': %s", clean_duns, e2)

        # Fallback 2: If gateway returned empty, construct baseline from candidate context to guarantee populated form
        if not data or not isinstance(data, dict):
            if candidate_ctx and (candidate_ctx.get("name") or candidate_ctx.get("duns")):
                data = {
                    "raison_sociale": candidate_ctx.get("name") or clean_duns,
                    "rc_number": candidate_ctx.get("rc_number") or candidate_ctx.get("rc") or "",
                    "rc_number_official": candidate_ctx.get("rc_official") or "",
                    "wilaya": candidate_ctx.get("wilaya") or candidate_ctx.get("city") or "",
                    "nif": candidate_ctx.get("vat") or candidate_ctx.get("nif") or "",
                    "statut_cnrc": "ACTIF",
                }
            elif hasattr(super(), "enrich_by_duns"):
                return super().enrich_by_duns(duns, timeout=timeout)
            else:
                return {}

        # Cache resolved/enriched entity in _KYB_RECENT_RESOLVE_CACHE so subsequent create()/write()
        # or onchange calls hit 0ms in-memory cache with 0 credits and preserve exact registry dates.
        try:
            import time as _time
            now_ts = _time.time()
            for ck_raw in (
                data.get("nif"),
                data.get("rc_number"),
                data.get("rc_number_official"),
                candidate_ctx.get("vat"),
                candidate_ctx.get("rc_number"),
                candidate_ctx.get("rc_official"),
                clean_duns,
            ):
                if ck_raw:
                    ck_norm = re.sub(r"[\s\-_/.]", "", str(ck_raw).strip()).upper()
                    if ck_norm:
                        _KYB_RECENT_RESOLVE_CACHE[ck_norm] = (now_ts, {"entity": data})
        except Exception:
            pass

        dz_country = self.env.ref("base.dz", raise_if_not_found=False) or self.env["res.country"].search([("code", "=", "DZ")], limit=1)
        dz_country_dict = {"id": dz_country.id, "display_name": dz_country.display_name or dz_country.name} if dz_country else False

        # Map Wilaya & Address components to res.country.state, street, street2, city, zip
        state_dict = False
        raw_street = data.get("adresse") or data.get("adresseSiegeSocial") or ""
        raw_wilaya = data.get("wilaya") or candidate_ctx.get("wilaya") or ""
        raw_cp = data.get("code_postal") or data.get("codePostal") or candidate_ctx.get("code_postal") or ""
        nif_candidate = data.get("nif") or candidate_ctx.get("vat") or candidate_ctx.get("nif") or ""
        addr_parsed = _parse_algerian_address_components(raw_street, raw_wilaya, raw_cp, raw_nif=nif_candidate)
        wilaya_name = addr_parsed["wilaya_name"] or str(raw_wilaya).title()
        wilaya_code = addr_parsed["wilaya_code"]

        if wilaya_name and dz_country:
            state = False
            # 1. Exact Wilaya code match (01..58)
            if wilaya_code and str(wilaya_code).isdigit():
                state = self.env["res.country.state"].search([
                    ("country_id", "=", dz_country.id),
                    ("code", "=", str(wilaya_code).zfill(2))
                ], limit=1)
            # 2. Exact case-insensitive name match (=ilike, strictly preventing substring joins like 'Ibn Ziad/Constantine')
            if not state:
                state = self.env["res.country.state"].search([
                    ("country_id", "=", dz_country.id),
                    ("name", "=ilike", wilaya_name)
                ], limit=1)
            if not state:
                try:
                    w_code = str(wilaya_code).zfill(2) if (wilaya_code and str(wilaya_code).isdigit()) else wilaya_name[:2].upper()
                    if not w_code.isalnum():
                        w_code = "DZ"
                    state = self.env["res.country.state"].sudo().create({
                        "name": wilaya_name,
                        "code": w_code,
                        "country_id": dz_country.id,
                    })
                except Exception:
                    state = False
            if state:
                state_dict = {"id": state.id, "display_name": state.display_name or state.name}

        # Format NAE codes
        nae_raw = data.get("nae_codes") or data.get("naeCodes") or data.get("code_nae") or data.get("codeNae")
        nae_str = ""
        if isinstance(nae_raw, list):
            nae_str = ", ".join(str(c).strip() for c in nae_raw if c)
        elif isinstance(nae_raw, str):
            nae_str = nae_raw.strip()

        # Format RC activities: Séparation Activité Principale Dominante & Activités Secondaires
        acts_raw = data.get("activities") or data.get("activites") or []
        primary_act = data.get("activite_principale") or data.get("activitePrincipale") or data.get("activite") or ""
        primary_formatted = ""
        secondary_acts_lines = []

        if isinstance(acts_raw, list) and acts_raw:
            for idx, act in enumerate(acts_raw):
                if isinstance(act, dict):
                    code = act.get("code") or ""
                    libelle = act.get("libelle") or act.get("name") or act.get("designation") or ""
                    formatted = f"[{code}] {libelle}".strip() if code else libelle.strip()
                    if idx == 0:
                        primary_formatted = formatted
                    elif formatted:
                        secondary_acts_lines.append(f"• {formatted}")
                elif isinstance(act, str) and act.strip():
                    if idx == 0:
                        primary_formatted = act.strip()
                    else:
                        secondary_acts_lines.append(f"• {act.strip()}")
        elif isinstance(acts_raw, str) and acts_raw.strip():
            primary_formatted = acts_raw.strip()

        if not primary_formatted and primary_act:
            primary_formatted = str(primary_act).strip()

        statut_raw = (data.get("statut_cnrc") or data.get("statutCnrc") or data.get("statut") or "INCONNU").upper()
        if "RAD" in statut_raw or "مشطب" in statut_raw:
            statut_mapped = "RADIE"
        elif "ACT" in statut_raw or "نشط" in statut_raw:
            statut_mapped = "ACTIF"
        elif "SUSP" in statut_raw:
            statut_mapped = "SUSPENDU"
        else:
            statut_mapped = "INCONNU"

        # ── Strict Algerian Classification: Personne Morale vs Personne Physique ──
        rc_official = data.get("rc_number_official") or data.get("rcNumberOfficial") or candidate_ctx.get("rc_official") or ""
        rc_raw = data.get("rc_number") or data.get("rcNumber") or data.get("rc") or candidate_ctx.get("rc_number") or ""
        date_crea_val = _normalize_algerian_date(data.get("date_creation") or data.get("date_immatriculation") or data.get("dateImmatriculation") or data.get("dateCreation"))
        if not date_crea_val:
            date_crea_val = _deduce_algerian_creation_date(nif=nif_candidate, rc=rc_official or rc_raw or candidate_ctx.get("rc_official") or candidate_ctx.get("rc_number"))
        fallback_y = date_crea_val or (nif_candidate[2:4] if nif_candidate and len(nif_candidate) in (15, 20) and nif_candidate.isdigit() else None)
        rc_val = format_official_rc(rc_official or rc_raw, fallback_y, addr_parsed["wilaya_code"]) or rc_official or rc_raw
        if not date_crea_val and rc_val:
            date_crea_val = _deduce_algerian_creation_date(rc=rc_val)
        forme_val = data.get("forme_juridique") or data.get("formeJuridique") or ""

        is_pm = False
        if rc_val and (re.search(r'[0-9]+[B][0-9]+', rc_val, re.IGNORECASE) or re.search(r'B\d{2}$', rc_val, re.IGNORECASE)):
            is_pm = True
        elif any(f in (forme_val or "").upper() for f in ("SARL", "EURL", "SPA", "SNC", "SCS", "SCA", "GIE", "EPE", "MORALE")):
            is_pm = True

        is_pp = False
        if rc_val and (re.search(r'[0-9]+[AC][0-9]+', rc_val, re.IGNORECASE) or re.search(r'[AC]\d{2}$', rc_val, re.IGNORECASE)):
            is_pp = True
        elif "PHYSIQUE" in (forme_val or "").upper() or (forme_val or "").upper() == "PP":
            is_pp = True

        nif_val = data.get("nif") or candidate_ctx.get("vat") or candidate_ctx.get("nif") or ""
        date_rad_val = _normalize_algerian_date(data.get("date_radiation") or data.get("dateRadiation") or data.get("radiation_date"))

        enrich_dict = {
            "name": data.get("raison_sociale") or data.get("raisonSociale") or data.get("name") or candidate_ctx.get("name", ""),
            "vat": nif_val,
            "kyb_nif": nif_val,
            "kyb_rc": rc_val,
            "kyb_nis": data.get("nis") or data.get("numero_nis") or "",
            "kyb_article_imposition": data.get("article_imposition") or data.get("articleImposition") or "",
            "kyb_statut_cnrc": statut_mapped,
            "kyb_date_creation": date_crea_val or False,
            "kyb_date_radiation": date_rad_val if statut_mapped == "RADIE" else False,
            "kyb_activite": primary_formatted,
            "kyb_nae_codes": nae_str,
            "kyb_activites_rc": "\n".join(secondary_acts_lines) if secondary_acts_lines else False,
            "street": addr_parsed["street"] or "",
            "street2": addr_parsed["street2"] or False,
            "city": addr_parsed["city"] or "",
            "zip": addr_parsed["zip"] or "",
        }
        if data.get("telephone"):
            enrich_dict["phone"] = str(data.get("telephone")).strip()

        if is_pm:
            enrich_dict["is_company"] = True
            if "company_type" in self._fields:
                enrich_dict["company_type"] = "company"
            if not forme_val:
                forme_val = "Société (Personne Morale)"
        elif is_pp:
            enrich_dict["is_company"] = False
            if "company_type" in self._fields:
                enrich_dict["company_type"] = "person"
            if not forme_val:
                forme_val = "Personne Physique"

        if forme_val:
            enrich_dict["kyb_forme_juridique"] = forme_val
        if data.get("capital_social") or data.get("capitalSocial"):
            enrich_dict["kyb_capital_social"] = str(data.get("capital_social") or data.get("capitalSocial"))
        elif is_pp:
            enrich_dict["kyb_capital_social"] = "N/A (Patrimoine Individuel)"

        rep_raw = data.get("representant_legal") or data.get("representantLegal")
        clean_rep = _clean_algerian_representant(rep_raw) if rep_raw else False
        if clean_rep:
            enrich_dict["kyb_representant_legal"] = clean_rep
        elif is_pp:
            enrich_dict["kyb_representant_legal"] = str(enrich_dict.get("name") or "") + " (Titulaire)"
        if dz_country_dict:
            enrich_dict["country_id"] = dz_country_dict
        else:
            enrich_dict["country_id"] = False
        if state_dict:
            enrich_dict["state_id"] = state_dict
        else:
            enrich_dict["state_id"] = False
        if "company_registry" in self._fields:
            enrich_dict["company_registry"] = rc_val or False

        # Whitelisted core fields: always return so Odoo's autocomplete client
        # cleanly replaces previous candidate values without bleeding or leakage.
        # Date fields (kyb_date_creation, kyb_date_radiation) are EXCLUDED
        # from this autocomplete return path to prevent Odoo 20's serializeDate()
        # TypeError: value.toFormat is not a function. In Odoo 20, the web framework
        # expects Luxon DateTime objects for Date fields in onchange payloads, but this
        # autocomplete RPC returns raw ISO strings / False. Dates are written correctly
        # by the server-side write() path in action_verify_kyb_sheet, which bypasses
        # the client-side Luxon serialization layer entirely. (Fix: v2.0.1)
        ALWAYS_SYNC_FIELDS = {
            "name", "vat", "kyb_nif", "kyb_rc", "kyb_nis", "kyb_article_imposition",
            "kyb_statut_cnrc", "kyb_activite",
            "kyb_nae_codes", "kyb_activites_rc", "street", "street2", "city", "zip", "country_id", "state_id",
            "is_company", "company_type", "kyb_forme_juridique", "kyb_capital_social",
            "kyb_representant_legal", "company_registry", "kyb_date_creation", "kyb_date_radiation"
        }
        # In Odoo 14.0, 15.0, 16.0: web client accepts standard ISO strings (YYYY-MM-DD) for Date fields.
        # In Odoo 17+: OWL 2 uses Luxon DateTime for Date fields, so raw strings crash serializeDate().
        try:
            import odoo.release
            is_legacy_web = getattr(odoo.release, "version_info", (14,))[0] < 17
        except Exception:
            is_legacy_web = False
        _AUTOCOMPLETE_DATE_EXCLUDE = set() if is_legacy_web else {"kyb_date_creation", "kyb_date_radiation"}
        return {
            k: v for k, v in enrich_dict.items()
            if k not in _AUTOCOMPLETE_DATE_EXCLUDE
            and (k in ALWAYS_SYNC_FIELDS or (v is not None and v != ""))
        }

    # ──────────────── Odoo 14.0 & 15.0 Partner Autocomplete Compatibility ────────────────

    @api.model
    def autocomplete(self, query, timeout=15):
        """
        Odoo 14.0 & 15.0 Partner Autocomplete Override:
        Delegates legacy `res.partner.autocomplete(query)` RPC to `autocomplete_by_name`
        and maps `partner_gid` / `website` so Odoo 14/15 `_getOdooSuggestions` and `_enrichCompany`
        display the rich KYB subtitle and trigger full entity enrichment on selection.
        """
        res = self.autocomplete_by_name(query, timeout=timeout)
        for item in res:
            if isinstance(item, dict):
                if not item.get("website") and item.get("city"):
                    item["website"] = item["city"]
                if not item.get("partner_gid"):
                    item["partner_gid"] = item.get("duns") or item.get("vat") or item.get("rc_number") or 1
        return res

    @api.model
    def read_by_vat(self, vat, timeout=15):
        """
        Odoo 14.0 & 15.0 VAT Autocomplete Override:
        Delegates legacy `res.partner.read_by_vat(vat)` RPC to `autocomplete_by_vat`.
        """
        res = self.autocomplete_by_vat(vat, timeout=timeout)
        for item in res:
            if isinstance(item, dict):
                if not item.get("website") and item.get("city"):
                    item["website"] = item["city"]
                if not item.get("partner_gid"):
                    item["partner_gid"] = item.get("duns") or item.get("vat") or 1
        return res

    @api.model
    def enrich_company(self, company_domain, partner_gid, vat, timeout=15):
        """
        Odoo 14.0 & 15.0 Partner Autocomplete Enrichment Override:
        Delegates legacy `res.partner.enrich_company(company_domain, partner_gid, vat)` RPC
        to `enrich_by_duns`.
        """
        duns_query = vat or (str(partner_gid) if partner_gid and str(partner_gid) != "1" else "") or company_domain or ""
        return self.enrich_by_duns(duns_query, timeout=timeout)

    @api.model
    def cron_kyb_sync_telemetry(self):
        """Automated daily cron: sends heartbeat telemetry and checks for updates."""
        try:
            self.env["res.config.settings"].cron_kyb_sync_telemetry()
        except Exception as err:
            _logger.warning("KYB res.partner cron telemetry failed: %s", err)
        return True

