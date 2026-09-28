"""Interbet adapter.

Reads Interbet's public, unauthenticated `FixedOdds/LoadCouponsPartial`
feed -- the same endpoint interbet.co.za's own sports pages call (via a
plain jQuery `$.ajax` GET, see `Scripts/sport.js`) to fill in the fixture
list for any visitor. This is a plain HTTP GET with no TLS impersonation,
no stealth browser, and no Cloudflare bypass: verified with a completely
bare `curl` (no User-Agent, no cookies, no Referer) returning the exact
same payload as a normal browser session, so none of that is needed
here, same as Betway ZA and WSB. This adapter polls the same endpoint
for five sports each cycle -- Soccer, Rugby (South Africa's #2 sport),
Cricket, Tennis and Basketball -- using different SportID/SportTypeID/
VenueID query values for each; all five were confirmed open with the
same bare-curl test, no new auth or anti-bot workaround needed for
Rugby, Cricket, Tennis or Basketball, it's genuinely the same feed.

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
not scraping prose -- no more fragile than reading JSON keys. This is
true for Soccer, Rugby, Cricket, Tennis and Basketball alike -- same
markup, same query-string shape, just a different SportType label and
Market name ("Match Odds" vs "Match Result") inside it, neither of which
this parser even reads.

Tennis's own quirk (see `_participant_matches_team` below): Interbet
renders a singles player's ParticipantName as "SURNAME, First" -- the
reverse order of, and sometimes with the given name abbreviated to just
an initial compared to, the full "First Surname" used in the fixture's
own EventDescription -- so it needs its own name-matching rule, not just
the hyphen/case folding `_normalize_name` already does for team sports.
Basketball has no such quirk -- verified against a live "Coming up"
coupon (93 fixtures across 26 competitions worldwide): ParticipantName
is always the team's name (case-folded, hyphens intact the same way
Soccer/Rugby/Cricket render them, e.g. "ETOILE CHARLEVILLE-MEZIERES" for
EventDescription's "Etoile Charleville-Mezieres"), no reordering, so it
reuses the plain `_normalize_name` equality check unchanged.

Endpoint discovered by ordinary browsing (curl against the pages
interbet.co.za/Prematch/Sport/Soccer/*, .../Prematch/Sport/Rugby/*,
.../Prematch/Sport/Cricket/*, .../Prematch/Sport/Tennis/* and
.../Prematch/Sport/Basketball/* themselves link to) and inspecting the
`data-url` the page's own sport.js issues via `$.ajax` GET.
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
from typing import NamedTuple
from urllib.parse import parse_qs, urlparse

import httpx
from bs4 import BeautifulSoup
from ingestion.base_scraper import BaseScraper
from schemas import MarketOdds, OddsEvent

logger = logging.getLogger(__name__)

INTERBET_COUPONS_URL = "https://interbet.co.za/FixedOdds/LoadCouponsPartial"


class SportConfig(NamedTuple):
    """One sport this adapter polls each cycle: the `sport` value it maps
    onto OddsEvent.sport, plus everything LoadCouponsPartial needs on its
    query string to return that sport's single broadest coupon in one
    call. See the SPORTS tuple below for how each field was chosen per
    sport -- Soccer, Rugby, Cricket, Tennis and Basketball don't share the
    same VenueID or even the same notion of "broadest", so this is
    deliberately not one shared constant with a swapped-in SportID.
    """

    sport: str
    sport_id: int
    venue_id: int
    sport_description: str
    venue_description: str
    country: str
    cou_id: str
    order: int


# SportID=48 is Interbet's sport-level id for Soccer. VenueID=65 ("All
# Leagues 24H") is the broadest single-call coupon: every soccer fixture
# (any competition) kicking off in the next 24 hours, in one response --
# discovered from the "All Leagues 24H" tab on /Prematch/Sport/Soccer
# (as opposed to e.g. VenueID=60 "Starting in 4 hours", which is
# narrower, or the various single-competition venues).
SOCCER_SPORT_ID = 48
ALL_LEAGUES_24H_VENUE_ID = 65

# SportID=50 is Interbet's sport-level id for Rugby -- discovered the same
# way as Soccer's SportID=48: rendering /Prematch/Sport/Rugby and reading
# the SportID/SportTypeID Interbet's own default coupons-container
# data-url embeds. VenueID=53 ("Coming up") is the venue to use, but for
# a different reason than Soccer's VenueID=65: Soccer's nav bar on
# /Prematch/Sport/Soccer has a dozen-plus tabs (Starting in 4 hours / UEFA
# Nations League / ... / All Leagues 24H / Europe / ...), and "All Leagues
# 24H" is deliberately the broadest of those. Rugby's nav bar on
# /Prematch/Sport/Rugby renders exactly one tab -- "Coming up" -- full
# stop; there is no separate "All Leagues 24H" (or any other) venue to
# choose instead for Rugby, and VenueID=65/SportID=50 (guessing Soccer's
# venue would carry over) returns a genuinely empty coupon. VenueID=53 is
# simultaneously the broadest and the only coupon Interbet exposes for
# this sport -- confirmed by fetching it and finding fixtures spanning
# several days out, not clipped to a 24h window the way Soccer's other,
# narrower venues are.
RUGBY_SPORT_ID = 50
RUGBY_COMING_UP_VENUE_ID = 53

# SportID=59 is Interbet's sport-level id for Cricket -- discovered the
# same way as Soccer and Rugby: rendering /Prematch/Sport/Cricket and
# reading the SportID/SportTypeID its default coupons-container data-url
# embeds. VenueID=29 ("Coming up") is the venue to use, for the same
# reason as Rugby's VenueID=53: Cricket's nav bar on
# /Prematch/Sport/Cricket renders exactly one tab -- "Coming up" -- same
# as Rugby, no separate "All Leagues 24H" to choose instead, and no
# other venue exists to compare it against. Confirmed populated with a
# live fetch: 14 fixtures across 8 competitions (CSA T20 Challenge,
# Test International Friendlies, LG ICC ODI Championship, Asia Games,
# and others), spanning international, women's and domestic South
# African cricket, not clipped to a narrow window.
CRICKET_SPORT_ID = 59
CRICKET_COMING_UP_VENUE_ID = 29

# SportID=55 is Interbet's sport-level id for Tennis -- discovered the
# same way as Soccer, Rugby and Cricket: rendering /Prematch/Sport/Tennis
# and reading the SportID/SportTypeID its default coupons-container
# data-url embeds (VenueID=6, distinct from every other sport's "Coming
# up" VenueID -- Rugby's is 53, Cricket's is 29 -- confirming this isn't
# shared across sports and really was read off Tennis's own page, not
# assumed). Tennis's nav bar on /Prematch/Sport/Tennis renders exactly
# one tab -- "Coming up" -- same single-venue situation as Rugby and
# Cricket, no separate "All Leagues 24H" to choose instead. Confirmed
# populated with a live fetch: over 260 fixtures (singles and doubles)
# across dozens of ATP/WTA/Challenger/ITF competitions worldwide, not
# clipped to a narrow window.
TENNIS_SPORT_ID = 55
TENNIS_COMING_UP_VENUE_ID = 6

# SportID=76 is Interbet's sport-level id for Basketball -- discovered the
# same way as Soccer, Rugby, Cricket and Tennis: rendering
# /Prematch/Sport/Basketball and reading the SportID/SportTypeID its
# default coupons-container data-url embeds (VenueID=56, distinct from
# every other sport's "Coming up" VenueID -- Rugby's is 53, Cricket's is
# 29, Tennis's is 6 -- confirming this isn't shared across sports and
# really was read off Basketball's own page, not assumed). Basketball's
# nav bar on /Prematch/Sport/Basketball renders exactly one tab -- "Coming
# up" -- same single-venue situation as Rugby, Cricket and Tennis, no
# separate "All Leagues 24H" to choose instead. Confirmed populated with a
# live fetch: 93 fixtures across 26 competitions worldwide (NBL, EuroCup,
# various domestic leagues), spanning at least two days out, not clipped
# to a narrow window.
BASKETBALL_SPORT_ID = 76
BASKETBALL_COMING_UP_VENUE_ID = 56

# The exact query values captured from each sport's own default
# coupons-container data-url (see comments above) -- Rugby's, Cricket's,
# Tennis's and Basketball's Country and CouID are genuinely empty strings
# there, not a placeholder, unlike Soccer's "International"/"INT".
SPORTS: tuple[SportConfig, ...] = (
    SportConfig(
        sport="soccer",
        sport_id=SOCCER_SPORT_ID,
        venue_id=ALL_LEAGUES_24H_VENUE_ID,
        sport_description="Soccer",
        venue_description="All Leagues 24H",
        country="International",
        cou_id="INT",
        order=5,
    ),
    SportConfig(
        sport="rugby",
        sport_id=RUGBY_SPORT_ID,
        venue_id=RUGBY_COMING_UP_VENUE_ID,
        sport_description="Rugby",
        venue_description="Coming up",
        country="",
        cou_id="",
        order=1,
    ),
    SportConfig(
        sport="cricket",
        sport_id=CRICKET_SPORT_ID,
        venue_id=CRICKET_COMING_UP_VENUE_ID,
        sport_description="Cricket",
        venue_description="Coming up",
        country="",
        cou_id="",
        order=1,
    ),
    SportConfig(
        sport="tennis",
        sport_id=TENNIS_SPORT_ID,
        venue_id=TENNIS_COMING_UP_VENUE_ID,
        sport_description="Tennis",
        venue_description="Coming up",
        country="",
        cou_id="",
        order=1,
    ),
    SportConfig(
        sport="basketball",
        sport_id=BASKETBALL_SPORT_ID,
        venue_id=BASKETBALL_COMING_UP_VENUE_ID,
        sport_description="Basketball",
        venue_description="Coming up",
        country="",
        cou_id="",
        order=1,
    ),
)

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
    it, ~9% of live fixtures silently lost one or more outcomes.

    Reused as-is for Rugby, Cricket and Basketball fixtures -- nothing
    about it is soccer-specific, and Interbet renders their
    EventDescription/ParticipantName pairs with the exact same
    casing/hyphenation inconsistency (provincial/union names, hyphenated
    or multi-word team names for Cricket, and hyphenated club names for
    Basketball, e.g. "ETOILE CHARLEVILLE-MEZIERES" vs "Etoile
    Charleville-Mezieres", are just as likely to trip this up as a
    country name is), so the same collapsing is needed there too.

    Reused for Tennis too, but not on its own -- see
    `_participant_matches_team` below, which layers Tennis's own
    "Surname, First" ParticipantName ordering on top of this same
    case/hyphen folding rather than replacing it."""
    return " ".join(name.replace("-", " ").split()).lower()


def _participant_matches_team(participant_name: str, team_name: str, sport: str) -> bool:
    """Whether an odds button's ParticipantName refers to the given
    home/away team or player.

    Soccer, Rugby, Cricket and Basketball: ParticipantName and the team
    name pulled from EventDescription are the same string modulo case and
    hyphenation (see `_normalize_name`) -- a straight equality check
    after folding both, as this adapter has always done. Confirmed for
    Basketball against a live "Coming up" coupon (93 fixtures, 26
    competitions): no player-name reordering quirk like Tennis's, team
    names come through straightforwardly, including hyphenated ones like
    "Etoile Charleville-Mezieres".

    Tennis is different: Interbet renders a singles player's
    ParticipantName as "SURNAME, First" -- reversed from, and often with
    the given name abbreviated down to a bare initial compared to, the
    full "First Surname" order EventDescription uses for the same player
    (confirmed against Interbet's own live "Coming up" Tennis coupon,
    e.g. ParticipantName "STORCH, S" for a player EventDescription spells
    out in full as "Stefan Storch"). Reversing the comma therefore isn't
    reliable -- "S" will never equal "Stefan" -- but the surname (the
    part before the comma, which Interbet always renders in full, hyphen
    and all, e.g. "BRUCE-SMITH, JACK") is: this matches by checking that
    the team name's normalized words *end with* the participant's
    normalized surname word(s), independent of whether the given name
    agrees or was abbreviated at all.

    Some Tennis fixtures buck even that pattern and render ParticipantName
    with no comma at all, already in the same "First Surname" order
    EventDescription uses (e.g. "PETR BAR BIRYUKOV", observed live
    alongside a same-fixture opponent rendered the usual "SURNAME, First"
    way) -- those fall through to the plain equality check below, which
    already handles them correctly with no special casing needed.

    Doubles fixtures are a known, deliberately out-of-scope gap: Interbet
    joins both players' "Surname, First" names with a "/" in
    ParticipantName (e.g. "DETIUC, ANASTASIA/KHROMACHEVA, IRINA"), which
    doesn't reduce to a single trailing surname the way singles does.
    Neither the home nor away check below matches that shape, so a
    doubles fixture's buttons are logged as unmatched and it is silently
    dropped by `to_odds_events`'s existing "both prices must be present"
    check -- never mismatched to the wrong team, just not published.
    Widening this to also parse doubles pairs was left out as unwarranted
    complexity for a first cut; nothing here would need to change to add
    it later, since this is purely a matching predicate.
    """
    if sport == "tennis" and "," in participant_name:
        surname_words = _normalize_name(participant_name.split(",", 1)[0]).split()
        team_words = _normalize_name(team_name).split()
        return bool(surname_words) and team_words[-len(surname_words):] == surname_words
    return _normalize_name(participant_name) == _normalize_name(team_name)


class InterbetScraper(BaseScraper):
    bookmaker_id = "interbet"

    def __init__(self, sports: tuple[SportConfig, ...] = SPORTS):
        self.sports = sports
        self._client = httpx.AsyncClient(timeout=15)

    async def fetch_raw_odds(self) -> dict:
        """GETs the HTML coupons partial for every sport in self.sports
        (Soccer, Rugby, Cricket, Tennis and Basketball by default) and
        extracts each fixture's structured fields from its odds buttons'
        `data-url` query strings, returning one combined dict of
        already-flattened fixture records, each tagged with which sport
        it came from.
        Domain mapping onto OddsEvent happens separately in
        to_odds_events, same split as Betway ZA/WSB.

        The configured sports are fetched sequentially and treated as
        one atomic unit for this cycle, same as when this method fetched
        a single URL: a transient failure fetching any one of them
        raises (raise_for_status/httpx's own connection errors) and
        aborts the whole cycle rather than trying to salvage a partial
        batch missing one sport -- poll() below already logs that and
        retries cleanly next cycle, so there's no need for separate
        per-sport failure handling here.
        """
        fixtures: list[dict] = []
        for cfg in self.sports:
            response = await self._client.get(
                INTERBET_COUPONS_URL,
                params={
                    "VenueID": cfg.venue_id,
                    "SportID": cfg.sport_id,
                    "VenueDescription": cfg.venue_description,
                    "SportDescription": cfg.sport_description,
                    "Country": cfg.country,
                    "CouID": cfg.cou_id,
                    "EventGroup": "",
                    "SportTypeID": cfg.sport_id,
                    "Order": cfg.order,
                },
            )
            response.raise_for_status()
            fixtures.extend(self._parse_fixtures(response.text, sport=cfg.sport))
        return {"fixtures": fixtures}

    @staticmethod
    def _parse_fixtures(html: str, sport: str = "soccer") -> list[dict]:
        """Parses one sport's coupons partial into one dict per fixture
        (keyed by EventID), each holding whatever home/away/draw odds
        were found on its "Match Odds"/"Match Result" (1X2) buttons, and
        tagged with `sport` (the value fetch_raw_odds calls this with --
        "soccer", "rugby", "cricket", "tennis" or "basketball" --
        defaulted here to "soccer" so every existing call site and test
        that predates Rugby/Cricket/Tennis/Basketball support, which only
        ever passed one positional `html` argument, keeps working
        unchanged).

        Scoped to `div.participant_match_odds` specifically -- Interbet
        renders handicap and double-chance odds for the same fixture in
        sibling `div.participant_handicap_odds` blocks right next to it,
        and (misleadingly) those buttons' own query strings also carry
        `BetType=Win`, so the div class, not any query param, is what
        actually distinguishes the 1X2 market from the others. This is
        true for Rugby too -- its handicap buttons carry BetType=Win and
        Market=Handicap right alongside Match Result buttons the same
        way, and some Rugby fixtures currently have an empty (button-less)
        `participant_match_odds` div with only a handicap price posted --
        those naturally produce zero buttons for this selector to find,
        so no fixture entry is created for them at all, same as a
        fixture BeautifulSoup finds no buttons for today would already be
        skipped. Cricket's live "Coming up" coupon currently has no
        handicap blocks at all, but the same div-class scoping still
        applies -- it's what protects this parser if/when Interbet adds
        one, not something specific to Rugby's current markup.

        Rugby's market shape also genuinely varies fixture to fixture --
        some competitions post a Draw price (three-way, same as Soccer's
        1X2) and some don't (two-way, ordinary win/loss); nothing in this
        method assumes a Draw exists (draw_odds simply stays at its
        None default when there's no "DRAW" participant button), so
        both shapes come through faithfully without forcing a two-way
        Rugby market into a three-way struct or vice versa. Cricket's
        "Match Result" market is genuinely two-way in every fixture seen
        live so far -- 14 fixtures checked across 8 competitions,
        including ones labelled "Test International Friendlies" (e.g.
        India A v Australia A), all posted exactly 2 buttons and no DRAW
        participant, unlike a traditional Test match's win/lose/draw
        result. Interbet may simply not be offering a draw price for
        Cricket at all right now (or these specific "Test"-labelled
        fixtures may not be genuine 5-day Tests), but nothing here
        assumes either way -- the same Draw-optional handling used for
        Rugby applies unchanged, so a three-way Cricket fixture (if
        Interbet ever posts one) would come through with draw_odds set,
        not get coerced into a two-way struct. Tennis's "Match Result"
        market is genuinely always two-way (no draw is possible in
        tennis, so Interbet never renders a DRAW button for it at all --
        confirmed against over 260 live singles and doubles fixtures);
        draw_odds simply stays None for every Tennis fixture, the same
        optional-field path Rugby/Cricket already exercise, not a
        separate code path. Basketball's "Match Result" market is
        likewise genuinely always two-way (a basketball game always
        resolves to a winner, no draw is possible) -- confirmed against a
        live "Coming up" coupon where every one of 93 fixtures across 26
        competitions posted exactly 2 buttons and no DRAW participant;
        draw_odds simply stays None for every Basketball fixture too, the
        same optional-field path, not a separate code path.

        Participant matching (which button's odds go to home_odds vs
        away_odds) is delegated to `_participant_matches_team` rather
        than a bare `_normalize_name` equality check, because Tennis
        renders ParticipantName in a different order ("Surname, First",
        sometimes with the given name abbreviated) than EventDescription
        does ("First Surname") -- see that function's docstring for the
        full explanation, including why a doubles fixture's participants
        deliberately fail to match either side and get dropped rather
        than mismatched.

        Defensive per-fixture and per-button: a single malformed card
        must not lose every other fixture in the same snapshot.
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
                    "sport": sport,
                    "league": event_group,
                    "home_team": home_name,
                    "away_team": away_name,
                    "event_date": event_date,
                    "home_odds": None,
                    "away_odds": None,
                    "draw_odds": None,
                },
            )

            if _participant_matches_team(participant_name, home_name, sport):
                fixture["home_odds"] = odds
            elif _participant_matches_team(participant_name, away_name, sport):
                fixture["away_odds"] = odds
            elif _normalize_name(participant_name) == "draw":
                fixture["draw_odds"] = odds
            else:
                logger.warning("Unmatched participant %r for fixture %s v %s", participant_name, home_name, away_name)

        return list(fixtures.values())

    def to_odds_events(self, raw: dict) -> list[OddsEvent]:
        """Maps the already-flattened fixture dicts from fetch_raw_odds
        onto the universal OddsEvent schema. Moneyline (Match Odds/Match
        Result / 1X2) market only for now, matching Betway ZA and WSB's
        scope. `draw_odds` is left None on MarketOdds for a fixture whose
        market never had a Draw price (a real, valid shape for some Rugby
        competitions, for every Cricket fixture observed live so far, and
        for every Tennis or Basketball fixture -- a draw is not a possible
        result in either sport at all -- not a missing-data bug) --
        MarketOdds already models it as optional for exactly this reason.

        `fixture.get("sport", "soccer")` rather than a bare "soccer"
        literal: raw fixture dicts built by _parse_fixtures are tagged
        with their sport (see that method), but this defaults to
        "soccer" for any raw dict that predates that tagging -- keeping
        this method's behavior unchanged for every existing caller/test
        that hand-builds a fixture dict without a "sport" key.

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
                        sport=fixture.get("sport", "soccer"),
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
