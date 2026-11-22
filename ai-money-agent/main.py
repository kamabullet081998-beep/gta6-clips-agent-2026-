from __future__ import annotations

import csv
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import feedparser
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
TRACKS = {
    "Тексты": ["текст", "статья", "описание", "карточк", "редакт", "рерайт", "копирайт", "пост"],
    "Изображения": ["изображ", "фото", "обработ", "удалить фон", "баннер", "обложк", "инфограф"],
    "Короткий контент": ["видео", "shorts", "клип", "рилс", "reels", "монтаж", "сценарий", "субтитр"],
}

@dataclass
class Lead:
    title: str
    url: str
    summary: str
    source: str
    track: str
    score: int


def clean(value: str) -> str:
    return re.sub(r"\\s+", " ", value or "").strip()


def classify(text: str) -> tuple[str, int]:
    text = text.casefold()
    scores = {name: sum(term in text for term in terms) for name, terms in TRACKS.items()}
    track = max(scores, key=scores.get)
    return track, scores[track]


def collect(urls: list[str], limit: int) -> list[Lead]:
    results: list[Lead] = []
    for url in urls:
        if not url.startswith(("https://", "http://")):
            print(f"Пропуск некорректного URL: {url}")
            continue
        feed = feedparser.parse(url)
        if getattr(feed, "bozo", False) and not feed.entries:
            print(f"Не удалось прочитать ленту: {url}")
            continue
        source = clean(getattr(feed.feed, "title", "")) or url
        for entry in feed.entries[:limit]:
            title = clean(getattr(entry, "title", "Без названия"))
            summary = clean(getattr(entry, "summary", ""))
            link = clean(getattr(entry, "link", ""))
            if not link.startswith(("https://", "http://")):
                continue
            track, score = classify(f"{title} {summary}")
            if score:
                results.append(Lead(title, link, summary[:700], source, track, score))
    return sorted(results, key=lambda item: item.score, reverse=True)


def make_draft(lead: Lead) -> str:
    offer = {
        "Тексты": "подготовкой или редактурой текстов",
        "Изображения": "обработкой изображений и простой графикой",
        "Короткий контент": "подготовкой сценариев, субтитров и коротких роликов",
    }[lead.track]
    return (
        f"Здравствуйте! Увидел(а) вашу задачу «{lead.title}». "
        f"Могу помочь с {offer}. Подскажите, пожалуйста, точный объём, "
        "требования к результату, срок и бюджет. После уточнения смогу подтвердить стоимость."
    )


def main() -> None:
    load_dotenv(ROOT / ".env")
    urls = [x.strip() for x in os.getenv("FEED_URLS", "").split(",") if x.strip()]
    limit = max(1, int(os.getenv("MAX_ENTRIES_PER_FEED", "40")))
    if not urls:
        print("Ленты не настроены. Заполните FEED_URLS в файле .env.")
        print("Добавляйте только публичные RSS/Atom-ленты, чтение которых разрешено их владельцем.")
        return

    leads = collect(urls, limit)
    if not leads:
        print("Подходящих объявлений не найдено. Проверьте адреса лент и попробуйте позже.")
        return

    output = ROOT / "leads.csv"
    with output.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(leads[0]).keys()) + ["draft"])
        writer.writeheader()
        for lead in leads:
            row = asdict(lead)
            row["draft"] = make_draft(lead)
            writer.writerow(row)

    print(f"Найдено подходящих объявлений: {len(leads)}")
    print(f"Результаты и черновики сохранены: {output}")
    for index, lead in enumerate(leads[:10], 1):
        print(f"{index}. [{lead.track}; оценка {lead.score}] {lead.title}")
        print(f"   {lead.url}")
        print(f"   Черновик: {make_draft(lead)}")


if __name__ == "__main__":
    main()
