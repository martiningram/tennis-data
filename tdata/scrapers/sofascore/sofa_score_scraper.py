import os
import json
from pathlib import Path
from datetime import datetime

from unidecode import unidecode

from tdata.enums.round import Rounds
from tdata.enums.surface import Surfaces
from tdata.datasets.match import CompletedMatch
from tdata.datasets.match_stats import MatchStats
from tdata.datasets.score import Score, BadFormattingException
from tdata.enums.t_type import (Tours, is_singles, is_standard_doubles,
                                is_mixed_doubles)
from tdata.scrapers.utils import (load_json_url, fetch_logger, prettify_json,
                                  load_html_page)
from tdata.utils.utils import load_cached_json, save_to_cache, is_cached


logger = fetch_logger(__name__, 'sofa_score.log')


class IncompleteException(Exception):
    pass


class SofaScoreScraper(object):

    def __init__(self):

        exec_dir = Path(os.path.abspath(__file__)).parents[3]
        cache_dir = '{}/data/sofa_cache/'.format(exec_dir)
        self.output_dir = '{}/data/sofa_csv/'.format(exec_dir)
        self.tournament_cache_dir = os.path.join(cache_dir, 'tournaments')
        self.match_cache_dir = os.path.join(cache_dir, 'matches')

        for cur_path in [self.tournament_cache_dir, self.match_cache_dir,
                         self.output_dir]:
            if not os.path.isdir(cur_path):
                os.makedirs(cur_path)

        self.base_url = 'https://www.sofascore.com'

        self.surface_lookup = {
            'Hardcourt indoor': Surfaces.indoor_hard,
            'Clay': Surfaces.clay,
            'Hardcourt outdoor': Surfaces.hard,
            'Hard': Surfaces.hard,
            'Grass': Surfaces.grass
        }

        self.rounds_numbers = {x: i for i, x in enumerate(
            sorted(self.rounds_to_query.keys()))}

    @property
    def rounds_to_query(self):

        # TODO: Could make this more granular (break down qualifying rounds)
        round_lookup = {'44/Qualification?': Rounds.qualifying,
                        '45/Qualification?': Rounds.qualifying,
                        '46/Qualification?': Rounds.qualifying,
                        '54/Qualification?': Rounds.qualifying,
                        '23/R128?': Rounds.last_128,
                        '23/1/64-finals%20(R128)?': Rounds.last_128,
                        '24/1/32-finals%20(R64)?': Rounds.last_64,
                        '25/1/16-finals%20(R32)?': Rounds.last_32,
                        '26/1/8-finals%20(R16)': Rounds.last_16,
                        '24/1/32?': Rounds.last_64,
                        '25/1/16?': Rounds.last_32,
                        '26/1/8?': Rounds.last_16,
                        '27/Quarterfinals?': Rounds.QF,
                        '28/Semifinals?': Rounds.SF,
                        '29/Final?': Rounds.F}

        rounds_to_query = {'matches/round/' + x: y for x, y in
                           round_lookup.items()}

        return rounds_to_query

    @property
    def season_ids(self):

        # These could be scraped, but manually state them for now.
        # TODO: Maybe use beautifulsoup to scrape instead.
        atp_season_ids = {
            2018: 15801,
            2017: 12805,
            2016: 11183,
            2015: 11172,
            2014: 11182,
            2013: 11187,
            2012: 11195,
            2011: 11189,
            2010: 11196,
            2009: 11192
        }

        # Add the ATP part
        season_ids = {(x, Tours.atp): y for x, y in atp_season_ids.items()}

        # WTA appears to be identical until the last three years
        wta_changes = {
            2018: 15802,
            2017: 12809,
            2016: 11216
        }

        wta_ids = atp_season_ids.copy()
        wta_ids.update(wta_changes)
        wta_ids = {(x, Tours.wta): y for x,y in wta_ids.items()}

        season_ids.update(wta_ids)

        return season_ids

    @property
    def tournament_pages(self):
        # FIXME: These could maybe be found somehow rather than magic-ed
        # Also, there are more -- for challengers etc...
        pages = {Tours.atp: '/esi/category/3/tournaments?_=152826353',
                 Tours.wta: '/esi/category/6/tournaments?_=152826440'}

        # Doubles are on the same page
        pages[Tours.atp_doubles] = pages[Tours.atp]
        pages[Tours.wta_doubles] = pages[Tours.wta]

        # I believe mixed is listed under ATP
        pages[Tours.mixed_doubles] = pages[Tours.atp]

        return pages

    def find_tournament_matches(self, tournament_url, tournament_id, season_id,
                                has_happened):

        all_matches = list()
        all_ids = set()

        for cur_link, cur_round in self.rounds_to_query.items():

            logger.debug('Scraping round {} for tournament {}'.format(
                cur_round, tournament_id))

            to_try = tournament_url + cur_link
            cur_cache_file = os.path.join(
                self.tournament_cache_dir, '{}_{}_{}.json'.format(
                    tournament_id, season_id, self.rounds_numbers[cur_link]))

            if is_cached(cur_cache_file) and has_happened:
                logger.debug('Loading cached file.')
                # Load the cache
                json_data = load_cached_json(cur_cache_file)
                # Continue if we don't have information.
                if json_data.keys() == []:
                    logger.debug(
                        'Cached json is empty for round {} and link {}'.format(
                            cur_link, to_try))
                    continue
            else:
                # We need to fetch it instead
                try:
                    json_data = load_json_url(to_try)

                    if has_happened:
                        save_to_cache(json_data, cur_cache_file)
                    else:
                        logger.debug('Not caching since tournament is not'
                                     ' certain to be over.')
                except ValueError:
                    logger.debug(
                        'No json found for round {} and link {}'.format(
                            cur_link, to_try))
                    # Store an empty json so that cache will work.
                    if has_happened:
                        save_to_cache({}, cur_cache_file)
                    else:
                        logger.debug('Not caching since tournament is not'
                                     ' certain to be over.')
                    continue

            # Now that we have the json data, try to extract the information.
            try:
                round_data = json_data['roundMatches']['tournaments'][0]
                events = round_data['events']
                to_add = [{'round': cur_round, 'id': x['id']} for x in events
                          if x['id'] not in all_ids]
                all_matches.extend(to_add)
                all_ids |= set([x['id'] for x in events])

                assert(len(all_matches) == len(all_ids))

            except IndexError:
                logger.debug('json record empty found for round {} '
                             'and link {}'.format(cur_link, to_try))
                continue

        return all_matches

    @staticmethod
    def parse_tournament_html(url, t_type):

        soup = load_html_page(url)
        all_links = soup.find_all('a')

        links = [x.get('href') for x in all_links]
        names = [x.get_text().strip() for x in all_links]
        lookup = {x: y for x, y in zip(names, links)}

        if is_singles(t_type):
            # This is a singles event -- discard doubles
            lookup = {x: y for x, y in lookup.items() if 'Doubles' not in x}
        elif is_standard_doubles(t_type):
            lookup = {x: y for x, y in lookup.items() if 'Doubles' in x and
                      'Mixed' not in x}
        elif is_mixed_doubles(t_type):
            lookup = {x: y for x, y in lookup.items() if 'Mixed' in x}
        else:
            raise ValueError('Unknown tournament type')

        return lookup

    def get_tournament_list(self, t_type=Tours.atp):

        subpage = self.tournament_pages[t_type]
        full_url = self.base_url + subpage
        logger.debug('Fetching tournament list...')
        lookup = self.parse_tournament_html(full_url, t_type)
        logger.debug('Manually adding Montreal.')
        if t_type == Tours.atp:
            lookup['Montreal'] = '/tournament/tennis/atp/montreal/2390'
        logger.debug('Fetched tournament list.')
        return lookup

    @staticmethod
    def entry_from_key_value_list(kv_list, key):

        entry = [x['value'] for x in kv_list if x['name'] == key]
        assert(len(entry) <= 1)
        if len(entry) == 0:
            raise IncompleteException()
        return entry[0]

    def find_surface(self, tournament_json):

        if tournament_json['tournamentInfo'] is None:
            raise IncompleteException('Tournament appears to be incomplete!')

        t_info = tournament_json['tournamentInfo']['tennisTournamentInfo']
        surface_entry = self.entry_from_key_value_list(t_info, 'Ground type')
        surface = self.surface_lookup[surface_entry]

        return surface

    def parse_tournament_json(self, json_data):

        tournament_name = json_data['uniqueTournament']['name']

        surface = self.find_surface(json_data)
        end_date = json_data['tournamentInfo']['endDate']
        end_date = datetime.fromtimestamp(int(end_date))

        return {'surface': surface, 'tournament_name': tournament_name,
                'end_date': end_date}

    def fetch_week_matches(self, json_data):

        all_ids = set()

        tournaments = json_data['events']['weekMatches']['tournaments']

        for cur_ts in tournaments:
            for cur_event in cur_ts['events']:
                all_ids.add(cur_event['id'])

        # The rounds are unknown, so:
        return [{'id': x, 'round': None} for x in all_ids]

    def get_tournament_data(self, tournament_link, year, t_type):

        tournament_id = tournament_link.split('/')[-1]
        season_id = self.season_ids[(year, t_type)]

        logger.debug('Fetching tournament data for {} in year {}...'.format(
            tournament_link, year))

        subpage = '/u-tournament/{}/season/{}/'.format(
            tournament_id, season_id)

        full_url = self.base_url + subpage

        cache_file = os.path.join(
            self.tournament_cache_dir, '{}_{}.json'.format(
                tournament_id, season_id))

        # Tournament start date and end dates are unreliable. Only cache
        # previous years.
        has_happened = year < datetime.now().year

        # TODO: Potentially, the end dates _are_ reliable for the current year.
        # Investigate.
        # TODO: Consider deleting cache for 2018.

        if is_cached(cache_file) and has_happened:
            logger.debug('Using cache.')
            json_data = load_cached_json(cache_file)
            parsed = self.parse_tournament_json(json_data)
        else:
            json_data = load_json_url(full_url + 'json')
            parsed = self.parse_tournament_json(json_data)

            # Only cache if complete, i.e. we are past the end date of the
            # tournament
            if has_happened:
                save_to_cache(json_data, cache_file)

        tournament_matches = self.find_tournament_matches(
            full_url, tournament_id, season_id, has_happened)

        if ('hasRounds' in json_data['events'] and
                not json_data['events']['hasRounds']):
            week_ids = self.fetch_week_matches(json_data)
            already_present = set([x['id'] for x in tournament_matches])
            to_add = [x for x in week_ids if x['id'] not in already_present]
            tournament_matches.extend(to_add)

        parsed['matches'] = tournament_matches

        logger.debug('Parsed.')

        return parsed

    @staticmethod
    def to_score(winner_dict, loser_dict, winner_name, loser_name):

        # TODO: Think about retirements.

        periods = [x for x in winner_dict if 'period' in x
                   and 'TieBreak' not in x]
        periods = sorted(periods, key=lambda x: int(x[-1]))

        set_scores = list()

        for cur_period in periods:

            tb_key = cur_period + 'TieBreak'

            set_score = '{}-{}'.format(winner_dict[cur_period],
                                       loser_dict[cur_period])

            if tb_key in winner_dict:

                winner_score = winner_dict[tb_key]
                loser_score = loser_dict[tb_key]
                tb_score = (winner_score if winner_score < loser_score else
                            loser_score)
                set_score += '({})'.format(tb_score)

            set_scores.append(set_score)

        full_score = ' '.join(set_scores)

        return Score(full_score, winner_name, loser_name)

    @staticmethod
    def extract_match_data(match_json_data):

        try:

            event_details = match_json_data['event']
            was_finished = event_details['statusDescription'] == 'FT'

            # Let's find winner and loser
            home = event_details['homeTeam']
            away = event_details['awayTeam']

            # TODO: This seems to be an abbreviated name. Maybe get the full name
            # from elsewhere.
            home_name = unidecode(home['name'])
            away_name = unidecode(away['name'])

            # Not sure -- check this
            home_won = event_details['winnerCode'] == 1
            winner = home_name if home_won else away_name
            loser = home_name if not home_won else away_name
            match_date = datetime.fromtimestamp(event_details['startTimestamp'])

            # Extract the score
            away_score = event_details['awayScore']
            home_score = event_details['homeScore']

            winner_score = home_score if home_won else away_score
            loser_score = away_score if home_won else home_score

        except KeyError:
            logger.debug('KeyError when extracting match data.')
            raise IncompleteException()

        try:
            score = SofaScoreScraper.to_score(winner_score, loser_score, winner,
                                              loser)
        except BadFormattingException:
            logger.debug('Failed to parse score in match {}.'.format(
                event_details['id']))
            score = None
        except KeyError:
            logger.debug('There was an issue parsing match {}.'.format(
                event_details['id']))
            score = None

        if (match_json_data['statistics'] is not None
                and 'homeServicePointsTotal' in match_json_data['statistics']):
            statistics = SofaScoreScraper.parse_statistics(
                match_json_data['statistics'], home_name, away_name)
        else:
            statistics = None

        return {'winner': winner, 'loser': loser, 'score': score,
                'date': match_date, 'stats': statistics,
                'was_finished': was_finished}

    @staticmethod
    def parse_statistics(player_statistics, home_name, away_name):

        stats = dict()

        for cur_player, cur_id in zip(
                [home_name, away_name], ['home', 'away']):

            cur_serve_played = player_statistics[cur_id + 'ServicePointsTotal']
            cur_serve_won = player_statistics[cur_id + 'ServicePointsScored']

            cur_return_played = player_statistics[cur_id + 'ReceiverPointsTotal']
            cur_return_won = player_statistics[cur_id + 'ReceiverPointsScored']

            cur_stats = MatchStats(
                cur_player,
                serve_points_played=cur_serve_played,
                serve_points_won=cur_serve_won,
                return_points_played=cur_return_played,
                return_points_won=cur_return_won
            )

            stats[cur_player] = cur_stats

        return stats

    def get_match_data_from_id(self, match_id):

        logger.debug('Parsing match data for match id {}...'.format(match_id))

        # TODO: Could make a function handling the path generation instead.
        cache_path = os.path.join(
            self.match_cache_dir, '{}.json'.format(match_id))

        if is_cached(cache_path):
            logger.debug('Using cache.')
            json_data = load_cached_json(cache_path)
            match_data = self.extract_match_data(json_data)
        else:
            subpage = '/event/{}/json'.format(match_id)
            full_url = self.base_url + subpage
            json_data = load_json_url(full_url)
            match_data = self.extract_match_data(json_data)

            if match_data['date'] < datetime.now():
                save_to_cache(json_data, cache_path)

        logger.debug('Parsed.')

        return match_data

    def parse_tournament(self, tournament_link, year, t_type):

        # Get match ids
        tournament_data = self.get_tournament_data(
            tournament_link, year, t_type)

        # Find the match ids
        match_ids = [x['id'] for x in tournament_data['matches']]
        assert(len(set(match_ids)) == len(match_ids))

        match_data = list()

        for cur_id in match_ids:
            try:
                cur_match_data = self.get_match_data_from_id(cur_id)
                match_data.append(cur_match_data)
            except IncompleteException:
                # TODO: Think about whether this is OK. Basically, we're
                # skipping incomplete matches in tournaments.
                continue

        # Make matches out of these, discarding those without a score
        matches = [CompletedMatch(
            x['winner'], x['loser'], x['date'], x['winner'], x['score'],
            surface=tournament_data['surface'], stats=x['stats'],
            tournament_round=y['round'],
            tournament_name=tournament_data['tournament_name'],
            additional_info={'sofa_id': y['id']},
            was_retirement=not x['was_finished'])
            for x, y in zip(match_data, tournament_data['matches']) if
            x['score'] is not None]

        return matches

    def scrape_year(self, year, t_type=Tours.atp):

        all_matches = list()

        t_list = scraper.get_tournament_list(t_type=t_type)

        for t in tqdm(t_list.items()):

            try:
                matches = scraper.parse_tournament(t[1], year, t_type)
                all_matches.extend(matches)
            except IncompleteException:
                continue
            except ValueError:
                continue

        df = CompletedMatch.to_df(all_matches)

        target_dir = os.path.join(self.output_dir, t_type.name)

        if not os.path.isdir(target_dir):
            os.makedirs(target_dir)

        target_path = os.path.join(target_dir, '{}.csv'.format(year))

        df.to_csv(target_path)

if __name__ == '__main__':

    # TODO: Skip scraping tournaments that haven't started yet.

    from tqdm import tqdm

    scraper = SofaScoreScraper()
    to_scrape = [x for x in scraper.season_ids.keys() if x[1] == Tours.wta]
    for year, t_type in sorted(to_scrape, key=lambda x: x[0], reverse=True):
        logger.debug('Scraping year {}'.format(year))
        scraper.scrape_year(year, t_type=t_type)
        logger.debug('Done scraping year {}'.format(year))
