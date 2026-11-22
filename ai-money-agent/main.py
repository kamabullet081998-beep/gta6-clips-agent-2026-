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
    "Тексты": ["текст", "статья", "описание", "карточк", "редакт", "рерайт", "копирайт", "пост", "контент", "сценарий"],
    "Изображения": ["изображ", "фото", "обработ", "удалить фон", "баннер", "обложк", "инфограф", "дизайн", "презентац"],
    "Короткий контент": ["видео", "shorts", "клип", "рилс", "reels", "монтаж", "субтитр", "youtube", "тик ток", "вертикальн"],
}
RISK_TERMS = [
    "оплатить отклик", "оплата за доступ", "внести залог", "страховой взнос",
    "предоплата исполнителя", "купить аккаунт", "перевести для проверки",
    "написать положительный отзыв", "накрутить отзывы", "фейковый отзыв",
]
GOOD_TERMS = ["понятное тз", "техническое задание", "пример", "референс", "долгосрочно", "постоянно", "срочно"]


@dataclass
class Lead:
    title: str
    url: str
    summary: str
    source: str
    track: str
    score: int
    risk_level: str
    budget_hint: str
    reason: str
    warning: str
    draft: str


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def classify(text: str) -> tuple[str, int]:
    normalized = text.casefold()
    scores = {name: sum(2 if term in normalized else 0 for term in terms) for name, terms in TRACKS.items()}
    track = max(scores, key=scores.get)
    return track, scores[track]


def load_sources() -> list[dict[str, str]]:
    custom = [x.strip() for x in os.getenv("FEED_URLS", "").split(",") if x.strip()]
    if custom:
        return [{"name": url, "url": url} for url in custom]
    config = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
    return [item for item in config["sources"] if item.get("enabled")]


def assess(title: str, summary: str, track_score: int) -> tuple[int, str, str, str, str]:
    text = (title + " " + summary).casefold()
    risk_hits = [term for term in RISK_TERMS if term in text]
    risk = "Высокий" if risk_hits else "Низкий"
    budget_match = re.search(r"(\d[\d\\s]{2,}(?:[.,]\d{1,2})?\\s*(?:₽|руб(?:лей|ля|ль)?))", title + " " + summary, re.I)
    budget = clean(budget_match.group(1)) if budget_match else "Не указан"
    score = min(100, track_score * 12 + sum(5 for term in GOOD_TERMS if term in text) + (10 if budget != "Не указан" else 0) - (50 if risk_hits else 0))
    reason = "Есть совпадение с нашими услугами"
    if budget == "Не указан":
        reason += "; бюджет нужно уточнить"
    if any(term in text for term in ("долгосрочно", "постоянно")):
        reason += "; возможна повторная работа"
    warning = ("Не откликаться без тщательной проверки: обнаружены рискованные условия (" + ", ".join(risk_hits) + ")."
               if risk_hits else "Проверь заказчика, объём, сроки, права на материалы и порядок оплаты до начала работы.")
    return max(0, score), risk, budget, reason, warning


def make_draft(title: str, track: str, summary: str) -> str:
    services = {
        "Тексты": "текстом, описанием или редактурой",
        "Изображения": "обложкой, баннером или обработкой изображения",
        "Короткий контент": "коротким видео, монтажом или субтитрами",
    }
    detail = f" Вижу в описании: {summary[:180]}." if summary else ""
    return (f"Здравствуйте! Готов обсудить задачу «{title}». Могу помочь с {services[track]}. "
            f"{detail} Подскажите, пожалуйста, какой нужен итоговый формат, есть ли примеры/референсы, "
            "какой срок и бюджет предусмотрены? До согласования ТЗ и оплаты работу не начинаю.")


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
            track, track_score = classify(title + " " + summary)
            if track_score == 0:
                continue
            score, risk, budget, reason, warning = assess(title, summary, track_score)
            if score < min_score:
                continue
            found[link] = Lead(title, link, summary[:600], name, track, score, risk, budget, reason, warning,
                               make_draft(title, track, summary))
    return sorted(found.values(), key=lambda x: (x.risk_level == "Низкий", x.score), reverse=True)


def main() -> None:
    load_dotenv(ROOT / ".env")
    sources = load_sources()
    limit = max(1, int(os.getenv("MAX_ENTRIES_PER_FEED", "60")))
    minimum = max(0, int(os.getenv("MIN_MATCH_SCORE", "1")))
    output = ROOT / "leads.csv"
    leads = collect(sources, limit, minimum) if sources else []
    fields = list(Lead.__dataclass_fields__.keys())
    with output.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(asdict(item) for item in leads)
    print(f"Найдено подходящих задач: {len(leads)}")
    print(f"Сохранено в: {output}")
    for number, item in enumerate(leads[:15], 1):
        print()
        print(f"{number}. [{item.track}; приоритет {item.score}/100; риск: {item.risk_level}] {item.title}")
        print(f"Бюджет: {item.budget_hint}")
        print(item.url)
        print(item.warning)
        print("Черновик:", item.draft)


if __name__ == "__main__":
    main()
