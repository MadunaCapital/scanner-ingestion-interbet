import pytest

from interbet import InterbetScraper

# Real HTML captured from a live, plain GET to Interbet's public
# FixedOdds/LoadCouponsPartial endpoint (see scraper.py's docstring),
# trimmed to two fixtures' worth of markup. Field values (team names,
# EventIDs, odds, EventDate) are unchanged from the real response; only
# unrelated markup (flags, "More Bets" links, page chrome) is stripped.
# The second fixture also keeps its real `participant_handicap_odds`
# sibling block, to exercise the "must not leak into moneyline" case.
SAMPLE_HTML = """
<div class="sport">
  <div class="sports_card">
    <div class="sports_card_body">
      <div class="sports_card_body_fixtures">
        <div class="sport_fixture">
          <div class="sport_fixture_title_group">
            <span class="sport_fixture_title_text">28 Sep 2026 - 18:00</span>
            <span class="sport_fixture_title_text">Central African Republic v Burkina Faso</span>
          </div>
          <div class="sport_fixture_participant_odds">
            <div id="Event-91270296" class="participant_match_odds">
              <button type="button" data-url="/FixedOdds/AddBet?EventDate=9%2f28%2f2026+6%3a00%3a00+PM&amp;EventParticipantID=344267637&amp;ParticipantName=CENTRAL+AFRICAN+REPUBLIC&amp;EventID=91270296&amp;VenueID=3156666&amp;BetType=Win&amp;Market=Match+odds&amp;SportType=Soccer&amp;ImgId=48&amp;EventGroup=African+Cup+of+Nations+Qualification&amp;EventDescription=Central+African+Republic+v+Burkina+Faso&amp;AllowMultiple=True&amp;Odds=11&amp;OddsDisplay=11&amp;InRunning=N&amp;InRunningDelay=0" class="btnOdds add_bet_link match_odds" title="Bet on CENTRAL AFRICAN REPUBLIC" rel="nofollow noopener">11</button>
              <button type="button" data-url="/FixedOdds/AddBet?EventDate=9%2f28%2f2026+6%3a00%3a00+PM&amp;EventParticipantID=344267635&amp;ParticipantName=BURKINA+FASO&amp;EventID=91270296&amp;VenueID=3156666&amp;BetType=Win&amp;Market=Match+Odds&amp;SportType=Soccer&amp;ImgId=48&amp;EventGroup=African+Cup+of+Nations+Qualification&amp;EventDescription=Central+African+Republic+v+Burkina+Faso&amp;AllowMultiple=True&amp;Odds=1.3&amp;OddsDisplay=1.3&amp;InRunning=N&amp;InRunningDelay=0" class="btnOdds add_bet_link match_odds" title="Bet on BURKINA FASO" rel="nofollow noopener">1.3</button>
              <button type="button" data-url="/FixedOdds/AddBet?EventDate=9%2f28%2f2026+6%3a00%3a00+PM&amp;EventParticipantID=344267636&amp;ParticipantName=DRAW&amp;EventID=91270296&amp;VenueID=3156666&amp;BetType=Win&amp;Market=Match+Odds&amp;SportType=Soccer&amp;ImgId=48&amp;EventGroup=African+Cup+of+Nations+Qualification&amp;EventDescription=Central+African+Republic+v+Burkina+Faso&amp;AllowMultiple=True&amp;Odds=5&amp;OddsDisplay=5&amp;InRunning=N&amp;InRunningDelay=0" class="btnOdds add_bet_link match_odds" title="Bet on DRAW" rel="nofollow noopener">5</button>
            </div>
          </div>
        </div>
        <div class="sport_fixture">
          <div class="sport_fixture_title_group">
            <span class="sport_fixture_title_text">28 Sep 2026 - 18:00</span>
            <span class="sport_fixture_title_text">Equatorial Guinea v Sierra Leone</span>
          </div>
          <div class="sport_fixture_participant_odds">
            <div id="Event-91290795" class="participant_match_odds">
              <button type="button" data-url="/FixedOdds/AddBet?EventDate=9%2f28%2f2026+6%3a00%3a00+PM&amp;EventParticipantID=344334126&amp;ParticipantName=EQUATORIAL+GUINEA&amp;EventID=91290795&amp;VenueID=3156666&amp;BetType=Win&amp;Market=Match+odds&amp;SportType=Soccer&amp;ImgId=48&amp;EventGroup=African+Cup+of+Nations+Qualification&amp;EventDescription=Equatorial+Guinea+v+Sierra+Leone&amp;AllowMultiple=True&amp;Odds=2.25&amp;OddsDisplay=2.25&amp;InRunning=N&amp;InRunningDelay=0" class="btnOdds add_bet_link match_odds" title="Bet on EQUATORIAL GUINEA" rel="nofollow noopener">2.25</button>
              <button type="button" data-url="/FixedOdds/AddBet?EventDate=9%2f28%2f2026+6%3a00%3a00+PM&amp;EventParticipantID=344334124&amp;ParticipantName=SIERRA+LEONE&amp;EventID=91290795&amp;VenueID=3156666&amp;BetType=Win&amp;Market=Match+Odds&amp;SportType=Soccer&amp;ImgId=48&amp;EventGroup=African+Cup+of+Nations+Qualification&amp;EventDescription=Equatorial+Guinea+v+Sierra+Leone&amp;AllowMultiple=True&amp;Odds=3.5&amp;OddsDisplay=3.5&amp;InRunning=N&amp;InRunningDelay=0" class="btnOdds add_bet_link match_odds" title="Bet on SIERRA LEONE" rel="nofollow noopener">3.5</button>
              <button type="button" data-url="/FixedOdds/AddBet?EventDate=9%2f28%2f2026+6%3a00%3a00+PM&amp;EventParticipantID=344334125&amp;ParticipantName=DRAW&amp;EventID=91290795&amp;VenueID=3156666&amp;BetType=Win&amp;Market=Match+Odds&amp;SportType=Soccer&amp;ImgId=48&amp;EventGroup=African+Cup+of+Nations+Qualification&amp;EventDescription=Equatorial+Guinea+v+Sierra+Leone&amp;AllowMultiple=True&amp;Odds=3&amp;OddsDisplay=3&amp;InRunning=N&amp;InRunningDelay=0" class="btnOdds add_bet_link match_odds" title="Bet on DRAW" rel="nofollow noopener">3</button>
            </div>
            <div id="Event-91290808" class="participant_handicap_odds">
              <div class="add_bet_link_grouped">
                <span class="handicap_value">(H+A)</span>
                <button type="button" data-url="/FixedOdds/AddBet?EventDate=9%2f28%2f2026+6%3a00%3a00+PM&amp;EventParticipantID=999999999&amp;ParticipantName=EQUATORIAL+GUINEA+OR+SIERRA+LEONE&amp;EventID=91290808&amp;VenueID=3156666&amp;BetType=Win&amp;Market=Double+Chance&amp;SportType=Soccer&amp;ImgId=48&amp;EventGroup=African+Cup+of+Nations+Qualification&amp;EventDescription=Equatorial+Guinea+v+Sierra+Leone&amp;AllowMultiple=True&amp;Odds=1.4&amp;OddsDisplay=1.4" class="btnOdds add_bet_link handicap_odds" title="Bet on EQUATORIAL GUINEA OR SIERRA LEONE" rel="nofollow noopener">1.4</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
"""


def test_parse_fixtures_extracts_teams_league_date_and_odds():
    fixtures = InterbetScraper._parse_fixtures(SAMPLE_HTML)

    assert len(fixtures) == 2
    caf = next(f for f in fixtures if f["home_team"] == "Central African Republic")
    assert caf["away_team"] == "Burkina Faso"
    assert caf["league"] == "African Cup of Nations Qualification"
    assert caf["event_date"] == "9/28/2026 6:00:00 PM"
    assert caf["home_odds"] == 11
    assert caf["away_odds"] == 1.3
    assert caf["draw_odds"] == 5


def test_parse_fixtures_ignores_handicap_and_double_chance_odds():
    """The handicap/double-chance buttons for the second fixture also
    carry BetType=Win in their own data-url, so the div-class scope (not
    the BetType field) must be what keeps them out of the 1X2 market."""
    fixtures = InterbetScraper._parse_fixtures(SAMPLE_HTML)

    egsl = next(f for f in fixtures if f["home_team"] == "Equatorial Guinea")
    assert egsl["home_odds"] == 2.25
    assert egsl["away_odds"] == 3.5
    assert egsl["draw_odds"] == 3
    # None of the handicap/double-chance odds (e.g. 1.4) leaked in.
    assert 1.4 not in (egsl["home_odds"], egsl["away_odds"], egsl["draw_odds"])


def test_to_odds_events_maps_parsed_fixtures_onto_the_universal_schema():
    scraper = InterbetScraper()
    raw = {"fixtures": InterbetScraper._parse_fixtures(SAMPLE_HTML)}

    events = scraper.to_odds_events(raw)

    assert len(events) == 2
    event = next(e for e in events if e.home_team == "Central African Republic")
    assert event.away_team == "Burkina Faso"
    assert event.sport == "soccer"
    assert event.league == "African Cup of Nations Qualification"
    assert event.bookmaker == "interbet"
    assert event.event_id is None  # left for the engine to compute
    assert event.markets["moneyline"].home_odds == 11
    assert event.markets["moneyline"].away_odds == 1.3
    assert event.markets["moneyline"].draw_odds == 5
    # 28 Sep 2026 18:00 SAST (UTC+2) -> 16:00 UTC.
    assert event.start_time.isoformat() == "2026-09-28T16:00:00+00:00"


def test_to_odds_events_skips_incomplete_price_data():
    """If a price is missing for home or away, don't publish a
    partial/misleading market."""
    raw = {
        "fixtures": [
            {
                "event_id": "1",
                "league": "Test League",
                "home_team": "Home",
                "away_team": "Away",
                "event_date": "9/28/2026 6:00:00 PM",
                "home_odds": 1.5,
                "away_odds": None,  # missing
                "draw_odds": 3.0,
            }
        ]
    }
    scraper = InterbetScraper()

    assert scraper.to_odds_events(raw) == []


def test_to_odds_events_skips_a_malformed_event_date_without_crashing_the_batch():
    raw = {
        "fixtures": [
            {
                "event_id": "1",
                "league": "Test League",
                "home_team": "Home",
                "away_team": "Away",
                "event_date": "not-a-date",
                "home_odds": 1.5,
                "away_odds": 2.5,
                "draw_odds": 3.0,
            },
            {
                "event_id": "2",
                "league": "Test League",
                "home_team": "Good",
                "away_team": "Fixture",
                "event_date": "9/28/2026 6:00:00 PM",
                "home_odds": 1.9,
                "away_odds": 1.9,
                "draw_odds": 3.2,
            },
        ]
    }
    scraper = InterbetScraper()

    events = scraper.to_odds_events(raw)

    # The well-formed fixture still comes through; the malformed one is
    # skipped rather than raising and losing the whole batch.
    assert len(events) == 1
    assert events[0].home_team == "Good"


def test_parse_fixtures_skips_a_button_with_an_unparseable_event_description():
    html = """
    <div id="Event-1" class="participant_match_odds">
      <button type="button" data-url="/FixedOdds/AddBet?EventDate=9%2f28%2f2026+6%3a00%3a00+PM&amp;EventParticipantID=1&amp;ParticipantName=HOME&amp;EventID=1&amp;BetType=Win&amp;Market=Match+Odds&amp;EventGroup=Test&amp;EventDescription=NoVSeparatorHere&amp;Odds=2&amp;OddsDisplay=2" class="btnOdds" title="Bet on HOME">2</button>
    </div>
    """

    assert InterbetScraper._parse_fixtures(html) == []


def test_parse_fixtures_skips_a_button_missing_a_required_field():
    html = """
    <div id="Event-1" class="participant_match_odds">
      <button type="button" data-url="/FixedOdds/AddBet?EventParticipantID=1&amp;ParticipantName=HOME&amp;EventID=1&amp;BetType=Win&amp;Market=Match+Odds&amp;EventGroup=Test&amp;EventDescription=Home+v+Away&amp;Odds=2&amp;OddsDisplay=2" class="btnOdds" title="Bet on HOME">2</button>
    </div>
    """
    # EventDate is missing entirely.

    assert InterbetScraper._parse_fixtures(html) == []


@pytest.mark.asyncio
async def test_poll_yields_events_on_a_fixed_interval(monkeypatch):
    scraper = InterbetScraper()

    async def fake_fetch_raw_odds():
        return {"fixtures": InterbetScraper._parse_fixtures(SAMPLE_HTML)}

    monkeypatch.setattr(scraper, "fetch_raw_odds", fake_fetch_raw_odds)

    results = []
    async for events in scraper.poll(interval_seconds=0.01):
        results.append(events)
        if len(results) == 3:
            break

    assert len(results) == 3
    assert all(len(batch) == 2 for batch in results)


@pytest.mark.asyncio
async def test_poll_continues_past_a_transient_fetch_failure(monkeypatch):
    import httpx

    scraper = InterbetScraper()
    call_count = 0

    async def flaky_fetch_raw_odds():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise httpx.ConnectError("simulated network blip")
        return {"fixtures": InterbetScraper._parse_fixtures(SAMPLE_HTML)}

    monkeypatch.setattr(scraper, "fetch_raw_odds", flaky_fetch_raw_odds)

    results = []
    async for events in scraper.poll(interval_seconds=0.01):
        results.append(events)
        break  # first successful yield should be the second call, after the failure

    assert call_count == 2
    assert len(results) == 1
    assert len(results[0]) == 2
