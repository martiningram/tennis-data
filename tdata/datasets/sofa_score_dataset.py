import os
import numpy as np
import pandas as pd
from glob import glob
from pathlib import Path

from tdata.datasets.dataset import Dataset
from tdata.enums.t_type import Tours
from tdata.enums.round import Rounds
from tdata.utils.utils import base_name_from_path
from tdata.datasets.match_stats import MatchStats


class SofaScoreDataset(Dataset):

    def __init__(self, t_type=Tours.atp, min_year=None):

        exec_dir = Path(os.path.abspath(__file__)).parents[2]

        self.t_type = t_type
        self.min_year = min_year

        csv_dir = os.path.join(str(exec_dir), 'data', 'sofa_csv', t_type.name)
        csvs = glob(os.path.join(csv_dir, '*.csv'))
        year_lookup = {int(base_name_from_path(x)): x for x in csvs}

        if min_year is not None:
            keys_to_keep = [x for x in year_lookup.keys() if x >= min_year]
        else:
            keys_to_keep = year_lookup.keys()

        loaded = [pd.read_csv(year_lookup[x], index_col=0) for x in
                  sorted(keys_to_keep)]
        combined = pd.concat(loaded, axis=0, ignore_index=True)
        combined['date'] = pd.to_datetime(combined['date'])

        # For now, drop qualifying
        combined = combined[~(combined['round'] == 'qualifying')]

        # Also drop retirements
        combined = combined[~combined['was_retirement']]

        # Rename date to start_date
        self.df = combined.rename(columns={'date': 'start_date'})

        self.df = self.fix_world_tour_finals(self.df)

        self.df = self.df.dropna(subset=['round'])

        # TODO: Is this slow? Could do something more efficient.
        self.df['round_number'] = [Rounds[x].value for x in
                                   self.df['round'].values]

        self.check_unique(self.df)

        super(SofaScoreDataset, self).__init__(start_date_is_exact=True)

        self.df = self.df.set_index(self.df_index, drop=False)

    def fix_world_tour_finals(self, df):

        # WARNING: This is a bit of a band-aid and may fail.
        df = df.sort_values('start_date')
        tf_rows = df.loc[df['tournament_name'] == 'Tour Finals London']
        years = np.unique(tf_rows['start_date'].dt.year)

        for cur_year in years:

            cur_relevant = tf_rows.loc[
                tf_rows['start_date'].dt.year == cur_year, 'round']

            # Last match is final
            cur_relevant.iloc[-1] = Rounds.F.name

            # Two before that are semis
            cur_relevant.iloc[-2] = Rounds.SF.name
            cur_relevant.iloc[-3] = Rounds.SF.name

            # All before are round robin.
            cur_relevant.iloc[:-3] = Rounds.RR.name

            df.loc[cur_relevant.index, 'round'] = cur_relevant

        return df

    @staticmethod
    def check_unique(df):

        unique_to_check = [['winner', 'loser', 'start_date']]

        for cur_check in unique_to_check:

            subset = df[cur_check].values
            tuples = [tuple(x) for x in subset]
            tuple_set = set(tuples)

            assert len(tuples) == len(tuple_set)

    def get_stats_df(self):

        return self.df

    def calculate_stats(self, winner, loser, row):

        stats = dict()

        winners, ues, odds = None, None, None

        for role in ['winner', 'loser']:

            s_played = row['serve_points_played_{}'.format(role)]
            s_won = row['serve_points_won_{}'.format(role)]
            r_played = row['return_points_played_{}'.format(role)]
            r_won = row['return_points_won_{}'.format(role)]

            optional_args = {x: None for x in ['winners', 'ues', 'odds']}

            for cur_field in optional_args.keys():
                cur_relevant = cur_field + '_' + role
                if cur_relevant in row and not np.isnan(row[cur_relevant]):
                    optional_args[cur_field] = row[cur_relevant]

            name = row[role]

            stats[name] = MatchStats(player_name=name,
                                     serve_points_played=s_played,
                                     serve_points_won=s_won,
                                     return_points_played=r_played,
                                     return_points_won=r_won,
                                     **optional_args)

        return stats

if __name__ == '__main__':

    # TODO: Look for and handle retirements. One way to do this could be to add
    # an "appears complete" function to the score. Another could be to see
    # whether Sofascore has a field specifying whether it was a retirement,
    # and maybe adding that to the score.

    import numpy as np

    dataset = SofaScoreDataset()
    df = dataset.get_stats_df()
