"""Question drafter: turns lesson text into multiple-choice question drafts.

Steps
1. Find the key terms of the text with TF-IDF, compared with the rest of the course.
2. Definition sentences ("A tuple is an ordered, immutable collection") become
   "Which term matches this description?" questions.
3. Other sentences that contain a key term become fill-in-the-blank questions.
4. Wrong options (distractors) are other key terms from the same course that
   appear in similar contexts. Term similarity comes from LSA: a term-by-sentence
   matrix of the whole course is compressed with truncated SVD, so terms used
   around the same words end up close together ("tuple" near "list").
5. Quality filters drop sentences that are too short, too long, mostly code,
   or where the blank would be guessable from the sentence itself.

Every draft goes to the instructor for review before students see it.
"""
import random
import re
from dataclasses import dataclass, field

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import CountVectorizer

from smart import text as tt

DEFINITION = re.compile(
    r"^(?:an?\s+|the\s+)?(?P<term>[a-z][\w\s\-]{2,40}?)\s+(?P<verb>is|are|refers to|means|describes)\s+(?P<rest>.{15,})$",
    re.IGNORECASE,
)
MIN_WORDS, MAX_WORDS = 7, 40


@dataclass
class Draft:
    kind: str                     # "definition" or "fill-in"
    prompt: str
    options: list[str]
    correct: int
    term: str
    sentence: str
    notes: list[str] = field(default_factory=list)


def _usable(sentence: str) -> bool:
    n = len(sentence.split())
    if not MIN_WORDS <= n <= MAX_WORDS or "?" in sentence:
        return False
    if any(mark in sentence for mark in (">>>", "#", "print(")):
        return False
    code_marks = sum(sentence.count(c) for c in "=()[]{}#_")
    if code_marks > 3 or sentence.count('"') > 2:
        return False
    return not sentence.lower().startswith(("ex:", "figure", "table", "note", "by the end"))


class TermSpace:
    """Term vectors from LSA over every sentence of the course."""

    def __init__(self, sentences: list[str]):
        self.vectorizer = CountVectorizer(stop_words="english", ngram_range=(1, 2), min_df=2, binary=True,
                                          token_pattern=r"(?u)\b[A-Za-z][A-Za-z_]+\b")
        matrix = self.vectorizer.fit_transform(sentences)
        k = max(2, min(100, min(matrix.shape) - 1))
        svd = TruncatedSVD(k, random_state=0).fit(matrix)
        vectors = svd.components_.T * svd.singular_values_
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        self.vectors = vectors / np.where(norms == 0, 1, norms)
        self.index = {t: i for i, t in enumerate(self.vectorizer.get_feature_names_out())}
        self.counts = np.asarray(matrix.sum(axis=0)).ravel()

    def known(self, term: str, min_count: int = 2) -> bool:
        i = self.index.get(term)
        return i is not None and self.counts[i] >= min_count

    def similar(self, term: str, candidates: list[str]) -> list[tuple[str, float]]:
        if term not in self.index:
            return []
        target = self.vectors[self.index[term]]
        scored = [(c, float(self.vectors[self.index[c]] @ target)) for c in candidates if c in self.index]
        return sorted(scored, key=lambda x: -x[1])


def _distractors(answer: str, pool: list[str], sentence: str, space: TermSpace, rng: random.Random,
                 n: int = 3) -> list[str]:
    low_sentence = sentence.lower()
    ok = [
        p for p in pool
        if p != answer and p not in low_sentence and p[:4] != answer[:4]
        and answer not in p and p not in answer and len(p.split()) == len(answer.split())
        and not set(p.split()) & set(answer.split())
    ]
    ranked = [t for t, sim in space.similar(answer, ok) if sim < 0.95]
    picked: list[str] = []
    for t in ranked[: n * 3]:
        if all(t[:4] != p[:4] for p in picked):
            picked.append(t)
    rng.shuffle(picked)
    return picked[:n]


def draft(text: str, corpus: list[str], how_many: int = 8, seed: int = 1) -> list[Draft]:
    """Draft up to `how_many` questions from `text`. `corpus` is the other lesson
    texts of the course: it makes TF-IDF fair and supplies distractors."""
    rng = random.Random(seed)
    course_sentences = [s for doc in corpus + [text] for s in tt.sentences(doc)]
    if len(course_sentences) < 10:
        return []
    space = TermSpace(course_sentences)
    terms = [t for t, _ in tt.key_terms(text, corpus, top=40) if space.known(t)]
    if len(terms) < 4:
        return []
    pool = list(dict.fromkeys(
        terms + [t for doc in corpus[:60] for t, _ in tt.key_terms(doc, corpus, top=10) if space.known(t, 3)]
    ))

    drafts: list[Draft] = []
    used_terms: set[str] = set()
    used_sentences: set[str] = set()

    def add(kind: str, prompt: str, answer: str, sentence: str) -> None:
        wrong = _distractors(answer, pool, sentence, space, rng)
        if len(wrong) < 3:
            return
        options = wrong + [answer]
        rng.shuffle(options)
        drafts.append(Draft(kind, prompt, options, options.index(answer), answer, sentence))
        used_terms.add(answer)
        used_sentences.add(sentence)

    all_sentences = [s for s in tt.sentences(text) if _usable(s)]

    # Definitions first: they make the clearest questions.
    for s in all_sentences:
        m = DEFINITION.match(s)
        if not m:
            continue
        term = m.group("term").strip().lower()
        if term not in terms or term in used_terms:
            continue
        description = m.group("rest").rstrip(".")
        add("definition", f"Which term matches this description?\n“{description[0].upper() + description[1:]}.”",
            term, s)
        if len(drafts) >= how_many:
            return drafts

    # Then fill-in-the-blank, strongest terms first.
    for term in terms:
        if term in used_terms:
            continue
        pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
        for s in all_sentences:
            if s in used_sentences or len(pattern.findall(s)) != 1:
                continue
            blanked = pattern.sub("_____", s)
            if blanked.startswith("_____") and len(blanked.split()) < 9:
                continue
            add("fill-in", f"Fill in the blank:\n{blanked}", term, s)
            break
        if len(drafts) >= how_many:
            break
    return drafts


def draft_for_module(conn, module_id: int, how_many: int = 8, seed: int = 1, source_text: str | None = None) -> list[Draft]:
    """Draft from a module's lessons (or from pasted text), using the rest of the
    course as the comparison corpus."""
    course_id = conn.execute("SELECT course_id FROM modules WHERE id = ?", (module_id,)).fetchone()[0]
    lessons = conn.execute(
        """SELECT l.body, l.module_id FROM lessons l JOIN modules m ON m.id = l.module_id
           WHERE m.course_id = ? ORDER BY m.position, l.position""",
        (course_id,),
    ).fetchall()
    own = "\n\n".join(r["body"] for r in lessons if r["module_id"] == module_id)
    corpus = [r["body"] for r in lessons if r["module_id"] != module_id]
    return draft(source_text or own, corpus, how_many, seed)
