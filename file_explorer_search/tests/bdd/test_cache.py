"""BDD-тесты для кэширования результатов (Rule + Background)."""

import pytest
from pytest_bdd import scenario, given, when, then, parsers

from core.cache import SearchCache


# --- Сценарии ---

@scenario("../../features/cache.feature", "Сохранение и получение результата")
def test_put_get():
    pass


@scenario("../../features/cache.feature", "Промах кэша при запросе отсутствующего ключа")
def test_cache_miss():
    pass


@scenario("../../features/cache.feature", "Вытеснение при переполнении")
def test_eviction():
    pass


@scenario("../../features/cache.feature", "Доступ обновляет позицию элемента")
def test_access_updates_position():
    pass


@scenario("../../features/cache.feature", "Подсчёт попаданий и промахов")
def test_stats():
    pass


# --- Фикстура контекста ---

@pytest.fixture
def ctx():
    return {"cache": None, "result": None}


# --- Given (Background) ---

@given(parsers.parse("кэш с максимальным размером {size:d}"), target_fixture="ctx")
def create_cache(ctx, size):
    ctx = {"cache": SearchCache(max_size=size), "result": None}
    return ctx


# --- When ---

@when(parsers.parse('в кэш добавлен запрос "{key}" с {count:d} результатами'))
def cache_put(ctx, key, count):
    results = [{"file": f"file_{i}.txt"} for i in range(count)]
    ctx["cache"].put(key, results)


@when(parsers.parse('запрошен кэш по ключу "{key}"'))
def cache_get(ctx, key):
    ctx["result"] = ctx["cache"].get(key)


# --- Then ---

@then(parsers.parse("получены {count:d} результата из кэша"))
def check_cached_count(ctx, count):
    assert ctx["result"] is not None
    assert len(ctx["result"]) == count


@then("результат из кэша равен None")
def check_none(ctx):
    assert ctx["result"] is None


@then(parsers.parse('запрос "{key}" отсутствует в кэше'))
def check_absent(ctx, key):
    result = ctx["cache"].get(key)
    assert result is None


@then(parsers.parse('запрос "{key}" присутствует в кэше'))
def check_present(ctx, key):
    # Сбрасываем result чтобы не влиять на статистику проверок
    old_hits = ctx["cache"]._hits
    old_misses = ctx["cache"]._misses
    result = ctx["cache"].get(key)
    assert result is not None
    # Восстанавливаем счётчики — проверка не должна менять статистику
    ctx["cache"]._hits = old_hits
    ctx["cache"]._misses = old_misses


@then(parsers.parse("счётчик промахов равен {count:d}"))
def check_misses(ctx, count):
    assert ctx["cache"].stats()["misses"] == count


@then(parsers.parse("количество попаданий равно {count:d}"))
def check_hits(ctx, count):
    assert ctx["cache"].stats()["hits"] == count


@then(parsers.parse("количество промахов равно {count:d}"))
def check_miss_count(ctx, count):
    assert ctx["cache"].stats()["misses"] == count


@then(parsers.parse("hit rate равен {rate:f}"))
def check_hit_rate(ctx, rate):
    actual = ctx["cache"].stats()["hit_rate"]
    assert abs(actual - rate) < 0.01
