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

        # Rename date to start_date
        self.df = combined.rename(columns={'date': 'start_date'})

        # TODO: Is this slow? Could do something more efficient.
        self.df['round_number'] = [Rounds[x].value for x in
                                   self.df['round'].values]

        self.check_unique(self.df)

        super(SofaScoreDataset, self).__init__(start_date_is_exact=True)

        self.df = self.df.set_index(self.df_index, drop=False)


    @staticmethod
    def check_unique(df):

        unique_to_check = [['winner', 'loser', 'tournament_name', 'round'],
                           ['winner', 'loser', 'start_date']]

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

    # TODO: Maybe have an attribute called "start_date_is_exact" or something.
    # Because for MatchStat, I used to adjust dates with the round. No need to
    # do that (I think) with Sofa.

    import numpy as np

    dataset = SofaScoreDataset()
    df = dataset.get_stats_df()
