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

        # TODO: I think this is right, but could check
        # self.round_lookup = {
        #     'Qualification': Rounds.qualifying,
        #     '1/64': Rounds.last_128,
        #     '1/32': Rounds.last_64,
        #     '1/16': Rounds.last_32,
        #     '1/8': Rounds.last_16,
        #     'Quarterfinals': Rounds.QF,
        #     'Semifinals': Rounds.SF,
        #     'Final': Rounds.F
        # }

        # Could make this more granular
        round_lookup = {'44/Qualification?': Rounds.qualifying,
                        '45/Qualification?': Rounds.qualifying,
                        '46/Qualification?': Rounds.qualifying,
                        '54/Qualification?': Rounds.qualifying,
                        '23/R128?': Rounds.last_128,
                        '23/1-64-finals%20(R128)?': Rounds.last_128,
                        '24/1/32?': Rounds.last_64,
                        '24/1/32-finals%20(R64)?': Rounds.last_64,
                        '25/1/16?': Rounds.last_32,
                        '25/1/16-finals%20(R32)?': Rounds.last_32,
                        '26/1/8?': Rounds.last_16,
                        '26/1/8-finals%20(R16)': Rounds.last_16,
                        '27/Quarterfinals?': Rounds.QF,
                        '28/Semifinals?': Rounds.SF,
                        '29/Final?': Rounds.F}

        self.rounds_to_query = {'matches/round/' + x: y for x, y in
                                round_lookup.items()}

        self.rounds_numbers = {x: i for i, x in enumerate(
            self.rounds_to_query.keys())}

    @property
    def season_ids(self):

        # These could be scraped, but manually state them for now.
        # TODO: Maybe use beautifulsoup to scrape instead.
        season_ids = {
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

            if is_cached(cur_cache_file):
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
                except ValueError:
                    logger.debug(
                        'No json found for round {} and link {}'.format(
                            cur_link, to_try))
                    # Store an empty json so that cache will work.
                    if has_happened:
                        save_to_cache({}, cur_cache_file)
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

        t_info = tournament_json['tournamentInfo']['tennisTournamentInfo']
        surface_entry = self.entry_from_key_value_list(t_info, 'Ground type')
        surface = self.surface_lookup[surface_entry]

        return surface

    def parse_tournament_json(self, json_data):

        tournament_name = json_data['uniqueTournament']['name']

        if 'weekMatches' not in json_data['events']:
            logger.debug('{} appears to be incomplete!'.format(
                tournament_name))
            raise IncompleteException()

        event_list = json_data['events']['weekMatches']['tournaments'][0][
            'events']

        surface = self.find_surface(json_data)
        end_date = self.entry_from_key_value_list(
            json_data['tournamentInfo']['tennisTournamentInfo'], 'End date')
        end_date = datetime.fromtimestamp(float(end_date))

        return {'surface': surface, 'tournament_name': tournament_name,
                'end_date': end_date}

    def get_tournament_data(self, tournament_link, year):

        tournament_id = tournament_link.split('/')[-1]
        season_id = self.season_ids[year]

        logger.debug('Fetching tournament data for {} in year {}...'.format(
            tournament_link, year))

        subpage = '/u-tournament/{}/season/{}/'.format(
            tournament_id, season_id)

        full_url = self.base_url + subpage

        cache_file = os.path.join(
            self.tournament_cache_dir, '{}_{}.json'.format(
                tournament_id, season_id))

        if is_cached(cache_file):
            logger.debug('Using cache.')
            json_data = load_cached_json(cache_file)
            parsed = self.parse_tournament_json(json_data)
        else:
            json_data = load_json_url(full_url + 'json')
            parsed = self.parse_tournament_json(json_data)

            # Only cache if complete, i.e. we are past the end date of the
            # tournament
            if datetime.now() > parsed['end_date']:
                save_to_cache(json_data, cache_file)

        has_happened = datetime.now() > parsed['end_date']

        tournament_matches = self.find_tournament_matches(
            full_url, tournament_id, season_id, has_happened)

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

    def parse_tournament(self, tournament_link, year):

        # Get match ids
        tournament_data = self.get_tournament_data(tournament_link, year)

        # Find the match ids
        match_ids = [x['id'] for x in tournament_data['matches']]
        assert(len(set(match_ids)) == len(match_ids))
        match_data = [self.get_match_data_from_id(x) for x in match_ids]

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

        t_list = scraper.get_tournament_list()

        for t in tqdm(t_list.items()):

            try:
                matches = scraper.parse_tournament(t[1], year)
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

    # TODO: Check that tournaments in the future are definitely skipped and that
    # there is no mistaken caching.

    from tqdm import tqdm

    scraper = SofaScoreScraper()
    t_list = scraper.get_tournament_list()
    for year in sorted(scraper.season_ids.keys(), reverse=True):
        logger.debug('Scraping year {}'.format(year))
        scraper.scrape_year(year, t_type=Tours.atp)
        logger.debug('Done scraping year {}'.format(year))
