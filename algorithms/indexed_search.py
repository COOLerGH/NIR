"""
Индексный алгоритм поиска.

Использует предварительно построенный инвертированный индекс.
Ранжирует результаты по TF-IDF. Быстрый при повторных запросах.
Сложность поиска: O(k), где k — количество документов-кандидатов.
"""

from typing import List, Set

from algorithms.base import SearchAlgorithm
from api.interface import FileSystemAPI, SearchResult
from core.parser import ParsedQuery
from core.ranker import remove_stop_words, rank_documents
from core.indexer import FileIndexer


class IndexedSearch(SearchAlgorithm):
    """Поиск по инвертированному индексу с TF-IDF ранжированием."""

    def __init__(self, api: FileSystemAPI, indexer: FileIndexer):
        super().__init__(api)
        self.indexer = indexer

    def _execute_search(
        self, query: ParsedQuery, root_path: str
    ) -> List[SearchResult]:
        """
        Найти кандидатов через индекс, ранжировать по TF-IDF.
        """
        if not self.indexer.is_built:
            return []

        query_terms = remove_stop_words(query.terms)

        if not query_terms:
            return []

        candidates = self._get_candidates(query_terms, query.operator)

        if query.exclude_terms:
            candidates = self._apply_exclusions(candidates, query.exclude_terms)

        if not candidates:
            return []

        ranked = rank_documents(
            query_terms=query_terms,
            index=self.indexer.index,
            doc_lengths=self.indexer.doc_lengths,
            total_docs=self.indexer.total_docs,
        )

        results = []
        for filepath, score in ranked:
            if filepath not in candidates:
                continue

            name = filepath.rsplit("/", 1)[-1] if "/" in filepath else filepath
            doc_len = self.indexer.doc_lengths.get(filepath, 0)

            snippet = ""
            try:
                content = self.api.get_content(filepath)
                snippet = self._make_snippet(content, query_terms)
            except Exception:
                pass

            results.append(SearchResult(
                path=filepath,
                name=name,
                score=score,
                size=doc_len,
                modified_date="",
                snippet=snippet,
            ))

        return results

    def _get_candidates(
        self, query_terms: List[str], operator: str
    ) -> Set[str]:
        """
        Собрать множество файлов-кандидатов из индекса.

        AND: пересечение множеств (файл содержит все термы)
        OR: объединение множеств (файл содержит хотя бы один терм)
        NOT: обрабатывается отдельно через _apply_exclusions
        """
        sets = []
        for term in query_terms:
            if term in self.indexer.index:
                sets.append(set(self.indexer.index[term].keys()))
            else:
                sets.append(set())

        if not sets:
            return set()

        if operator == "OR":
            result = set()
            for s in sets:
                result = result.union(s)
            return result

        # AND (по умолчанию) и NOT (исключения применяются позже)
        result = sets[0]
        for s in sets[1:]:
            result = result.intersection(s)
        return result

    def _apply_exclusions(
        self, candidates: Set[str], exclude_terms: List[str]
    ) -> Set[str]:
        """Исключить файлы, содержащие запрещённые термы."""
        for term in exclude_terms:
            term_lower = term.lower()
            if term_lower in self.indexer.index:
                excluded_files = set(self.indexer.index[term_lower].keys())
                candidates = candidates - excluded_files
        return candidates

    @staticmethod
    def _make_snippet(content: str, query_terms: list, length: int = 100) -> str:
        """Создать сниппет — фрагмент текста вокруг первого вхождения терма."""
        content_lower = content.lower()
        best_pos = -1

        for term in query_terms:
            pos = content_lower.find(term)
            if pos != -1 and (best_pos == -1 or pos < best_pos):
                best_pos = pos

        if best_pos == -1:
            return content[:length] + "..." if len(content) > length else content

        start = max(0, best_pos - length // 4)
        end = min(len(content), start + length)
        snippet = content[start:end]

        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."

        return snippet
