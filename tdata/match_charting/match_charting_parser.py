import logging
import numpy as np
import pandas as pd

from tdata.point_level.monte_carlo.monte_carlo import Score
from tdata.point_level.point_utils import generate_points

from copy import deepcopy
from tdata.match_charting.shot_sequence import ShotSequence
from tdata.match_charting.exceptions import CodeParsingException

# Set up logging
logger = logging.getLogger(__name__)

# Make sure we write to log
fh = logging.FileHandler('chart_parse.log')
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)


class MatchChartingParser(object):

    def __init__(self):

        self.match_dfs = {x: self.get_match_df(x) for x in ['atp', 'wta']}
        self.points_dfs = {x: self.get_points_df(x) for x in ['atp', 'wta']}
        self.error_messages = list()

    def get_match_df(self, t_type='atp'):

        assert(t_type in ['atp', 'wta'])

        if t_type == 'atp':

            df = pd.read_csv(
                'data/tennis_MatchChartingProject/charting-m-matches.csv')

        else:

            df = pd.read_csv(
                'data/tennis_MatchChartingProject/charting-w-matches.csv')

        if t_type == 'atp':
            df['Date'] = pd.to_datetime(df['Date'])
        else:
            df['Date'] = pd.to_datetime(df['Date'], format='%Y%m%d')

        return df

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

                logger.info('Skipping match {} -- contains date'.format(
                    match_df.iloc[0]['match_id']))

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
                    logger.info('Skipping match -- unexpected score format')
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
        sequence = generate_points(initial_score, win_sequence)

        return sequence

    def parse_match(self, match_id, t_type='atp'):

        # Find match data
        indexed_match_df = self.match_dfs[t_type].set_index('match_id')

        match_data = indexed_match_df.loc[match_id]

        if len(match_data.shape) > 1:
            match_data = match_data.iloc[0]

        # Find match df
        match_df = self.points_dfs[t_type].groupby('match_id').get_group(
            match_id)

        is_bo5 = match_data['Best of'] == 5
        first_server = match_data['Player 1']
        first_receiver = match_data['Player 2']

        first_codes, second_codes = match_df['1st'], match_df['2nd']

        sequence = self.turn_into_boolean_sequence(match_df)

        points = self.points_from_sequence(first_server, first_receiver,
                                           sequence, is_bo5)

        points = self.add_shot_sequence(points, first_codes, second_codes)

        return points

    def add_shot_sequence(self, points, first_codes, second_codes):

        with_sequence = list()

        for point, first_code, second_code in zip(points, first_codes,
                                                  second_codes):

            server_won = point.server_won
            cur_server = point.score.cur_server
            cur_returner = point.score.cur_returner()

            try:

                shot_sequence = ShotSequence.from_code(
                    cur_server, cur_returner, server_won, first_code,
                    second_code)

            except CodeParsingException as e:

                self.error_messages.append(str(e))

                logger.warning('Parsing failed: {} at score: {}'.format(
                    e, point.score))

                shot_sequence = None

            new_point = deepcopy(point)

            new_point.shot_sequence = shot_sequence

            with_sequence.append(new_point)

        return with_sequence
