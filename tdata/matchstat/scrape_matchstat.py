import os
import re
import json
import urllib2
import logging
import pandas as pd
import cPickle as pkl

from datetime import date
from bs4 import BeautifulSoup
from tdata.utils import retry

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Make sure we write to log
fh = logging.FileHandler('scrape_log.log')
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)


class ScrapingException(Exception):
    pass


class MatchStatScraper(object):
    """Scrapes match data from MatchStat.com."""

    def __init__(self):

        self.cache_path = 'data/cache/'

        self.tournament_surfaces = dict()

        if os.path.isfile(self.cache_path + 'surfaces.pkl'):

            self.tournament_surfaces = pkl.load(
                open(self.cache_path + 'surfaces.pkl', 'rb'))

    def find_surface(self, p1, p2, tournament_link):

        if tournament_link in self.tournament_surfaces:
            return self.tournament_surfaces[tournament_link]

        # Find h2h:
        base_link = 'https://matchstat.com/tennis/h2h-odds-bets/'

        p1_alt = p1.replace(' ', '%20')
        p2_alt = p2.replace(' ', '%20')

        h2h_link = base_link + p1_alt + '/' + p2_alt

        page = self.get_page(h2h_link)

        soup = BeautifulSoup(page, 'html.parser')

        for entry in soup.find_all('tr', class_="date h2h-entry"):

            cur_link = entry.find('td', class_='tmt').find('a').get('href')

            if cur_link != tournament_link:
                continue

            surface = entry.find('span', class_=re.compile('label*')).string

        self.tournament_surfaces[tournament_link] = surface

        # Update the pickle:
        pkl.dump(self.tournament_surfaces,
                 open(self.cache_path + 'surfaces.pkl', 'wb'))

        return surface

    def get_calendar_link(self, year):
        """Helper function returning link to calendar site.

        Args:
            year (int): The year to get the link for.

        Returns:
            str: The link to the calendar for that year.
        """

        cur_year = date.today().year

        assert(year <= cur_year)

        if year == cur_year:
            return 'https://matchstat.com/tennis/calendar'
        else:
            return 'https://matchstat.com/tennis/calendar/' + str(year)

    def get_tournament_links(self, year, t_type='atp'):
        """Fetches links to the tournament result pages for the year and tour
        given.

        Args:
            year (int): The year to fetch tournament links for.
            t_type (str): The tour to fetch tournament links for [either atp or
                wta].

        Returns:
            pd.DataFrame: A DataFrame containing fields tournament_name,
                start_date, tournament_link.
        """

        calendar_link = self.get_calendar_link(year)

        # Open calendar
        page = self.get_page(calendar_link)

        soup = BeautifulSoup(page, 'html.parser')

        # Find the links
        trs = soup.find_all('tr')

        results = list()

        for tr in trs:

            # Note: looking for just br like this could be prone to breaking.
            start_date = tr.find('br')

            if start_date is None:
                continue

            start_date = start_date.string.strip()

            cur_tournaments = tr.find_all('span', class_=t_type)

            for tournament in cur_tournaments:

                results.append({'start_date': start_date,
                                'tournament_name': tournament.a.string.strip(),
                                'tournament_link': tournament.a.get('href')})

        results = pd.DataFrame(results)
        results['start_date'] = pd.to_datetime(results['start_date'])

        return results

    def get_winner_loser(self, match_data):
        """Extracts winner and loser link objects from the match data given.

        Args:
            match_data (BeautifulSoup object): The match data scraped for this
                match.

        Returns:
            Pair[BeautifulSoup object, BeautifulSoup object]: The winner and
            loser link objects.
        """

        # Extract player names
        players = match_data.find_all('td', class_='player-name')

        if len(players) != 2:

            raise ScrapingException(
                'Only found {} players; expecting 2.'.format(len(players)))

        winner = players[0].find('a', class_='w')
        loser = players[1].find('a')

        return winner, loser

    def get_odds(self, match_data):
        """Extracts winner and loser odds from the match data.

        Args:
            match_data (BeautifulSoup object): The match data scraped for this
                match.

        Returns:
            Dict[str] to float: A dictionary containing keys 'odds_winner' and
            'odds_loser' containing the winner and loser's odds, respectively,
            if odds are available; the dictionary misses entries if they are
            not available.
        """

        cur_results = {}

        # Extract the odds
        odds_winner = match_data.find('td', class_='odds-td odds-0')
        odds_loser = match_data.find('td', class_='odds-td odds-1')

        if odds_winner is not None:

            span = odds_winner.find('span')

            if span is not None:

                cur_results['odds_winner'] = span.string.strip()

        if odds_loser is not None:

            span = odds_loser.find('span')

            if span is not None:

                cur_results['odds_loser'] = span.string.strip()

        return cur_results

    @retry(urllib2.URLError, tries=4, delay=3, backoff=2)
    def get_page(self, link):

        data = urllib2.urlopen(link, timeout=10)
        return data

    def get_stats(self, match_data, winner_name, loser_name):
        """Fetches the match statistics for the match.

        Args:
            match_data (BeautifulSoup object): The match data scraped for this
                match.
            winner_name (str): The match winner's name.
            loser_name (str): The match loser's name.

        Returns:
            dict[str] to value: Returns various statistics, using the naming
            MatchStat uses, but prefixing them with winner and loser.

        Example:
            One entry may be 'loser_points_won', which has a corresponding
            entry 'winner_points_won' for the winning player.
        """

        cur_results = {}

        stats = match_data.find('a', class_='btn-stats')

        if stats is not None:

            link = stats.get('href')
            data = self.get_page(link)
            parsed = BeautifulSoup(data, 'html.parser')
            loaded = json.loads(parsed.string)

            if 'stats' in loaded:

                stat_list = loaded['stats']

            else:

                stat_list = []

            for stat_dict in stat_list:

                cur_player = stat_dict['player_fullname']

                if cur_player not in [winner_name, loser_name]:

                    raise ScrapingException(
                        'Could not find player {} in stat_dict.')

                if cur_player == winner_name:

                    new_dict = {'winner_' + x: stat_dict[x] for x in
                                stat_dict}

                    cur_results.update(new_dict)

                elif cur_player == loser_name:

                    new_dict = {'loser_' + x: stat_dict[x] for x in
                                stat_dict}

                    cur_results.update(new_dict)

        return cur_results

    def get_tournament_data(self, tournament_link, get_stats=False):
        """Fetches all match data available for the tournament linked.

        Args:
            tournament_link (str): The link to MatchStat.com's tournament
                results page.
            get_stats (Optional[bool]): If True, fetches match statistics.

        Returns:
            pd.DataFrame: A DataFrame containing a row with information for
            each match.
        """

        # Open the page
        page = self.get_page(tournament_link)
        soup = BeautifulSoup(page, 'html.parser')

        match_highlights = soup.find_all('tr', class_=re.compile('match *'))

        results = list()

        for match_data in match_highlights:

            cur_results = {}

            try:
                winner, loser = self.get_winner_loser(match_data)

            except ScrapingException as s:
                logger.debug(s)
                continue

            if winner is None or loser is None:
                continue

            winner_name = winner.string.strip()
            loser_name = loser.string.strip()

            cur_results.update({'winner': winner_name,
                                'loser': loser_name})

            # Fetch the surface:
            surface = self.find_surface(
                winner_name, loser_name, tournament_link)

            cur_results.update({'surface': surface})

            cur_results.update(self.get_odds(match_data))

            # Extract the score
            score = match_data.find('div', class_='score-content')

            if score is not None:

                if score.a.string is None:

                    logger.debug(
                        'Found score string which is None: {}'.format(score))

                    continue

                score_str = score.a.string.strip()
                cur_results['score'] = score_str.replace(u'\u2011', '-')

            # Get the h2h
            h2h = match_data.find('a', class_='h2h')

            if h2h is not None:

                h2h_str = h2h.string
                cur_results['h2h'] = h2h_str

            # Get the round
            t_round = match_data.find('td', class_='round')

            if t_round is not None:

                cur_results['round'] = t_round.string.strip()

            if get_stats:

                try:

                    result = self.get_stats(match_data, winner_name,
                                            loser_name)

                    cur_results.update(result)

                except ScrapingException as s:
                    logger.debug(s)
                    continue

            results.append(cur_results)

        results = pd.DataFrame(results)

        return results

    def scrape_all(self, year, t_type='atp', use_cache=True):
        """Scrapes all available matches in the given year for the given tour.

        Args:
            year (int): The year to scrape matches for.
            t_type (str): The tour type to scrape. Can be either atp or wta.

        Returns:
            pd.DataFrame: A DataFrame with one row of info per match.
        """

        cache_dir = os.path.join(self.cache_path, t_type)

        data = self.get_tournament_links(year, t_type=t_type)

        # Only keep times before now
        cur_date = date.today()

        data = data[data['start_date'] < cur_date]

        all_dfs = list()

        for i, (index, tournament) in enumerate(data.iterrows()):

            logger.info('Current tournament is: {} {}'.format(
                tournament['tournament_name'], year))

            cache_name = '{}/{}_{}_cached.csv'.format(
                cache_dir, tournament['tournament_name'].replace('/', ' '),
                year)

            if use_cache and os.path.isfile(cache_name):

                logger.info('Using cached csv.')

                cur_data = pd.read_csv(cache_name, index_col=0)

            else:

                cur_link = tournament['tournament_link']

                cur_data = self.get_tournament_data(cur_link, get_stats=True)

                for value in tournament.index:

                    cur_data[value] = tournament[value]

                if use_cache:

                    if not os.path.isdir(cache_dir):

                        os.makedirs(cache_dir)

                    cur_data.to_csv(cache_name, encoding='utf-8')

            all_dfs.append(cur_data)

        all_dfs = pd.concat(all_dfs, ignore_index=True)

        return all_dfs


if __name__ == '__main__':

    scraper = MatchStatScraper()

    print(scraper.find_surface(
        'Roger Federer', 'Rafael Nadal',
        'https://matchstat.com/tennis/tournaments/m/Basel/2015'))

    # for year in [2016]:

    #    all_data = scraper.scrape_all(year, t_type='atp')
    #    all_data.to_csv('data/year_csvs/{}_atp.csv'.format(year),
    #                    encoding='utf-8')
