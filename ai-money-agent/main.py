from __future__ import annotations

import csv
import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import feedparser
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
TRACKS = {
    "Тексты": ["текст", "статья", "описание", "карточк", "редакт", "рерайт", "копирайт", "пост", "контент"],
    "Изображения": ["изображ", "фото", "обработ", "удалить фон", "баннер", "обложк", "инфограф", "дизайн"],
    "Короткий контент": ["видео", "shorts", "клип", "рилс", "reels", "монтаж", "сценарий", "субтитр", "youtube", "тик ток"],
}

@dataclass
class Lead:
    title: str
    url: str
    summary: str
    source: str
    track: str
    score: int
    warning: str
    draft: str


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def classify(text: str) -> tuple[str, int]:
    normalized = text.casefold()
    scores = {name: sum(term in normalized for term in terms) for name, terms in TRACKS.items()}
    track = max(scores, key=scores.get)
    return track, scores[track]


def load_sources() -> list[dict[str, str]]:
    custom = [x.strip() for x in os.getenv("FEED_URLS", "").split(",") if x.strip()]
    if custom:
        return [{"name": url, "url": url} for url in custom]
    config = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
    return [item for item in config["sources"] if item.get("enabled")]


def draft(title: str, track: str) -> str:
    services = {
        "Тексты": "подготовкой и редактурой текстов",
        "Изображения": "обработкой изображений и простой графикой",
        "Короткий контент": "сценариями, субтитрами и короткими роликами",
    }
    return (f"Здравствуйте! Увидел(а) задачу «{title}». Могу помочь с {services[track]}. "
            "Уточните, пожалуйста, объём, требования к результату, срок и бюджет. "
            "После этого смогу подтвердить стоимость и срок выполнения.")


def collect(sources: list[dict[str, str]], limit: int, min_score: int) -> list[Lead]:
    found: dict[str, Lead] = {}
    for source in sources:
        url = source["url"]
        if not url.startswith(("https://", "http://")):
            continue
        print(f"Проверяю: {source['name']}")
        parsed = feedparser.parse(url)
        if getattr(parsed, "bozo", False) and not parsed.entries:
            print(f"Не удалось прочитать ленту: {getattr(parsed, 'bozo_exception', 'unknown error')}")
            continue
        name = source.get("name") or getattr(parsed.feed, "title", url)
        for entry in parsed.entries[:limit]:
            title = clean(getattr(entry, "title", "Без названия"))
            summary = clean(getattr(entry, "summary", ""))
            link = clean(getattr(entry, "link", ""))
            if not link.startswith(("https://", "http://")):
                continue
            track, score = classify(title + " " + summary)
            if score < min_score:
                continue
            risk_terms = ("бесплатно", "оплатить отклик", "внести залог", "предоплата исполнителя")
            warning = ("Возможный риск: не плати за доступ к заказу и не отправляй залог."
                       if any(term in (title + " " + summary).casefold() for term in risk_terms)
                       else "Проверь заказчика, условия, объём и оплату до начала работы.")
            found[link] = Lead(title, link, summary[:600], name, track, score, warning, draft(title, track))
    return sorted(found.values(), key=lambda x: x.score, reverse=True)


def main() -> None:
    load_dotenv(ROOT / ".env")
    sources = load_sources()
    limit = max(1, int(os.getenv("MAX_ENTRIES_PER_FEED", "60")))
    minimum = max(1, int(os.getenv("MIN_MATCH_SCORE", "1")))
    if not sources:
        print("Нет источников. Проверь sources.json или FEED_URLS в .env.")
        return
    leads = collect(sources, limit, minimum)
    if not leads:
        print("Подходящих задач пока нет. Проверь интернет и RSS-источник.")
        return
    output = ROOT / "leads.csv"
    with output.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(asdict(leads[0]).keys()))
        writer.writeheader()
        writer.writerows(asdict(item) for item in leads)
    print(f"Найдено подходящих задач: {len(leads)}")
    print(f"Сохранено в: {output}")
    for number, item in enumerate(leads[:15], 1):
        print(f"\\n{number}. [{item.track}; score {item.score}] {item.title}")
        print(item.url)
        print(item.warning)
        print("Черновик:", item.draft)


if __name__ == "__main__":
    main()
