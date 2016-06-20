import numpy as np
import pandas as pd

from pbm.monte_carlo.monte_carlo import Score
from pbm.match_prediction.in_play_predictor import InPlayPredictor


class MatchChartingParser(object):

    def __init__(self):

        self.atp_match_df = self.get_match_df(t_type='atp')
        self.wta_match_df = self.get_match_df(t_type='wta')

        self.atp_points_df = self.get_points_df(t_type='atp')
        self.wta_points_df = self.get_points_df(t_type='wta')

    def get_match_df(self, t_type='atp'):

        assert(t_type in ['atp', 'wta'])

        if t_type == 'atp':

            return pd.read_csv(
                'data/tennis_MatchChartingProject/charting-m-matches.csv')

        else:

            return pd.read_csv(
                'data/tennis_MatchChartingProject/charting-w-matches.csv')

    def get_points_df(self, t_type='atp'):

        assert(t_type in ['atp', 'wta'])

        if t_type == 'atp':

            return pd.read_csv(
                'data/tennis_MatchChartingProject/charting-m-points.csv',
                low_memory=False)

        else:

            return pd.read_csv(
                'data/tennis_MatchChartingProject/charting-w-points.csv',
                low_memory=False)

    @staticmethod
    def turn_into_boolean_sequence(match_df):

        # Check whether there are any dates:

        for col in ['Pts', 'PtsAfter']:

            all_pts = match_df[col]

            date_version = all_pts.str.contains(
                'Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec')

            if np.sum(date_version) > 0:
                print('Skipping match -- contains date')
                return []

        boolean_list = list()

        for i, point in match_df.iterrows():

            cur_score = point['Pts']

            cur_score = cur_score.replace('AD', '50')

            score_after = point['PtsAfter'].replace('AD', '50')

            split_version = [int(x) for x in cur_score.split('-')]

            if score_after == 'GM':

                boolean_list.append(split_version[0] > split_version[1])

            else:

                try:

                    score_after_split = [int(x) for x in
                                         score_after.split('-')]
                    boolean_list.append(
                        split_version[0] < score_after_split[0] or
                        split_version[1] > score_after_split[1])

                except IndexError:
                    print('Skipping match -- unexpected score format')
                    return []

        return boolean_list

    def get_all_sequences(self, t_type='atp'):

        indexed = self.get_match_df(t_type).set_index('match_id')
        grouped = self.get_points_df(t_type).groupby('match_id')

        sequences = grouped.apply(
            MatchChartingParser.turn_into_boolean_sequence)

        subset = indexed.loc[sequences.index].copy()
        subset['win_sequence'] = sequences

        return subset

    @staticmethod
    def points_from_sequence(first_server, first_receiver, win_sequence,
                             best_of_five):

        initial_score = Score(first_server, first_receiver, best_of_five)
        sequence = InPlayPredictor.generate_points(initial_score, win_sequence)

        return sequence


if __name__ == '__main__':

    def get_final_scores():

        parser = MatchChartingParser()

        sequence_df = parser.get_all_sequences()

        suggested_final_scores = list()

        for i, row in sequence_df.iterrows():

            win_sequence = row['win_sequence']
            first_server = row['Player 1']
            first_receiver = row['Player 2']
            bo5 = row['Best of'] == 5

            points = parser.points_from_sequence(
                first_server, first_receiver, win_sequence, bo5)

            final_score = str(points[-1].score)

            print(final_score)

            suggested_final_scores.append(final_score)

        sequence_df['final_score_suggested'] = suggested_final_scores

        sequence_df.to_csv('sequences_with_scores.csv')

    def get_sequences(t_type='atp'):

        parser = MatchChartingParser()

        sequence_df = parser.get_all_sequences(t_type)

        sequence_df.to_csv('{}_sequences.csv'.format(t_type))

    get_sequences('atp')
    get_sequences('wta')
