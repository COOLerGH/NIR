"""
Анализ результатов нагрузочного тестирования.

Строит графики:
1. Время поиска vs количество файлов (тип A)
2. Время поиска vs количество файлов (тип B)
3. Сравнение 4 датасетов (столбчатая диаграмма)
4. Профилирование — составные части
"""

import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib.pyplot as plt
import matplotlib

matplotlib.use("Agg")

RESULTS_DIR = "results"
PLOTS_DIR = "results/plots"


def load_results():
    """Загрузить результаты из JSON."""
    filepath = os.path.join(RESULTS_DIR, "benchmark_results.json")
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def plot_preliminary_type(data, type_label, tokens_label):
    """График предварительного эксперимента для одного типа."""
    entries = [e for e in data if e["type"] == type_label]
    if not entries:
        return

    files = [e["num_files"] for e in entries]
    naive = [e["naive_mean"] for e in entries]
    indexed = [e["indexed_mean"] for e in entries]
    index_time = [e["index_time"] for e in entries]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(files, naive, "o-", label="Наивный поиск", color="red", linewidth=2)
    ax.plot(files, indexed, "s-", label="Индексный поиск", color="green", linewidth=2)
    ax.plot(files, index_time, "^--", label="Построение индекса", color="blue", linewidth=1)

    ax.set_xlabel("Количество файлов", fontsize=12)
    ax.set_ylabel("Время (сек)", fontsize=12)
    ax.set_title(f"Предварительный эксперимент — тип {type_label} "
                 f"({tokens_label} токенов/файл)", fontsize=14)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.set_xscale("log")
    ax.set_yscale("log")

    filepath = os.path.join(PLOTS_DIR, f"preliminary_{type_label}.png")
    fig.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Сохранён: {filepath}")


def plot_main_comparison(main_data):
    """Столбчатая диаграмма — сравнение на 4 датасетах."""
    names = list(main_data.keys())
    naive_times = [main_data[n]["naive"]["mean"] for n in names]
    indexed_times = [main_data[n]["indexed"]["mean"] for n in names]

    x = range(len(names))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))
    bars1 = ax.bar([i - width/2 for i in x], naive_times, width,
                   label="Наивный", color="red", alpha=0.8)
    bars2 = ax.bar([i + width/2 for i in x], indexed_times, width,
                   label="Индексный", color="green", alpha=0.8)

    ax.set_xlabel("Датасет", fontsize=12)
    ax.set_ylabel("Время поиска (сек)", fontsize=12)
    ax.set_title("Сравнение алгоритмов на 4 датасетах", fontsize=14)
    ax.set_xticks(list(x))
    ax.set_xticklabels(names, fontsize=11)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, axis="y")

    # Подписи значений
    for bar in bars1:
        h = bar.get_height()
        ax.annotate(f"{h:.3f}",
                    xy=(bar.get_x() + bar.get_width()/2, h),
                    xytext=(0, 3), textcoords="offset points",
                    ha="center", fontsize=9)
    for bar in bars2:
        h = bar.get_height()
        ax.annotate(f"{h:.3f}",
                    xy=(bar.get_x() + bar.get_width()/2, h),
                    xytext=(0, 3), textcoords="offset points",
                    ha="center", fontsize=9)

    filepath = os.path.join(PLOTS_DIR, "main_comparison.png")
    fig.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Сохранён: {filepath}")


def plot_profiling(main_data):
    """Профилирование — составные части для каждого датасета."""
    names = list(main_data.keys())
    gen_times = [main_data[n]["generation_time"] for n in names]
    idx_times = [main_data[n]["index_time"] for n in names]
    naive_times = [main_data[n]["naive"]["mean"] for n in names]
    indexed_times = [main_data[n]["indexed"]["mean"] for n in names]

    fig, ax = plt.subplots(figsize=(10, 6))
    x = range(len(names))
    width = 0.2

    ax.bar([i - 1.5*width for i in x], gen_times, width,
           label="Генерация", color="gray", alpha=0.8)
    ax.bar([i - 0.5*width for i in x], idx_times, width,
           label="Индексация", color="blue", alpha=0.8)
    ax.bar([i + 0.5*width for i in x], naive_times, width,
           label="Наивный поиск", color="red", alpha=0.8)
    ax.bar([i + 1.5*width for i in x], indexed_times, width,
           label="Индексный поиск", color="green", alpha=0.8)

    ax.set_xlabel("Датасет", fontsize=12)
    ax.set_ylabel("Время (сек)", fontsize=12)
    ax.set_title("Профилирование операций", fontsize=14)
    ax.set_xticks(list(x))
    ax.set_xticklabels(names, fontsize=11)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis="y")

    filepath = os.path.join(PLOTS_DIR, "profiling.png")
    fig.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Сохранён: {filepath}")


def plot_memory(main_data):
    """График потребления памяти индексом."""
    names = list(main_data.keys())
    memory_mb = [main_data[n]["memory"]["total_mb"] for n in names]

    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(names, memory_mb, color="steelblue", alpha=0.8)

    for bar in bars:
        h = bar.get_height()
        ax.annotate(f"{h:.2f} МБ",
                    xy=(bar.get_x() + bar.get_width()/2, h),
                    xytext=(0, 3), textcoords="offset points",
                    ha="center", fontsize=10)

    ax.set_xlabel("Датасет", fontsize=12)
    ax.set_ylabel("Память (МБ)", fontsize=12)
    ax.set_title("Потребление памяти индексом", fontsize=14)
    ax.grid(True, alpha=0.3, axis="y")

    filepath = os.path.join(PLOTS_DIR, "memory.png")
    fig.savefig(filepath, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Сохранён: {filepath}")


def print_summary_table(main_data):
    """Вывести сводную таблицу результатов."""
    print("\n" + "=" * 80)
    print("СВОДНАЯ ТАБЛИЦА РЕЗУЛЬТАТОВ")
    print("=" * 80)

    header = (f"{'Датасет':<10} {'Файлов':>8} {'Ток/файл':>9} "
              f"{'Индекс(с)':>10} {'Наивный(с)':>11} "
              f"{'Индексн(с)':>11} {'Ускорение':>10} {'Память':>10}")
    print(header)
    print("-" * 80)

    for name, d in main_data.items():
        num = d["params"]["num_files"]
        tok = d["params"]["tokens_per_file"]
        idx_t = d["index_time"]
        naive_t = d["naive"]["mean"]
        indexed_t = d["indexed"]["mean"]
        speedup = naive_t / indexed_t if indexed_t > 0 else float("inf")
        mem = d["memory"]["total_mb"]

        print(f"{name:<10} {num:>8} {tok:>9} {idx_t:>10.4f} "
              f"{naive_t:>11.4f} {indexed_t:>11.4f} "
              f"{speedup:>9.1f}x {mem:>9.2f}МБ")

    print("-" * 80)


def print_preliminary_table(preliminary):
    """Вывести таблицу предварительного эксперимента."""
    print("\n" + "=" * 60)
    print("ПРЕДВАРИТЕЛЬНЫЙ ЭКСПЕРИМЕНТ")
    print("=" * 60)

    for type_label in ["A", "B"]:
        entries = [e for e in preliminary if e["type"] == type_label]
        if not entries:
            continue

        tok = entries[0]["tokens_per_file"]
        print(f"\nТип {type_label} ({tok} токенов/файл):")
        print(f"{'Файлов':>10} {'Индексация':>12} {'Наивный':>12} {'Индексный':>12}")
        print("-" * 50)

        for e in entries:
            print(f"{e['num_files']:>10} {e['index_time']:>11.4f}с "
                  f"{e['naive_mean']:>11.4f}с {e['indexed_mean']:>11.4f}с")


def analyze():
    """Основной анализ."""
    os.makedirs(PLOTS_DIR, exist_ok=True)

    data = load_results()

    # Таблицы
    print_preliminary_table(data["preliminary"])
    print_summary_table(data["main"])

    # Графики
    print("\nПостроение графиков...")
    plot_preliminary_type(data["preliminary"], "A", "50")
    plot_preliminary_type(data["preliminary"], "B", "2500")
    plot_main_comparison(data["main"])
    plot_profiling(data["main"])
    plot_memory(data["main"])

    print("\nАнализ завершён.")


if __name__ == "__main__":
    analyze()
