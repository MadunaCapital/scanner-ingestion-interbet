# scanner-ingestion-interbet

Interbet odds scraper for the MadunaCapital arbitrage scanner. One of several independent per-bookmaker repos, kept maximally decoupled from the others: a bug, dependency bump, or bad release here can't touch any other bookmaker's scraper.

## How it works

Reads Interbet's public, unauthenticated `FixedOdds/LoadCouponsPartial` feed -- the same endpoint interbet.co.za's own sports pages call (via a plain jQuery `$.ajax` GET) to fill in the fixture list for any visitor. Plain `httpx` GET, no TLS impersonation, no stealth browser, no Cloudflare bypass: verified with a completely bare `curl` (no User-Agent, no cookies, no Referer) returning the identical payload as a real browser session, so none of that is needed here, same as Betway ZA and WSB. Polls on a plain, fixed 45-second interval by default -- no jitter, no randomization to look human.

**Format difference from Betway ZA / WSB:** this endpoint returns a server-rendered HTML fragment (an ASP.NET MVC partial view), not JSON -- interbet.co.za has no JSON REST API for odds at all. The data is nonetheless fully structured: every odds button embeds `EventID`/`ParticipantName`/`Odds`/`EventDate`/`EventGroup` as a query string in its `data-url` attribute (the URL the page's own JS would call to place a bet), so `scraper.py` parses those attributes with `BeautifulSoup` + `urllib.parse` rather than `response.json()`. See the module docstring in `src/interbet/scraper.py` for the full reasoning, including why this is still within the project's "plain HTTP GET, no bot-detection workaround" boundary, and why the site's SignalR/msgpack live-odds websocket is deliberately not used.

Depends on:
- [scanner-ingestion](https://github.com/MadunaCapital/scanner-ingestion) (base install only, no `stealth` extra -- this adapter doesn't need it) for `BaseScraper`
- [scanner-schemas](https://github.com/MadunaCapital/scanner-schemas) for `OddsEvent`/`MarketOdds`
- `beautifulsoup4` for parsing the HTML coupons partial (the one dependency this repo needs beyond what Betway ZA/WSB use, precisely because the feed is HTML, not JSON)

All pulled in via `requirements.txt`, same pattern as every other repo in this project.

## Status

Working and verified live: `InterbetScraper().fetch_raw_odds()` + `.to_odds_events()` returns real current soccer fixtures (confirmed against `/Prematch/Sport/Soccer`'s "All Leagues 24H" venue: 119 fixtures across 46 competitions in one call) with sane decimal odds. Tests use a real trimmed HTML fragment captured from a live response, no live network in tests.

## Local dev

```
pip install -r requirements.txt
pytest
```

## Scope note

This adapter intentionally only reads what Interbet's own frontend already fetches publicly, at a reasonable polling interval -- no authentication bypass, no anti-bot evasion. Terms of Service exposure for scraping public data is a real but different (lower-severity, contractual rather than computer-misuse) question than the Cybercrimes Act question that applies to defeating security measures.

## Known limitations / open items

- **Timezone assumption:** Interbet's `EventDate` query param and its human-readable fixture header both show the same clock time with no timezone marker. This adapter assumes SAST (UTC+2, no DST) based on that match and the site being a ZA bookmaker. If wrong, the effect is a fixed 2-hour skew on `start_time`, not bad odds -- worth spot-checking against a known kickoff time before relying on this in production.
- **Coverage:** uses the "All Leagues 24H" venue (`VenueID=65`), Interbet's broadest single-call soccer coupon. This only covers the next 24 hours; Interbet also has separate venues for specific competitions and longer horizons (see `/Prematch/Sport/Soccer`'s venue nav) that aren't polled here. Widening coverage would mean polling multiple venues per cycle.
- **Live/in-play odds:** not covered. Interbet pushes in-play odds updates over a SignalR (`/signalr/hubs`) websocket using `msgpack-lite` framing -- a persistent binary-protocol connection, not a plain HTTP GET/POST, so it's out of scope for this adapter by the project's own boundary.
