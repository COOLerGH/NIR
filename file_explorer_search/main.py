"""
Точка входа в приложение.

Запуск:
    python main.py          — подключение к API на localhost:8000
    python main.py --demo   — демо-режим с тестовыми данными
"""

import sys

from api.real_api import RealFileExplorerAPI, APIConnectionError
from api.mock_fs import InMemoryFileSystem
from ui.menu import MainMenu
from ui.display import print_colored, print_header, print_error, print_recommendation


def create_demo_fs() -> InMemoryFileSystem:
    """Создать файловую систему с демо-данными."""
    fs = InMemoryFileSystem()

    fs.add_directory("/projects")
    fs.add_directory("/projects/web")
    fs.add_directory("/projects/data")
    fs.add_directory("/docs")

    fs.add_file(
        "/projects/web/app.py",
        "from flask import Flask\n"
        "app = Flask(__name__)\n"
        "python web application server\n"
        "routing and request handling\n",
        modified_date="2025-03-15",
    )
    fs.add_file(
        "/projects/web/test_app.py",
        "import pytest\n"
        "def test_index():\n"
        "    assert response.status_code == 200\n"
        "python test automation pytest\n",
        modified_date="2025-03-16",
    )
    fs.add_file(
        "/projects/web/config.json",
        '{"host": "localhost", "port": 8000, "debug": true}\n'
        "configuration settings for web server\n",
        modified_date="2025-02-10",
    )
    fs.add_file(
        "/projects/data/analysis.py",
        "import pandas as pd\n"
        "data = pd.read_csv('data.csv')\n"
        "python data analysis machine learning\n"
        "statistical processing and visualization\n",
        modified_date="2025-04-01",
    )
    fs.add_file(
        "/projects/data/pipeline.py",
        "def extract(): pass\n"
        "def transform(): pass\n"
        "def load(): pass\n"
        "python data pipeline etl processing\n",
        modified_date="2025-03-20",
    )
    fs.add_file(
        "/projects/data/data.csv",
        "name,age,city\n"
        "Alice,30,Moscow\n"
        "Bob,25,London\n"
        "Charlie,35,Paris\n",
        modified_date="2025-01-05",
    )
    fs.add_file(
        "/docs/readme.txt",
        "Project documentation and user guide\n"
        "Installation instructions and setup\n"
        "python project overview\n",
        modified_date="2025-02-20",
    )
    fs.add_file(
        "/docs/api_reference.txt",
        "API reference documentation\n"
        "REST endpoints and methods\n"
        "authentication and authorization\n",
        modified_date="2025-03-01",
    )
    fs.add_file(
        "/docs/changelog.md",
        "# Changelog\n"
        "## v1.0 - Initial release\n"
        "## v1.1 - Bug fixes and improvements\n"
        "python project version history\n",
        modified_date="2025-04-10",
    )
    fs.add_file(
        "/projects/web/styles.css",
        "body { margin: 0; padding: 0; }\n"
        "header { background: blue; color: white; }\n"
        "web design stylesheet layout\n",
        modified_date="2025-01-20",
    )

    return fs


def main():
    """Главная функция."""
    demo_mode = "--demo" in sys.argv

    if demo_mode:
        print_header("демо-режим")
        api = create_demo_fs()
        print_colored("  Загружены демо-данные (10 файлов).", "green")
    else:
        print_header("подключение к API")
        base_url = "http://localhost:8000"
        api = RealFileExplorerAPI(base_url)
        if not api.check_connection():
            print_error(f"Не удалось подключиться к {base_url}")
            print_recommendation(
                "Запустите сервер File Explorer или используйте --demo для демо-режима."
            )
            answer = input("  Запустить в демо-режиме? (y/n): ").strip().lower()
            if answer == "y":
                api = create_demo_fs()
                print_colored("  Загружены демо-данные.", "green")
            else:
                sys.exit(1)

    menu = MainMenu(api)
    try:
        menu.run()
    except KeyboardInterrupt:
        print()
        print_colored("  Завершение по Ctrl+C.", "yellow")


if __name__ == "__main__":
    main()
