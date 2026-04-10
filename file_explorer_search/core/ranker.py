"""
TF-IDF ранжирование и токенизация.

Предоставляет функции для разбиения текста на токены,
вычисления TF, IDF, TF-IDF и ранжирования документов по запросу.
"""

import re
import math
from typing import List, Dict, Tuple


STOP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "not", "in", "on", "at", "to",
    "for", "of", "with", "by", "from", "is", "it", "as", "be",
    "was", "are", "were", "been", "has", "have", "had", "do", "does",
    "did", "but", "if", "than", "that", "this", "these", "those",
})


def tokenize(text: str) -> List[str]:
    """
    Разбить текст на токены.
    Приводит к нижнему регистру, разделяет по не-буквоцифровым символам,
    убирает токены короче 2 символов.
    """
    if not text:
        return []
    tokens = re.split(r"[^a-zA-Z0-9]+", text.lower())
    return [t for t in tokens if len(t) >= 2]


def remove_stop_words(tokens: List[str]) -> List[str]:
    """Убрать стоп-слова из списка токенов."""
    return [t for t in tokens if t not in STOP_WORDS]


def compute_tf(term: str, tokens: List[str]) -> float:
    """
    Term Frequency — частота слова в документе.
    TF = количество_вхождений / общее_количество_токенов
    """
    if not tokens:
        return 0.0
    count = tokens.count(term)
    return count / len(tokens)


def compute_idf(total_docs: int, docs_with_term: int) -> float:
    """
    Inverse Document Frequency — обратная частота документа.
    IDF = log(всего_документов / количество_документов_с_термином)
    Если docs_with_term == 0, возвращает 0.
    """
    if docs_with_term <= 0 or total_docs <= 0:
        return 0.0
    return math.log(total_docs / docs_with_term)


def compute_tfidf(tf: float, idf: float) -> float:
    """TF-IDF = TF * IDF."""
    return tf * idf


def rank_documents(
    query_terms: List[str],
    index: Dict[str, Dict[str, int]],
    doc_lengths: Dict[str, int],
    total_docs: int,
) -> List[Tuple[str, float]]:
    """
    Ранжировать документы по запросу на основе TF-IDF.

    Args:
        query_terms: список термов запроса (уже токенизированы, без стоп-слов)
        index: инвертированный индекс {term: {filepath: count}}
        doc_lengths: длины документов в токенах {filepath: length}
        total_docs: общее количество документов

    Returns:
        список (filepath, score) отсортированный по убыванию score
    """
    if not query_terms or total_docs == 0:
        return []

    scores: Dict[str, float] = {}

    for term in query_terms:
        if term not in index:
            continue

        docs_with_term = len(index[term])
        idf = compute_idf(total_docs, docs_with_term)

        for filepath, count in index[term].items():
            doc_len = doc_lengths.get(filepath, 1)
            tf = count / doc_len if doc_len > 0 else 0.0
            tfidf = compute_tfidf(tf, idf)

            if filepath in scores:
                scores[filepath] += tfidf
            else:
                scores[filepath] = tfidf

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return ranked
