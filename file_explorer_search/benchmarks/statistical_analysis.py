"""
Статистический анализ результатов экспериментов.

1. Доверительные интервалы (95%, t-распределение Стьюдента)
2. Проверка гипотезы (индексный быстрее наивного)
3. Сходство распределений (Манна-Уитни)
"""

import os
import sys
import json
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

RESULTS_DIR = "results"


def load_results():
    filepath = os.path.join(RESULTS_DIR, "benchmark_results.json")
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


# --- t-распределение Стьюдента (критические значения для 95%) ---

T_CRITICAL = {
    2: 4.303,
    3: 3.182,
    4: 2.776,
    5: 2.571,
    6: 2.447,
    7: 2.365,
    8: 2.306,
    9: 2.262,
    10: 2.228,
    15: 2.131,
    20: 2.086,
    30: 2.042,
}


def t_critical(n):
    df = n - 1
    if df in T_CRITICAL:
        return T_CRITICAL[df]
    return 2.0  # приближение для больших df


def mean(values):
    return sum(values) / len(values)


def std_dev(values):
    m = mean(values)
    return math.sqrt(sum((x - m) ** 2 for x in values) / (len(values) - 1))


def confidence_interval_95(values):
    """95% доверительный интервал по t-распределению."""
    n = len(values)
    m = mean(values)
    s = std_dev(values)
    t = t_critical(n)
    margin = t * s / math.sqrt(n)
    return m, margin, m - margin, m + margin


def paired_t_test(values_a, values_b):
    """
    Односторонний парный t-тест.
    H0: mean(A) <= mean(B)  (наивный не медленнее индексного)
    H1: mean(A) > mean(B)   (наивный медленнее индексного)
    """
    n = min(len(values_a), len(values_b))
    diffs = [values_a[i] - values_b[i] for i in range(n)]

    d_mean = mean(diffs)
    d_std = std_dev(diffs)
    t_stat = d_mean / (d_std / math.sqrt(n))
    t_crit = t_critical(n)

    # Для одностороннего теста: отвергаем H0 если t_stat > t_crit_one_sided
    # t_crit_one_sided при alpha=0.05 меньше чем двусторонний
    # Приближение: для одностороннего теста при alpha=0.05, df=4: t_crit = 2.132
    t_crit_one_sided = {
        2: 2.920, 3: 2.353, 4: 2.132, 5: 2.015,
        6: 1.943, 7: 1.895, 8: 1.860, 9: 1.833,
    }
    df = n - 1
    tc = t_crit_one_sided.get(df, 1.833)

    rejected = t_stat > tc

    return {
        "t_stat": t_stat,
        "t_critical": tc,
        "df": df,
        "d_mean": d_mean,
        "d_std": d_std,
        "rejected": rejected,
    }


def mann_whitney_u(x, y):
    """
    Критерий Манна-Уитни для двух независимых выборок.
    Проверяет, различаются ли распределения.
    """
    combined = [(val, "x") for val in x] + [(val, "y") for val in y]
    combined.sort(key=lambda t: t[0])

    # Ранги
    ranks = {}
    i = 0
    while i < len(combined):
        j = i
        while j < len(combined) and combined[j][0] == combined[i][0]:
            j += 1
        avg_rank = (i + 1 + j) / 2
        for k in range(i, j):
            if k not in ranks:
                ranks[k] = []
            ranks[k] = avg_rank
        i = j

    r_x = sum(ranks[i] for i in range(len(combined)) if combined[i][1] == "x")
    r_y = sum(ranks[i] for i in range(len(combined)) if combined[i][1] == "y")

    n_x = len(x)
    n_y = len(y)

    u_x = r_x - n_x * (n_x + 1) / 2
    u_y = r_y - n_y * (n_y + 1) / 2
    u = min(u_x, u_y)

    # Нормальное приближение для p-value (для n >= 5)
    mu = n_x * n_y / 2
    sigma = math.sqrt(n_x * n_y * (n_x + n_y + 1) / 12)
    z = (u - mu) / sigma if sigma > 0 else 0

    return {
        "U": u,
        "U_x": u_x,
        "U_y": u_y,
        "z": z,
        "n_x": n_x,
        "n_y": n_y,
    }


def normalize_by_volume(times, num_files, tokens_per_file):
    """Нормировать время на единицу объёма (файл × токен)."""
    volume = num_files * tokens_per_file
    return [t / volume * 1e6 for t in times]  # микросекунды на единицу


def analyze():
    data = load_results()
    main = data["main"]

    print("=" * 70)
    print("СТАТИСТИЧЕСКИЙ АНАЛИЗ РЕЗУЛЬТАТОВ")
    print("=" * 70)

    # --- 1. Доверительные интервалы ---
    print("\n1. ДОВЕРИТЕЛЬНЫЕ ИНТЕРВАЛЫ (95%, t-распределение Стьюдента)")
    print("-" * 70)
    print(f"{'Датасет':<10} {'Алгоритм':<12} {'Среднее':>10} {'±Погрешн':>10} "
          f"{'Нижняя':>10} {'Верхняя':>10}")
    print("-" * 70)

    ci_results = {}
    for name, d in main.items():
        ci_results[name] = {}
        for algo, key in [("Наивный", "naive"), ("Индексный", "indexed")]:
            times = d[key]["times"]
            m, margin, lo, hi = confidence_interval_95(times)
            ci_results[name][key] = {"mean": m, "margin": margin, "lo": lo, "hi": hi}
            print(f"{name:<10} {algo:<12} {m:>10.4f} {margin:>10.4f} "
                  f"{lo:>10.4f} {hi:>10.4f}")

    # --- 2. Проверка гипотезы ---
    print(f"\n\n2. ПРОВЕРКА ГИПОТЕЗЫ")
    print("-" * 70)
    print("H₀: μ(наивный) ≤ μ(индексный) — индексный не быстрее наивного")
    print("H₁: μ(наивный) > μ(индексный) — индексный быстрее наивного")
    print("Уровень значимости: α = 0.05")
    print("Метод: односторонний парный t-тест")
    print("-" * 70)

    for name, d in main.items():
        result = paired_t_test(d["naive"]["times"], d["indexed"]["times"])
        verdict = "ОТВЕРГНУТА" if result["rejected"] else "НЕ ОТВЕРГНУТА"
        print(f"\n  {name}:")
        print(f"    Средняя разность: {result['d_mean']:.6f} сек")
        print(f"    t-статистика: {result['t_stat']:.4f}")
        print(f"    t-критическое (df={result['df']}, α=0.05): {result['t_critical']:.3f}")
        print(f"    H₀ {verdict}")
        if result["rejected"]:
            print(f"    → Индексный поиск статистически значимо быстрее наивного")

    # --- 3. Сходство распределений ---
    print(f"\n\n3. СХОДСТВО РАСПРЕДЕЛЕНИЙ (критерий Манна-Уитни)")
    print("-" * 70)

    # Сравнение нормированного времени наивного поиска: тип A vs тип B
    for size_label, name_a, name_b in [("small", "A_small", "B_small"),
                                         ("large", "A_large", "B_large")]:
        da = main[name_a]
        db = main[name_b]

        norm_a = normalize_by_volume(
            da["naive"]["times"],
            da["params"]["num_files"],
            da["params"]["tokens_per_file"],
        )
        norm_b = normalize_by_volume(
            db["naive"]["times"],
            db["params"]["num_files"],
            db["params"]["tokens_per_file"],
        )

        result = mann_whitney_u(norm_a, norm_b)
        print(f"\n  Наивный поиск, нормированное время (мкс / файл×токен):")
        print(f"    {name_a}: среднее = {mean(norm_a):.4f} мкс")
        print(f"    {name_b}: среднее = {mean(norm_b):.4f} мкс")
        print(f"    U-статистика: {result['U']:.1f}")
        print(f"    z-статистика: {result['z']:.4f}")
        print(f"    |z| > 1.96 (α=0.05): {abs(result['z']) > 1.96}")
        if abs(result["z"]) > 1.96:
            print(f"    → Распределения статистически различаются")
        else:
            print(f"    → Нет оснований считать распределения различными")

    # Сравнение нормированного времени индексного поиска: тип A vs тип B
    for size_label, name_a, name_b in [("large", "A_large", "B_large")]:
        da = main[name_a]
        db = main[name_b]

        norm_a = normalize_by_volume(
            da["indexed"]["times"],
            da["params"]["num_files"],
            da["params"]["tokens_per_file"],
        )
        norm_b = normalize_by_volume(
            db["indexed"]["times"],
            db["params"]["num_files"],
            db["params"]["tokens_per_file"],
        )

        result = mann_whitney_u(norm_a, norm_b)
        print(f"\n  Индексный поиск, нормированное время (мкс / файл×токен):")
        print(f"    {name_a}: среднее = {mean(norm_a):.6f} мкс")
        print(f"    {name_b}: среднее = {mean(norm_b):.6f} мкс")
        print(f"    U-статистика: {result['U']:.1f}")
        print(f"    z-статистика: {result['z']:.4f}")
        print(f"    |z| > 1.96 (α=0.05): {abs(result['z']) > 1.96}")
        if abs(result["z"]) > 1.96:
            print(f"    → Распределения статистически различаются")
        else:
            print(f"    → Нет оснований считать распределения различными")


    # --- Сохранение ---
    output = {
        "confidence_intervals": {},
        "hypothesis_tests": {},
    }
    for name, d in main.items():
        output["confidence_intervals"][name] = ci_results[name]
        result = paired_t_test(d["naive"]["times"], d["indexed"]["times"])
        output["hypothesis_tests"][name] = result

    filepath = os.path.join(RESULTS_DIR, "statistical_analysis.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n\nРезультаты сохранены: {filepath}")


if __name__ == "__main__":
    analyze()
