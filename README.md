# RateTerrain v1 — rateterrain.com

Static site: Astro + data from CMS Exchange PUF (PY2026, Texas).

## Structure
- `scripts/etl.py` — превращает 3 файла CMS (Rate_PUF.csv, plan_attributes_PUF.csv, service_area_PUF.csv) в `src/data/*.json`. Встроенные QA-проверки останавливают сборку при любой аномалии. Путь к CSV задан константой UP в начале файла.
- `src/` — исходники страниц (Astro). `src/data/` — готовые данные текущей сборки.
- `dist/` — ГОТОВЫЙ К ПУБЛИКАЦИИ сайт (уже собран). Для запуска ничего собирать не нужно.

## Публикация (Cloudflare Pages, без командной строки)
1. dash.cloudflare.com → Workers & Pages → Create → Pages → Upload assets.
2. Имя проекта: rateterrain. Перетащить СОДЕРЖИМОЕ папки dist (не саму папку). Deploy.
3. Проверить временный адрес вида rateterrain.pages.dev.
4. В проекте: Custom domains → добавить rateterrain.com → следовать подсказкам (Cloudflare предложит перенести DNS домена к себе — соглашаться, это же даст бесплатную почту-пересылку для hello@rateterrain.com через Email Routing).

## Пересборка при обновлении данных (когда выйдет PY2027)
```
python3 scripts/etl.py      # положить новые CSV, обновить UP при необходимости
npm install                 # один раз
npm run build               # результат в dist/
```
Затем повторить Upload assets в Cloudflare (новый деплой поверх старого).
