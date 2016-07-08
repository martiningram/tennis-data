import pandas as pd


class Match(object):

    def __init__(self, p1, p2, date, surface=None, tournament_name=None):

        self.p1 = p1
        self.p2 = p2
        self.date = date
        self.surface = surface
        self.tournament_name = tournament_name

    def get_opponent(self, player):

        assert(player in [self.p1, self.p2])

        return self.p1 if player == self.p2 else self.p2

    def __str__(self):

        string = '{} is playing {} on {}.'.format(self.p1, self.p2, self.date)
        return string

    def to_dict(self):

        info_dict = {'p1': self.p1, 'p2': self.p2, 'surface': self.surface,
                     'tournament_name': self.tournament_name, 'date':
                     self.date}

        return info_dict

    @staticmethod
    def to_df(matches):

        results = list()

        for match in matches:

            results.append(match.to_dict)

        return pd.DataFrame(results)


class CompletedMatch(Match):

    def __init__(self, p1, p2, date, winner, surface=None, stats=None,
                 points=None, tournament_name=None):

        super(CompletedMatch, self).__init__(
            p1=p1, p2=p2, date=date, surface=surface,
            tournament_name=tournament_name)

        assert(winner in [p1, p2])

        if stats is not None:

            assert(p1 in stats and p2 in stats)

        self.stats = stats
        self.points = points
        self.winner = winner
        self.loser = self.p2 if self.winner == self.p1 else self.p1

    def to_dict(self):

        parent_dict = super(CompletedMatch, self).to_dict()

        parent_dict.update({'winner': self.winner, 'loser': self.loser})

        if self.stats is not None:

            parent_dict.update({
                'spw_winner': self.stats[self.winner].pct_won_serve,
                'spw_loser': self.stats[self.loser].pct_won_serve,
                'rpw_winner': self.stats[self.winner].pct_won_return,
                'rpw_loser': self.stats[self.losser].pct_won_return})

        return parent_dict

    def __str__(self):

        string = '{} beat {} in match on {} in {}.'.format(
            self.winner, self.loser, self.date, self.tournament_name)

        if self.stats is not None:
            string += ' '
            for player in self.stats:
                string += str(self.stats[player])
                string += ' '

        return string.strip()
