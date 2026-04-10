Feature: Простой поиск файлов
  As a пользователь приложения
  I want to искать файлы по ключевому слову
  So that я могу быстро находить документы по содержимому

  Scenario: Поиск существующего слова
    Given создана файловая система с файлами:
      | путь               | содержимое                          |
      | /src/app.py        | python flask web application server |
      | /src/test_app.py   | python pytest test automation       |
      | /src/utils.py      | python utility helper functions     |
      | /docs/readme.txt   | project documentation guide         |
      | /data/report.csv   | name age city alice bob              |
    When пользователь выполняет поиск по слову "python"
    Then результат содержит 3 файла
    And каждый результат имеет score больше нуля
    And результат содержит файл "app.py"
    But результат не содержит файл "report.csv"

  Scenario: Поиск несуществующего слова
    Given создана файловая система с файлами:
      | путь               | содержимое                          |
      | /src/app.py        | python flask web application server |
      | /docs/readme.txt   | project documentation guide         |
    When пользователь выполняет поиск по слову "nonexistent999"
    Then результат пустой

  Scenario: Пустой запрос
    Given создана файловая система с файлами:
      | путь               | содержимое                          |
      | /src/app.py        | python flask web application server |
    When пользователь выполняет поиск по слову ""
    Then результат пустой

  Scenario: Запрос из спецсимволов
    Given создана файловая система с файлами:
      | путь               | содержимое                          |
      | /src/app.py        | python flask web application server |
    When пользователь выполняет поиск по слову "@#$%"
    Then результат пустой

  Scenario Outline: Поиск по различным запросам
    Given создана файловая система с файлами:
      | путь               | содержимое                          |
      | /src/app.py        | python flask web application server |
      | /src/test_app.py   | python pytest test automation       |
      | /docs/readme.txt   | project documentation guide         |
    When пользователь выполняет поиск по слову "<запрос>"
    Then результат содержит <количество> файла

    Examples:
      | запрос       | количество |
      | python       | 2          |
      | flask        | 1          |
      | guide        | 1          |
      | zzzzzzz      | 0          |
