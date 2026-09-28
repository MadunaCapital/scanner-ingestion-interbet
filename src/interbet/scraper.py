"""Interbet adapter.

Reads Interbet's public, unauthenticated `FixedOdds/LoadCouponsPartial`
feed -- the same endpoint interbet.co.za's own sports pages call (via a
plain jQuery `$.ajax` GET, see `Scripts/sport.js`) to fill in the fixture
list for any visitor. This is a plain HTTP GET with no TLS impersonation,
no stealth browser, and no Cloudflare bypass: verified with a completely
bare `curl` (no User-Agent, no cookies, no Referer) returning the exact
same ~1.3MB payload as a normal browser session, so none of that is
needed here, same as Betway ZA and WSB.

Unlike Betway ZA and WSB, this endpoint returns a server-rendered HTML
fragment (an ASP.NET MVC partial view), not JSON -- the site has no JSON
REST API for odds at all. (Interbet also runs a SignalR/msgpack websocket
hub for pushing live in-play odds updates on top of this snapshot; this
adapter deliberately does not use it -- a persistent, binary-framed
websocket protocol is a fundamentally different and heavier integration
than "plain HTTP GET", and is out of scope here. Polling the same plain
snapshot endpoint the page itself uses for its initial/refreshed render
is enough for pre-match arbitrage scanning.)

The data is nonetheless fully structured despite the HTML wrapper: every
odds button embeds its EventID/ParticipantName/Odds/EventDate/EventGroup
as a query string in its `data-url` attribute (the URL the page's own JS
would POST to place a bet), so parsing means reading those attributes,
not scraping prose -- no more fragile than reading JSON keys.

Endpoint discovered by ordinary browsing (curl against the pages
interbet.co.za/Prematch/Sport/Soccer/* itself links to) and inspecting
the `data-url` the page's own sport.js issues via `$.ajax` GET.
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

import httpx
from bs4 import BeautifulSoup
from ingestion.base_scraper import BaseScraper
from schemas import MarketOdds, OddsEvent

logger = logging.getLogger(__name__)

INTERBET_COUPONS_URL = "https://interbet.co.za/FixedOdds/LoadCouponsPartial"

# SportID=48 is Interbet's sport-level id for Soccer. VenueID=65 ("All
# Leagues 24H") is the broadest single-call coupon: every soccer fixture
# (any competition) kicking off in the next 24 hours, in one response --
# discovered from the "All Leagues 24H" tab on /Prematch/Sport/Soccer
# (as opposed to e.g. VenueID=60 "Starting in 4 hours", which is
# narrower, or the various single-competition venues).
SOCCER_SPORT_ID = 48
ALL_LEAGUES_24H_VENUE_ID = 65

# Plain, fixed-interval polling -- same cadence as a normal page refresh,
# not randomized or disguised to look human, same as Betway ZA and WSB.
DEFAULT_POLL_INTERVAL_SECONDS = 45

# Interbet's own site displays fixture times in SAST (South Africa
# Standard Time, UTC+2, no DST) with no timezone marker anywhere in the
# HTML or in the EventDate query param -- confirmed by comparing the
# human-readable "28 Sep 2026 - 18:00" header rendered next to a fixture
# against that same fixture's EventDate=9/28/2026 6:00:00 PM (identical
# clock time, no offset between them). So this fixed +2:00 isn't a guess
# about *whether* there's a timezone, just about *which* one it is; if
# it's ever wrong, the effect is a fixed start_time skew, not bad odds.
INTERBET_DISPLAY_TZ = timezone(timedelta(hours=2))


def _normalize_name(name: str) -> str:
    """Interbet renders the same participant's name inconsistently
    between the fixture header's EventDescription ("Bosnia-Herzegovina")
    and the odds button's ParticipantName ("BOSNIA HERZEGOVINA") --
    hyphens become spaces (and case differs) in one but not the other.
    Collapsing both to the same normal form is what lets a button's odds
    be matched back to the right side (home/away/draw) at all; without
    it, ~9% of live fixtures silently lost one or more outcomes."""
    return " ".join(name.replace("-", " ").split()).lower()


class InterbetScraper(BaseScraper):
    bookmaker_id = "interbet"

    def __init__(self, venue_id: int = ALL_LEAGUES_24H_VENUE_ID, sport_id: int = SOCCER_SPORT_ID):
        self.venue_id = venue_id
        self.sport_id = sport_id
        self._client = httpx.AsyncClient(timeout=15)

    async def fetch_raw_odds(self) -> dict:
        """GETs the HTML coupons partial and extracts each fixture's
        structured fields from its odds buttons' `data-url` query
        strings, returning a dict of already-flattened fixture records.
        Domain mapping onto OddsEvent happens separately in
        to_odds_events, same split as Betway ZA/WSB.
        """
        response = await self._client.get(
            INTERBET_COUPONS_URL,
            params={
                "VenueID": self.venue_id,
                "SportID": self.sport_id,
                "VenueDescription": "All Leagues 24H",
                "SportDescription": "Soccer",
                "Country": "International",
                "CouID": "INT",
                "EventGroup": "",
                "SportTypeID": self.sport_id,
                "Order": 5,
            },
        )
        response.raise_for_status()
        return {"fixtures": self._parse_fixtures(response.text)}

    @staticmethod
    def _parse_fixtures(html: str) -> list[dict]:
        """Parses the coupons partial into one dict per fixture (keyed by
        EventID), each holding whatever home/away/draw odds were found on
        its "Match Odds" (1X2) buttons.

        Scoped to `div.participant_match_odds` specifically -- Interbet
        renders handicap and double-chance odds for the same fixture in
        sibling `div.participant_handicap_odds` blocks right next to it,
        and (misleadingly) those buttons' own query strings also carry
        `BetType=Win`, so the div class, not any query param, is what
        actually distinguishes the 1X2 market from the others.

        Defensive per-fixture and per-button: a single malformed card
        must not lose every other fixture in the same ~100-event
        snapshot.
        """
        soup = BeautifulSoup(html, "html.parser")
        fixtures: dict[str, dict] = {}

        for button in soup.select("div.participant_match_odds button.btnOdds"):
            data_url = button.get("data-url")
            if not data_url:
                continue
            try:
                q = parse_qs(urlparse(data_url).query)
                event_id = q["EventID"][0]
                participant_name = q["ParticipantName"][0]
                odds = float(q["Odds"][0])
                event_date = q["EventDate"][0]
                event_group = q["EventGroup"][0]
                event_description = q["EventDescription"][0]
            except (KeyError, IndexError, ValueError) as exc:
                logger.warning("Skipping malformed odds button: %s", exc)
                continue

            try:
                home_name, away_name = (p.strip() for p in event_description.split(" v ", 1))
            except ValueError:
                logger.warning("Skipping fixture with unparseable EventDescription: %r", event_description)
                continue

            fixture = fixtures.setdefault(
                event_id,
                {
                    "event_id": event_id,
                    "league": event_group,
                    "home_team": home_name,
                    "away_team": away_name,
                    "event_date": event_date,
                    "home_odds": None,
                    "away_odds": None,
                    "draw_odds": None,
                },
            )

            name = _normalize_name(participant_name)
            if name == _normalize_name(home_name):
                fixture["home_odds"] = odds
            elif name == _normalize_name(away_name):
                fixture["away_odds"] = odds
            elif name == "draw":
                fixture["draw_odds"] = odds
            else:
                logger.warning("Unmatched participant %r for fixture %s v %s", participant_name, home_name, away_name)

        return list(fixtures.values())

    def to_odds_events(self, raw: dict) -> list[OddsEvent]:
        """Maps the already-flattened fixture dicts from fetch_raw_odds
        onto the universal OddsEvent schema. Moneyline (Match Odds/1X2)
        market only for now, matching Betway ZA and WSB's scope.

        Note event_id (the OddsEvent field) is left unset here -- that's
        the engine's job downstream (see the note on OddsEvent.event_id
        in scanner-schemas).
        """
        scraped_at = datetime.now(timezone.utc)
        odds_events: list[OddsEvent] = []

        for fixture in raw.get("fixtures", []):
            try:
                if fixture["home_odds"] is None or fixture["away_odds"] is None:
                    continue  # incomplete market, don't publish a partial price

                naive_start = datetime.strptime(fixture["event_date"], "%m/%d/%Y %I:%M:%S %p")
                start_time = naive_start.replace(tzinfo=INTERBET_DISPLAY_TZ).astimezone(timezone.utc)

                odds_events.append(
                    OddsEvent(
                        sport="soccer",
                        league=fixture["league"],
                        home_team=fixture["home_team"],
                        away_team=fixture["away_team"],
                        start_time=start_time,
                        bookmaker=self.bookmaker_id,
                        markets={
                            "moneyline": MarketOdds(
                                home_odds=fixture["home_odds"],
                                away_odds=fixture["away_odds"],
                                draw_odds=fixture["draw_odds"],
                            )
                        },
                        scraped_at=scraped_at,
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning("Skipping malformed fixture %s: %s", fixture.get("event_id"), exc)
                continue

        return odds_events

    async def poll(
        self, interval_seconds: float = DEFAULT_POLL_INTERVAL_SECONDS
    ) -> AsyncIterator[list[OddsEvent]]:
        """Fetches odds on a fixed interval and yields the parsed events
        each time. Same defensive shape as Betway ZA/WSB: a transient
        fetch failure (network blip, momentary 5xx, or an HTML error page
        served with a 200 status) is logged and the loop continues on
        schedule rather than crashing -- this loop is meant to run
        unattended for the life of the process.
        """
        while True:
            try:
                raw = await self.fetch_raw_odds()
                yield self.to_odds_events(raw)
            except httpx.HTTPError as exc:
                logger.warning("%s: poll fetch failed: %s", self.bookmaker_id, exc)
            except Exception:
                logger.exception("%s: unexpected error in poll cycle", self.bookmaker_id)

            await asyncio.sleep(interval_seconds)

    async def close(self) -> None:
        await self._client.aclose()
