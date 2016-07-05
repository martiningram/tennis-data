import glob
import pandas as pd

from collections import defaultdict
from tdata.datasets.dataset import Dataset
from tdata.datasets.match import CompletedMatch
from tdata.datasets.match_stats import MatchStats


class MatchStatDataset(Dataset):

    def __init__(self):

        # Import all data:
        all_csvs = glob.glob('data/year_csvs/*.csv')
        all_read = [pd.read_csv(x, index_col=0) for x in all_csvs]
        concatenated = pd.concat(all_read, ignore_index=True)
        concatenated['start_date'] = pd.to_datetime(concatenated['start_date'])

        self.data_including_no_stats = concatenated

        # Drop those without stats
        concatenated = concatenated.dropna(subset=['winner_serve_1st_won'])
        concatenated = concatenated[
            concatenated['winner_serve_1st_attempts'] > 0]

        stats = self.calculate_stats_df(concatenated)

        concatenated = pd.concat([concatenated, stats], axis=1)

        self.by_players = concatenated.set_index(['winner', 'loser'])
        self.full_df = concatenated

    def get_stats_df(self):

        return self.full_df

    def get_tournament_serve_average(self, tournament_name, min_date=None,
                                     max_date=None):

        tournament_df = self.full_df.set_index('tournament_name')
        relevant_matches = tournament_df.loc[tournament_name]

        if min_date is not None:

            relevant_matches = relevant_matches[
                relevant_matches['Date'] > min_date]

        if max_date is not None:

            relevant_matches = relevant_matches[
                relevant_matches['Date'] < max_date]

        averages = (relevant_matches['winner_serve_points_won_pct'] +
                    relevant_matches['loser_serve_points_won_pct']) / 2

        return averages.mean()

    def calculate_stats_df(self, df):

        results = dict()

        for role in ['winner', 'loser']:

            results['{}_first_serve_pct'.format(role)] = (
                df['{}_serve_1st_total'.format(role)] / (
                df['{}_serve_1st_attempts'.format(role)]
                + df['{}_double_faults'.format(role)]))

            results['{}_first_serve_won_pct'.format(role)] = (
                df['{}_serve_1st_won'.format(role)] /
                df['{}_serve_1st_total'.format(role)])

            results['{}_second_serve_won_pct'.format(role)] = (
                df['{}_serve_2nd_won'.format(role)] / (
                df['{}_serve_2nd_total'.format(role)]
                + df['{}_double_faults'.format(role)]))

            results['{}_return_points_won_pct'.format(role)] = (
                df['{}_return_points_won'.format(role)] /
                df['{}_return_points_total'.format(role)])

            results['{}_serve_points_won_pct'.format(role)] = (
                results['{}_first_serve_pct'.format(role)] *
                results['{}_first_serve_won_pct'.format(role)] +
                (1 - results['{}_first_serve_pct'.format(role)]) *
                results['{}_second_serve_won_pct'.format(role)])

        results = pd.DataFrame(results)

        return results

    def get_player_matches(self, player_name, min_date=None, max_date=None,
                           surface=None):

        assert(surface is None)

        all_matches = list()

        # Get matches the player won:

        try:
            won_matches = self.by_players.xs(player_name, level='winner')
        except KeyError as k:
            won_matches = pd.DataFrame()

        if len(won_matches) > 0:

            # Reduce to date range:
            if min_date is not None:
                won_matches = won_matches[won_matches['start_date'] > min_date]

            if max_date is not None:
                won_matches = won_matches[won_matches['start_date'] < max_date]

            for loser, row in won_matches.iterrows():

                stats = self.calculate_stats(player_name, loser, row)

                match = CompletedMatch(
                    p1=player_name, p2=loser, date=row['start_date'],
                    winner=player_name, stats=stats,
                    tournament_name=row['tournament_name'])

                all_matches.append(match)

        # Get matches the player lost:

        try:
            lost_matches = self.by_players.xs(player_name, level='loser')
        except KeyError as k:
            lost_matches = pd.DataFrame()

        if len(lost_matches) > 0:

            # Reduce to date range:
            if min_date is not None:
                lost_matches = lost_matches[lost_matches['start_date'] > min_date]

            if max_date is not None:
                lost_matches = lost_matches[lost_matches['start_date'] < max_date]

            for winner, row in lost_matches.iterrows():

                stats = self.calculate_stats(winner, player_name, row)

                match = CompletedMatch(
                    p1=player_name, p2=winner, date=row['start_date'],
                    winner=winner, stats=stats,
                    tournament_name=row['tournament_name'])

                all_matches.append(match)

        return sorted(all_matches, key=lambda x: x.date)

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
            return_won_pct = row['{}_return_points_won_pct'.format(role)]

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
                pct_won_return=return_won_pct, odds=odds,
                pct_first_serve=first_serve_pct,
                pct_won_first_serve=first_won_pct,
                pct_won_second_serve=second_won_pct, winners=winners, ues=ues)

        return stats

if __name__ == '__main__':

    from datetime import date

    dataset = MatchStatDataset()

    print(dataset.get_tournament_serve_average('Stuttgart'))
