import re
from typing import Dict, List

import numpy as np
import nltk
import pymorphy2
from nltk.corpus import stopwords
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


try:
    nltk.data.find("corpora/stopwords")
except LookupError:
    nltk.download("stopwords")


STOP_WORDS = set(stopwords.words("russian"))
MORPH = pymorphy2.MorphAnalyzer()

# Если сходство ниже порога, считаем проблему новой
NOVELTY_THRESHOLD = 0.20

# Минимальный порог для отображения рекомендации в интерфейсе
MIN_RECOMMENDATION_PERCENT = 5


def normalize_text(text: str) -> str:
    """
    Выполняет базовую предобработку текста:
    приведение к нижнему регистру, очистка и лемматизация.
    """
    if not text:
        return ""

    text = text.lower()

    # Убираем символы, кроме букв, цифр и пробелов
    text = re.sub(r"[^а-яa-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    lemmas: List[str] = []

    for word in text.split():
        if len(word) < 3:
            continue
        if word in STOP_WORDS:
            continue

        lemma = MORPH.parse(word)[0].normal_form
        lemmas.append(lemma)

    return " ".join(lemmas)


def get_recommendations(
    ticket_text: str,
    kb_items: List[Dict],
    top_k: int = 3,
) -> Dict:
    """
    Формирует рекомендации на основе базы знаний с использованием TF-IDF
    и косинусного сходства.
    """
    if not kb_items:
        return {"is_novel": True, "max_similarity": 0, "recommendations": []}

    ticket_norm = normalize_text(ticket_text)
    if not ticket_norm:
        return {"is_novel": True, "max_similarity": 0, "recommendations": []}

    kb_norm: List[str] = []
    kb_meta: List[Dict] = []

    # Для поиска используем описание проблемы и решение
    for item in kb_items:
        text = f"{item.get('problem', '')} {item.get('solution', '')}"
        norm = normalize_text(text)

        if norm:
            kb_norm.append(norm)
            kb_meta.append(item)

    if not kb_norm:
        return {"is_novel": True, "max_similarity": 0, "recommendations": []}

    texts = [ticket_norm] + kb_norm

    # Векторизация текста методом TF-IDF
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=5000,
    )

    matrix = vectorizer.fit_transform(texts)

    # Вычисление косинусного сходства
    scores = cosine_similarity(matrix[0:1], matrix[1:]).flatten()

    if scores.size == 0:
        return {"is_novel": True, "max_similarity": 0, "recommendations": []}

    max_score = float(scores.max())
    best_indices = np.argsort(scores)[::-1][:top_k]

    recommendations: List[Dict] = []
    rank = 1

    for idx in best_indices:
        score = float(scores[idx])
        percent = int(score * 100)

        if percent < MIN_RECOMMENDATION_PERCENT:
            continue

        recommendations.append(
            {
                "kb_id": kb_meta[idx]["id"],
                "rank": rank,
                "similarity": percent,
                "problem": kb_meta[idx].get("problem", ""),
                "solution": kb_meta[idx].get("solution", ""),
            }
        )
        rank += 1

    return {
        "is_novel": max_score < NOVELTY_THRESHOLD,
        "max_similarity": int(max_score * 100),
        "recommendations": recommendations,
    }
