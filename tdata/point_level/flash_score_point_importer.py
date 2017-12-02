import os
import json
from glob import glob
from datetime import datetime
from tdata.datasets.score import Score
from tdata.datasets.match import CompletedMatch


class FlashScorePointImporter(object):

    def __init__(self, data_path='./data/flashscore/'):

        all_scraped = glob(os.path.join(data_path, '*.json'))
        self.all_loaded = self.load_json_files(all_scraped)

    @staticmethod
    def load_json_files(json_files):

        loaded = list()

        for cur_file in json_files:
            with open(cur_file) as f:
                loaded.append(json.load(f))

        return loaded

    @staticmethod
    def convert_to_string_score(final_score):

        set_results = list()

        for cur_set in final_score:

            odd_score, even_score = cur_set

            str_odd, str_even = map(str, cur_set)

            games_won_odd, games_won_even = map(
                int, [str_odd[0], str_even[0]])

            if games_won_odd > games_won_even:
                cur_set_str = str_odd[0] + '-' + str_even[0]
            else:
                cur_set_str = str_even[0] + '-' + str_odd[0]

            if odd_score > 7 or even_score > 7:
                # It was a tiebreak
                assert ('6' in cur_set_str) and ('7' in cur_set_str)
                tb_score = min(map(int, [str_odd[1:], str_even[1:]]))
                cur_set_str += '({})'.format(tb_score)

            set_results.append(cur_set_str)

        return ' '.join(set_results)

    def parse_match(self, match_dict):

        p1 = match_dict['player_scores']['full_name_odd_server']
        p2 = match_dict['player_scores']['full_name_even_server']
        match_date = datetime.strptime(match_dict['match_date'], '%d.%m.%Y %H:%M')
        winner = (p1 if (match_dict['player_scores']['odd_sets_won'] >
                         match_dict['player_scores']['even_sets_won'])
                  else p2)
        loser = p1 if winner == p2 else p2

        final_score = match_dict['player_scores']['final_score']
        string_version = self.convert_to_string_score(final_score)
        parsed_score = Score(string_version, winner, loser)


if __name__ == '__main__':

    importer = FlashScorePointImporter()

    print(importer.parse_match(importer.all_loaded[100]))
