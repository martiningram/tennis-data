import pandas as pd

import tdata.point_level.monte_carlo.monte_carlo as mc
from copy import deepcopy
from tdata.datasets.match import CompletedMatch
from tdata.point_level.point import Point
from tdata.datasets.score import Score, \
    BadFormattingException


class IncongruenceException(Exception):
    pass


class NotEnoughDataException(Exception):
    pass


class SackmannImporter(object):

    def __init__(self, filenames, min_matches=None, discard_challengers=False):

        dfs = [pd.read_csv(x) for x in filenames]
        self.df = pd.concat(dfs, ignore_index=True)
        self.error_rows = list()

        if min_matches is not None:
            self.df = self.keep_only_multiple(self.df, min_matches)

        self.df['date'] = pd.to_datetime(self.df['date'])
        self.discard_challengers = discard_challengers

    @staticmethod
    def keep_only_multiple(df, minimum):

        p1_counts = df['server1'].value_counts()
        p2_counts = df['server2'].value_counts()

        to_remove = list()

        all_players = set(p1_counts.index.tolist() + p2_counts.index.tolist())

        for player in all_players:
            if (player not in p1_counts.index or
                    player not in p2_counts.index or
                    p1_counts[player] + p2_counts[player] < minimum):
                to_remove.append(player)

        criterion = df.apply(lambda row: row['server1'] not in to_remove,
                             axis=1)

        reduced_df = df[criterion]

        return reduced_df

    @staticmethod
    def set_tournament(tournament_name, df):
        return df[df['tny_name'] == tournament_name]

    def extract_matches(self, max_matches=None, min_date=None, max_date=None,
                        tournament_name=None):

        df = self.df

        if min_date is not None:
            df = df[df['date'] >= min_date]

        if max_date is not None:
            df = df[df['date'] <= max_date]

        if tournament_name is not None:
            df = self.set_tournament(tournament_name, df)

        for j, (i, row) in enumerate(df.iterrows()):

            # Show status indication:
            if j % 100 == 0:
                print('Importing match: ' + str(j) + ' of ' +
                      str(df.shape[0]))

            (winner, loser) = ((row['server1'], row['server2']) if
                               row['winner'] == 1 else
                               (row['server2'], row['server1']))

            # Skip if it's a long non-tb final set:
            try:
                sack_score = Score(row['score'], winner, loser)
                if sack_score.was_long_final_set():
                    print("Skipping:")
                    print(row)
                    continue
            except BadFormattingException:
                continue

            # If it's a trial run, break early:
            if max_matches is not None and j >= max_matches:
                break

            # Parse and record any errors:
            try:

                yield self.parse_row(row)

            except NotEnoughDataException:
                cur_error_row = row.copy()
                cur_error_row['reason'] = \
                    "Match not finished when all data consumed"
                self.error_rows.append(cur_error_row)

            except IncongruenceException:
                cur_error_row = row.copy()
                cur_error_row['reason'] = \
                    "Match ended before all sequence consumed"
                self.error_rows.append(cur_error_row)

    # Parses a single row of Sackmann's dataset, returning a CompletedMatch
    # object.
    def parse_row(self, row):

        point_sequence = list(row['pbp'])
        points = list()

        # Make the scorer which advances the model according to the point
        # data:
        def curried_scorer(score, server):
            return self.sackmann_scorer(score, points, point_sequence)

        (winner, loser) = ((row['server1'], row['server2']) if
                           row['winner'] == 1 else
                           (row['server2'], row['server1']))

        # Find additional parameters for simulation
        sack_score = Score(row['score'], winner, loser)
        server = row['server1']
        returner = row['server2']
        bo5 = sack_score.bo5

        # Play the match using the points:
        start_score = mc.Score(server, returner, bo5)

        final_score = mc.play_match(
            start_score, start_score.cur_server, start_score.cur_returner(),
            curried_scorer)

        # Ensure they are consistent:
        self.ensure_consistent(sack_score, final_score)

        # Make sure all points were parsed:
        if (len(point_sequence) != 0) and not (
                (len(point_sequence) == 1 and point_sequence[0] == '.')):
            print(final_score)
            print("Remaining sequence:")
            print(point_sequence)
            raise IncongruenceException()

        # Find the date the match was played:
        date = row['date']

        # Store as a CompletedMatch:
        match = CompletedMatch(final_score.p1,
                               final_score.p2,
                               date,
                               points=points,
                               winner=sack_score.winner,
                               score=sack_score,
                               final_point_level_info=final_score,
                               tournament_name=row['tny_name'])

        return match

    # Compares the score in Sackmann's database against that determined by the
    # simulator and raises an Exception if they are not consistent.
    @staticmethod
    def ensure_consistent(sack_score, mc_score):

        winner_name = sack_score.winner

        if winner_name != mc_score.winner():
            print('Winners do not match!')
            print(winner_name, mc_score.winner())
            raise IncongruenceException()

        for set_num, set_data in enumerate(sack_score.sets):

            sack_set = set_data['score']
            match_winner_games = sack_set[0]
            match_loser_games = sack_set[1]

            mc_match_winner_games = mc_score.games[set_num][winner_name]
            mc_match_loser_games = mc_score.games[set_num][sack_score.loser]

            if not (match_winner_games == mc_match_winner_games and
                    match_loser_games == mc_match_loser_games):

                print('Scores do not match!')
                raise IncongruenceException()

    # Provides a bridge between the Monte Carlo simulator and the
    # point-by-point data. Since the simulator works by advancing according to
    # the probability of the server winning, setting this to zero or one
    # depending on the point-by-point data will advance the match to the
    # desired situation.
    @staticmethod
    def sackmann_scorer(score, points, point_sequence):

        if len(point_sequence) == 0:
            print("Ran out of data at score:")
            print(score)
            raise NotEnoughDataException()

        # Pop the next command
        cur_result = point_sequence.pop(0)

        # Skip the semi-colon if necessary:
        if cur_result in [';', '/', '.']:
            if len(point_sequence) == 0:
                print("Ran out of data at score:")
                print(score)
                raise NotEnoughDataException()
            cur_result = point_sequence.pop(0)

        if cur_result in ['S', 'A']:
            points.append(Point(deepcopy(score), True))
            return 1

        elif cur_result in ['R', 'D']:
            points.append(Point(deepcopy(score), False))
            return 0

        else:
            # At this stage, we must have a result:
            print("Parsing error!")
            print(cur_result)
            print(score)
            assert False
