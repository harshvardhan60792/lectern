"""Import SciQ, 13,679 crowd-written science exam questions.

Source: Welbl, J., Liu, N. F. & Gardner, M. Crowdsourcing Multiple Choice
Science Questions. W-NUT 2017. Allen Institute for AI. Licence: CC BY-NC 3.0.

SciQ has no topic labels, so we find topics ourselves: every question and its
supporting paragraph become a TF-IDF vector, LSA (truncated SVD) compresses
those to 100 dimensions so related words count together, and k-means groups
them into clusters. Each cluster becomes one module. Related modules are then
grouped into short courses of two or three modules each.
"""
import json
import random
import sqlite3
from pathlib import Path

import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import Normalizer

from db import transaction

N_TOPICS = 15
# Words that appear across every science topic and only blur the clusters.
FILLER = {
    "called", "type", "figure", "example", "known", "used", "use", "following", "process", "term",
    "does", "different", "form", "make", "certain", "common", "important", "refers", "describes",
    "usually", "like", "just", "include", "includes", "number", "small", "large", "main", "shown",
    "produce", "produced", "new", "way", "ways", "time", "results", "result",
}
READINGS_PER_TOPIC = 4
QUESTIONS_PER_TOPIC = 40
DESCRIBING = ("ed", "ous", "ive", "ent", "al", "ic", "eous")

# Short courses, each built from related topics. A topic is found by its strongest word.
COURSES = [
    ("SCI-101", "Chemistry basics", "Chemistry", "What matter is made of, and how gases and substances react.",
     [("atoms", "Atoms and elements"), ("gas", "Gases and reactions")]),
    ("SCI-102", "Physics basics", "Physics", "Forces, waves, light, and the forms energy takes.",
     [("light", "Forces, waves and light"), ("energy", "Energy and heat")]),
    ("SCI-103", "Earth science basics", "Earth science", "Water, rocks and oceans, and how scientists test ideas.",
     [("water", "Water, rocks and oceans"), ("science", "How science works")]),
    ("SCI-104", "Biology I: cells and genes", "Biology", "The cell, how traits pass on through DNA, and what makes us ill.",
     [("cell", "The cell"), ("genes", "Genes and DNA"), ("disease", "Germs and disease")]),
    ("SCI-105", "Biology II: the living body", "Biology", "How the human body works, and how plants and animals live.",
     [("blood", "Heart and blood"), ("plants", "How plants live"), ("animals", "Animal groups")]),
]


def _load(folder: Path) -> list[dict]:
    items = []
    for split in ("train", "valid", "test"):
        data = json.loads((folder / f"{split}.json").read_text(encoding="utf-8"))
        for i, q in enumerate(data):
            q["external_id"] = f"{split}-{i}"
            items.append(q)
    return items


def _distinct(words, n: int = 3) -> list[str]:
    """Top words without near-duplicates such as "cell" and "cells"."""
    picked: list[str] = []
    for w in words:
        if all(w[:4] != p[:4] for p in picked):
            picked.append(w)
        if len(picked) == n:
            break
    return picked


def run(conn: sqlite3.Connection, raw_dir: Path, log=print) -> None:
    folder = next((raw_dir / "sciq").glob("SciQ*"))
    items = _load(folder)
    log(f"SciQ: {len(items):,} questions, finding {N_TOPICS} topics with k-means")

    texts = [f"{q['question']} {q['correct_answer']} {q['support']}" for q in items]
    vectorizer = TfidfVectorizer(stop_words=list(ENGLISH_STOP_WORDS | FILLER), min_df=5, max_df=0.2,
                                 sublinear_tf=True)
    matrix = vectorizer.fit_transform(texts)
    lsa = make_pipeline(TruncatedSVD(100, random_state=0), Normalizer(copy=False))
    reduced = lsa.fit_transform(matrix)
    km = KMeans(n_clusters=N_TOPICS, n_init=10, random_state=42)
    labels = km.fit_predict(reduced)
    centres_in_words = lsa[0].inverse_transform(km.cluster_centers_)
    terms = np.array(vectorizer.get_feature_names_out())

    topics = []
    for k in range(N_TOPICS):
        members = np.where(labels == k)[0]
        topics.append({"k": k, "words": _distinct(terms[np.argsort(centres_in_words[k])[::-1][:12]]),
                       "size": len(members), "members": members})
    topics.sort(key=lambda t: -t["size"])

    by_word = {t["words"][0].lower(): t for t in topics}
    rng = random.Random(7)
    with transaction(conn):
        for code, title, subject, description, parts in COURSES:
            cur = conn.execute(
                "INSERT INTO courses (code, title, subject, description, source) VALUES (?, ?, ?, ?, 'sciq')",
                (code, title, subject, description),
            )
            course_id = cur.lastrowid
            for pos, (word, module_title) in enumerate(parts, start=1):
                _add_module(conn, course_id, pos, module_title, by_word[word], items, reduced, km, rng)
    log(f"SciQ: {len(COURSES)} short courses")


def _good_reading(item: dict) -> bool:
    """A passage that reads well on its own: plain prose, a clear one- or two-word subject."""
    text, subject = item["support"].strip(), item["correct_answer"].strip()
    first_sentence = text.split(". ")[0].lower()
    words = subject.lower().split()
    # Answers like "is conserved", "time" or "polarized" don't work as a lesson title.
    if words[0] in ("is", "are", "time") or (len(words) == 1 and words[0].endswith(DESCRIBING)):
        return False
    return (300 <= len(text) <= 1500 and text[:1].isupper() and "?" not in text and "chapter" not in text.lower()
            and subject.replace(" ", "").isalpha() and len(subject) >= 4 and len(subject.split()) <= 3
            and subject.lower() in first_sentence)


def _add_module(conn, course_id, pos, title, topic, items, reduced, km, rng) -> None:
    module_id = conn.execute(
        "INSERT INTO modules (course_id, position, title, kind) VALUES (?, ?, ?, 'topic')", (course_id, pos, title),
    ).lastrowid
    # The questions and readings closest to the topic's centre are the clearest examples of it.
    members = topic["members"]
    order = members[np.argsort(-(reduced[members] @ km.cluster_centers_[topic["k"]]))]

    readings, seen = [], set()
    for i in order:
        keys = {items[i]["support"].strip()[:80], items[i]["correct_answer"].strip().lower()[:6]}
        if _good_reading(items[i]) and not keys & seen:  # several questions share one passage
            readings.append(i)
            seen |= keys
        if len(readings) == READINGS_PER_TOPIC:
            break
    for lesson_pos, idx in enumerate(readings, start=1):
        answer = items[idx]["correct_answer"].strip()
        conn.execute(
            "INSERT INTO lessons (module_id, position, title, body) VALUES (?, ?, ?, ?)",
            (module_id, lesson_pos, answer[:1].upper() + answer[1:], items[idx]["support"].strip()),
        )

    for idx in order[:QUESTIONS_PER_TOPIC]:
        q = items[idx]
        cur = conn.execute(
            """INSERT INTO questions (module_id, source, external_id, prompt, explanation, support)
               VALUES (?, 'sciq', ?, ?, NULL, ?)""",
            (module_id, q["external_id"], q["question"].strip(), q["support"].strip() or None),
        )
        options = [(q["correct_answer"], 1), (q["distractor1"], 0), (q["distractor2"], 0), (q["distractor3"], 0)]
        rng.shuffle(options)
        conn.executemany(
            "INSERT INTO question_options (question_id, position, text, is_correct) VALUES (?, ?, ?, ?)",
            [(cur.lastrowid, i, text.strip(), ok) for i, (text, ok) in enumerate(options, start=1)],
        )
