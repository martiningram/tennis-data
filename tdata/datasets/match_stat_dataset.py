import glob
import numpy as np
import pandas as pd

from pathlib import Path
from tdata.datasets.dataset import Dataset
from tdata.datasets.match_stats import MatchStats


class MatchStatDataset(Dataset):

    def __init__(self):

        super(MatchStatDataset, self).__init__()

        # Import all data:
        # Find the correct directory:
        exec_dir = Path(__file__).parents[2]

        # Get all csv filenames:
        all_csvs = glob.glob(
            '{}/data/year_csvs/*.csv'.format(exec_dir))

        all_read = [pd.read_csv(x, index_col=0) for x in all_csvs]
        concatenated = pd.concat(all_read, ignore_index=True)
        concatenated['start_date'] = pd.to_datetime(concatenated['start_date'])

        self.data_including_no_stats = concatenated

        # Drop those without stats & round
        concatenated = concatenated.dropna(
            subset=['winner_serve_1st_won', 'round'])

        concatenated = concatenated[
            concatenated['winner_serve_1st_attempts'] > 0]

        # Drop retirements
        concatenated = concatenated[~concatenated['score'].str.contains('Ret.')]

        # Drop qualifying (for now)
        concatenated = concatenated[~(concatenated['round'].str.contains('FQ'))]

        # Drop doubles
        concatenated = concatenated[~(concatenated['winner'].str.contains('/'))]

        stats = self.calculate_stats_df(concatenated)

        concatenated = pd.concat([concatenated, stats], axis=1)

        self.by_players = concatenated.set_index(['winner', 'loser'],
                                                 drop=False)

        self.full_df = concatenated

    def get_stats_df(self):

        return self.full_df

    def get_player_df(self):

        return self.by_players

    def calculate_percentages(self, df, add_dfs=True):

        results = dict()

        for role in ['winner', 'loser']:

            # Note: These are somewhat suspect. Only the return points won
            # agree with Sackmann's results, so perhaps there is some issue
            # with double faults / aces that needs to be accounted for.

            if add_dfs:

                first_serve_pct_denom = (
                    df['{}_serve_1st_attempts'.format(role)] +
                    df['{}_double_faults'.format(role)])

                second_serve_pct_denom = (
                    df['{}_serve_2nd_total'.format(role)] +
                    df['{}_double_faults'.format(role)])

            else:

                first_serve_pct_denom = (
                    df['{}_serve_1st_attempts'.format(role)])

                second_serve_pct_denom = (
                    df['{}_serve_2nd_total'.format(role)])

            results['{}_first_serve_pct'.format(role)] = (
                df['{}_serve_1st_total'.format(role)] / (
                    first_serve_pct_denom))

            results['{}_second_serve_won_pct'.format(role)] = (
                df['{}_serve_2nd_won'.format(role)] / (
                    second_serve_pct_denom))

            results['{}_first_serve_won_pct'.format(role)] = (
                df['{}_serve_1st_won'.format(role)] /
                df['{}_serve_1st_total'.format(role)])

            fsp = results['{}_first_serve_pct'.format(role)]
            fsw = results['{}_first_serve_won_pct'.format(role)]
            ssw = results['{}_second_serve_won_pct'.format(role)]

            results['{}_serve_points_won_pct'.format(role)] = (
                fsp * fsw + (1 - fsp) * ssw)

            results['{}_return_points_won_pct'.format(role)] = (
                df['{}_return_points_won'.format(role)] /
                df['{}_return_points_total'.format(role)])

        return pd.DataFrame(results, index=df.index)

    def calculate_stats_df(self, df):

        results = self.calculate_percentages(df, add_dfs=True)

        results = results.dropna(subset=['loser_return_points_won_pct'])

        df = df.loc[results.index]

        # Try using potentially more reliable return info instead of that
        # calculated above:
        alt_w_spw = (
            1 - results['loser_return_points_won_pct'])

        alt_l_spw = (
            1 - results['winner_return_points_won_pct'])

        # Try to correct:
        faulty_rows = (
            (np.abs(results['winner_serve_points_won_pct'] - alt_w_spw)
            > 0.005) |
            (np.abs(results['loser_serve_points_won_pct'] - alt_l_spw)
             > 0.005))

        to_recalc = df[faulty_rows]

        to_recalc = self.calculate_percentages(to_recalc, add_dfs=False)

        results.loc[to_recalc.index] = to_recalc

        return results

    def calculate_stats(self, winner, loser, row):

        # Drop the nans:
        to_use = row.dropna()

        winners, ues, odds = None, None, None

        stats = dict()

        for role, name in zip(['winner', 'loser'], [winner, loser]):

            first_serve_pct = row['{}_first_serve_pct'.format(role)]
            first_won_pct = row['{}_first_serve_won_pct'.format(role)]
            second_won_pct = row['{}_second_serve_won_pct'.format(role)]
            return_won_pct = row['{}_return_points_won_pct'.format(role)]

            serve_won_pct = row['{}_serve_points_won_pct'.format(role)]

            if 'winners' in to_use.index:

                winners = row['{}_winners'.format(role)]
                ues = row['{}_ues'.format(role)]

            if 'odds' in to_use.index:

                odds = row['{}_odds'.format(role)]

            # Construct the object
            stats[name] = MatchStats(
                player_name=name, pct_won_serve=serve_won_pct,
                pct_won_return=return_won_pct, odds=odds,
                pct_first_serve=first_serve_pct,
                pct_won_first_serve=first_won_pct,
                pct_won_second_serve=second_won_pct, winners=winners, ues=ues)

        return stats


if __name__ == '__main__':

    from datetime import date

    dataset = MatchStatDataset()

    test = dataset.get_player_matches('Roger Federer', date(2015, 1, 1),
                                      date(2015, 12, 1))

    print(len(test))
