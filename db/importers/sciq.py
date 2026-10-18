"""Import SciQ, 13,679 crowd-written science exam questions.

Source: Welbl, J., Liu, N. F. & Gardner, M. Crowdsourcing Multiple Choice
Science Questions. W-NUT 2017. Allen Institute for AI. Licence: CC BY-NC 3.0.

SciQ has no topic labels, so we find topics ourselves: every question and its
supporting paragraph become a TF-IDF vector, LSA (truncated SVD) compresses
those to 100 dimensions so related words count together, and k-means groups
them into clusters. Each cluster becomes one module, named after its strongest
words.
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
READINGS_PER_TOPIC = 8
ATTRIBUTION = "Questions: SciQ dataset (Welbl, Liu & Gardner, 2017, Allen Institute for AI), CC BY-NC 3.0."


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

    rng = random.Random(7)
    with transaction(conn):
        cur = conn.execute(
            """INSERT INTO courses (code, title, subject, description, source, attribution)
               VALUES ('SCI-101', 'Science foundations', 'Science', ?, 'sciq', ?)""",
            ("Physics, chemistry, biology and earth science questions written for school-level exams. "
             f"Grouped into {N_TOPICS} topics by k-means clustering of the question text.",
             ATTRIBUTION),
        )
        course_id = cur.lastrowid

        for pos, topic in enumerate(topics, start=1):
            title = ", ".join(topic["words"]).capitalize()
            cur = conn.execute(
                "INSERT INTO modules (course_id, position, title, kind) VALUES (?, ?, ?, 'topic')",
                (course_id, pos, title),
            )
            module_id = cur.lastrowid

            # Readings: the supporting paragraphs closest to the topic's centre.
            members = topic["members"]
            closeness = reduced[members] @ km.cluster_centers_[topic["k"]]
            order = members[np.argsort(-closeness)]
            lesson_pos = 0
            for idx in order:
                support = items[idx]["support"].strip()
                if len(support) < 250:
                    continue
                lesson_pos += 1
                conn.execute(
                    "INSERT INTO lessons (module_id, position, title, body) VALUES (?, ?, ?, ?)",
                    (module_id, lesson_pos, f"Reading: {items[idx]['correct_answer']}", support),
                )
                if lesson_pos == READINGS_PER_TOPIC:
                    break

            for idx in members:
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
    log("SciQ: done")
