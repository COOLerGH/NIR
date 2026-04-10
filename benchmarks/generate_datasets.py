"""
Генерация наборов данных для нагрузочного тестирования.

Типы:
  A — много коротких файлов (50 токенов)
  B — мало длинных файлов (2500 токенов)

Размеры:
  small — базовый замер
  large — время наивного поиска >= 2 мин (определяется экспериментально)
"""

import os
import sys
import json
import random
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.mock_fs import InMemoryFileSystem


# --- Словарь ---

WORD_POOL = [
    "alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta",
    "iota", "kappa", "lambda", "mu", "nu", "xi", "omicron", "pi", "rho",
    "sigma", "tau", "upsilon", "phi", "chi", "psi", "omega", "apple",
    "banana", "cherry", "date", "elder", "fig", "grape", "honey", "iris",
    "jasmine", "kiwi", "lemon", "mango", "nectar", "olive", "peach",
    "quince", "rose", "sage", "tulip", "umbra", "violet", "willow",
    "xenon", "yarrow", "zinnia", "abstract", "binary", "compile",
    "debug", "execute", "function", "global", "handle", "import",
    "join", "kernel", "library", "module", "network", "object",
    "process", "query", "runtime", "stack", "thread", "update",
    "value", "widget", "xml", "yield", "zero", "access", "buffer",
    "cache", "driver", "engine", "format", "gateway", "hash",
    "index", "journal", "key", "loader", "mapper", "node", "output",
    "parser", "queue", "reader", "schema", "table", "unit", "vector",
    "worker", "proxy", "scope", "token", "server", "client", "route",
    "model", "view", "controller", "service", "factory", "builder",
    "adapter", "bridge", "facade", "observer", "strategy", "command",
    "iterator", "mediator", "memento", "state", "visitor", "chain",
    "composite", "decorator", "flyweight", "prototype", "singleton",
    "template", "interpreter", "filter", "pipeline", "channel",
    "message", "event", "signal", "handler", "listener", "emitter",
    "stream", "buffer", "frame", "packet", "segment", "block",
    "cluster", "sector", "region", "zone", "area", "domain", "realm",
    "sphere", "field", "space", "plane", "layer", "level", "tier",
    "grade", "rank", "class", "group", "batch", "set", "list",
    "array", "matrix", "tensor", "graph", "tree", "heap", "queue",
    "deque", "ring", "mesh", "grid", "lattice", "web", "net",
    "link", "edge", "vertex", "path", "route", "trail", "track",
    "lane", "road", "bridge", "tunnel", "gate", "door", "window",
    "panel", "board", "card", "chip", "core", "shell", "skin",
    "coat", "wrap", "cover", "shield", "guard", "fence", "wall",
    "floor", "roof", "base", "foundation", "anchor", "pillar",
    "column", "beam", "arch", "vault", "dome", "tower", "spire",
    "peak", "summit", "crest", "ridge", "slope", "valley", "canyon",
    "gorge", "cliff", "cave", "tunnel", "mine", "well", "spring",
    "river", "lake", "pond", "ocean", "sea", "bay", "gulf", "inlet",
    "harbor", "port", "dock", "pier", "wharf", "beach", "shore",
    "coast", "island", "cape", "delta", "marsh", "swamp", "forest",
    "jungle", "grove", "garden", "park", "meadow", "prairie", "plain",
    "desert", "tundra", "glacier", "volcano", "mountain", "hill",
    "plateau", "mesa", "butte", "knoll", "dune", "reef", "atoll",
    "lagoon", "fjord", "strait", "channel", "passage", "crossing",
    "junction", "intersection", "corner", "bend", "curve", "spiral",
    "helix", "coil", "loop", "ring", "circle", "oval", "ellipse",
    "sphere", "cube", "prism", "pyramid", "cone", "cylinder", "disk",
    "plate", "sheet", "strip", "band", "ribbon", "cord", "rope",
    "wire", "cable", "chain", "spring", "bolt", "screw", "nail",
    "pin", "clip", "clamp", "hook", "latch", "lock", "hinge",
    "lever", "gear", "wheel", "axle", "shaft", "crank", "piston",
    "valve", "pump", "motor", "engine", "turbine", "rotor", "blade",
    "fan", "propeller", "rudder", "sail", "mast", "hull", "keel",
    "stern", "bow", "deck", "cabin", "bridge", "helm", "anchor",
    "compass", "radar", "sonar", "beacon", "buoy", "lighthouse",
    "signal", "flag", "banner", "emblem", "badge", "seal", "stamp",
    "mark", "sign", "symbol", "icon", "logo", "brand", "label",
    "tag", "code", "cipher", "key", "token", "ticket", "pass",
    "permit", "license", "warrant", "charter", "patent", "title",
    "deed", "bond", "note", "bill", "receipt", "invoice", "ledger",
    "record", "file", "folder", "binder", "shelf", "rack", "cabinet",
    "drawer", "box", "case", "bag", "pack", "bundle", "parcel",
    "crate", "barrel", "tank", "vessel", "container", "bin", "basket",
]

TARGET_WORDS = ["python", "search", "algorithm", "test", "data"]
TARGET_PROBABILITY = 0.3
SEED = 42

# --- Конфигурация датасетов ---

DATASETS = {
    "A_small": {"num_files": 100, "tokens_per_file": 50},
    "A_large": {"num_files": 500000, "tokens_per_file": 50},
    "B_small": {"num_files": 20, "tokens_per_file": 2500},
    "B_large": {"num_files": 50000, "tokens_per_file": 2500},
}


def generate_file_content(rng, tokens_per_file):
    """Сгенерировать содержимое одного файла."""
    words = []
    for _ in range(tokens_per_file):
        if rng.random() < TARGET_PROBABILITY:
            words.append(rng.choice(TARGET_WORDS))
        else:
            words.append(rng.choice(WORD_POOL))
    return " ".join(words)


def generate_dataset(name, num_files, tokens_per_file, seed=SEED):
    """Сгенерировать датасет и вернуть список файлов."""
    rng = random.Random(seed)
    files = []

    for i in range(num_files):
        content = generate_file_content(rng, tokens_per_file)
        path = f"/gen/{name}/file_{i:06d}.txt"
        files.append({"path": path, "content": content})

    return files


def load_dataset_to_fs(files):
    """Загрузить датасет в InMemoryFileSystem."""
    fs = InMemoryFileSystem()
    for f in files:
        fs.add_file(f["path"], f["content"])
    return fs


def save_dataset(name, files, output_dir="datasets"):
    """Сохранить датасет в JSON."""
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, f"{name}.json")

    metadata = {
        "name": name,
        "num_files": len(files),
        "tokens_per_file": len(files[0]["content"].split()) if files else 0,
        "seed": SEED,
        "target_words": TARGET_WORDS,
        "target_probability": TARGET_PROBABILITY,
        "files": files,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False)

    size_mb = os.path.getsize(filepath) / (1024 * 1024)
    print(f"  {name}: {len(files)} файлов, {size_mb:.1f} МБ")
    return filepath


def load_dataset(name, input_dir="datasets"):
    """Загрузить датасет из JSON."""
    filepath = os.path.join(input_dir, f"{name}.json")
    with open(filepath, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    return metadata["files"]


def generate_all():
    """Сгенерировать и сохранить все датасеты."""
    print("Генерация датасетов...")
    print(f"  Словарь: {len(WORD_POOL)} слов")
    print(f"  Целевые слова: {TARGET_WORDS}")
    print(f"  Вероятность целевого слова: {TARGET_PROBABILITY}")
    print(f"  Seed: {SEED}")
    print()

    for name, params in DATASETS.items():
        start = time.perf_counter()
        files = generate_dataset(name, **params)
        save_dataset(name, files)
        elapsed = time.perf_counter() - start
        print(f"    Время генерации: {elapsed:.2f} сек")
        print()

    print("Все датасеты сгенерированы.")


if __name__ == "__main__":
    generate_all()
