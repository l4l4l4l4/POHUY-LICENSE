# ПО ХУЙ LICENSE

Скилл `pohuy` и правила вклада для репозиториев, которые его требуют.

`LICENSE` — грант на использование. Текст капсом. Это unapproved custom license, не OSI-approved open source.

`COVENANT.md` — правила вклада, идентификатор `POHUY-COVENANT-1.0`. Коммит делает агент с загруженным `pohuy`. Общаться по вкладу можно только с этим скиллом. К коммиту прикладывается вычищенный бандл чата. Обязательный набор скиллов: только `pohuy`.

Чекер проверяет форму бандла. Он не доказывает, что модель честно видела скилл.

## Файлы

- `SKILL.md`, `references/slovar.md`, `references/sceny.md` — скилл.
- `LICENSE` — грант.
- `COVENANT.md` — правила вклада.
- `checker/pohuy_check.py` — проверка.
- `.github/workflows/pohuy-check.yml` — тот же чекер для GitHub Actions и Forgejo Actions.

## Установка скилла

Клонировать этот репозиторий в каталог скиллов агента под именем `pohuy`.

Раздел вклада в `SKILL.md` включается только если первая строка `LICENSE` в рабочей копии равна `ПО ХУЙ LICENSE`.

## Проверка

```bash
python3 checker/pohuy_check.py
python3 -m unittest discover -s tests -v
```

Код возврата чекера `0` — бандл сходится с деревом. Иначе причины на stderr.

## Топик

На GitHub топик только `pohuy`: topics принимают `[a-z0-9-]`. Кириллица живёт в заголовке `LICENSE`.
