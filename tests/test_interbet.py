import pytest

from interbet import InterbetScraper
from interbet.scraper import SportConfig

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

# Real HTML captured from a live, plain GET to Interbet's public
# FixedOdds/LoadCouponsPartial with SportID=50/SportTypeID=50 (Rugby) and
# VenueID=53 ("Coming up" -- Rugby's only coupon venue, see scraper.py's
# RUGBY_COMING_UP_VENUE_ID comment), trimmed of unrelated markup the same
# way SAMPLE_HTML is. All three fixtures are real, unmodified field
# values from the same New Zealand domestic competition:
#   - Otago v Auckland and Southland v Northland both post a three-way
#     (home/away/Draw) Match Result market, same shape as Soccer's 1X2 --
#     proving Rugby fixtures that do carry a Draw price parse the same
#     way Soccer's do.
#   - Taranaki v Wellington's `participant_match_odds` div is present but
#     genuinely empty (no buttons at all -- only its sibling
#     `participant_handicap_odds` block has prices), a real, currently-
#     occurring case of a posted fixture with no moneyline price yet --
#     proving it's silently skipped rather than crashing or producing a
#     spurious record.
RUGBY_SAMPLE_HTML = """
<div class="sport">
  <div class="sports_card">
    <div class="sports_card_body">
      <div class="sports_card_body_fixtures">
        <div class="sport_fixture">
          <div class="sport_fixture_title_group">
            <span class="sport_fixture_title_text">01 Oct 2026 - 08:10</span>
            <span class="sport_fixture_title_text">Otago v Auckland</span>
          </div>
          <div class="sport_fixture_participant_odds">
            <div id="Event-91336488" class="participant_match_odds">
              <button type="button" data-url="/FixedOdds/AddBet?EventDate=10%2f1%2f2026+8%3a10%3a00+AM&amp;EventParticipantID=344472940&amp;ParticipantName=AUCKLAND&amp;EventID=91336488&amp;VenueID=4024990&amp;BetType=Win&amp;Market=Match+Result&amp;SportType=Rugby&amp;ImgId=50&amp;EventGroup=Bunnings+Warehouse+Cup&amp;EventDescription=Otago+v+Auckland&amp;AllowMultiple=True&amp;Odds=5.5&amp;OddsDisplay=5.5&amp;InRunning=N&amp;InRunningDelay=0" class="btnOdds add_bet_link match_odds" decimalvalue="5.5" title="Bet on AUCKLAND" rel="nofollow noopener">5.5</button>
              <button type="button" data-url="/FixedOdds/AddBet?EventDate=10%2f1%2f2026+8%3a10%3a00+AM&amp;EventParticipantID=344472942&amp;ParticipantName=OTAGO&amp;EventID=91336488&amp;VenueID=4024990&amp;BetType=Win&amp;Market=Match+Result&amp;SportType=Rugby&amp;ImgId=50&amp;EventGroup=Bunnings+Warehouse+Cup&amp;EventDescription=Otago+v+Auckland&amp;AllowMultiple=True&amp;Odds=1.16&amp;OddsDisplay=1.16&amp;InRunning=N&amp;InRunningDelay=0" class="btnOdds add_bet_link match_odds" decimalvalue="1.16" title="Bet on OTAGO" rel="nofollow noopener">1.16</button>
              <button type="button" data-url="/FixedOdds/AddBet?EventDate=10%2f1%2f2026+8%3a10%3a00+AM&amp;EventParticipantID=344472941&amp;ParticipantName=DRAW&amp;EventID=91336488&amp;VenueID=4024990&amp;BetType=Win&amp;Market=Match+Result&amp;SportType=Rugby&amp;ImgId=50&amp;EventGroup=Bunnings+Warehouse+Cup&amp;EventDescription=Otago+v+Auckland&amp;AllowMultiple=True&amp;Odds=34&amp;OddsDisplay=34&amp;InRunning=N&amp;InRunningDelay=0" class="btnOdds add_bet_link match_odds" decimalvalue="34" title="Bet on DRAW" rel="nofollow noopener">34</button>
            </div>
            <div id="Event-91336488" class="participant_handicap_odds">
              <div class="add_bet_link_grouped">
                <span class="handicap_value">(+14.50)</span>
                <button type="button" data-url="/FixedOdds/AddBet?EventDate=10%2f1%2f2026+8%3a10%3a00+AM&amp;EventParticipantID=344497496&amp;ParticipantName=AUCKLAND+%2b14.50&amp;EventID=91344221&amp;VenueID=4024990&amp;BetType=Win&amp;Market=Handicap&amp;SportType=Rugby&amp;ImgId=50&amp;EventGroup=Bunnings+Warehouse+Cup&amp;EventDescription=Otago+v+Auckland&amp;AllowMultiple=True&amp;Odds=1.95&amp;OddsDisplay=1.95&amp;InRunning=N&amp;InRunningDelay=0" class="btnOdds add_bet_link handicap_odds" decimalvalue="1.95" title="Bet on AUCKLAND +14.50" rel="nofollow noopener">1.95</button>
              </div>
            </div>
          </div>
        </div>
        <div class="sport_fixture">
          <div class="sport_fixture_title_group">
            <span class="sport_fixture_title_text">02 Oct 2026 - 08:10</span>
            <span class="sport_fixture_title_text">Southland v Northland</span>
          </div>
          <div class="sport_fixture_participant_odds">
            <div id="Event-91341135" class="participant_match_odds">
              <button type="button" data-url="/FixedOdds/AddBet?EventDate=10%2f2%2f2026+8%3a10%3a00+AM&amp;EventParticipantID=344472717&amp;ParticipantName=NORTHLAND&amp;EventID=91341135&amp;VenueID=4024990&amp;BetType=Win&amp;Market=Match+Result&amp;SportType=Rugby&amp;ImgId=50&amp;EventGroup=Bunnings+Warehouse+Cup&amp;EventDescription=Southland+v+Northland&amp;AllowMultiple=True&amp;Odds=1.2&amp;OddsDisplay=1.2&amp;InRunning=N&amp;InRunningDelay=0" class="btnOdds add_bet_link match_odds" decimalvalue="1.2" title="Bet on NORTHLAND" rel="nofollow noopener">1.2</button>
              <button type="button" data-url="/FixedOdds/AddBet?EventDate=10%2f2%2f2026+8%3a10%3a00+AM&amp;EventParticipantID=344472719&amp;ParticipantName=SOUTHLAND&amp;EventID=91341135&amp;VenueID=4024990&amp;BetType=Win&amp;Market=Match+Result&amp;SportType=Rugby&amp;ImgId=50&amp;EventGroup=Bunnings+Warehouse+Cup&amp;EventDescription=Southland+v+Northland&amp;AllowMultiple=True&amp;Odds=4.75&amp;OddsDisplay=4.75&amp;InRunning=N&amp;InRunningDelay=0" class="btnOdds add_bet_link match_odds" decimalvalue="4.75" title="Bet on SOUTHLAND" rel="nofollow noopener">4.75</button>
              <button type="button" data-url="/FixedOdds/AddBet?EventDate=10%2f2%2f2026+8%3a10%3a00+AM&amp;EventParticipantID=344472718&amp;ParticipantName=DRAW&amp;EventID=91341135&amp;VenueID=4024990&amp;BetType=Win&amp;Market=Match+Result&amp;SportType=Rugby&amp;ImgId=50&amp;EventGroup=Bunnings+Warehouse+Cup&amp;EventDescription=Southland+v+Northland&amp;AllowMultiple=True&amp;Odds=41&amp;OddsDisplay=41&amp;InRunning=N&amp;InRunningDelay=0" class="btnOdds add_bet_link match_odds" decimalvalue="41" title="Bet on DRAW" rel="nofollow noopener">41</button>
            </div>
          </div>
        </div>
        <div class="sport_fixture">
          <div class="sport_fixture_title_group">
            <span class="sport_fixture_title_text">04 Oct 2026 - 03:05</span>
            <span class="sport_fixture_title_text">Taranaki v Wellington</span>
          </div>
          <div class="sport_fixture_participant_odds">
            <div id="Event-91344401" class="participant_match_odds">
            </div>
            <div id="Event-91344401" class="participant_handicap_odds">
              <div class="add_bet_link_grouped">
                <span class="handicap_value">(-29.50)</span>
                <button type="button" data-url="/FixedOdds/AddBet?EventDate=10%2f4%2f2026+3%3a05%3a00+AM&amp;EventParticipantID=344498111&amp;ParticipantName=TARANAKI+-29.50&amp;EventID=91344401&amp;VenueID=4024990&amp;BetType=Win&amp;Market=Handicap&amp;SportType=Rugby&amp;ImgId=50&amp;EventGroup=Bunnings+Warehouse+Cup&amp;EventDescription=Taranaki+v+Wellington&amp;AllowMultiple=True&amp;Odds=1.85&amp;OddsDisplay=1.85&amp;InRunning=N&amp;InRunningDelay=0" class="btnOdds add_bet_link handicap_odds" decimalvalue="1.85" title="Bet on TARANAKI -29.50" rel="nofollow noopener">1.85</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
"""

# Hand-built (not a live capture) following the same real markup shape as
# RUGBY_SAMPLE_HTML, for a two-way Rugby market (no Draw participant at
# all) -- the live "Coming up" coupon only had one competition running
# with fixtures posted at the time this adapter was written, and it
# happened to be a three-way (Draw-inclusive) one; some Rugby
# competitions (many test matches/knockout cups) settle a drawn scoreline
# with no push/refund option instead, so Interbet simply never renders a
# DRAW button for those fixtures. This fixture exercises that shape.
RUGBY_TWO_WAY_HTML = """
<div id="Event-90000001" class="participant_match_odds">
  <button type="button" data-url="/FixedOdds/AddBet?EventDate=10%2f10%2f2026+3%3a00%3a00+PM&amp;EventParticipantID=1&amp;ParticipantName=SPRINGBOKS&amp;EventID=90000001&amp;BetType=Win&amp;Market=Match+Result&amp;SportType=Rugby&amp;ImgId=50&amp;EventGroup=Rugby+Championship&amp;EventDescription=Springboks+v+Wallabies&amp;AllowMultiple=True&amp;Odds=1.4&amp;OddsDisplay=1.4&amp;InRunning=N&amp;InRunningDelay=0" class="btnOdds add_bet_link match_odds" title="Bet on SPRINGBOKS" rel="nofollow noopener">1.4</button>
  <button type="button" data-url="/FixedOdds/AddBet?EventDate=10%2f10%2f2026+3%3a00%3a00+PM&amp;EventParticipantID=2&amp;ParticipantName=WALLABIES&amp;EventID=90000001&amp;BetType=Win&amp;Market=Match+Result&amp;SportType=Rugby&amp;ImgId=50&amp;EventGroup=Rugby+Championship&amp;EventDescription=Springboks+v+Wallabies&amp;AllowMultiple=True&amp;Odds=3&amp;OddsDisplay=3&amp;InRunning=N&amp;InRunningDelay=0" class="btnOdds add_bet_link match_odds" title="Bet on WALLABIES" rel="nofollow noopener">3</button>
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


def test_default_sports_config_covers_soccer_and_rugby_with_the_real_ids():
    """Locks in the discovered SportID/SportTypeID/VenueID values (see the
    comments above SPORTS in scraper.py for how each was confirmed against
    the live site) so a future refactor can't silently drop Rugby or
    revert its VenueID to Soccer's."""
    scraper = InterbetScraper()

    by_sport = {cfg.sport: cfg for cfg in scraper.sports}
    assert set(by_sport) == {"soccer", "rugby"}

    assert by_sport["soccer"] == SportConfig(
        sport="soccer",
        sport_id=48,
        venue_id=65,
        sport_description="Soccer",
        venue_description="All Leagues 24H",
        country="International",
        cou_id="INT",
        order=5,
    )
    assert by_sport["rugby"] == SportConfig(
        sport="rugby",
        sport_id=50,
        venue_id=53,
        sport_description="Rugby",
        venue_description="Coming up",
        country="",
        cou_id="",
        order=1,
    )


def test_parse_fixtures_tags_rugby_fixtures_with_sport_and_extracts_a_three_way_market():
    """Otago v Auckland and Southland v Northland both post a Draw price,
    same three-way shape as a Soccer 1X2 market -- proving the parser
    doesn't need separate logic for a Rugby fixture that happens to carry
    a draw."""
    fixtures = InterbetScraper._parse_fixtures(RUGBY_SAMPLE_HTML, sport="rugby")

    assert len(fixtures) == 2  # Taranaki v Wellington has no moneyline buttons at all
    assert all(f["sport"] == "rugby" for f in fixtures)

    otago = next(f for f in fixtures if f["home_team"] == "Otago")
    assert otago["away_team"] == "Auckland"
    assert otago["league"] == "Bunnings Warehouse Cup"
    assert otago["home_odds"] == 1.16
    assert otago["away_odds"] == 5.5
    assert otago["draw_odds"] == 34

    southland = next(f for f in fixtures if f["home_team"] == "Southland")
    assert southland["away_team"] == "Northland"
    assert southland["home_odds"] == 4.75
    assert southland["away_odds"] == 1.2
    assert southland["draw_odds"] == 41


def test_parse_fixtures_skips_a_rugby_fixture_with_no_moneyline_buttons_posted_yet():
    """Taranaki v Wellington's `participant_match_odds` div is present in
    the real captured markup but empty -- only its sibling handicap block
    has a price. No buttons means no fixture record at all, not a record
    with all-None odds."""
    fixtures = InterbetScraper._parse_fixtures(RUGBY_SAMPLE_HTML, sport="rugby")

    assert not any(f["home_team"] == "Taranaki" for f in fixtures)


def test_parse_fixtures_handles_a_two_way_rugby_market_with_no_draw_option():
    """Some Rugby competitions never post a Draw price at all (a knockout
    fixture, say) -- draw_odds must come through as None, a real market
    shape, not a bug to force into a three-way struct."""
    fixtures = InterbetScraper._parse_fixtures(RUGBY_TWO_WAY_HTML, sport="rugby")

    assert len(fixtures) == 1
    fixture = fixtures[0]
    assert fixture["home_team"] == "Springboks"
    assert fixture["away_team"] == "Wallabies"
    assert fixture["home_odds"] == 1.4
    assert fixture["away_odds"] == 3
    assert fixture["draw_odds"] is None


def test_to_odds_events_maps_a_two_way_rugby_fixture_with_no_draw_odds_field_set():
    scraper = InterbetScraper()
    raw = {"fixtures": InterbetScraper._parse_fixtures(RUGBY_TWO_WAY_HTML, sport="rugby")}

    events = scraper.to_odds_events(raw)

    assert len(events) == 1
    event = events[0]
    assert event.sport == "rugby"
    assert event.home_team == "Springboks"
    assert event.away_team == "Wallabies"
    assert event.league == "Rugby Championship"
    assert event.markets["moneyline"].home_odds == 1.4
    assert event.markets["moneyline"].away_odds == 3
    assert event.markets["moneyline"].draw_odds is None


def test_to_odds_events_defaults_untagged_fixtures_to_soccer():
    """A raw fixture dict with no "sport" key at all (the shape every
    pre-Rugby caller/test builds by hand) must still map onto sport
    "soccer" -- the exact backward-compatibility case that lets the
    original soccer-only tests above keep passing unmodified."""
    scraper = InterbetScraper()
    raw = {
        "fixtures": [
            {
                "event_id": "1",
                "league": "Test League",
                "home_team": "Home",
                "away_team": "Away",
                "event_date": "9/28/2026 6:00:00 PM",
                "home_odds": 1.5,
                "away_odds": 2.5,
                "draw_odds": 3.0,
            }
        ]
    }

    events = scraper.to_odds_events(raw)

    assert len(events) == 1
    assert events[0].sport == "soccer"


@pytest.mark.asyncio
async def test_fetch_raw_odds_fetches_every_configured_sport_and_tags_each_fixture(monkeypatch):
    """fetch_raw_odds must hit LoadCouponsPartial once per sport in
    self.sports (not just Soccer), passing each sport's own VenueID/
    SportID/SportTypeID/VenueDescription/SportDescription/Country/CouID,
    and combine both sports' fixtures -- tagged correctly -- into one
    flat list for to_odds_events to consume."""
    scraper = InterbetScraper()
    requested_params = []

    class FakeResponse:
        def __init__(self, text):
            self.text = text

        def raise_for_status(self):
            pass

    async def fake_get(url, params):
        requested_params.append(params)
        if params["SportDescription"] == "Soccer":
            return FakeResponse(SAMPLE_HTML)
        return FakeResponse(RUGBY_SAMPLE_HTML)

    monkeypatch.setattr(scraper._client, "get", fake_get)

    raw = await scraper.fetch_raw_odds()

    assert len(requested_params) == 2
    soccer_params, rugby_params = requested_params
    assert soccer_params["SportID"] == 48
    assert soccer_params["VenueID"] == 65
    assert rugby_params["SportID"] == 50
    assert rugby_params["VenueID"] == 53
    assert rugby_params["Country"] == ""
    assert rugby_params["CouID"] == ""

    fixtures_by_sport = {}
    for f in raw["fixtures"]:
        fixtures_by_sport.setdefault(f["sport"], []).append(f)
    assert len(fixtures_by_sport["soccer"]) == 2
    assert len(fixtures_by_sport["rugby"]) == 2  # Taranaki v Wellington excluded, no moneyline posted

    events = scraper.to_odds_events(raw)
    events_by_sport = {}
    for e in events:
        events_by_sport.setdefault(e.sport, []).append(e)
    assert len(events_by_sport["soccer"]) == 2
    assert len(events_by_sport["rugby"]) == 2


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
