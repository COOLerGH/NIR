"""
Наивный алгоритм поиска.

При каждом запросе перебирает все файлы, читает содержимое,
подсчитывает вхождения слов запроса. Простой, но медленный.
Сложность: O(n * m), где n — количество файлов, m — средний размер файла.
"""

from typing import List

from algorithms.base import SearchAlgorithm
from api.interface import FileSystemAPI, SearchResult
from core.parser import ParsedQuery
from core.ranker import tokenize, remove_stop_words


class NaiveSearch(SearchAlgorithm):
    """Поиск линейным перебором всех файлов."""

    def __init__(self, api: FileSystemAPI):
        super().__init__(api)

    def _execute_search(
        self, query: ParsedQuery, root_path: str
    ) -> List[SearchResult]:
        """
        Обойти все файлы, прочитать содержимое, посчитать score.
        """
        files = self.api.walk(root_path)
        query_terms = remove_stop_words(query.terms)

        if not query_terms:
            return []

        results = []

        for file_info in files:
            try:
                content = self.api.get_content(file_info.path)
            except (FileNotFoundError, Exception):
                continue

            tokens = tokenize(content)

            if not tokens:
                continue

            score = self._compute_score(query_terms, tokens, query.operator)

            if score > 0:
                exclude_tokens = query.exclude_terms
                if exclude_tokens and self._has_excluded(exclude_tokens, tokens):
                    continue

                snippet = self._make_snippet(content, query_terms)

                results.append(SearchResult(
                    path=file_info.path,
                    name=file_info.name,
                    score=score,
                    size=file_info.size,
                    modified_date=file_info.modified_date,
                    snippet=snippet,
                ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results

    @staticmethod
    def _compute_score(
        query_terms: List[str], tokens: List[str], operator: str
    ) -> float:
        """
        Вычислить простой score на основе частоты вхождений.

        AND: все термы должны присутствовать, score = сумма частот
        OR: хотя бы один терм, score = сумма частот найденных
        NOT: обрабатывается отдельно (исключение в _execute_search)
        """
        counts = {}
        for term in query_terms:
            counts[term] = tokens.count(term)

        if operator == "AND":
            if any(c == 0 for c in counts.values()):
                return 0.0

        total = sum(counts.values())
        if total == 0:
            return 0.0

        return total / len(tokens)

    @staticmethod
    def _has_excluded(exclude_terms: List[str], tokens: List[str]) -> bool:
        """Проверить, содержит ли документ исключённые слова."""
        for term in exclude_terms:
            if term.lower() in tokens:
                return True
        return False

    @staticmethod
    def _make_snippet(content: str, query_terms: List[str], length: int = 100) -> str:
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
