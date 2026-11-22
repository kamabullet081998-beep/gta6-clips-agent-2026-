# AI Money Agent — starter MVP

A free-first assistant for the Russian/CIS freelance market. This starter version collects public RSS/Atom listings that you explicitly configure, ranks them across three service tracks, and prepares draft replies for your review.

## Service tracks
1. Text: descriptions, editing, rewriting, posts.
2. Images: basic image briefs, backgrounds, banners and covers.
3. Short content: scripts, subtitles and short-video editing briefs.

## Requirements
- Python 3.10+
- Internet access for configured feeds
- No paid API or hosting required for this local starter

## Run
1. Install Python.
2. In this folder run: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env`.
4. Add public RSS/Atom feed URLs you are permitted to access to `FEED_URLS`.
5. Run: `python main.py`

## Safety and limitations
- This is a starter tool, not an autonomous money-making system.
- It does not log into freelance platforms, bypass CAPTCHAs, send applications, contact clients, or accept jobs.
- Review every listing and draft before contacting anyone. Confirm scope, deadline, price and payment terms directly.
- Follow each platform's terms and local laws. Do not scrape sites that prohibit it.
- Never commit passwords, API keys, bot tokens, payment details or identity documents. Keep secrets in local `.env` (ignored by Git).
- Income is not guaranteed. You need a real client and must deliver the work.

## Current status
The feed reader works only after you configure allowed feed URLs. No marketplace accounts or payment services are connected.
