from selenium.webdriver.common.by import By
from tdata.scrapers.flashscore.utils import wait_for_element_and_parse


class FlashScoreMatchInfo(object):

    def __init__(self, match_website, driver, max_delay=10):

        driver.get(match_website)

        cur_source = wait_for_element_and_parse(
            driver, 'odd', max_delay, by=By.CLASS_NAME)

        # Find out whether it has finished
        self.is_over = self.has_finished(cur_source)

        # Find event_name and date
        event_name_date = self.event_name_and_date(cur_source)

        self.event_name = event_name_date['event_name']
        self.match_date = event_name_date['match_date']
        self.player_scores = self.extract_player_scores(cur_source)

        # Make sure next link is available
        wait_for_element_and_parse(
            driver, 'Point by Point', max_delay)

        # Navigate to point by point
        driver.find_element_by_partial_link_text('Point by Point').click()

        cur_source = wait_for_element_and_parse(
            driver, 'tab-mhistory-1-history', max_delay, by=By.ID)

        # Get point sequence
        self.point_sequence = self.get_point_sequence(cur_source)
        self.score_history = self.get_score_history(cur_source)

    def to_dict(self):

        return {'is_over': self.is_over,
                'event_name': self.event_name,
                'match_date': self.match_date,
                'player_scores': self.player_scores,
                'point_sequence': self.point_sequence,
                'score_history': self.score_history}

    @staticmethod
    def get_score_history(point_by_point_page):

        score_history = list()

        # Find the scoring history
        all_scores = point_by_point_page.find_all(
            'td', class_='match-history-score')

        # Extract the scores
        for cur_td in all_scores:

            # Find the spans
            spans = cur_td.find_all('span')

            # Extract the score
            score_history.append((int(spans[0].contents[0]),
                                  int(spans[1].contents[0])))

        return score_history

    @staticmethod
    def parse_history(history):

        score_sequence = list()

        for cur_tr in history:

            contents = cur_tr.find('td').text

            score_sequence.append(contents)

        return score_sequence

    @staticmethod
    def get_point_sequence(point_by_point_page):

        # FIXME: There is a problem here. It looks like at set changes, the
        # "even" and "odd" distinction might reset, or something to that effect.
        # This needs to be fixed, otherwise everything gets messed up...!

        odd_history = point_by_point_page.find_all(
            'tr', class_='odd fifteen')

        even_history = point_by_point_page.find_all(
            'tr', class_='even fifteen')

        odd_history = FlashScoreMatchInfo.parse_history(odd_history)
        even_history = FlashScoreMatchInfo.parse_history(even_history)

        # Make a series out of these
        odd_history = {i: x for i, x in enumerate(odd_history)}
        even_history = {i: x for i, x in enumerate(even_history)}

        odd_history = {i * 2 + 1: x for i, x in odd_history.items()}
        even_history = {i * 2 + 2: x for i, x in even_history.items()}

        full_history = dict(odd_history.items() + even_history.items())

        # Try to zip these together
        return full_history

    @staticmethod
    def scores_from_player_page(player_page):

        all_scores = player_page.find_all('td', class_='score')

        sets_won = int(all_scores[0].text)

        set_games_won = list()

        for cur_other_set in all_scores[1:]:

            try:
                set_games_won.append(int(cur_other_set.text))
            except ValueError:
                pass

        return {'sets_won': sets_won,
                'set_games_won': set_games_won}

    @staticmethod
    def extract_player_scores(summary_page):

        summary_content = summary_page.find(
            'div', id='summary-content')

        even_player = summary_content.find(
            'tr', class_='even')

        odd_player = summary_content.find(
            'tr', class_='odd')

        even_player_name = even_player.find('a').text
        odd_player_name = odd_player.find('a').text

        full_names_from_title = [x.strip() for x in summary_page.find(
            'title').text.split('|')[1].split(' - ')]

        odd_player_name_full, even_player_name_full = full_names_from_title

        scores_even = FlashScoreMatchInfo.scores_from_player_page(even_player)
        scores_odd = FlashScoreMatchInfo.scores_from_player_page(odd_player)

        even_set_games_won = scores_even['set_games_won']
        odd_set_games_won = scores_odd['set_games_won']

        final_score = [(x, y) for x, y in zip(odd_set_games_won,
                                              even_set_games_won)]

        return {'odd_server': odd_player_name,
                'even_server': even_player_name,
                'full_name_odd_server': odd_player_name_full,
                'full_name_even_server': even_player_name_full,
                'even_sets_won': scores_even['sets_won'],
                'odd_sets_won': scores_odd['sets_won'],
                'final_score': final_score}

    @staticmethod
    def event_name_and_date(match_page):

        event_name = match_page.find('th', class_='header').text.strip()
        match_date = match_page.find('td', class_='mstat-date').text

        return {'event_name': event_name,
                'match_date': match_date}

    @staticmethod
    def has_finished(match_page):

        return match_page.find('td', class_='mstat').text == u'Finished'
