import pandas as pd


class Match(object):
    """Class representing a tennis match.

    Attributes:
        p1 (str): Player 1's name.
        p2 (str): Player 2's name.
        date (datetime.date): The date the match takes place.
        surface (Optional[str]): The surface the match is played on. The names
            can vary by dataset, however they must be consistent.
        tournament_name (Optional[str]): The name of the tournament the match
            is played in.
    """

    def __init__(self, p1, p2, date, best_of_five, surface=None,
                 tournament_name=None, tournament_round=None):

        self.p1 = p1
        self.p2 = p2
        self.bo5 = best_of_five
        self.date = date
        self.surface = surface
        self.tournament_name = tournament_name
        self.tournament_round = tournament_round
        self.opponent_dict = {self.p1: self.p2, self.p2: self.p1}

    def get_opponent(self, player):
        """Returns the player faced by the player given.

        Args:
            player (str): The player whose opponent is to be found.

        Returns:
            str: The name of the player's opponent. If the player given is
            not present in the match, the program will exit.
        """

        return self.opponent_dict[player]

    def __str__(self):

        string = '{} is playing {} on {}.'.format(self.p1, self.p2, self.date)
        return string

    def to_dict(self):
        """Converts the Match object to a dictionary.

        Returns:
            dict: A dictionary with keys 'p1', 'p2', 'surface',
            'tournament_name' and 'date' containing the information stored in
            this class.
        """

        info_dict = {'p1': self.p1, 'p2': self.p2, 'surface': self.surface,
                     'tournament_name': self.tournament_name, 'date':
                     self.date}

        return info_dict

    @staticmethod
    def to_df(matches):
        """A helper function which converts a list of matches into a
        DataFrame."""

        results = list()

        for match in matches:

            results.append(match.to_dict())

        return pd.DataFrame(results)


class CompletedMatch(Match):
    """Stores information about a completed tennis match.

    Note: Only the attributes added to the Match class are specified here.
        For the attributes of the Match base class, see Match.

    Attributes:
        winner (str): The name of the player who won the match.
        loser (str): The name of the player who lost the match.
        stats (Optional[dict[str to MatchStats]]): A dictionary mapping player
            names to their MatchStats object for this match.
        points (Optional[List[Point]]): A list of the points played in the
            match, if available.
    """

    def __init__(self, p1, p2, date, winner, score, surface=None, stats=None,
                 points=None, tournament_name=None, tournament_round=None,
                 odds=None, final_point_level_info=None):

        super(CompletedMatch, self).__init__(
            p1=p1, p2=p2, best_of_five=score.bo5, date=date, surface=surface,
            tournament_name=tournament_name, tournament_round=tournament_round)

        assert(winner in [p1, p2])

        if stats is not None:

            assert(p1 in stats and p2 in stats)

        self.stats = stats
        self.points = points
        self.winner = winner
        self.loser = self.p2 if self.winner == self.p1 else self.p1
        self.odds = odds
        self.score = score
        self.final_point_level_info = final_point_level_info

    def to_dict(self):
        """Converts the CompletedMatch object to a dictionary representation.

        Returns:
            dict: A dictionary containing the information from Match's to_dict
            function, adding information about the winner and loser, as well as
            serve and return points won, if available.
        """

        parent_dict = super(CompletedMatch, self).to_dict()

        parent_dict.update({'winner': self.winner, 'loser': self.loser})

        if self.stats is not None:

            parent_dict.update({
                'spw_winner': self.stats[self.winner].pct_won_serve,
                'spw_loser': self.stats[self.loser].pct_won_serve,
                'rpw_winner': self.stats[self.winner].pct_won_return,
                'rpw_loser': self.stats[self.loser].pct_won_return})

        if self.odds is not None:

            parent_dict.update({
                'odds_winner': self.odds[self.winner],
                'odds_loser': self.odds[self.loser]})

        return parent_dict

    def __str__(self):

        string = '{} beat {} {} in match on {} in {}.'.format(
            self.winner, self.loser, self.score, self.date,
            self.tournament_name)

        if self.stats is not None:
            string += ' '
            for player in self.stats:
                string += str(self.stats[player])
                string += ' '

        if self.odds is not None:
            string += ' '
            for player in self.odds:
                string += player + ' ' + str(self.odds[player])
                string += ' '

        return string.strip()
