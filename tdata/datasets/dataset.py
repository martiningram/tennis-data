import pandas as pd

from abc import abstractmethod
from datetime import timedelta
from tdata.datasets.match import CompletedMatch


class Dataset(object):

    def get_player_matches(self, player_name, min_date=None, max_date=None,
                           surface=None):

        by_players = self.get_player_df()

        all_matches = list()

        for level in ['winner', 'loser']:

            try:

                cur_matches = by_players.xs(player_name, level=level)

            except KeyError as k:

                cur_matches = pd.DataFrame()

            if len(cur_matches) > 0:

                if min_date is not None or max_date is not None:

                    cur_matches = cur_matches.set_index(
                        'start_date', drop=False)

                # Reduce to date range:
                if min_date is not None:

                    cur_matches = cur_matches[str(min_date):]

                if max_date is not None:

                    cur_matches = cur_matches[:str(
                        max_date - timedelta(days=1))]

                if len(cur_matches.shape) == 1:

                    # Turn into DataFrame
                    cur_matches = pd.DataFrame([cur_matches])

                if surface is not None:

                    cur_matches = cur_matches.set_index('surface', drop=False)

                    try:

                        cur_matches = cur_matches.loc[[surface]]

                    except KeyError:

                        return all_matches

                for _, row in cur_matches.iterrows():

                    stats = self.calculate_stats(
                        row['winner'], row['loser'], row)

                    opponent = (row['winner'] if player_name == row['loser']
                                else row['loser'])

                    if 'surface' in row.index:
                        surface = row['surface']
                    else:
                        surface = None

                    match = CompletedMatch(
                        p1=player_name, p2=opponent, date=row['start_date'],
                        winner=row['winner'], stats=stats,
                        tournament_name=row['tournament_name'],
                        surface=surface)

                    all_matches.append(match)

        return sorted(all_matches, key=lambda x: x.date)

    @abstractmethod
    def get_tournament_serve_average(self, tournament_name, min_date=None,
                                     max_date=None):
        pass

    def get_matches_between(self, min_date=None, max_date=None, surface=None):

        matches = list()

        subset = self.get_stats_df()

        try:

            if min_date is not None or max_date is not None:

                subset = subset.set_index('start_date', drop=False)

            if min_date is not None:

                subset = subset[str(min_date):]

            if max_date is not None:

                subset = subset[:str(max_date - timedelta(days=1))]

            if surface is not None:

                if 'surface' not in subset.columns:
                    print('Surface information not in this dataset')

                subset = subset.set_index('surface', drop=False)
                subset = subset.loc[[surface]]

        except KeyError:

            # Something wasn't in the index, which means there are no matches
            # satisfying the criteria given.
            return matches

        if len(subset) == 0:
            return matches

        for i, row in subset.iterrows():

            stats = self.calculate_stats(
                row['winner'], row['loser'], row)

            if 'surface' not in row.index:
                surface = None
            else:
                surface = row['surface']

            match = CompletedMatch(
                p1=row['winner'], p2=row['loser'], date=row['start_date'],
                winner=row['winner'], stats=stats,
                tournament_name=row['tournament_name'],
                surface=surface)

            matches.append(match)

        return matches

    @abstractmethod
    def get_stats_df(self):
        pass

    @abstractmethod
    def get_player_df(self):
        pass
