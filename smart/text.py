"""Small text tools shared by the smart features."""
import difflib
import re

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer

SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'(])")
WORD = re.compile(r"[A-Za-z][A-Za-z0-9_'\-]*")


def sentences(text: str) -> list[str]:
    """Split text into sentences.

    Lines wrapped mid-sentence are joined back up. Short lines without end
    punctuation are headings, so they are kept apart instead of being glued to
    the next sentence.
    """
    blocks, current = [], []
    for line in text.splitlines():
        line = line.strip()
        is_heading = line and len(line.split()) <= 7 and not line.endswith((".", "?", "!", ":", ","))
        if not line or is_heading:
            if current:
                blocks.append(" ".join(current))
                current = []
            continue
        current.append(line)
    if current:
        blocks.append(" ".join(current))
    return [s.strip() for b in blocks for s in SENTENCE_END.split(b) if s.strip()]


PY_START = ("if ", "elif ", "else:", "for ", "while ", "def ", "class ", "try:", "except", "finally:", "with ",
            "return", "import ", "from ", "print(", "pass", "break", "continue", "#", ">>>")
ASSIGNMENT = re.compile(r"^[A-Za-z_][\w.\[\]'\"]*\s*([+\-*/%]|//)?=\s*\S")
CALL = re.compile(r"^[A-Za-z_][\w.]*\(.*\)$")


def looks_like_python(line: str) -> bool:
    """A short line that starts like a Python statement."""
    line = line.strip()
    if not line or len(line) > 90:
        return False
    return line.startswith(PY_START) or bool(ASSIGNMENT.match(line)) or bool(CALL.match(line))


def words(text: str) -> list[str]:
    return WORD.findall(text.lower())


def key_terms(text: str, corpus: list[str], top: int = 25) -> list[tuple[str, float]]:
    """Terms that matter in `text` compared with the rest of `corpus` (TF-IDF).

    A term scores high when it is frequent in this text but rare in the other
    documents, so "assignment operator" beats "the" or "program".
    """
    docs = [d for d in corpus if d.strip()] + [text]
    vectorizer = TfidfVectorizer(
        stop_words="english", ngram_range=(1, 3), min_df=1, max_df=0.6 if len(docs) > 4 else 1.0,
        sublinear_tf=True, token_pattern=r"(?u)\b[A-Za-z][A-Za-z_]+\b",
    )
    matrix = vectorizer.fit_transform(docs)
    row = matrix[len(docs) - 1].toarray().ravel()
    terms = vectorizer.get_feature_names_out()
    ranked = sorted(((terms[i], float(row[i])) for i in row.nonzero()[0]), key=lambda t: -t[1])

    picked: list[tuple[str, float]] = []
    for term, score in ranked:
        if len(term) < 4 or term in ENGLISH_STOP_WORDS:
            continue
        # Skip a phrase if a stronger picked term already contains it, or vice versa,
        # unless the longer phrase is the stronger one.
        if any(term in p or p in term for p, _ in picked):
            continue
        picked.append((term, score))
        if len(picked) == top:
            break
    return picked


def best_match(phrase: str, choices: list[str], cutoff: float = 0.75) -> str | None:
    """Closest choice to `phrase`, tolerant of typos ("pyhton" -> "python")."""
    phrase = phrase.lower().strip()
    lowered = {c.lower(): c for c in choices}
    if phrase in lowered:
        return lowered[phrase]
    hit = difflib.get_close_matches(phrase, list(lowered), n=1, cutoff=cutoff)
    return lowered[hit[0]] if hit else None
