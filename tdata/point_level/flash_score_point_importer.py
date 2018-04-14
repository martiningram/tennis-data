import os
import json
from glob import glob
from datetime import datetime
from tdata.datasets.score import Score
from tdata.datasets.match import CompletedMatch
from tdata.point_level.point_utils import generate_points
from tdata.point_level.monte_carlo.monte_carlo import Score as MCScore


# TODO: Handle non-TB final set
# TODO: Parse event and event round
# TODO: Maybe rename one of the "Score" objects -- it's not great that
# there are two.
# TODO: Investigate why stats seem out of whack. Am I getting the serve order
# right?

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

            cur_set_str = str_odd[0] + '-' + str_even[0]

            if odd_score > 7 or even_score > 7:
                # It was a tiebreak
                assert ('6' in cur_set_str) and ('7' in cur_set_str)
                tb_score = min(map(int, [str_odd[1:], str_even[1:]]))
                cur_set_str += '({})'.format(tb_score)

            set_results.append(cur_set_str)

        return ' '.join(set_results)

    @staticmethod
    def score_as_int(score):

        mapping = {'0': 0, '15': 1, '30': 2, '40': 3, 'A': 4}
        return mapping[score]

    @staticmethod
    def parse_service_game(service_game_str, server_is_first=True):

        old_score = (0, 0)

        # Split each point
        points = [x.strip() for x in service_game_str.split(',')]

        first_player_won = list()

        for cur_point in points:

            # Remove all extra annotations
            cur_point = ''.join([x for x in cur_point if x.isdigit() or x ==
                                 'A' or x == ':'])

            score_a, score_b = cur_point.split(':')

            # Convert to integers
            score_a, score_b = map(FlashScorePointImporter.score_as_int,
                                   [score_a, score_b])

            first_player_won.append(old_score[0] < score_a or
                                    old_score[1] > score_b)

            old_score = (score_a, score_b)

        # Parse the final point
        first_player_won.append(old_score[0] > old_score[1])

        if not server_is_first:
            server_won = [not x for x in first_player_won]
        else:
            server_won = first_player_won

        return server_won

    @staticmethod
    def parse_score_history(score_history):

        # Returns a list of game point sequences in the correct order, with
        # each one having a flag of whether it is a tiebreak or not.

        cur_history = score_history

        tiebreak_sequences = list()
        without_tiebreak = list()

        def find_candidates(cur_history):

            return [i for i, x in enumerate(cur_history) if
                    (x[0] == 7 and x[1] == 6) or (x[0] == 6 and x[1] == 7)]

        candidates = find_candidates(cur_history)

        while len(candidates) > 0:

            # Find the tiebreak end
            cur_candidate = candidates[0]
            cur_sub_history = cur_history[cur_candidate + 1:]

            tiebreak_end = [i for i, x in enumerate(cur_sub_history) if
                            abs(x[0] - x[1]) >= 2 and (x[0] >= 7 or x[1] >= 7)]

            assert(len(tiebreak_end) >= 1)

            # Slice out the tiebreak
            tiebreak_sequences.append(cur_sub_history[:tiebreak_end[0] + 1])
            without_tiebreak.extend(cur_history[:cur_candidate + 1])

            # Update the history
            cur_history = cur_history[cur_candidate + tiebreak_end[0] + 2:]
            candidates = find_candidates(cur_history)

        without_tiebreak.extend(cur_history)

        return {'game_score_sequence': without_tiebreak,
                'tiebreak_sequences': tiebreak_sequences}

    @staticmethod
    def find_win_sequence(point_sequence, game_score_sequence,
                          tiebreak_sequence):

        point_sequence = [point_sequence[x] for x in sorted(
            point_sequence.keys(), key=int)]

        point_sequence = [FlashScorePointImporter.parse_service_game(
            x, server_is_first=i % 2 == 0) for i, x in
            enumerate(point_sequence)]

        # Find any tiebreaks
        tiebreaks = [i for i, x in enumerate(game_score_sequence)
                     if x[0] == 6 and x[1] == 6]

        assert(len(tiebreaks) == len(tiebreak_sequence))

        for cur_tiebreak, cur_sequence in zip(tiebreaks, tiebreak_sequence):

            # Who is serving?
            odd_serving_first = cur_tiebreak % 2 == 0

            # Parse this one
            parsed_tiebreak = FlashScorePointImporter.parse_tiebreak(
                cur_sequence, odd_serving_first)

            # insert the score sequence
            point_sequence.insert(cur_tiebreak + 1, parsed_tiebreak)

        assert(len(point_sequence) == len(game_score_sequence))

        # Flatten the win sequence
        flattened = [y for x in point_sequence for y in x]

        return flattened

    @staticmethod
    def parse_tiebreak(tiebreak_sequence, odd_serves_first=True):

        prev_score = (0, 0)
        server_won = list()

        for cur_score in tiebreak_sequence:

            if odd_serves_first:
                odd_serving = sum(prev_score) % 4 in [0, 3]
            else:
                odd_serving = sum(prev_score) % 4 in [1, 2]

            server_won.append(
                (cur_score[0] > prev_score[0] and odd_serving) or
                (cur_score[1] > prev_score[1] and not odd_serving))

            prev_score = cur_score

        return server_won

    def parse_match(self, match_dict):

        p1 = match_dict['player_scores']['full_name_odd_server']
        p2 = match_dict['player_scores']['full_name_even_server']
        match_date = datetime.strptime(match_dict['match_date'],
                                       '%d.%m.%Y %H:%M')
        winner = (p1 if (match_dict['player_scores']['odd_sets_won'] >
                         match_dict['player_scores']['even_sets_won'])
                  else p2)
        loser = p1 if winner == p2 else p2

        final_score = match_dict['player_scores']['final_score']

        string_version = self.convert_to_string_score(final_score)
        parsed_score = Score(string_version, winner, loser)

        sequence = match_dict['point_sequence']

        parsed_tbs = self.parse_score_history(match_dict['score_history'])

        win_sequence = self.find_win_sequence(
            sequence, parsed_tbs['game_score_sequence'],
            parsed_tbs['tiebreak_sequences'])

        # Parse this back
        initial_score = MCScore(p1, p2, bo5=parsed_score.bo5)

        point_sequence, advanced_score = generate_points(
            initial_score, win_sequence)

        match = CompletedMatch(p1=p1, p2=p2, winner=winner, date=match_date,
                               score=parsed_score, points=point_sequence,
                               final_point_level_info=advanced_score)

        return match

    def get_match_generator(self, skip_on_error=False):
        for cur_dict in self.all_loaded:
            try:
                yield self.parse_match(cur_dict)
            except AssertionError as e:
                if skip_on_error:
                    print("Found error: {} but continuing.".format(e))
                    continue
                else:
                    raise AssertionError(e)

if __name__ == '__main__':

    importer = FlashScorePointImporter()

    try:
        parsed = importer.parse_match(importer.all_loaded[3])
        print(parsed)
        print(parsed.final_point_level_info)
    except AssertionError as e:
        print(e)
