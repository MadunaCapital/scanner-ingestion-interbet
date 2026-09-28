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

# Real HTML captured from a live, plain GET to Interbet's public
# FixedOdds/LoadCouponsPartial with SportID=59/SportTypeID=59 (Cricket)
# and VenueID=29 ("Coming up" -- Cricket's only coupon venue, same
# single-tab situation as Rugby's; see scraper.py's
# CRICKET_COMING_UP_VENUE_ID comment), trimmed of unrelated markup the
# same way SAMPLE_HTML/RUGBY_SAMPLE_HTML are. Both fixtures are real,
# unmodified field values:
#   - India A v Australia A is from the "Test International Friendlies"
#     competition (VenueDescription in the live page), yet still posts
#     only a two-way (home/away) Match Result market with no DRAW
#     participant button -- proving the market shape genuinely observed
#     live for Cricket, even for a "Test"-labelled fixture, is two-way,
#     not the three-way (win/lose/draw) shape a genuine 5-day Test match
#     could in principle carry.
#   - Boland Cricket v Knights (CSA T20 Challenge, a limited-overs
#     competition) is also two-way, for comparison.
# Neither the live "Coming up" coupon nor any other fixture checked at
# capture time had a participant_handicap_odds sibling block for
# Cricket at all (unlike Soccer/Rugby), but the parser's div-class
# scoping doesn't depend on one being present or absent.
CRICKET_SAMPLE_HTML = """
<div class="sport">
  <div class="sports_card">
    <div class="sports_card_body">
      <div class="sports_card_body_fixtures">
        <div class="sport_fixture">
          <div class="sport_fixture_title_group">
            <span class="sport_fixture_title_text">29 Sep 2026 - 06:00</span>
            <span class="sport_fixture_title_text">India A v Australia A</span>
          </div>
          <div class="sport_fixture_participant_odds">
            <div id="Event-91351326" class="participant_match_odds">
              <button type="button" data-url="/FixedOdds/AddBet?EventDate=9%2f29%2f2026+6%3a00%3a00+AM&amp;EventParticipantID=344519977&amp;ParticipantName=AUSTRALIA+A&amp;EventID=91351326&amp;VenueID=6212281&amp;BetType=Win&amp;Market=Match+Result&amp;SportType=Cricket&amp;ImgId=59&amp;EventGroup=Test+International+Friendlies&amp;EventDescription=India+A+v+Australia+A&amp;AllowMultiple=True&amp;Odds=2.85&amp;OddsDisplay=2.85&amp;InRunning=N&amp;InRunningDelay=0" id="344519977-W" class="btnOdds add_bet_link match_odds" decimalvalue="2.85" title="Bet on AUSTRALIA A" rel="nofollow noopener">2.85</button>
              <button type="button" data-url="/FixedOdds/AddBet?EventDate=9%2f29%2f2026+6%3a00%3a00+AM&amp;EventParticipantID=344519978&amp;ParticipantName=INDIA+A&amp;EventID=91351326&amp;VenueID=6212281&amp;BetType=Win&amp;Market=Match+Result&amp;SportType=Cricket&amp;ImgId=59&amp;EventGroup=Test+International+Friendlies&amp;EventDescription=India+A+v+Australia+A&amp;AllowMultiple=True&amp;Odds=1.45&amp;OddsDisplay=1.45&amp;InRunning=N&amp;InRunningDelay=0" id="344519978-W" class="btnOdds add_bet_link match_odds" decimalvalue="1.45" title="Bet on INDIA A" rel="nofollow noopener">1.45</button>
            </div>
          </div>
        </div>
        <div class="sport_fixture">
          <div class="sport_fixture_title_group">
            <span class="sport_fixture_title_text">29 Sep 2026 - 18:00</span>
            <span class="sport_fixture_title_text">Boland Cricket v Knights</span>
          </div>
          <div class="sport_fixture_participant_odds">
            <div id="Event-91354282" class="participant_match_odds">
              <button type="button" data-url="/FixedOdds/AddBet?EventDate=9%2f29%2f2026+6%3a00%3a00+PM&amp;EventParticipantID=344529694&amp;ParticipantName=BOLAND+CRICKET&amp;EventID=91354282&amp;VenueID=3682765&amp;BetType=Win&amp;Market=Match+Result&amp;SportType=Cricket&amp;ImgId=59&amp;EventGroup=CSA+T20+Challenge&amp;EventDescription=Boland+Cricket+v+Knights&amp;AllowMultiple=True&amp;Odds=1.65&amp;OddsDisplay=1.65&amp;InRunning=N&amp;InRunningDelay=0" id="344529694-W" class="btnOdds add_bet_link match_odds" decimalvalue="1.65" title="Bet on BOLAND CRICKET" rel="nofollow noopener">1.65</button>
              <button type="button" data-url="/FixedOdds/AddBet?EventDate=9%2f29%2f2026+6%3a00%3a00+PM&amp;EventParticipantID=344529693&amp;ParticipantName=KNIGHTS&amp;EventID=91354282&amp;VenueID=3682765&amp;BetType=Win&amp;Market=Match+Result&amp;SportType=Cricket&amp;ImgId=59&amp;EventGroup=CSA+T20+Challenge&amp;EventDescription=Boland+Cricket+v+Knights&amp;AllowMultiple=True&amp;Odds=2.25&amp;OddsDisplay=2.25&amp;InRunning=N&amp;InRunningDelay=0" id="344529693-W" class="btnOdds add_bet_link match_odds" decimalvalue="2.25" title="Bet on KNIGHTS" rel="nofollow noopener">2.25</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
"""

# Hand-built (not a live capture) -- exercises the three-way (win/lose/
# draw) shape a genuine multi-day Test match's Match Result market could
# carry, the same way RUGBY_SAMPLE_HTML's Otago v Auckland exercises it
# for Rugby. Every live Cricket fixture checked while writing this
# adapter (see CRICKET_SAMPLE_HTML above) was two-way, including ones
# labelled "Test International Friendlies", so this shape wasn't
# observed live -- but the parser makes no assumption either way (see
# scraper.py's _parse_fixtures docstring), so this fixture proves a
# DRAW button, if Interbet ever posts one for Cricket, comes through
# correctly rather than being silently dropped or mismatched.
CRICKET_THREE_WAY_HTML = """
<div id="Event-90000002" class="participant_match_odds">
  <button type="button" data-url="/FixedOdds/AddBet?EventDate=10%2f15%2f2026+8%3a00%3a00+AM&amp;EventParticipantID=1&amp;ParticipantName=ENGLAND&amp;EventID=90000002&amp;BetType=Win&amp;Market=Match+Result&amp;SportType=Cricket&amp;ImgId=59&amp;EventGroup=The+Ashes&amp;EventDescription=England+v+Australia&amp;AllowMultiple=True&amp;Odds=2.5&amp;OddsDisplay=2.5&amp;InRunning=N&amp;InRunningDelay=0" class="btnOdds add_bet_link match_odds" title="Bet on ENGLAND" rel="nofollow noopener">2.5</button>
  <button type="button" data-url="/FixedOdds/AddBet?EventDate=10%2f15%2f2026+8%3a00%3a00+AM&amp;EventParticipantID=2&amp;ParticipantName=AUSTRALIA&amp;EventID=90000002&amp;BetType=Win&amp;Market=Match+Result&amp;SportType=Cricket&amp;ImgId=59&amp;EventGroup=The+Ashes&amp;EventDescription=England+v+Australia&amp;AllowMultiple=True&amp;Odds=2.1&amp;OddsDisplay=2.1&amp;InRunning=N&amp;InRunningDelay=0" class="btnOdds add_bet_link match_odds" title="Bet on AUSTRALIA" rel="nofollow noopener">2.1</button>
  <button type="button" data-url="/FixedOdds/AddBet?EventDate=10%2f15%2f2026+8%3a00%3a00+AM&amp;EventParticipantID=3&amp;ParticipantName=DRAW&amp;EventID=90000002&amp;BetType=Win&amp;Market=Match+Result&amp;SportType=Cricket&amp;ImgId=59&amp;EventGroup=The+Ashes&amp;EventDescription=England+v+Australia&amp;AllowMultiple=True&amp;Odds=4.5&amp;OddsDisplay=4.5&amp;InRunning=N&amp;InRunningDelay=0" class="btnOdds add_bet_link match_odds" title="Bet on DRAW" rel="nofollow noopener">4.5</button>
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


# Real HTML captured from a live, plain GET to Interbet's public
# FixedOdds/LoadCouponsPartial with SportID=55/SportTypeID=55 (Tennis)
# and VenueID=6 ("Coming up" -- Tennis's only coupon venue, same
# single-tab situation as Rugby/Cricket; see scraper.py's
# TENNIS_COMING_UP_VENUE_ID comment), trimmed of unrelated markup the
# same way SAMPLE_HTML/RUGBY_SAMPLE_HTML/CRICKET_SAMPLE_HTML are. Both
# fixtures are real, unmodified field values, chosen to exercise
# Tennis's two distinct ParticipantName shapes seen live in the same
# snapshot:
#   - Adrian Arcon v Aleksandar Govedarica: both players' ParticipantName
#     is rendered "SURNAME, First" (e.g. "ARCON, ADRIAN"), reversed from
#     and differently cased than EventDescription's "Adrian Arcon" --
#     proving the surname-suffix match handles the common case.
#   - Masamichi Imamura v Petr Bar Biryukov: the home player follows the
#     same "SURNAME, First" pattern ("IMAMURA, M" -- note the given name
#     is *abbreviated* to a bare initial here, unlike Arcon/Govedarica),
#     but the away player, "Petr Bar Biryukov", is rendered with no comma
#     at all, already in the same "First Surname" order EventDescription
#     uses -- proving both shapes are handled correctly even within one
#     fixture. This fixture also keeps its real `participant_handicap_odds`
#     sibling block (Market=Handicap, ParticipantName carries a point
#     spread like "PETR BAR BIRYUKOV -0.50"), to exercise the "must not
#     leak into moneyline" case the same way SAMPLE_HTML's second fixture
#     does for Soccer.
# Neither fixture has a DRAW participant button -- no live Tennis fixture
# checked while building this adapter did (see scraper.py's
# `_parse_fixtures` docstring): a draw isn't a possible result in tennis.
TENNIS_SAMPLE_HTML = """
<div class="sport">
  <div class="sports_card">
    <div class="sports_card_body">
      <div class="sports_card_body_fixtures">
        <div class="sport_fixture">
          <div class="sport_fixture_title_group">
            <span class="sport_fixture_title_text">29 Sep 2026 - 07:30</span>
            <span class="sport_fixture_title_text">Adrian Arcon v Aleksandar Govedarica</span>
          </div>
          <div class="sport_fixture_participant_odds">
            <div id="Event-91365623" class="participant_match_odds">
              <button type="button" data-url="/FixedOdds/AddBet?EventDate=9%2f29%2f2026+7%3a30%3a00+AM&amp;EventParticipantID=344567855&amp;ParticipantName=ARCON%2c+ADRIAN&amp;EventID=91365623&amp;VenueID=7630416&amp;BetType=Win&amp;Market=Match+Result&amp;SportType=Tennis&amp;ImgId=55&amp;EventGroup=Darwin+International&amp;EventDescription=Adrian+Arcon+v+Aleksandar+Govedarica&amp;AllowMultiple=True&amp;Odds=1.18&amp;OddsDisplay=1.18&amp;InRunning=N&amp;InRunningDelay=0" id="344567855-W" class="btnOdds add_bet_link match_odds" decimalvalue="1.18" title="Bet on ARCON, ADRIAN" rel="nofollow noopener">1.18</button>
              <button type="button" data-url="/FixedOdds/AddBet?EventDate=9%2f29%2f2026+7%3a30%3a00+AM&amp;EventParticipantID=344567854&amp;ParticipantName=GOVEDARICA%2c+ALEKSANDAR&amp;EventID=91365623&amp;VenueID=7630416&amp;BetType=Win&amp;Market=Match+Result&amp;SportType=Tennis&amp;ImgId=55&amp;EventGroup=Darwin+International&amp;EventDescription=Adrian+Arcon+v+Aleksandar+Govedarica&amp;AllowMultiple=True&amp;Odds=4.75&amp;OddsDisplay=4.75&amp;InRunning=N&amp;InRunningDelay=0" id="344567854-W" class="btnOdds add_bet_link match_odds" decimalvalue="4.75" title="Bet on GOVEDARICA, ALEKSANDAR" rel="nofollow noopener">4.75</button>
            </div>
          </div>
        </div>
        <div class="sport_fixture">
          <div class="sport_fixture_title_group">
            <span class="sport_fixture_title_text">30 Sep 2026 - 11:00</span>
            <span class="sport_fixture_title_text">Masamichi Imamura v Petr Bar Biryukov</span>
          </div>
          <div class="sport_fixture_participant_odds">
            <div id="Event-91307528" class="participant_match_odds">
              <button type="button" data-url="/FixedOdds/AddBet?EventDate=9%2f30%2f2026+11%3a00%3a00+AM&amp;EventParticipantID=344387995&amp;ParticipantName=IMAMURA%2c+M&amp;EventID=91307528&amp;VenueID=7612961&amp;BetType=Win&amp;Market=Match+Result&amp;SportType=Tennis&amp;ImgId=55&amp;EventGroup=ATP+Jingshan+Challenger&amp;EventDescription=Masamichi+Imamura+v+Petr+Bar+Biryukov&amp;AllowMultiple=True&amp;Odds=2&amp;OddsDisplay=2&amp;InRunning=N&amp;InRunningDelay=0" id="344387995-W" class="btnOdds add_bet_link match_odds" decimalvalue="2" title="Bet on IMAMURA, M" rel="nofollow noopener">2</button>
              <button type="button" data-url="/FixedOdds/AddBet?EventDate=9%2f30%2f2026+11%3a00%3a00+AM&amp;EventParticipantID=344387993&amp;ParticipantName=PETR+BAR+BIRYUKOV&amp;EventID=91307528&amp;VenueID=7612961&amp;BetType=Win&amp;Market=Match+Result&amp;SportType=Tennis&amp;ImgId=55&amp;EventGroup=ATP+Jingshan+Challenger&amp;EventDescription=Masamichi+Imamura+v+Petr+Bar+Biryukov&amp;AllowMultiple=True&amp;Odds=1.8&amp;OddsDisplay=1.8&amp;InRunning=N&amp;InRunningDelay=0" id="344387993-W" class="btnOdds add_bet_link match_odds" decimalvalue="1.8" title="Bet on PETR BAR BIRYUKOV" rel="nofollow noopener">1.8</button>
            </div>
            <div id="Event-91307528" class="participant_handicap_odds">
              <div class="add_bet_link_grouped">
                <span class="handicap_value">(+0.50)</span>
                <button type="button" data-url="/FixedOdds/AddBet?EventDate=9%2f30%2f2026+11%3a00%3a00+AM&amp;EventParticipantID=344444931&amp;ParticipantName=IMAMURA%2c+M+%2b0.50&amp;EventID=91327101&amp;VenueID=7612961&amp;BetType=Win&amp;Market=Handicap&amp;SportType=Tennis&amp;ImgId=55&amp;EventGroup=ATP+Jingshan+Challenger&amp;EventDescription=Masamichi+Imamura+v+Petr+Bar+Biryukov&amp;AllowMultiple=True&amp;Odds=1.95&amp;OddsDisplay=1.95&amp;InRunning=N&amp;InRunningDelay=0" id="344444931-W" class="btnOdds add_bet_link handicap_odds" decimalvalue="1.95" title="Bet on IMAMURA, M +0.50" rel="nofollow noopener">1.95</button>
              </div>
              <div class="add_bet_link_grouped">
                <span class="handicap_value">(-0.50)</span>
                <button type="button" data-url="/FixedOdds/AddBet?EventDate=9%2f30%2f2026+11%3a00%3a00+AM&amp;EventParticipantID=344444930&amp;ParticipantName=PETR+BAR+BIRYUKOV+-0.50&amp;EventID=91327101&amp;VenueID=7612961&amp;BetType=Win&amp;Market=Handicap&amp;SportType=Tennis&amp;ImgId=55&amp;EventGroup=ATP+Jingshan+Challenger&amp;EventDescription=Masamichi+Imamura+v+Petr+Bar+Biryukov&amp;AllowMultiple=True&amp;Odds=1.85&amp;OddsDisplay=1.85&amp;InRunning=N&amp;InRunningDelay=0" id="344444930-W" class="btnOdds add_bet_link handicap_odds" decimalvalue="1.85" title="Bet on PETR BAR BIRYUKOV -0.50" rel="nofollow noopener">1.85</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
"""

# Real HTML captured from the same live Tennis "Coming up" coupon as
# TENNIS_SAMPLE_HTML, for a doubles fixture (Anastasia Detiuc / Irina
# Khromacheva v Sofia Costoulas / Ingrid Gamarra Martins, from the "WTA
# Jingshan 125K Series Doubles" competition). Interbet renders a doubles
# ParticipantName as both players' "Surname, First" joined by "/" (e.g.
# "DETIUC, ANASTASIA/KHROMACHEVA, IRINA"), which doesn't reduce to a
# single trailing surname the way a singles ParticipantName does --
# see scraper.py's `_participant_matches_team` docstring for why this is
# a deliberate, documented gap rather than a bug: this fixture proves
# that gap fails *safe* (both buttons go unmatched and the fixture is
# dropped for having no home/away price at all) instead of mismatching
# the odds to the wrong pairing.
TENNIS_DOUBLES_HTML = """
<div class="sport_fixture">
  <div class="sport_fixture_title_group">
    <span class="sport_fixture_title_text">29 Sep 2026 - 09:00</span>
    <span class="sport_fixture_title_text">Anastasia Detiuc / Irina Khromacheva v Sofia Costoulas / Ingrid Gamarra Martins</span>
  </div>
  <div class="sport_fixture_participant_odds">
    <div id="Event-91338463" class="participant_match_odds">
      <button type="button" data-url="/FixedOdds/AddBet?EventDate=9%2f29%2f2026+9%3a00%3a00+AM&amp;EventParticipantID=344479631&amp;ParticipantName=COSTOULAS%2c+SOFIA%2fGAMARRA+MARTINS%2c+INGRID&amp;EventID=91338463&amp;VenueID=7613942&amp;BetType=Win&amp;Market=Match+Result&amp;SportType=Tennis&amp;ImgId=55&amp;EventGroup=WTA+Jingshan+125K+Series+Doubles&amp;EventDescription=Anastasia+Detiuc+%2f+Irina+Khromacheva+v+Sofia+Costoulas+%2f+Ingrid+Gamarra+Martins&amp;AllowMultiple=True&amp;Odds=2.8&amp;OddsDisplay=2.8&amp;InRunning=N&amp;InRunningDelay=0" id="344479631-W" class="btnOdds add_bet_link match_odds" decimalvalue="2.8" title="Bet on COSTOULAS, SOFIA/GAMARRA MARTINS, INGRID" rel="nofollow noopener">2.8</button>
      <button type="button" data-url="/FixedOdds/AddBet?EventDate=9%2f29%2f2026+9%3a00%3a00+AM&amp;EventParticipantID=344479632&amp;ParticipantName=DETIUC%2c+ANASTASIA%2fKHROMACHEVA%2c+IRINA&amp;EventID=91338463&amp;VenueID=7613942&amp;BetType=Win&amp;Market=Match+Result&amp;SportType=Tennis&amp;ImgId=55&amp;EventGroup=WTA+Jingshan+125K+Series+Doubles&amp;EventDescription=Anastasia+Detiuc+%2f+Irina+Khromacheva+v+Sofia+Costoulas+%2f+Ingrid+Gamarra+Martins&amp;AllowMultiple=True&amp;Odds=1.45&amp;OddsDisplay=1.45&amp;InRunning=N&amp;InRunningDelay=0" id="344479632-W" class="btnOdds add_bet_link match_odds" decimalvalue="1.45" title="Bet on DETIUC, ANASTASIA/KHROMACHEVA, IRINA" rel="nofollow noopener">1.45</button>
    </div>
  </div>
</div>
"""


# Real HTML captured from a live, plain GET to Interbet's public
# FixedOdds/LoadCouponsPartial with SportID=76/SportTypeID=76 (Basketball)
# and VenueID=56 ("Coming up" -- Basketball's only coupon venue, same
# single-tab situation as Rugby/Cricket/Tennis; see scraper.py's
# BASKETBALL_COMING_UP_VENUE_ID comment), trimmed of unrelated markup the
# same way the other sports' *_SAMPLE_HTML constants are. Both fixtures
# are real, unmodified field values:
#   - Club Atletico Lanus v Gimnasia Esgrima Comodoro Rivadavia (Liga
#     Nacional de Basquetbol) is a straightforward two-way market with no
#     name-formatting quirk -- ParticipantName is just the team's name,
#     case-folded, same order as EventDescription.
#   - Etoile Charleville-Mezieres v Mulhouse Basket Agglomeration (French
#     National Division 1) exercises a hyphenated club name the same way
#     Soccer's "Bosnia-Herzegovina" and Rugby/Cricket's hyphenated team
#     names do -- proving `_normalize_name`'s hyphen-folding is enough for
#     Basketball too, with no Tennis-style surname-matching needed.
# Neither fixture has a DRAW participant button -- no live Basketball
# fixture checked while building this adapter did (93 fixtures across 26
# competitions, all exactly 2 buttons each): a basketball game always
# resolves to a winner, no draw is possible.
BASKETBALL_SAMPLE_HTML = """
<div class="sport">
  <div class="sports_card">
    <div class="sports_card_body">
      <div class="sports_card_body_fixtures">
        <div class="sport_fixture">
          <div class="sport_fixture_title_group">
            <span class="sport_fixture_title_text">29 Sep 2026 - 03:05</span>
            <span class="sport_fixture_title_text">Club Atletico Lanus v Gimnasia Esgrima Comodoro Rivadavia</span>
          </div>
          <div class="sport_fixture_participant_odds">
            <div id="Event-91345641" class="participant_match_odds">
              <button type="button" data-url="/FixedOdds/AddBet?EventDate=9%2f29%2f2026+3%3a05%3a00+AM&amp;EventParticipantID=344501975&amp;ParticipantName=CLUB+ATLETICO+LANUS&amp;EventID=91345641&amp;VenueID=2337239&amp;BetType=Win&amp;Market=Match+Result&amp;SportType=Basketball&amp;ImgId=76&amp;EventGroup=Liga+Nacional+de+Basquetbol&amp;EventDescription=Club+Atletico+Lanus+v+Gimnasia+Esgrima+Comodoro+Rivadavia&amp;AllowMultiple=True&amp;Odds=2.35&amp;OddsDisplay=2.35&amp;InRunning=N&amp;InRunningDelay=0" id="344501975-W" class="btnOdds add_bet_link match_odds" decimalvalue="2.35" title="Bet on CLUB ATLETICO LANUS" rel="nofollow noopener">2.35</button>
              <button type="button" data-url="/FixedOdds/AddBet?EventDate=9%2f29%2f2026+3%3a05%3a00+AM&amp;EventParticipantID=344501974&amp;ParticipantName=GIMNASIA+ESGRIMA+COMODORO+RIVADAVIA&amp;EventID=91345641&amp;VenueID=2337239&amp;BetType=Win&amp;Market=Match+Result&amp;SportType=Basketball&amp;ImgId=76&amp;EventGroup=Liga+Nacional+de+Basquetbol&amp;EventDescription=Club+Atletico+Lanus+v+Gimnasia+Esgrima+Comodoro+Rivadavia&amp;AllowMultiple=True&amp;Odds=1.55&amp;OddsDisplay=1.55&amp;InRunning=N&amp;InRunningDelay=0" id="344501974-W" class="btnOdds add_bet_link match_odds" decimalvalue="1.55" title="Bet on GIMNASIA ESGRIMA COMODORO RIVADAVIA" rel="nofollow noopener">1.55</button>
            </div>
          </div>
        </div>
        <div class="sport_fixture">
          <div class="sport_fixture_title_group">
            <span class="sport_fixture_title_text">29 Sep 2026 - 20:00</span>
            <span class="sport_fixture_title_text">Etoile Charleville-Mezieres v Mulhouse Basket Agglomeration</span>
          </div>
          <div class="sport_fixture_participant_odds">
            <div id="Event-91317586" class="participant_match_odds">
              <button type="button" data-url="/FixedOdds/AddBet?EventDate=9%2f29%2f2026+8%3a00%3a00+PM&amp;EventParticipantID=344416693&amp;ParticipantName=ETOILE+CHARLEVILLE-MEZIERES&amp;EventID=91317586&amp;VenueID=1607325&amp;BetType=Win&amp;Market=Match+Result&amp;SportType=Basketball&amp;ImgId=76&amp;EventGroup=French+National+Division+1&amp;EventDescription=Etoile+Charleville-Mezieres+v+Mulhouse+Basket+Agglomeration&amp;AllowMultiple=True&amp;Odds=2.6&amp;OddsDisplay=2.6&amp;InRunning=N&amp;InRunningDelay=0" id="344416693-W" class="btnOdds add_bet_link match_odds" decimalvalue="2.6" title="Bet on ETOILE CHARLEVILLE-MEZIERES" rel="nofollow noopener">2.6</button>
              <button type="button" data-url="/FixedOdds/AddBet?EventDate=9%2f29%2f2026+8%3a00%3a00+PM&amp;EventParticipantID=344416692&amp;ParticipantName=MULHOUSE+BASKET+AGGLOMERATION&amp;EventID=91317586&amp;VenueID=1607325&amp;BetType=Win&amp;Market=Match+Result&amp;SportType=Basketball&amp;ImgId=76&amp;EventGroup=French+National+Division+1&amp;EventDescription=Etoile+Charleville-Mezieres+v+Mulhouse+Basket+Agglomeration&amp;AllowMultiple=True&amp;Odds=1.45&amp;OddsDisplay=1.45&amp;InRunning=N&amp;InRunningDelay=0" id="344416692-W" class="btnOdds add_bet_link match_odds" decimalvalue="1.45" title="Bet on MULHOUSE BASKET AGGLOMERATION" rel="nofollow noopener">1.45</button>
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


def test_default_sports_config_covers_soccer_rugby_cricket_tennis_and_basketball_with_the_real_ids():
    """Locks in the discovered SportID/SportTypeID/VenueID values (see the
    comments above SPORTS in scraper.py for how each was confirmed against
    the live site) so a future refactor can't silently drop Rugby/Cricket/
    Tennis/Basketball or revert any of their VenueIDs to Soccer's (or to
    each other's -- Rugby=53, Cricket=29, Tennis=6 and Basketball=56 are
    all genuinely distinct)."""
    scraper = InterbetScraper()

    by_sport = {cfg.sport: cfg for cfg in scraper.sports}
    assert set(by_sport) == {"soccer", "rugby", "cricket", "tennis", "basketball"}

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
    assert by_sport["cricket"] == SportConfig(
        sport="cricket",
        sport_id=59,
        venue_id=29,
        sport_description="Cricket",
        venue_description="Coming up",
        country="",
        cou_id="",
        order=1,
    )
    assert by_sport["tennis"] == SportConfig(
        sport="tennis",
        sport_id=55,
        venue_id=6,
        sport_description="Tennis",
        venue_description="Coming up",
        country="",
        cou_id="",
        order=1,
    )
    assert by_sport["basketball"] == SportConfig(
        sport="basketball",
        sport_id=76,
        venue_id=56,
        sport_description="Basketball",
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


def test_parse_fixtures_tags_cricket_fixtures_with_sport_and_extracts_a_two_way_market():
    """India A v Australia A and Boland Cricket v Knights are both real,
    live-captured Cricket fixtures with a two-way (home/away, no Draw)
    Match Result market -- including India A v Australia A, which comes
    from the "Test International Friendlies" competition. Proves the
    parser handles Cricket's own SportType/Market labels ("Cricket" /
    "Match Result") the same way it already handles Soccer's and
    Rugby's."""
    fixtures = InterbetScraper._parse_fixtures(CRICKET_SAMPLE_HTML, sport="cricket")

    assert len(fixtures) == 2
    assert all(f["sport"] == "cricket" for f in fixtures)

    india = next(f for f in fixtures if f["home_team"] == "India A")
    assert india["away_team"] == "Australia A"
    assert india["league"] == "Test International Friendlies"
    assert india["home_odds"] == 1.45
    assert india["away_odds"] == 2.85
    assert india["draw_odds"] is None  # no DRAW button posted for this fixture

    boland = next(f for f in fixtures if f["home_team"] == "Boland Cricket")
    assert boland["away_team"] == "Knights"
    assert boland["league"] == "CSA T20 Challenge"
    assert boland["home_odds"] == 1.65
    assert boland["away_odds"] == 2.25
    assert boland["draw_odds"] is None


def test_parse_fixtures_handles_a_three_way_cricket_market_with_a_draw_option():
    """No live Cricket fixture observed while building this adapter posted
    a Draw price (see CRICKET_SAMPLE_HTML's docstring) -- but the parser
    doesn't assume that shape, so a hand-built three-way (win/lose/draw)
    Cricket fixture, the shape a genuine multi-day Test match could in
    principle carry, must still parse with draw_odds populated rather
    than being coerced into a two-way struct."""
    fixtures = InterbetScraper._parse_fixtures(CRICKET_THREE_WAY_HTML, sport="cricket")

    assert len(fixtures) == 1
    fixture = fixtures[0]
    assert fixture["home_team"] == "England"
    assert fixture["away_team"] == "Australia"
    assert fixture["home_odds"] == 2.5
    assert fixture["away_odds"] == 2.1
    assert fixture["draw_odds"] == 4.5


def test_to_odds_events_maps_cricket_fixtures_onto_the_universal_schema():
    scraper = InterbetScraper()
    raw = {"fixtures": InterbetScraper._parse_fixtures(CRICKET_SAMPLE_HTML, sport="cricket")}

    events = scraper.to_odds_events(raw)

    assert len(events) == 2
    event = next(e for e in events if e.home_team == "India A")
    assert event.away_team == "Australia A"
    assert event.sport == "cricket"
    assert event.league == "Test International Friendlies"
    assert event.bookmaker == "interbet"
    assert event.markets["moneyline"].home_odds == 1.45
    assert event.markets["moneyline"].away_odds == 2.85
    assert event.markets["moneyline"].draw_odds is None


def test_parse_fixtures_tags_tennis_fixtures_and_matches_surname_first_participant_names():
    """Adrian Arcon v Aleksandar Govedarica: both ParticipantNames are
    "SURNAME, First" (reversed and differently cased from EventDescription's
    "First Surname") -- proving the surname-suffix match in
    `_participant_matches_team` correctly pairs each button with its
    player despite the reordering."""
    fixtures = InterbetScraper._parse_fixtures(TENNIS_SAMPLE_HTML, sport="tennis")

    assert len(fixtures) == 2
    assert all(f["sport"] == "tennis" for f in fixtures)

    arcon = next(f for f in fixtures if f["home_team"] == "Adrian Arcon")
    assert arcon["away_team"] == "Aleksandar Govedarica"
    assert arcon["league"] == "Darwin International"
    assert arcon["home_odds"] == 1.18
    assert arcon["away_odds"] == 4.75
    assert arcon["draw_odds"] is None  # tennis can't end in a draw


def test_parse_fixtures_handles_an_abbreviated_given_name_and_a_no_comma_participant_name():
    """Masamichi Imamura v Petr Bar Biryukov exercises two more real
    ParticipantName shapes in the same fixture:
      - "IMAMURA, M" -- "Surname, First" but with the given name
        abbreviated to a bare initial, which a naive comma-reversal
        would never match against "Masamichi Imamura" -- only matching
        on the surname handles this.
      - "PETR BAR BIRYUKOV" -- no comma at all, already in the same
        "First Surname" order as EventDescription's "Petr Bar Biryukov",
        which the plain equality fallback handles directly.
    Also proves the real captured `participant_handicap_odds` sibling
    block (Market=Handicap, e.g. "PETR BAR BIRYUKOV -0.50") doesn't leak
    into the moneyline market, the same div-class scoping already
    proven for Soccer/Rugby."""
    fixtures = InterbetScraper._parse_fixtures(TENNIS_SAMPLE_HTML, sport="tennis")

    imamura = next(f for f in fixtures if f["home_team"] == "Masamichi Imamura")
    assert imamura["away_team"] == "Petr Bar Biryukov"
    assert imamura["league"] == "ATP Jingshan Challenger"
    assert imamura["home_odds"] == 2
    assert imamura["away_odds"] == 1.8
    # None of the handicap odds (e.g. 1.95/1.85) leaked in.
    assert 1.95 not in (imamura["home_odds"], imamura["away_odds"])
    assert 1.85 not in (imamura["home_odds"], imamura["away_odds"])


def test_to_odds_events_maps_tennis_fixtures_onto_the_universal_schema():
    scraper = InterbetScraper()
    raw = {"fixtures": InterbetScraper._parse_fixtures(TENNIS_SAMPLE_HTML, sport="tennis")}

    events = scraper.to_odds_events(raw)

    assert len(events) == 2
    event = next(e for e in events if e.home_team == "Adrian Arcon")
    assert event.away_team == "Aleksandar Govedarica"
    assert event.sport == "tennis"
    assert event.league == "Darwin International"
    assert event.bookmaker == "interbet"
    assert event.markets["moneyline"].home_odds == 1.18
    assert event.markets["moneyline"].away_odds == 4.75
    assert event.markets["moneyline"].draw_odds is None


def test_parse_fixtures_skips_a_doubles_fixture_rather_than_mismatching_its_odds():
    """Interbet renders a doubles ParticipantName as both players' names
    joined by "/" (e.g. "DETIUC, ANASTASIA/KHROMACHEVA, IRINA"), which
    doesn't reduce to a single trailing surname the way singles does.
    Both buttons must go unmatched -- and the fixture dropped for having
    no home/away price -- rather than being guessed into the wrong
    pairing."""
    fixtures = InterbetScraper._parse_fixtures(TENNIS_DOUBLES_HTML, sport="tennis")

    assert len(fixtures) == 1
    fixture = fixtures[0]
    assert fixture["home_odds"] is None
    assert fixture["away_odds"] is None

    scraper = InterbetScraper()
    events = scraper.to_odds_events({"fixtures": fixtures})
    assert events == []  # incomplete market, correctly never published


def test_parse_fixtures_tags_basketball_fixtures_and_extracts_a_two_way_market():
    """Both fixtures in BASKETBALL_SAMPLE_HTML are real, live-captured
    Basketball fixtures with a two-way (home/away, no Draw) Match Result
    market -- proving the parser handles Basketball's own SportType label
    ("Basketball") the same way it already handles the other sports', and
    that team names (including the hyphenated "Etoile
    Charleville-Mezieres") match straightforwardly via `_normalize_name`
    with no Tennis-style reordering needed."""
    fixtures = InterbetScraper._parse_fixtures(BASKETBALL_SAMPLE_HTML, sport="basketball")

    assert len(fixtures) == 2
    assert all(f["sport"] == "basketball" for f in fixtures)

    lanus = next(f for f in fixtures if f["home_team"] == "Club Atletico Lanus")
    assert lanus["away_team"] == "Gimnasia Esgrima Comodoro Rivadavia"
    assert lanus["league"] == "Liga Nacional de Basquetbol"
    assert lanus["home_odds"] == 2.35
    assert lanus["away_odds"] == 1.55
    assert lanus["draw_odds"] is None  # basketball always resolves to a winner

    charleville = next(f for f in fixtures if f["home_team"] == "Etoile Charleville-Mezieres")
    assert charleville["away_team"] == "Mulhouse Basket Agglomeration"
    assert charleville["league"] == "French National Division 1"
    assert charleville["home_odds"] == 2.6
    assert charleville["away_odds"] == 1.45
    assert charleville["draw_odds"] is None


def test_to_odds_events_maps_basketball_fixtures_onto_the_universal_schema():
    scraper = InterbetScraper()
    raw = {"fixtures": InterbetScraper._parse_fixtures(BASKETBALL_SAMPLE_HTML, sport="basketball")}

    events = scraper.to_odds_events(raw)

    assert len(events) == 2
    event = next(e for e in events if e.home_team == "Club Atletico Lanus")
    assert event.away_team == "Gimnasia Esgrima Comodoro Rivadavia"
    assert event.sport == "basketball"
    assert event.league == "Liga Nacional de Basquetbol"
    assert event.bookmaker == "interbet"
    assert event.markets["moneyline"].home_odds == 2.35
    assert event.markets["moneyline"].away_odds == 1.55
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
    and combine all five sports' fixtures -- tagged correctly -- into one
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
        if params["SportDescription"] == "Rugby":
            return FakeResponse(RUGBY_SAMPLE_HTML)
        if params["SportDescription"] == "Cricket":
            return FakeResponse(CRICKET_SAMPLE_HTML)
        if params["SportDescription"] == "Tennis":
            return FakeResponse(TENNIS_SAMPLE_HTML)
        return FakeResponse(BASKETBALL_SAMPLE_HTML)

    monkeypatch.setattr(scraper._client, "get", fake_get)

    raw = await scraper.fetch_raw_odds()

    assert len(requested_params) == 5
    soccer_params, rugby_params, cricket_params, tennis_params, basketball_params = requested_params
    assert soccer_params["SportID"] == 48
    assert soccer_params["VenueID"] == 65
    assert rugby_params["SportID"] == 50
    assert rugby_params["VenueID"] == 53
    assert rugby_params["Country"] == ""
    assert rugby_params["CouID"] == ""
    assert cricket_params["SportID"] == 59
    assert cricket_params["VenueID"] == 29
    assert cricket_params["Country"] == ""
    assert cricket_params["CouID"] == ""
    assert tennis_params["SportID"] == 55
    assert tennis_params["VenueID"] == 6
    assert tennis_params["Country"] == ""
    assert tennis_params["CouID"] == ""
    assert basketball_params["SportID"] == 76
    assert basketball_params["VenueID"] == 56
    assert basketball_params["Country"] == ""
    assert basketball_params["CouID"] == ""

    fixtures_by_sport = {}
    for f in raw["fixtures"]:
        fixtures_by_sport.setdefault(f["sport"], []).append(f)
    assert len(fixtures_by_sport["soccer"]) == 2
    assert len(fixtures_by_sport["rugby"]) == 2  # Taranaki v Wellington excluded, no moneyline posted
    assert len(fixtures_by_sport["cricket"]) == 2
    assert len(fixtures_by_sport["tennis"]) == 2
    assert len(fixtures_by_sport["basketball"]) == 2

    events = scraper.to_odds_events(raw)
    events_by_sport = {}
    for e in events:
        events_by_sport.setdefault(e.sport, []).append(e)
    assert len(events_by_sport["soccer"]) == 2
    assert len(events_by_sport["rugby"]) == 2
    assert len(events_by_sport["cricket"]) == 2
    assert len(events_by_sport["tennis"]) == 2
    assert len(events_by_sport["basketball"]) == 2


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
