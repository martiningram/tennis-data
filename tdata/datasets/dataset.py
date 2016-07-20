import datetime
import pandas as pd

from abc import abstractmethod
from datetime import timedelta, date, datetime
from tdata.datasets.match import CompletedMatch
from tdata.datasets.parsed_string_score import ParsedStringScore


class Dataset(object):
    """An abstract base class designed to handle match data from any source.

    Attributes:
        tour_averages (dict): A dictionary storing the tour's average spw, if
            calculated, for a particular year. This is to avoid costly
            recomputation.
    """

    def __init__(self):

        self.tour_averages = dict()

    def reduce_to_subset(self, df, min_date=None, max_date=None, surface=None,
                         before_round=None):

        if min_date is not None or max_date is not None:

            df = df.set_index('start_date', drop=False)
            df = df.sort_index()

        # Reduce to date range:
        if min_date is not None:

            df = df[min_date:]

        if max_date is not None:

            if before_round is None:

                # Pick only matches before the current date
                df = df[:(max_date - timedelta(days=1))]

            else:

                # Add matches before current round

                previous_date = df[:(max_date - timedelta(days=1))]
                same_date = df[max_date:max_date]

                earlier_round = same_date[same_date['round_number'] <
                                          before_round]

                df = pd.concat([previous_date, earlier_round], axis=0)

        if len(df.shape) == 1:

            # Turn single match into DataFrame
            df = pd.DataFrame([df])

        if surface is not None:

            df = df.set_index('surface', drop=False)

            try:

                df = df.loc[[surface]]

            except KeyError:

                # No matching matches. Return empty DataFrame.

                return pd.DataFrame()

        return df

    def get_player_matches(self, player_name, min_date=None, max_date=None,
                           surface=None, before_round=None):
        """
        Fetches a player's matches, filtered by date and surface.

        Args:
            player_name (str): The name of the player to find matches for.
            min_date (Optional[datetime.date]): The lowest date to find matches
                for. This date is inclusive, i.e. the minimum date is included.
            max_date (Optional[datetime.date]): The maximum date to find
                matches for. This date is exclusive, i.e. the maximum date is
                not included. This is to ensure that the match to predict is
                not included when making predictions.
            surface (str): The surface to filter matches for.

        Returns:
            List[CompletedMatch]: The list of matches the player played
            in the given period on a given surface.
        """

        by_players = self.get_player_df()

        all_matches = list()

        for level in ['winner', 'loser']:

            try:

                cur_matches = by_players.xs(player_name, level=level)

            except KeyError:

                continue

            subset = self.reduce_to_subset(
                cur_matches, min_date=min_date, max_date=max_date,
                before_round=before_round, surface=surface)

            all_matches.extend(self.turn_into_matches(subset))

        return sorted(all_matches, key=lambda x: x.date)

    def get_tournament_serve_average(self, tournament_name, min_date=None,
                                     max_date=None):
        """Returns the average probability of winning a point on serve for
        the tournament given.

        Note:
            TODO: Could accelerate this with an index.

        Args:
            tournament_name (str): The name of the tournament to find the
                serve average for.
            min_date (Optional[datetime.date]): The minimum date to use
                for the average.
            max_date (Optional[datetime.date]): The maximum date to use
                for the average.

        Returns:
            double: The average probability of winning a point on serve
            in the tournament given in the date range given.
        """

        full_df = self.get_stats_df()
        tournament_df = full_df.set_index('tournament_name')
        relevant_matches = tournament_df.loc[tournament_name]

        if min_date is not None:

            relevant_matches = relevant_matches[
                relevant_matches['start_date'] > min_date]

        if max_date is not None:

            relevant_matches = relevant_matches[
                relevant_matches['start_date'] < max_date]

        averages = (relevant_matches['winner_serve_points_won_pct'] +
                    relevant_matches['loser_serve_points_won_pct']) / 2

        return averages.mean()

    def turn_into_matches(self, df):

        """Converts the DataFrame given into a list of CompletedMatches."""

        matches = list()

        for _, row in df.iterrows():

            stats = self.calculate_stats(
                row['winner'], row['loser'], row)

            score = ParsedStringScore(
                row['score'], row['winner'], row['loser'])

            if 'surface' not in row:
                cur_surface = None
            else:
                cur_surface = row['surface']

            if 'odds_winner' in row.index:
                odds = {row['winner']: row['winner_odds'],
                        row['loser']: row['loser_odds']}
            else:
                odds = None

            match = CompletedMatch(
                p1=row['winner'], p2=row['loser'], date=row['start_date'],
                winner=row['winner'], stats=stats,
                tournament_name=row['tournament_name'], surface=cur_surface,
                tournament_round=row['round_number'], odds=odds, score=score)

            matches.append(match)

        return matches

    def get_matches_between(self, min_date=None, max_date=None, surface=None):
        """Fetches matches in the dataset, optionally filtered by date and
        surface.

        Args:
            min_date (Optional[datetime.date]): The lowest date to find matches
                for. This date is inclusive, i.e. the minimum date is included.
            max_date (Optional[datetime.date]): The maximum date to find
                matches for. This date is exclusive, i.e. the maximum date is
                not included. This is to ensure that the match to predict is
                not included when making predictions.
            surface (Optional[str]): The surface to filter matches for.

        Returns:
            List[CompletedMatch]: The list of matches satisfying the criteria
            given.
        """

        subset = self.get_stats_df()

        subset = self.reduce_to_subset(subset, min_date=min_date,
                                       max_date=max_date, surface=surface)

        if len(subset) == 0:
            return []

        matches = self.turn_into_matches(subset)

        return matches

    def calculate_tour_average(self, year):
        """Calculate the tour's average probability of winning a point on serve
        for a given year.

        Args:
            year (int): The year to calculate the average for.

        Returns:
            double: The tour's average probability of winning a point on serve
            for the year given.
        """

        if year in self.tour_averages:

            return self.tour_averages[year]

        else:

            subset = self.get_stats_df()

            subset = subset.set_index('start_date')

            date_version = date(year, 1, 1)

            end_date = date_version + timedelta(days=364)

            relevant = subset[str(date_version):str(end_date)]

            averages = (relevant['winner_serve_points_won_pct'] +
                        relevant['loser_serve_points_won_pct']) / 2

            result = averages.mean()

            self.tour_averages[year] = result

            return result

    @abstractmethod
    def get_stats_df(self):
        pass

    @abstractmethod
    def get_player_df(self):
        pass
