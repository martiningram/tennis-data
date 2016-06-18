import re
import json
import urllib2
import pandas as pd

from datetime import date
from bs4 import BeautifulSoup


class MatchStatScraper(object):

    def __init__(self):
        pass

    def get_calendar(self, year):

        cur_year = date.today().year

        assert(year <= cur_year)

        if year == cur_year:
            return 'https://matchstat.com/tennis/calendar'
        else:
            return 'https://matchstat.com/tennis/calendar/' + str(year)

    def get_tournament_links(self, year, t_type='atp'):

        calendar = self.get_calendar(year)

        # Open calendar
        page = urllib2.urlopen(calendar)
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

        # Extract player names
        players = match_data.find_all('td', class_='player-name')

        assert(len(players) == 2)

        winner = players[0].find('a', class_='w')
        loser = players[1].find('a')

        return winner, loser

    def get_odds(self, match_data):

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

    def get_stats(self, match_data, winner_name, loser_name):

        cur_results = {}

        stats = match_data.find('a', class_='btn-stats')

        if stats is not None:

            link = stats.get('href')
            data = urllib2.urlopen(link)
            parsed = BeautifulSoup(data, 'html.parser')
            loaded = json.loads(parsed.string)

            if 'stats' in loaded:

                stat_list = loaded['stats']

            else:

                stat_list = []

            for stat_dict in stat_list:

                cur_player = stat_dict['player_fullname']

                assert(cur_player in [winner_name, loser_name])

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

        # Open the page
        page = urllib2.urlopen(tournament_link)
        soup = BeautifulSoup(page, 'html.parser')

        match_highlights = soup.find_all('tr',
                                            class_=re.compile('match *'))

        results = list()

        for match_data in match_highlights:

            cur_results = {}

            winner, loser = self.get_winner_loser(match_data)

            if winner is None or loser is None:
                continue

            winner_name = winner.string.strip()
            loser_name = loser.string.strip()

            cur_results.update({'winner': winner_name,
                                'loser': loser_name})

            cur_results.update(self.get_odds(match_data))

            # Extract the score
            score = match_data.find('div', class_='score-content')

            if score is not None:

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

                cur_results.update(
                    self.get_stats(match_data, winner_name, loser_name))

            results.append(cur_results)

        results = pd.DataFrame(results)

        return results

    def scrape_all(self, year, t_type='atp'):

        data = self.get_tournament_links(year, t_type=t_type)

        # Only keep times before now
        cur_date = date.today()

        data = data[data['start_date'] < cur_date]

        all_dfs = list()

        for i, (index, tournament) in enumerate(data.iterrows()):

            print('Current tournament is: {}'.format(
                tournament['tournament_name']))

            cur_link = tournament['tournament_link']

            cur_data = self.get_tournament_data(cur_link, get_stats=True)

            for value in tournament.index:

                cur_data[value] = tournament[value]

            all_dfs.append(cur_data)

        all_dfs = pd.concat(all_dfs, ignore_index=True)

        return all_dfs


if __name__ == '__main__':

    scraper = MatchStatScraper()
    all_data = scraper.scrape_all(2016)

    all_data.to_csv('2016_atp.csv', encoding='utf-8')
