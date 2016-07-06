import os
import glob
import pandas as pd

from pathlib import Path
from collections import defaultdict
from tdata.datasets.dataset import Dataset
from tdata.datasets.match import CompletedMatch
from tdata.datasets.match_stats import MatchStats


class SackmannDataset(Dataset):

    def __init__(self):

        # Find the correct directory:
        exec_dir = Path(__file__).parents[2]

        # Get all csv filenames:
        all_csvs = glob.glob(
            '{}/data/sackmann/tennis_atp/atp_matches_*.csv'.format(exec_dir))

        # Remove futures and challengers (and possibly corrupt 2016):
        all_csvs = [x for x in all_csvs if 'futures' not in x
                    and '2016' not in x and 'chall' not in x]

        # Read them and concatenate them
        big_df = pd.concat([pd.read_csv(x) for x in all_csvs],
                           ignore_index=True)

        # Keep only those with stats:
        big_df = big_df.dropna(subset=['w_1stWon'])
        big_df = self.rename_cols(big_df)

        big_df['start_date'] = pd.to_datetime(
            big_df['start_date'], format='%Y%m%d')

        # Find stats
        stats_df = self.calculate_stats_df(big_df)

        # Concatenate
        big_df = pd.concat([big_df, stats_df], axis=1)

        self.full_df = big_df
        self.by_players = big_df.set_index(['winner', 'loser'], drop=False)

    def get_stats_df(self):

        return self.full_df

    def get_player_df(self):

        return self.by_players

    def rename_cols(self, df):

        # Rename for consistency:
        renaming_dict = {'1stIn': 'serve_1st_total',
                         '1stWon': 'serve_1st_won',
                         'svpt': 'serve_1st_attempts',
                         '2ndWon': 'serve_2nd_won',
                         'df': 'double_faults'}

        final_dict = dict()

        winner_dict = {'w_' + x: 'winner_' + renaming_dict[x]
                       for x in renaming_dict}

        loser_dict = {'l_' + x: 'loser_' + renaming_dict[x]
                      for x in renaming_dict}

        final_dict.update(winner_dict)
        final_dict.update(loser_dict)

        df = df.rename(columns=final_dict)

        # Rename other columns:
        renaming_dict = {'winner_name': 'winner',
                         'loser_name': 'loser',
                         'tourney_date': 'start_date',
                         'tourney_name': 'tournament_name'}

        df = df.rename(columns=renaming_dict)

        return df

    def calculate_stats_df(self, df):

        results = dict()

        for role in ['winner', 'loser']:

            df['{}_serve_2nd_total'.format(role)] = (
                df['{}_serve_1st_attempts'.format(role)] -
                df['{}_serve_1st_total'.format(role)])

            results['{}_first_serve_pct'.format(role)] = (
                df['{}_serve_1st_total'.format(role)] / (
                df['{}_serve_1st_attempts'.format(role)]))

            results['{}_first_serve_won_pct'.format(role)] = (
                df['{}_serve_1st_won'.format(role)] /
                df['{}_serve_1st_total'.format(role)])

            results['{}_second_serve_won_pct'.format(role)] = (
                df['{}_serve_2nd_won'.format(role)] / (
                df['{}_serve_2nd_total'.format(role)]))

            results['{}_serve_points_won_pct'.format(role)] = (
                results['{}_first_serve_pct'.format(role)] *
                results['{}_first_serve_won_pct'.format(role)] +
                (1 - results['{}_first_serve_pct'.format(role)]) *
                results['{}_second_serve_won_pct'.format(role)])

        results = pd.DataFrame(results)

        return results

    def calculate_stats(self, winner, loser, row):

        # Drop the nans:
        to_use = row.dropna()

        winners, ues, odds = None, None, None

        stats = dict()

        for role, name in zip(['winner', 'loser'], [winner, loser]):

            stats_results = defaultdict(dict)

            first_serve_pct = row['{}_first_serve_pct'.format(role)]
            first_won_pct = row['{}_first_serve_won_pct'.format(role)]
            second_won_pct = row['{}_second_serve_won_pct'.format(role)]

            serve_won_pct = (first_serve_pct * first_won_pct +
                             (1 - first_serve_pct) * second_won_pct)

            if 'winners' in to_use.index:

                winners = row['{}_winners'.format(role)]
                ues = row['{}_ues'.format(role)]

            if 'odds' in to_use.index:

                odds = row['{}_odds'.format(role)]

            # Construct the object
            stats[name] = MatchStats(
                player_name=name, pct_won_serve=serve_won_pct,
                pct_won_return=None, odds=odds,
                pct_first_serve=first_serve_pct,
                pct_won_first_serve=first_won_pct,
                pct_won_second_serve=second_won_pct, winners=winners, ues=ues)

        stats[winner].pct_won_return = 1 - stats[loser].pct_won_serve
        stats[loser].pct_won_return = 1 - stats[winner].pct_won_serve

        return stats


if __name__ == '__main__':

    from datetime import date

    ds = SackmannDataset()

#     matches = ds.get_matches_between(min_date=date(2015, 1, 1),
                                     # max_date=date(2015, 12, 31),
                                     # surface='Hard')

    player_matches = ds.get_player_matches('Roger Federer',
                                           date(2015, 1, 1),
                                           date(2015, 3, 1))

    for match in player_matches:

        print(match)
