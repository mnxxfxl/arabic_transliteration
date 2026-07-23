#!/usr/bin/env python3
"""
Dual-form Arabic transliterator for the dissertation prototype.

OUTPUTS:
    T_rev  - compact reversible/typeable transliteration based on the proposed
             QWERTY-safe Arabic-Latin inventory. Users do NOT type artificial
             separators. A dot (.) is a sukun marker, not a token separator.
    T_read - Indonesian-readable transliteration without Latin diacritics, with
             sentence-final waqf that drops the final short vowel/tanween.

USAGE EXAMPLE:
    from_t_rev("bis.mi") == "بِسْمِ"

STRUCTURE:
    1. Unicode constants for Arabic diacritical marks
    2. T_rev and T_read inventories with character/mark mappings
    3. Helper functions for text analysis and boundary detection
    4. Main encoding functions: to_t_rev(), to_t_read()
    5. Decoding function: from_t_rev()
    6. Script demonstration; regression tests live under tests/

NOTES:
    - This module is self-contained and uses only the Python standard library
    - Both T_rev and T_read preserve diacritic order in a stable, reproducible manner
    - T_rev enables round-trip conversion; T_read is optimized for readability
"""
from dataclasses import dataclass
import re
import sys
import unittest
import unicodedata
from typing import Dict, List, Optional, Tuple

__all__ = [
    "ALLOW_CONVENTIONAL_T_REV_USER_INPUT",
    "SHOW_TESTS_IN_UI",
    "TransliterationResult",
    "normalize_arabic",
    "to_t_rev",
    "to_t_read",
    "from_t_rev",
    "transliterate",
]

ALLOW_CONVENTIONAL_T_REV_USER_INPUT = True
SHOW_TESTS_IN_UI = False
VISUAL_RTL_CONSOLE_FALLBACK = sys.platform == "win32"
ARABIC_SCRIPT_RE = re.compile(r"[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff]")

# ---------------------------------------------------------------------------
# Arabic signs
# ---------------------------------------------------------------------------
FATHA = "\u064e"       # َ
DAMMA = "\u064f"       # ُ
KASRA = "\u0650"       # ِ
FATHATAN = "\u064b"    # ً
DAMMATAN = "\u064c"    # ٌ
KASRATAN = "\u064d"    # ٍ
SUKUN = "\u0652"       # ْ
SHADDA = "\u0651"      # ّ
DAGGER_ALEF = "\u0670" # ٰ
MADDA_ABOVE = "\u0653" # ٓ
TATWEEL = "\u0640"     # ـ
HAMZA_ABOVE = "\u0654" # ٔ
HAMZA_BELOW = "\u0655" # ٕ
ALEF_MADDA_ABOVE = "\u0622"    # آ
ALEF_WASLA = "\u0671"          # ٱ
SUBSCRIPT_ALEF = "\u0656"       # ٖ
INVERTED_DAMMA = "\u0657"      # ٗ
OPEN_FATHATAN = "\u08f0"       # ࣰ
OPEN_DAMMATAN = "\u08f1"       # ࣱ
OPEN_KASRATAN = "\u08f2"       # ࣲ
SUKUN2 = "\u06e1"              # ۡ
SMALL_WAW = "\u06e5"           # ۥ
SMALL_YEH = "\u06e6"           # ۦ
KEMENAG_STOP_MARK = "\u06d5"   # ە
ARABIC_FULL_STOP = "\u06d4"    # ۔

HARAKAT = {FATHA, DAMMA, KASRA, FATHATAN, DAMMATAN, KASRATAN, SUKUN, SHADDA,
           DAGGER_ALEF, MADDA_ABOVE, SUBSCRIPT_ALEF, INVERTED_DAMMA,
           OPEN_FATHATAN, OPEN_DAMMATAN, OPEN_KASRATAN,
           SUKUN2, SMALL_WAW, SMALL_YEH}

# ---------------------------------------------------------------------------
# T_rev inventory: compact, QWERTY-safe, no artificial separators.
# ---------------------------------------------------------------------------
AR_TO_TREV_LETTER: Dict[str, str] = {
    "ا": "A",   "ب": "b",   "ت": "t",   "ث": "ts",  "ج": "j",
    "ح": "H",   "خ": "kh",  "د": "d",   "ذ": "dz",  "ر": "r",
    "ز": "z",   "س": "s",   "ش": "sy",  "ص": "sh",  "ض": "dh",
    "ط": "th",  "ظ": "zh",  "ع": "'",   "غ": "gh",  "ف": "f",
    "ق": "q",   "ك": "k",   "ل": "l",   "م": "m",   "ن": "n",
    "ه": "h",   "و": "w",   "ي": "y",   "ة": "t-",  "ء": "`",
    "ى": "Y",
    # Hamzah-carrier letters are kept typeable. The standalone hamzah uses `.
    # These carrier tokens are handled before the bare hamzah token in decoding.
    "أ": "`A", "إ": "`I", "ئ": "`y", "ؤ": "`w",
}

AR_TO_TREV_MARK: Dict[str, str] = {
    FATHA: "a", DAMMA: "u", KASRA: "i",
    DAGGER_ALEF: "AA", INVERTED_DAMMA: "UU", SUBSCRIPT_ALEF: "II",
    MADDA_ABOVE: "~",
    ALEF_MADDA_ABOVE: "A~~", ALEF_WASLA: "A&",
    FATHATAN: "an-", DAMMATAN: "un-", KASRATAN: "in-",
    OPEN_FATHATAN: "an_", OPEN_DAMMATAN: "un_", OPEN_KASRATAN: "in_",
    SUKUN: ".", SUKUN2: "..",
    TATWEEL: "_",
    SMALL_WAW: "^W", SMALL_YEH: "^Y",
}

# T_read inventory: one Indonesian-readable profile, no Latin diacritics.
# Consonants largely copy T_rev because T_rev has already been made QWERTY-safe.
AR_TO_TREAD_LETTER: Dict[str, str] = {
    "ا": "",    "ب": "b",   "ت": "t",   "ث": "ts",  "ج": "j",
    "ح": "hh",  "خ": "kh",  "د": "d",   "ذ": "dz",  "ر": "r",
    "ز": "z",   "س": "s",   "ش": "sy",  "ص": "sh",  "ض": "dh",
    "ط": "th",  "ظ": "zh",  "ع": "'",   "غ": "gh",  "ف": "f",
    "ق": "q",   "ك": "k",   "ل": "l",   "م": "m",   "ن": "n",
    "ه": "h",   "و": "w",   "ي": "y",   "ة": "h",   "ء": "`",
    "ى": "aa",  "أ": "`",   "إ": "`",   "آ": "aa",  "ٱ": "",    "ئ": "`",  "ؤ": "`",
}

AR_TO_TREAD_MARK: Dict[str, str] = {
    FATHA: "a", DAMMA: "u", KASRA: "i",
    DAGGER_ALEF: "aa", INVERTED_DAMMA: "uu", SUBSCRIPT_ALEF: "ii",
    MADDA_ABOVE: "",
    FATHATAN: "an", DAMMATAN: "un", KASRATAN: "in",
    OPEN_FATHATAN: "an", OPEN_DAMMATAN: "un", OPEN_KASRATAN: "in",
    SUKUN: "", SUKUN2: "",
    SMALL_WAW: "uu", SMALL_YEH: "ii",
}

# Decomposed hamzah-carrier sequences in some Uthmani sources are
# preserved as distinct T_rev tokens. These are different Unicode strings
# from the precomposed carrier letters أ، ؤ، ئ and must not collapse during
# T_rev round-trip reconstruction.
DECOMP_HAMZA_SEQ_TO_TREV: Dict[str, str] = {
    "ءا": "`_A",
    "ءو": "`_w",
    "ءي": "`_y",
    "ءى": "`_Y",
}
TREV_TO_DECOMP_HAMZA_SEQ: Dict[str, str] = {
    v: k for k, v in DECOMP_HAMZA_SEQ_TO_TREV.items()
}

# Reverse maps for T_rev.
TREV_CONSONANT_TO_AR: Dict[str, str] = {v: k for k, v in AR_TO_TREV_LETTER.items()
                                       if k not in {"أ", "إ", "ئ", "ؤ"}}
# Special carrier and mark tokens must be checked before consonant tokens.
TREV_SPECIAL_TO_AR: Dict[str, str] = {
    **TREV_TO_DECOMP_HAMZA_SEQ,
    "`A": "أ", "`I": "إ", "`y": "ئ", "`w": "ؤ",
    "AA": DAGGER_ALEF, "UU": INVERTED_DAMMA, "II": SUBSCRIPT_ALEF,
    "A~~": ALEF_MADDA_ABOVE, "A&": ALEF_WASLA,
    "~": MADDA_ABOVE, "^s": SHADDA,
    "^W": SMALL_WAW, "^Y": SMALL_YEH,
    "_": TATWEEL,
    "..": SUKUN2,
    "an-": FATHATAN, "un-": DAMMATAN, "in-": KASRATAN,
    "an_": OPEN_FATHATAN, "un_": OPEN_DAMMATAN, "in_": OPEN_KASRATAN,
    ".": SUKUN,
}
TREV_VOWEL_TO_AR = {"a": FATHA, "u": DAMMA, "i": KASRA}

# Tokens that are safe to treat as consonants for shaddah detection.
CONSONANT_TOKENS = sorted(TREV_CONSONANT_TO_AR.keys(), key=len, reverse=True)
SPECIAL_TOKENS = sorted(TREV_SPECIAL_TO_AR.keys(), key=len, reverse=True)
TREV_LONG_SEQUENCES = (
    ("aa", FATHA + "ا"),
    ("aY", FATHA + "ى"),
    ("iY", KASRA + "ى"),
    ("iy", KASRA + "ي"),
    ("uw", DAMMA + "و"),
    ("aw.", FATHA + "و" + SUKUN),
    ("ay.", FATHA + "ي" + SUKUN),
)
TREV_SEPARATOR = "|"
TREV_EXPLICIT_SHADDA = "^s"
TREV_LONG_SEQUENCE_TOKENS = {seq for seq, _ in TREV_LONG_SEQUENCES}
TREV_ALLAH_ALIAS_RE = re.compile(r"(?<![A-Za-z])[Aa]llah([aiu]?)(?![A-Za-z])")

SUN_LETTERS = set("تثدذرزسشصضطظلن")
SUN_TREAD_TOKENS = sorted(
    (AR_TO_TREAD_LETTER[ch] for ch in SUN_LETTERS if ch in AR_TO_TREAD_LETTER),
    key=len,
    reverse=True,
)
TREAD_SHADDA_GROUPS = sorted(
    (group for group in set(AR_TO_TREAD_LETTER.values()) if group),
    key=len,
    reverse=True,
)

# Tanween vowel markers that can trigger idgham rules
TANWEEN_MARKS = {
    FATHATAN,
    OPEN_FATHATAN,
    DAMMATAN,
    OPEN_DAMMATAN,
    KASRATAN,
    OPEN_KASRATAN,
}
TANWEEN_TO_VOWEL = {
    FATHATAN: "a", OPEN_FATHATAN: "a",
    DAMMATAN: "u", OPEN_DAMMATAN: "u",
    KASRATAN: "i", OPEN_KASRATAN: "i",
}
IKHFA_LETTERS = set("تثجدذزسشصضطظفقك")
TREAD_IKHFA_MARKER = "\u2060"
_TREAD_IQLAB_MEEM = "\u06E2"

# Ta marbutah vowel markers
TA_MARBUTAH_VOWELS = {FATHA, DAMMA, KASRA, FATHATAN, DAMMATAN, KASRATAN,
                      OPEN_FATHATAN, OPEN_DAMMATAN, OPEN_KASRATAN}

# Sentence-final pause markers for the T_read waqf rule. Comma is intentionally
# excluded because it is normally a continuation mark, not a sentence boundary.
SENTENCE_END_CHARS = set(".!?؟؛;۝" + ARABIC_FULL_STOP)
WAQF_DROPPED_MARKS = {FATHA, DAMMA, KASRA, FATHATAN, DAMMATAN, KASRATAN,
                      OPEN_FATHATAN, OPEN_DAMMATAN, OPEN_KASRATAN}

# --------- Regex patterns for T_read article rules ---------
# Group of punctuation marks for word/article boundaries
ARABIC_PUNCTUATION = {",", "،", ":", "ۖ", "ۚ", "ۛ", "ۗ", "ۘ", "ۙ", "ۜ"}

# Divine name variants for normalization
ALLAH_VARIANTS = [
    (re.compile(r"\bal-llaa([hiu])?\b"), r"Allah\1"),
    (re.compile(r"\bal-llah([aiu])?\b"), r"Allah\1"),
    (re.compile(r"\bal-lah([aiu])?\b"), r"Allah\1"),
    (re.compile(r"\ballaah([aiu])?\b"), r"Allah\1"),
    (re.compile(r"\ballah([aiu])?\b"), r"Allah\1"),
]
SUN_ARTICLE_RULES = [
    (re.compile(pattern), replacement)
    for token in SUN_TREAD_TOKENS
    if token
    for escaped in [re.escape(token)]
    for pattern, replacement in (
        (rf"\bwaal-{escaped}{escaped}", rf"waa{token}{token}"),
        (rf"\bwaal-{escaped}", rf"waa{token}{token}"),
        (rf"\bal-{escaped}{escaped}", rf"a{token}-{token}"),
        (rf"\bal-{escaped}", rf"a{token}-{token}"),
    )
]
WA_ARTICLE_RE = re.compile(r"\bwaal-")
ATTACHED_ARTICLE_RE = re.compile(r"([aiu])al-")
CONNECTED_ALLAH_RE = re.compile(r"([aiu])\s+Allah")
ATTACHED_ALLAH_RE = re.compile(r"([aiu])Allah([aiu]?)\b")
CONNECTED_ARTICLE_RE = re.compile(r"([aiu])\s+a([a-z`]+-)")
SPLIT_LONG_A_RE = re.compile(r"(?<![A-Za-z])a_a(?![A-Za-z])")
SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([,.;:!?])")
HORIZONTAL_SPACE_RE = re.compile(r"[ \t]+")
_TREAD_IQLAB_VOWEL_MEEM_RE = re.compile(
    rf"([{FATHA}{KASRA}{DAMMA}]){_TREAD_IQLAB_MEEM}(?=\s+ب)"
)


def _at_sentence_boundary_after(text: str, index: int) -> bool:
    """Return True if a character at index is followed by sentence boundary/end.

    This helper is used only for T_read. It lets the readable output apply
    waqf by suppressing the final short vowel or tanween before a sentence
    boundary while leaving T_rev unchanged.
    """
    j = index + 1
    # Allow additional combining signs after the vowel mark.
    while j < len(text) and unicodedata.combining(text[j]):
        j += 1
    # Fathatan is commonly written before a silent alif. For the simplified
    # readable waqf profile, that alif is treated as part of the final ending.
    if (
        index < len(text)
        and text[index] in {FATHATAN, OPEN_FATHATAN}
        and j < len(text)
        and text[j] == "ا"
    ):
        j += 1
        while j < len(text) and unicodedata.combining(text[j]):
            j += 1
    while j < len(text) and text[j].isspace():
        j += 1
    return j >= len(text) or text[j] in SENTENCE_END_CHARS


def _next_base_index_after_for_tread(
    text: str,
    index_after_mark: int,
    skip_fathatan_carrier: bool = False,
) -> Tuple[Optional[int], Optional[str]]:
    """Return the index and value of the next Arabic base letter for T_read rules.

    This ignores combining marks, Arabic vowel marks, and whitespace. For
    fathatan written before a silent alif or alif maqsurah, the carrier can be
    skipped so that هُدًى ل... is treated as tanween followed by ل.
    """
    j = index_after_mark
    if skip_fathatan_carrier and j < len(text) and text[j] in {"ا", "ى"}:
        j += 1
        while j < len(text) and (unicodedata.combining(text[j]) or text[j] in HARAKAT):
            j += 1
    while (
        j < len(text)
        and (unicodedata.combining(text[j]) or text[j] in HARAKAT or text[j].isspace())
    ):
        j += 1
    if j < len(text) and text[j] not in SENTENCE_END_CHARS:
        return j, text[j]
    return None, None


def _next_base_after_for_tread(
    text: str,
    index_after_mark: int,
    skip_fathatan_carrier: bool = False,
) -> Optional[str]:
    """Return the next Arabic base letter after a mark for connected T_read rules.

    This ignores combining marks and whitespace. For fathatan written over a
    preceding consonant before alif maqsurah or silent alif, the carrier may be
    skipped so that هُدًى ل... is treated as tanween followed by ل, not as a
    pause-form long aa.
    """
    return _next_base_index_after_for_tread(
        text,
        index_after_mark,
        skip_fathatan_carrier,
    )[1]


def _is_dagger_alif_sequence(
    text: str,
    index: int,
    nxt: str,
    nxt2: str,
    nxt3: str,
) -> Optional[int]:
    """Check for fathah + various dagger-alif combinations.
    
    Returns the number of characters to consume if a dagger-alif sequence is found,
    otherwise None.
    """
    if nxt == "آ":
        return 2
    if nxt == "ى":
        if nxt2 == MADDA_ABOVE and nxt3 == DAGGER_ALEF:
            return 4
        if nxt2 == DAGGER_ALEF and nxt3 == MADDA_ABOVE:
            return 4
        if nxt2 == DAGGER_ALEF:
            return 3
    if nxt == DAGGER_ALEF:
        if nxt2 == MADDA_ABOVE:
            return 3
        return 2
    if nxt == MADDA_ABOVE and nxt2 == DAGGER_ALEF:
        return 3
    return None


def _previous_base_before(text: str, index_before_mark: int) -> Optional[str]:
    """Return the nearest preceding non-combining base character."""
    j = index_before_mark - 1
    while j >= 0 and (unicodedata.combining(text[j]) or text[j] in HARAKAT):
        j -= 1
    if j >= 0:
        return text[j]
    return None


def _prev_base_and_marks_before(
    text: str,
    index: int,
) -> Tuple[Optional[str], List[str], Optional[int]]:
    """Return nearest preceding base and the marks attached to it before index."""
    j = index - 1
    marks_reversed: List[str] = []
    while j >= 0 and (unicodedata.combining(text[j]) or text[j] in HARAKAT):
        marks_reversed.append(text[j])
        j -= 1
    if j < 0:
        return None, [], None
    return text[j], list(reversed(marks_reversed)), j


def _base_has_following_vowel_or_sukun(text: str, index: int) -> bool:
    """Return True if the base at index is explicitly vowelled or marked as consonantal."""
    j = index + 1
    while j < len(text) and (unicodedata.combining(text[j]) or text[j] in HARAKAT):
        if text[j] in {FATHA, DAMMA, KASRA, FATHATAN, DAMMATAN, KASRATAN,
                       OPEN_FATHATAN, OPEN_DAMMATAN, OPEN_KASRATAN, SUKUN, SUKUN2, SHADDA}:
            return True
        j += 1
    return False


def _at_word_initial(text: str, index: int) -> bool:
    """Return True if the base at index starts a token/word-like span."""
    j = index - 1
    while j >= 0 and (unicodedata.combining(text[j]) or text[j] in HARAKAT):
        j -= 1
    return (
        j < 0
        or text[j].isspace()
        or text[j] in SENTENCE_END_CHARS
        or text[j] in ARABIC_PUNCTUATION
    )


def _is_word_boundary_after(text: str, index: int) -> bool:
    """Return True if the base at index is followed by a word boundary or punctuation."""
    j = index + 1
    while j < len(text) and (unicodedata.combining(text[j]) or text[j] in HARAKAT):
        j += 1
    return (
        j >= len(text)
        or text[j].isspace()
        or text[j] in SENTENCE_END_CHARS
        or text[j] in ARABIC_PUNCTUATION
    )


def _is_aesthetic_or_recitation_mark(ch: str) -> bool:
    """Return True for unsupported Uthmani layout, pause, and recitation signs."""
    code = ord(ch)
    if ch == KEMENAG_STOP_MARK:
        return True
    if 0x0610 <= code <= 0x061A:
        return True
    if 0x06D6 <= code <= 0x06ED and ch not in {SUKUN2, SMALL_WAW, SMALL_YEH}:
        return True
    if 0x08D4 <= code <= 0x08FF:
        return True
    return False


def _strip_aesthetic_quranic_marks(text: str) -> str:
    """Remove ornamental Quranic marks outside the supported reversible layer."""
    cleaned_chars: List[str] = []
    i = 0
    while i < len(text):
        ch = text[i]

        if ch in {HAMZA_ABOVE, HAMZA_BELOW}:
            cleaned_chars.append("ء")
            i += 1
            continue

        if _is_aesthetic_or_recitation_mark(ch):
            i += 1
            continue

        cleaned_chars.append(ch)
        i += 1

    return "".join(cleaned_chars)


@dataclass
class TransliterationResult:
    """Result of Arabic transliteration into T_rev and T_read forms.
    
    Attributes:
        source: Original Arabic text.
        t_rev: Reversible (round-trip capable) compact transliteration.
        t_read: Indonesian-readable transliteration optimized for pronunciation.
    """
    source: str
    t_rev: str
    t_read: str


def _ordered_cluster(base: str, marks: List[str]) -> str:
    """Return one Arabic base character with combining marks in stable order."""
    priority = {
        SHADDA: 0,
        FATHA: 1, DAMMA: 1, KASRA: 1, FATHATAN: 1, DAMMATAN: 1, KASRATAN: 1,
        OPEN_FATHATAN: 1, OPEN_DAMMATAN: 1, OPEN_KASRATAN: 1,
        SUKUN: 2, SUKUN2: 2,
        DAGGER_ALEF: 3, MADDA_ABOVE: 3, SUBSCRIPT_ALEF: 3, INVERTED_DAMMA: 3,
        SMALL_WAW: 3, SMALL_YEH: 3,
    }
    return base + "".join(sorted(marks, key=lambda m: (priority.get(m, 9), ord(m))))


def normalize_arabic(text: str, *, collapse_kemenag_alef_fatha: bool = True) -> str:
    """Normalize Arabic text while preserving diacritics in a stable order."""
    text = unicodedata.normalize("NFC", text)
    text = _strip_aesthetic_quranic_marks(text).replace("ۡ", SUKUN2)
    # Kemenag text sometimes writes fatha + alef + fatha for a long /aa/.
    # Collapse the redundant alef-carried fatha for the canonical reversible form.
    if collapse_kemenag_alef_fatha:
        text = text.replace(FATHA + "ا" + FATHA, FATHA + "ا")
    text = re.sub(r"[ \t\r\n\f\v]+", " ", text).strip()
    out: List[str] = []
    base = ""
    marks: List[str] = []
    for ch in text:
        if unicodedata.combining(ch) or ch in HARAKAT:
            if base:
                marks.append(ch)
            else:
                out.append(ch)
        else:
            if base:
                out.append(_ordered_cluster(base, marks))
            base = ch
            marks = []
    if base:
        out.append(_ordered_cluster(base, marks))
    return "".join(out)


def _last_consonant_index_and_token(
    tokens: List[str],
) -> Tuple[Optional[int], Optional[str]]:
    for idx in range(len(tokens) - 1, -1, -1):
        token = tokens[idx]
        if token in TREV_CONSONANT_TO_AR:
            return idx, token
    return None, None


def _last_t_rev_token(tokens: List[str]) -> Optional[str]:
    for token in reversed(tokens):
        if token != TREV_SEPARATOR:
            return token
    return None


def _needs_t_rev_separator(
    previous: Optional[str],
    current: str,
    *,
    shadda_duplicate: bool = False,
    current_followed_by_shadda: bool = False,
) -> bool:
    """Return True when adjacent emitted tokens would decode differently."""
    if previous is None or shadda_duplicate:
        return False

    joined = previous + current
    if joined in TREV_LONG_SEQUENCE_TOKENS:
        if joined in {"iy", "uw", "aY", "iY"} and current_followed_by_shadda:
            return False
        return True

    if joined in TREV_CONSONANT_TO_AR or joined in TREV_SPECIAL_TO_AR:
        return True

    # Prefix collisions, e.g. standalone hamzah ` followed by AA would be
    # greedily read as the carrier token `A unless separated.
    for token in SPECIAL_TOKENS:
        if len(token) > len(previous) and joined.startswith(token):
            return True
    if previous == "`" and current == "_":
        return True

    # Repeated consonant tokens normally mean shaddah in T_rev. Keep the
    # compact triple form for cases like Allah (l + l + shaddah), but separate
    # ordinary adjacent identical letters.
    if previous == current and current in TREV_CONSONANT_TO_AR:
        return not current_followed_by_shadda

    return False


def _append_t_rev_token(
    tokens: List[str],
    token: str,
    *,
    shadda_duplicate: bool = False,
    current_followed_by_shadda: bool = False,
) -> None:
    if not token:
        return
    previous = _last_t_rev_token(tokens)
    if token == "_" and previous == "n":
        significant = [item for item in tokens if item != TREV_SEPARATOR]
        if len(significant) >= 2 and significant[-2] in TREV_VOWEL_TO_AR:
            tokens.append(TREV_SEPARATOR)
            tokens.append(token)
            return
    if _needs_t_rev_separator(
        previous,
        token,
        shadda_duplicate=shadda_duplicate,
        current_followed_by_shadda=current_followed_by_shadda,
    ):
        tokens.append(TREV_SEPARATOR)
    tokens.append(token)


def to_t_rev(arabic: str) -> str:
    """Convert Arabic text to compact T_rev (reversible form).
    
    Args:
        arabic: Normalized or unnormalized Arabic text with optional diacritics.
        
    Returns:
        Compact QWERTY-safe transliteration without separators. This form can be
        decoded back to Arabic via from_t_rev() for exact round-trip conversion.
        
    Example:
        >>> to_t_rev("بِسْمِ")
        'bis.mi'
    """
    text = normalize_arabic(arabic)
    out: List[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        nxt2 = text[i + 2] if i + 2 < len(text) else ""
        nxt3 = text[i + 3] if i + 3 < len(text) else ""

        # Preserve decomposed hamzah-carrier sequences exactly.
        # These occur in Uthmani text as two base characters, e.g. ءا, ءو, ءي.
        # They must remain distinct from precomposed أ, ؤ, ئ for strict T_rev
        # round-trip reconstruction.
        pair = ch + nxt
        if pair in DECOMP_HAMZA_SEQ_TO_TREV:
            _append_t_rev_token(out, DECOMP_HAMZA_SEQ_TO_TREV[pair])
            i += 2
            continue

        # Long-vowel and diphthong rules. These are typed without separators.
        if ch == FATHA and nxt == "ا":
            _append_t_rev_token(out, "aa"); i += 2; continue
        if ch == FATHA and nxt == "ى" and nxt2 != SHADDA:
            _append_t_rev_token(out, "aY"); i += 2; continue
        if ch == KASRA and nxt == "ي" and nxt2 != SHADDA:
            _append_t_rev_token(out, "iy"); i += 2; continue
        if ch == KASRA and nxt == "ى" and nxt2 != SHADDA:
            _append_t_rev_token(out, "iY"); i += 2; continue
        if ch == DAMMA and nxt == "و" and nxt2 != SHADDA:
            _append_t_rev_token(out, "uw"); i += 2; continue
        if ch == FATHA and nxt == "و" and nxt2 in {SUKUN, SUKUN2}:
            _append_t_rev_token(out, "aw."); i += 3; continue
        if ch == FATHA and nxt == "ي" and nxt2 in {SUKUN, SUKUN2}:
            _append_t_rev_token(out, "ay."); i += 3; continue

        if ch == SHADDA:
            token = out[-1] if out else None
            if token in TREV_CONSONANT_TO_AR:
                _append_t_rev_token(out, token, shadda_duplicate=True)
            else:
                _append_t_rev_token(out, TREV_EXPLICIT_SHADDA)
            i += 1
            continue

        if ch in AR_TO_TREV_LETTER:
            _append_t_rev_token(
                out,
                AR_TO_TREV_LETTER[ch],
                current_followed_by_shadda=nxt == SHADDA,
            )
            i += 1
            continue
        if ch in AR_TO_TREV_MARK:
            _append_t_rev_token(out, AR_TO_TREV_MARK[ch]); i += 1; continue
        _append_t_rev_token(out, ch)
        i += 1
    return "".join(out)


def _apply_tread_article_rules(text: str) -> str:
    """Apply the fixed Indonesian readable article profile.

    The readable form is pronunciation-oriented. In addition to ordinary
    sun-letter assimilation, it handles the divine name Allah as a conventional
    Indonesian/English spelling exception: the base word is written ``Allah``,
    not ``allaah``. In connected speech, a preceding final vowel joins directly
    to the lam of Allah because the hamzat al-wasl is not pronounced. For
    example, ``bismi Allahi`` is rendered as ``bismillahi`` and, under
    sentence-final waqf, ``bismillah``. The same connected-reading rule is
    also generalized for the ordinary definite article: when a word ending in
    a rendered vowel is followed by ``al-`` or an assimilated sun-letter article
    such as ``ar-`` or ``an-``, the initial article vowel is elided.
    For example, ``dzaalika al-kitaabu`` becomes ``dzaalikal-kitaabu``.
    """
    for pattern, replacement in SUN_ARTICLE_RULES:
        # Definite article attached to the conjunction wa-. This source form is
        # written without a space, e.g. وَالنَّاسِ. The readable output keeps
        # the familiar wa- vowel and applies sun-letter assimilation directly:
        # wa + al-naas -> waannaas.
        # Most sun-letter words are already doubled by shaddah, e.g. al-rr...
        # The final pattern is a fallback for undiacritized words.
        text = pattern.sub(replacement, text)

    # Definite article attached to wa- before moon letters: wa + al-kitaab -> wal-kitaab.
    text = WA_ARTICLE_RE.sub("wal-", text)

    # Attached-prefix hamzat-al-wasl elision before the definite article.
    # When prefixes such as bi- are written directly before al-, the article
    # hamzah is not pronounced in connected reading:
    #   bi + al-ghaib -> bil-ghaib.
    # This is restricted to rendered article forms containing the hyphen, so
    # ordinary word-internal sequences such as maaliki are not touched.
    text = ATTACHED_ARTICLE_RE.sub(r"\1l-", text)

    # Divine-name normalization. The internal renderer can produce variants
    # such as al-llah, al-llahi, or al-llaahi depending on the exact diacritic
    # sequence. T_read normalizes these to the conventional spelling Allah plus
    # any remaining pronounced case vowel. If waqf has already removed the final
    # case vowel, the output is simply Allah.
    for pattern, replacement in ALLAH_VARIANTS:
        text = pattern.sub(replacement, text)

    # Connected pronunciation: when Allah follows a word ending in a short
    # vowel, suppress the word boundary and the initial hamzat al-wasl while
    # keeping the conventional spelling without doubled-aa.
    # Examples: bismi Allah -> bismillah; bismi Allahi -> bismillahi.
    text = CONNECTED_ALLAH_RE.sub(r"\1llah", text)
    text = ATTACHED_ALLAH_RE.sub(r"\1llah\2", text)

    # General hamzat-al-wasl elision before the definite article in connected
    # reading. This applies after sun-letter assimilation has already converted
    # forms such as al-rahhmaan into ar-rahhmaan. It joins a preceding rendered
    # vowel to the article consonant while dropping only the article's initial
    # vowel. Examples:
    #   dzaalika al-kitaab   -> dzaalikal-kitaab
    #   huwa ar-rahhmaan     -> huwar-rahhmaan
    #   birabbi an-naas      -> birabbin-naas
    text = CONNECTED_ARTICLE_RE.sub(r"\1\2", text)
    return text


def _sanitize_tread_output(text: str) -> str:
    """Remove internal placeholders and non-readable Uthmani marks from T_read.

    T_read is the user-facing readable form. It must not expose internal long-
    vowel placeholders such as ``a_a`` and it should not pass through Qur'anic
    annotation signs that are not part of the Latin-readable output. T_rev is
    intentionally left unchanged for strict round-trip reconstruction.
    """
    # Internal placeholder cleanup. These should never be visible to users.
    text = text.replace("a_a", "aa").replace("i_i", "ii").replace("u_u", "uu")
    # Defensive cleanup for accidental split long vowels around underscores.
    text = SPLIT_LONG_A_RE.sub("aa", text)

    cleaned: List[str] = []
    for ch in text:
        code = ord(ch)
        # Tatweel and Qur'anic annotation/stop signs are not part of T_read.
        if ch == "\u0640":
            continue
        if 0x0610 <= code <= 0x061A:
            continue
        if 0x06D6 <= code <= 0x06ED:
            continue
        if 0x08D4 <= code <= 0x08FF:
            continue
        # Drop any remaining combining mark that leaked after rendering.
        if unicodedata.combining(ch):
            continue
        if ch == "؟":
            cleaned.append("?")
        elif ch == "؛":
            cleaned.append(";")
        elif ch == "،":
            cleaned.append(",")
        elif ch == ARABIC_FULL_STOP:
            cleaned.append(".")
        else:
            cleaned.append(ch)
    text = "".join(cleaned)
    # Remove spaces before punctuation and normalize whitespace.
    text = SPACE_BEFORE_PUNCT_RE.sub(r"\1", text)
    text = HORIZONTAL_SPACE_RE.sub(" ", text)
    return text.strip()


@dataclass
class _TReadState:
    """Mutable state for connected-reading rules during T_read rendering."""

    pending_idgham_lr: Optional[str] = None
    pending_idgham_bigunnah: Optional[str] = None
    suppress_shadda_at: Optional[int] = None
    skip_spaces_before_idgham_target: bool = False


def _peek(text: str, index: int) -> str:
    """Return a character by index, or an empty string beyond text bounds."""
    if 0 <= index < len(text):
        return text[index]
    return ""


def _is_mark(ch: str) -> bool:
    """Return True for combining marks and Arabic harakat handled by the rules."""
    return bool(ch) and (unicodedata.combining(ch) or ch in HARAKAT)


def _advance_after_tanween(ch: str, nxt: str) -> int:
    if ch in {FATHATAN, OPEN_FATHATAN} and nxt in {"ا", "ى"}:
        return 2
    return 1


def _advance_tread_pending(
    text: str,
    index: int,
    out: List[str],
    state: _TReadState,
) -> Optional[int]:
    """Apply delayed idgham state before processing the current character."""
    ch = text[index]
    nxt = _peek(text, index + 1)

    if state.skip_spaces_before_idgham_target:
        if ch.isspace():
            return index + 1
        if not _is_mark(ch):
            state.skip_spaces_before_idgham_target = False

    if state.pending_idgham_bigunnah is not None:
        if ch.isspace():
            return index + 1
        if ch in {"ي", "ن", "م", "و"}:
            out.append(state.pending_idgham_bigunnah + "-")
            state.pending_idgham_bigunnah = None
            state.suppress_shadda_at = index + 1 if nxt == SHADDA else None
        elif not _is_mark(ch):
            state.pending_idgham_bigunnah = None

    if state.pending_idgham_lr is not None:
        if ch.isspace():
            return index + 1
        if ch in {"ل", "ر"}:
            out.append(AR_TO_TREAD_LETTER[ch] + "-")
            state.pending_idgham_lr = None
            state.suppress_shadda_at = index + 1 if nxt == SHADDA else None
        else:
            state.pending_idgham_lr = None

    return None


def _consume_nun_sakinah_idgham(
    text: str,
    index: int,
    out: List[str],
    state: _TReadState,
) -> Optional[int]:
    """Handle nun-sakinah idgham before shaddah-bearing idgham letters."""
    ch = text[index]
    nxt = _peek(text, index + 1)
    if ch != "ن":
        return None

    has_explicit_sukun = nxt in {SUKUN, SUKUN2}
    if has_explicit_sukun:
        next_idx, next_base = _next_base_index_after_for_tread(text, index + 2)
        boundary_index = index + 1
        advance = 2
    elif nxt.isspace():
        next_idx, next_base = _next_base_index_after_for_tread(text, index + 1)
        boundary_index = index
        advance = 1
    else:
        next_idx, next_base = None, None
        boundary_index = index
        advance = 1

    target_has_shadda = (
        next_idx is not None and _peek(text, next_idx + 1) == SHADDA
    )
    no_sukun_bigunnah_target = (
        not has_explicit_sukun and next_base in {"و", "ي"}
    )
    no_sukun_shadda_target = (
        not has_explicit_sukun
        and next_base in {"م", "ن", "ل", "ر"}
        and target_has_shadda
    )
    if (
        not has_explicit_sukun
        and not (no_sukun_bigunnah_target or no_sukun_shadda_target)
    ):
        return None

    if (
        next_base in {"ي", "ن", "م", "و"}
        and (target_has_shadda or no_sukun_bigunnah_target)
        and not _at_sentence_boundary_after(text, boundary_index)
    ):
        out.append(AR_TO_TREAD_LETTER[next_base])
        if target_has_shadda and next_idx is not None:
            state.suppress_shadda_at = next_idx + 1
        return index + advance

    if next_base in {"ل", "ر"} and not _at_sentence_boundary_after(
        text,
        boundary_index,
    ):
        out.append(AR_TO_TREAD_LETTER[next_base] + "-")
        state.skip_spaces_before_idgham_target = True
        if target_has_shadda:
            state.suppress_shadda_at = next_idx + 1
        return index + advance

    return None


def _consume_meem_sakinah_idgham(
    text: str,
    index: int,
    out: List[str],
    state: _TReadState,
) -> Optional[int]:
    """Handle meem-sakinah assimilation before shaddah-bearing meem."""
    if text[index] != "م":
        return None

    nxt = _peek(text, index + 1)
    if nxt in {SUKUN, SUKUN2}:
        next_idx, next_base = _next_base_index_after_for_tread(text, index + 2)
        boundary_index = index + 1
        advance = 2
    elif nxt.isspace():
        next_idx, next_base = _next_base_index_after_for_tread(text, index + 1)
        boundary_index = index
        advance = 1
    else:
        return None

    if (
        next_base == "م"
        and next_idx is not None
        and _peek(text, next_idx + 1) == SHADDA
        and not _at_sentence_boundary_after(text, boundary_index)
    ):
        out.append("m")
        state.suppress_shadda_at = next_idx + 1
        return index + advance

    return None


def _consume_nun_sakinah_iqlab(
    text: str,
    index: int,
    out: List[str],
    state: _TReadState,
) -> Optional[int]:
    """Render nun sakinah as meem before ba."""
    del state
    if text[index] != "ن" or _peek(text, index + 1) not in {SUKUN, SUKUN2}:
        return None

    _, next_base = _next_base_index_after_for_tread(text, index + 2)
    if next_base == "ب" and not _at_sentence_boundary_after(text, index + 1):
        out.append("m")
        return index + 2

    return None


def _consume_nun_sakinah_ikhfa(
    text: str,
    index: int,
    out: List[str],
    state: _TReadState,
) -> Optional[int]:
    """Mark nun-sakinah ikhfa before the standard ikhfa letters."""
    del state
    ch = text[index]
    nxt = _peek(text, index + 1)
    if ch != "ن":
        return None

    if nxt in {SUKUN, SUKUN2}:
        _, next_base = _next_base_index_after_for_tread(text, index + 2)
        boundary_index = index + 1
        advance = 2
    elif nxt.isspace():
        _, next_base = _next_base_index_after_for_tread(text, index + 1)
        boundary_index = index
        advance = 1
    else:
        return None

    if next_base in IKHFA_LETTERS and not _at_sentence_boundary_after(
        text,
        boundary_index,
    ):
        out.append("n" + TREAD_IKHFA_MARKER)
        return index + advance

    return None


def _consume_ta_marbuta(
    text: str,
    index: int,
    out: List[str],
    state: _TReadState,
) -> Optional[int]:
    """Render ta marbutah as connected /t/ or pause /h/."""
    del state
    ch = text[index]
    nxt = _peek(text, index + 1)
    if ch != "ة":
        return None
    if nxt in TA_MARBUTAH_VOWELS and not _at_sentence_boundary_after(text, index + 1):
        out.append("t")
    else:
        out.append("h")
    return index + 1


def _consume_dagger_alif(
    text: str,
    index: int,
    out: List[str],
    state: _TReadState,
) -> Optional[int]:
    """Collapse readable fathah plus dagger-alif sequences to one long aa."""
    del state
    if text[index] != FATHA:
        return None
    consume = _is_dagger_alif_sequence(
        text,
        index,
        _peek(text, index + 1),
        _peek(text, index + 2),
        _peek(text, index + 3),
    )
    if consume is None:
        return None
    out.append("aa")
    return index + consume


def _consume_tanween_idgham(
    text: str,
    index: int,
    out: List[str],
    state: _TReadState,
) -> Optional[int]:
    """Handle connected tanween idgham before y/n/m/w and l/r."""
    ch = text[index]
    if ch not in TANWEEN_MARKS:
        return None

    nxt = _peek(text, index + 1)
    vowel = TANWEEN_TO_VOWEL[ch]
    skip_carrier = ch in {FATHATAN, OPEN_FATHATAN}
    nxt_base = _next_base_after_for_tread(
        text,
        index + 1,
        skip_fathatan_carrier=skip_carrier,
    )
    if nxt_base in {"ي", "ن", "م", "و"} and not _at_sentence_boundary_after(
        text,
        index,
    ):
        out.append(vowel)
        state.pending_idgham_bigunnah = AR_TO_TREAD_LETTER[nxt_base]
        return index + _advance_after_tanween(ch, nxt)

    if nxt_base in {"ل", "ر"} and not _at_sentence_boundary_after(text, index):
        out.append(vowel)
        state.pending_idgham_lr = AR_TO_TREAD_LETTER[nxt_base]
        return index + _advance_after_tanween(ch, nxt)

    return None


def _consume_tanween_iqlab(
    text: str,
    index: int,
    out: List[str],
    state: _TReadState,
) -> Optional[int]:
    """Render the nasal element of connected tanween as meem before ba."""
    del state
    ch = text[index]
    if ch not in TANWEEN_MARKS:
        return None

    nxt = _peek(text, index + 1)
    skip_carrier = ch in {FATHATAN, OPEN_FATHATAN}
    nxt_base = _next_base_after_for_tread(
        text,
        index + 1,
        skip_fathatan_carrier=skip_carrier,
    )
    if nxt_base == "ب" and not _at_sentence_boundary_after(text, index):
        out.append(TANWEEN_TO_VOWEL[ch] + "m")
        return index + _advance_after_tanween(ch, nxt)

    return None


def _consume_tanween_ikhfa(
    text: str,
    index: int,
    out: List[str],
    state: _TReadState,
) -> Optional[int]:
    """Mark tanween ikhfa and consume silent fathatan carriers."""
    del state
    ch = text[index]
    if ch not in TANWEEN_MARKS:
        return None

    nxt = _peek(text, index + 1)
    skip_carrier = ch in {FATHATAN, OPEN_FATHATAN}
    nxt_base = _next_base_after_for_tread(
        text,
        index + 1,
        skip_fathatan_carrier=skip_carrier,
    )
    if nxt_base in IKHFA_LETTERS and not _at_sentence_boundary_after(text, index):
        out.append(AR_TO_TREAD_MARK[ch] + TREAD_IKHFA_MARKER)
        return index + _advance_after_tanween(ch, nxt)

    return None


def _consume_waqf(
    text: str,
    index: int,
    out: List[str],
    state: _TReadState,
) -> Optional[int]:
    """Suppress sentence-final short vowels and tanween for T_read."""
    del out, state
    ch = text[index]
    nxt = _peek(text, index + 1)
    if ch not in WAQF_DROPPED_MARKS or not _at_sentence_boundary_after(text, index):
        return None
    if ch in {FATHATAN, OPEN_FATHATAN} and nxt == "ا":
        return index + 2
    return index + 1


def _match_allah_name(text: str, index: int) -> Optional[Tuple[int, str]]:
    """Return the end index and readable Allah form at index, if present."""
    ch = text[index]
    if ch in {"ا", "ٱ"}:
        j = index + 1
        if _peek(text, j) == FATHA:
            j += 1
        if _peek(text, j) != "ل":
            return None
        j += 1
        if _peek(text, j) in {SUKUN, SUKUN2}:
            j += 1
    elif ch == "ل":
        prev_base, prev_marks, _ = _prev_base_and_marks_before(text, index)
        if prev_base != "ل" or KASRA not in prev_marks:
            return None
        j = index
    else:
        return None

    if _peek(text, j) != "ل" or _peek(text, j + 1) != SHADDA:
        return None

    j += 2
    while _peek(text, j) in {FATHA, DAGGER_ALEF, MADDA_ABOVE}:
        j += 1
    if _peek(text, j) != "ه":
        return None

    j += 1
    suffix = ""
    if _peek(text, j) in {FATHA, DAMMA, KASRA}:
        mark = _peek(text, j)
        if not _at_sentence_boundary_after(text, j):
            suffix = AR_TO_TREAD_MARK[mark]
        j += 1
    return j, "Allah" + suffix


def _consume_allah_name(
    text: str,
    index: int,
    out: List[str],
    state: _TReadState,
) -> Optional[int]:
    """Render Allah with the conventional readable spelling."""
    del state
    match = _match_allah_name(text, index)
    if match is None:
        return None
    next_i, rendered = match
    out.append(rendered)
    return next_i


def _consume_definite_article(
    text: str,
    index: int,
    out: List[str],
    state: _TReadState,
) -> Optional[int]:
    """Render Arabic definite article as the readable base form al-."""
    del state
    if text[index] not in {"ا", "ٱ"}:
        return None

    j = index + 1
    if _peek(text, j) == FATHA:
        j += 1
    if _peek(text, j) != "ل":
        return None

    out.append("al-")
    j += 1
    if _peek(text, j) in {SUKUN, SUKUN2}:
        j += 1
    return j


def _consume_tread_vowel_sequence(
    text: str,
    index: int,
    out: List[str],
    state: _TReadState,
) -> Optional[int]:
    """Render explicit long vowels and diphthongs in T_read."""
    del state
    ch = text[index]
    nxt = _peek(text, index + 1)
    nxt2 = _peek(text, index + 2)

    if (
        ch == FATHA
        and nxt == "ا"
        and nxt2 == "ل"
        and _previous_base_before(text, index) in {"و", "ف", "ت"}
    ):
        out.append("a")
        return index + 1
    if ch == FATHA and nxt in {"ا", "ى"} and nxt2 == FATHA:
        out.append("a a")
        return index + 3
    if ch == KASRA and nxt in {"ي", "ى"} and nxt2 == KASRA:
        out.append("i i")
        return index + 3
    if ch == DAMMA and nxt == "و" and nxt2 == DAMMA:
        out.append("u u")
        return index + 3
    if ch == FATHA and nxt in {"ا", "ى"} and nxt2 != SHADDA:
        out.append("aa")
        return index + 2
    if (
        ch == KASRA
        and nxt in {"ي", "ى"}
        and (nxt2 not in HARAKAT or nxt2 in {SUKUN, SUKUN2})
        and nxt2 != SHADDA
    ):
        out.append("ii")
        return index + (3 if nxt2 in {SUKUN, SUKUN2} else 2)
    if (
        ch == DAMMA
        and nxt == "و"
        and (nxt2 not in HARAKAT or nxt2 in {SUKUN, SUKUN2})
    ):
        out.append("uu")
        return index + (3 if nxt2 in {SUKUN, SUKUN2} else 2)
    if ch == FATHA and nxt == "و" and nxt2 in {SUKUN, SUKUN2}:
        out.append("au")
        return index + 3
    if ch == FATHA and nxt == "ي" and nxt2 in {SUKUN, SUKUN2}:
        out.append("ai")
        return index + 3
    return None


def _consume_mater_lectionis(
    text: str,
    index: int,
    out: List[str],
    state: _TReadState,
) -> Optional[int]:
    """Fallback long-vowel handling for partially vocalized Uthmani text."""
    del state
    ch = text[index]
    if (
        ch == "ي"
        and not _base_has_following_vowel_or_sukun(text, index)
        and not _at_word_initial(text, index)
    ):
        _, prev_marks, _ = _prev_base_and_marks_before(text, index)
        if FATHA in prev_marks:
            out.append("i")
        elif DAMMA in prev_marks:
            out.append("y")
        else:
            out.append("ii")
        return index + 1

    if (
        ch == "و"
        and not _base_has_following_vowel_or_sukun(text, index)
        and not _at_word_initial(text, index)
    ):
        _, prev_marks, _ = _prev_base_and_marks_before(text, index)
        if FATHA in prev_marks:
            out.append("u")
        elif KASRA in prev_marks:
            out.append("w")
        else:
            out.append("uu")
        return index + 1

    if ch == "ا" and not _at_word_initial(text, index):
        prev_base, _, _ = _prev_base_and_marks_before(text, index)
        if prev_base == "و" and _is_word_boundary_after(text, index):
            return index + 1
        out.append("aa")
        return index + 1

    return None


def _consume_shadda(
    text: str,
    index: int,
    out: List[str],
    state: _TReadState,
) -> Optional[int]:
    """Repeat the preceding readable consonant group for shaddah."""
    if text[index] != SHADDA:
        return None
    if state.suppress_shadda_at == index:
        state.suppress_shadda_at = None
        return index + 1

    joined = "".join(out)
    insert_at_end = True
    trailing_vowel = ""
    if out and out[-1] in {"a", "i", "u"}:
        trailing_vowel = out.pop()
        joined = "".join(out)
        insert_at_end = False

    for group in TREAD_SHADDA_GROUPS:
        if joined.endswith(group):
            out.append(group)
            break
    if not insert_at_end:
        out.append(trailing_vowel)
    return index + 1


def _append_tread_fallback(text: str, index: int, out: List[str]) -> int:
    ch = text[index]
    if ch in AR_TO_TREAD_LETTER:
        out.append(AR_TO_TREAD_LETTER[ch])
    elif ch in AR_TO_TREAD_MARK:
        out.append(AR_TO_TREAD_MARK[ch])
    else:
        out.append(ch)
    return index + 1


TREAD_RULE_HANDLERS = (
    _consume_meem_sakinah_idgham,
    _consume_nun_sakinah_iqlab,
    _consume_nun_sakinah_idgham,
    _consume_nun_sakinah_ikhfa,
    _consume_ta_marbuta,
    _consume_dagger_alif,
    _consume_tanween_iqlab,
    _consume_tanween_idgham,
    _consume_tanween_ikhfa,
    _consume_waqf,
    _consume_allah_name,
    _consume_definite_article,
    _consume_tread_vowel_sequence,
    _consume_mater_lectionis,
    _consume_shadda,
)


def _prepare_tread_source(arabic: str) -> str:
    """Preserve small-high-meem iqlab semantics only for T_read."""
    source = arabic.replace("ن" + _TREAD_IQLAB_MEEM, "ن" + SUKUN2)
    return _TREAD_IQLAB_VOWEL_MEEM_RE.sub(
        lambda match: match.group(1) + "م" + SUKUN2,
        source,
    )


def to_t_read(arabic: str) -> str:
    """Convert Arabic text to T_read (Indonesian-readable form).
    
    Args:
        arabic: Arabic text with optional diacritics.
        
    Returns:
        Readable transliteration without Latin diacritics, optimized for Indonesian
        pronunciation and readability. Applies sun-letter assimilation, waqf rules,
        and connected-speech idgham normalization.
        
    Example:
        >>> to_t_read("بِسْمِ اللَّهِ")
        'bismillah'
    """
    # T_read is not required to preserve Uthmani layout signs. Removing tatweel
    # before rule application prevents fatha + tatweel + dagger alif from being
    # expanded as a short a plus a long aa.
    tread_source = _prepare_tread_source(arabic)
    text = normalize_arabic(
        tread_source,
        collapse_kemenag_alef_fatha=False,
    ).replace("\u0640", "")
    out: List[str] = []
    state = _TReadState()
    i = 0

    while i < len(text):
        pending_advance = _advance_tread_pending(text, i, out, state)
        if pending_advance is not None:
            i = pending_advance
            continue

        for handler in TREAD_RULE_HANDLERS:
            next_i = handler(text, i, out, state)
            if next_i is not None:
                i = next_i
                break
        else:
            i = _append_tread_fallback(text, i, out)

    rendered = "".join(out)
    rendered = rendered.replace("Al-", "al-")
    rendered = _apply_tread_article_rules(rendered)
    rendered = _sanitize_tread_output(rendered)
    return rendered


def transliterate(arabic: str) -> TransliterationResult:
    """Transliterate Arabic text into both T_rev and T_read forms.
    
    This is the primary entry point for dual-form transliteration.
    
    Args:
        arabic: Arabic text with optional diacritics.
        
    Returns:
        TransliterationResult containing the original text and both transliteration forms.
        
    Example:
        >>> result = transliterate("بِسْمِ اللَّهِ")
        >>> result.t_rev
        'bis.mi Alllahi'
        >>> result.t_read
        'bismillah'
    """
    return TransliterationResult(
        source=arabic,
        t_rev=to_t_rev(arabic),
        t_read=to_t_read(arabic),
    )


def _match_token(text: str, index: int, tokens: List[str]) -> Optional[str]:
    for token in tokens:
        if text.startswith(token, index):
            return token
    return None


def _match_consonant(text: str, index: int) -> Optional[str]:
    for token in CONSONANT_TOKENS:
        if text.startswith(token, index):
            return token
    return None


def _can_decode_vowel_sequence(text: str, index: int, seq: str) -> bool:
    """Return True if a compact vowel/semivowel sequence is unambiguous.

    T_rev is intentionally typed without artificial separators. This helper
    prevents greedy parsing from turning sequences such as ``wayu`` into
    ``وَيُْ`` or ``iyya`` into ``إِيَ``. The rule is conservative: a sequence
    that contains y/w as its second character is not consumed as a long vowel
    when that y/w is immediately followed by a short vowel marker or by the
    same semivowel, because those contexts indicate an onset consonant or
    shaddah. True marked aw/ay diphthongs are encoded as aw./ay. so unmarked
    a+w or a+y sequences can remain separator-free and reversible.
    """
    if seq not in {"iy", "uw", "aY", "iY"}:
        return True
    after = index + len(seq)
    if after >= len(text):
        return True
    next_char = text[after]
    if next_char in TREV_VOWEL_TO_AR:
        return False
    semivowel = seq[1]
    if next_char == semivowel:
        return False
    return True


def _normalize_t_rev_allah_aliases(t_rev: str) -> str:
    """Normalize whole-word readable Allah aliases to canonical T_rev."""
    return TREV_ALLAH_ALIAS_RE.sub(r"Alllah\1", t_rev)


def from_t_rev(t_rev: str) -> str:
    """Decode compact T_rev back into Arabic (round-trip conversion).

    Users type without separators. The decoder uses maximal-match tokenization
    with contextual parsing for unambiguous semivowel sequences. When
    ``ALLOW_CONVENTIONAL_T_REV_USER_INPUT`` is enabled, whole-word readable
    Allah aliases such as ``Allah`` and ``Allahi`` are first normalized to the
    canonical three-``l`` T_rev form.
    
    Args:
        t_rev: Compact T_rev transliteration string.
        
    Returns:
        Arabic text with full diacritics as represented in the T_rev form.
        
    Example:
        >>> from_t_rev("bis.mi")
        'بِسْمِ'
    """
    if ALLOW_CONVENTIONAL_T_REV_USER_INPUT:
        t_rev = _normalize_t_rev_allah_aliases(t_rev)
    out: List[str] = []
    i = 0
    while i < len(t_rev):
        if t_rev[i] == TREV_SEPARATOR:
            i += 1
            continue

        # Definite article convenience form, e.g. al-qamar -> اَلْقَمَر.
        if t_rev.startswith("al-", i):
            out.extend(["ا", FATHA, "ل", SUKUN])
            i += 3
            continue

        # Long vowel and diphthong typed forms.
        # The compact T_rev grammar is separator-free, so semivowel sequences
        # must be parsed contextually. For example, wayu must decode as
        # wa + yu, not as way + u; iyya must decode as i + yya, not as
        # long iy + ya.
        for seq, arabic_seq in TREV_LONG_SEQUENCES:
            if t_rev.startswith(seq, i) and _can_decode_vowel_sequence(
                t_rev,
                i,
                seq,
            ):
                out.append(arabic_seq)
                i += len(seq)
                break
        else:
            # Special tokens and marks.
            special = _match_token(t_rev, i, SPECIAL_TOKENS)
            if special:
                out.append(TREV_SPECIAL_TO_AR[special])
                i += len(special)
                continue
            # Short vowels.
            ch = t_rev[i]
            if ch in TREV_VOWEL_TO_AR:
                out.append(TREV_VOWEL_TO_AR[ch])
                i += 1
                continue
            # Consonants with possible shaddah by repeated token.
            consonant = _match_consonant(t_rev, i)
            if consonant:
                # Repeated consonant token means shaddah, but three repeats
                # represent one written consonant followed by a shaddah-bearing
                # consonant, as in Allah: A + l + ll + a + h + i.
                token_len = len(consonant)
                count = 1
                while t_rev.startswith(consonant, i + count * token_len):
                    count += 1
                if count >= 3:
                    out.append(TREV_CONSONANT_TO_AR[consonant])
                    i += token_len
                elif count == 2:
                    out.append(TREV_CONSONANT_TO_AR[consonant] + SHADDA)
                    i += token_len * 2
                else:
                    out.append(TREV_CONSONANT_TO_AR[consonant])
                    i += token_len
                continue
            # Preserve spaces, punctuation, and unknown characters.
            out.append(t_rev[i])
            i += 1
            continue
        # The for-loop matched a long sequence; continue outer loop.
        continue
    return "".join(out)


def _configure_stdio() -> None:
    """Prefer UTF-8 console I/O on Windows."""
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if not hasattr(stream, "reconfigure"):
            continue
        try:
            stream.reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass


def _arabic_console_clusters(text: str) -> List[str]:
    """Return display clusters so Arabic marks stay with their base letter."""
    clusters: List[str] = []
    for ch in text:
        if (unicodedata.combining(ch) or ch in HARAKAT) and clusters:
            clusters[-1] += ch
        else:
            clusters.append(ch)
    return clusters


def _format_arabic_for_console(text: str) -> str:
    """Preorder Arabic for LTR Windows consoles that do not apply bidi layout."""
    if not ARABIC_SCRIPT_RE.search(text) or not VISUAL_RTL_CONSOLE_FALLBACK:
        return text
    return "".join(reversed(_arabic_console_clusters(text)))


def _print_menu() -> None:
    print("Arabic Transliteration")
    print("1. Decode Latin transliteration to Arabic and T_read")
    print("2. Encode Arabic into Latin")
    if SHOW_TESTS_IN_UI:
        print("3. Execute tests")


def _decode_t_rev_interactive() -> None:
    t_rev = input("Enter T_rev: ").strip()
    arabic = from_t_rev(t_rev)
    print("Arabic:", _format_arabic_for_console(arabic))
    print("T_read:", to_t_read(arabic))


def _encode_arabic_interactive() -> None:
    arabic = input("Enter Arabic text: ").strip()
    result = transliterate(arabic)
    print("T_rev :", result.t_rev)
    print("T_read:", result.t_read)
    decoded_t_rev = from_t_rev(result.t_rev)
    if decoded_t_rev == normalize_arabic(arabic):
        print("T_REV ROUND-TRIP: PASS")
    else:
        print("T_REV ROUND-TRIP: FAIL")
        print("Decoded T_rev:", _format_arabic_for_console(decoded_t_rev))


def _run_test_suite() -> bool:
    suite = unittest.defaultTestLoader.discover("tests")
    result = unittest.TextTestRunner(verbosity=2, stream=sys.stdout).run(suite)
    quran_result = _run_kemenag_quran_roundtrip_check()
    return result.wasSuccessful() and quran_result


def _run_kemenag_quran_roundtrip_check() -> bool:
    print()
    print("Kemenag Quran T_rev round-trip check")
    try:
        import quran_kemenag_trev_audit
    except Exception as exc:
        print(f"Unable to import Kemenag Quran audit: {exc}", file=sys.stderr)
        return False

    try:
        return quran_kemenag_trev_audit.run_audit()
    except Exception as exc:
        print(f"Kemenag Quran T_rev round-trip check failed: {exc}", file=sys.stderr)
        return False


def main() -> int:
    _configure_stdio()
    _print_menu()
    available_options = "1-3" if SHOW_TESTS_IN_UI else "1-2"
    choice = input(f"Select option [{available_options}]: ").strip()

    if choice == "1":
        _decode_t_rev_interactive()
        return 0
    if choice == "2":
        _encode_arabic_interactive()
        return 0
    if choice == "3" and SHOW_TESTS_IN_UI:
        return 0 if _run_test_suite() else 1

    if SHOW_TESTS_IN_UI:
        print("Invalid option. Choose 1, 2, or 3.", file=sys.stderr)
    else:
        print("Invalid option. Choose 1 or 2.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
