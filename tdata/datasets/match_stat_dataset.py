import os
import glob
import numpy as np
import pandas as pd

from pathlib import Path
from tdata.datasets.dataset import Dataset
from tdata.datasets.match_stats import MatchStats


class MatchStatDataset(Dataset):

    def __init__(self, t_type='atp', stat_matches_only=True,
                 min_year=None, drop_qual=True):

        # Import all data:
        # Find the correct directory:
        exec_dir = Path(__file__).parents[2]

        # Get all csv filenames:
        all_csvs = glob.glob(
            '{}/data/year_csvs/*{}*.csv'.format(exec_dir, t_type))

        if min_year is not None:

            all_csvs = [x for x in all_csvs if
                        int(os.path.split(x)[1][:4]) >= min_year]

        all_read = [pd.read_csv(x, index_col=0) for x in all_csvs]
        concatenated = pd.concat(all_read, ignore_index=True)
        concatenated['start_date'] = pd.to_datetime(concatenated['start_date'])
        concatenated['year'] = concatenated['start_date'].dt.year

        # Drop matches without round (Davis Cup)
        concatenated = concatenated.dropna(subset=['round'])

        # Drop those without stats
        if stat_matches_only:

            concatenated = concatenated.dropna(
                subset=['winner_serve_1st_won'])

            concatenated = concatenated[
                concatenated['winner_serve_1st_attempts'] > 0]

        # Drop retirements
        concatenated = concatenated[
            ~concatenated['score'].str.contains('Ret.')]

        # Drop walkovers
        concatenated = concatenated[
            ~concatenated['score'].str.contains('WO|,|Default')]

        # Drop qualifying (for now)
        if drop_qual:
            concatenated = concatenated[
                ~(concatenated['round'].str.contains('FQ'))]

        # Drop doubles
        concatenated = concatenated[
            (~(concatenated['winner'].str.contains('/'))) &
            (~(concatenated['loser'].str.contains('/')))]

        # Add round number
        concatenated['round_number'] = self.make_round_number(concatenated)

        # Clean up surface
        concatenated['surface'] = concatenated['surface'].str.lower()

        # Group indoor clay as clay
        concatenated['surface'] = concatenated['surface'].str.replace(
            'i clay', 'clay')

        stats = self.calculate_stats_df(concatenated)

        concatenated = pd.concat([concatenated, stats], axis=1)

        if stat_matches_only:

            concatenated = concatenated.dropna(
                subset=['winner_serve_points_won_pct'])

        concatenated = concatenated.sort_values(['start_date', 'round_number'])

        concatenated['start_date'] = pd.to_datetime(concatenated['start_date'])

        self.full_df = concatenated.set_index(
            ['winner', 'loser', 'round', 'tournament_name', 'year'],
            drop=False)

        super(MatchStatDataset, self).__init__()

    def make_round_number(self, df):

        substitutions = {'R128': 0, 'R64': 1, 'R32': 2, 'R16': 3, 'QF': 4,
                         'SF': 5, 'F': 6, 'RR A': 0, 'RR B': 0}

        round_numbers = df['round'].replace(substitutions)

        return round_numbers

    def get_stats_df(self):

        return self.full_df

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

        winners, ues, odds = None, None, None

        stats = dict()

        for role, name in zip(['winner', 'loser'], [winner, loser]):

            # First find return points won
            other_role = 'winner' if role == 'loser' else 'loser'

            rp_won = row['{}_return_points_won'.format(role)]
            rp_out_of = row['{}_return_points_total'.format(role)]

            other_rp_won = row['{}_return_points_won'.format(other_role)]
            other_rp_out_of = row['{}_return_points_total'.format(other_role)]

            sp_won = other_rp_out_of - other_rp_won
            sp_out_of = other_rp_out_of

            if ('{}_winners'.format(role) in row and
                    not np.isnan(row['{}_winners'.format(role)])):

                winners = row['{}_winners'.format(role)]
                ues = row['{}_unforced_errors'.format(role)]

            if ('{}_odds'.format(role) in row and
                    not np.isnan(row['{}_odds'.format(role)])):

                odds = row['{}_odds'.format(role)]

            # Construct the object
            stats[name] = MatchStats(
                player_name=name, serve_points_played=sp_out_of,
                serve_points_won=sp_won, return_points_played=rp_out_of,
                return_points_won=rp_won, odds=odds,
                winners=winners, ues=ues)

        return stats


if __name__ == '__main__':

    from datetime import date

    dataset = MatchStatDataset(t_type='wta', min_year=2014)

    test = dataset.get_player_matches('Madison Keys', date(2016, 7, 1),
                                      date(2016, 7, 31), before_round=2)

    for match in test:

        print(match)
