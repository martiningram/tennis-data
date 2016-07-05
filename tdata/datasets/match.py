class Match(object):

    def __init__(self, p1, p2, date, surface=None, tournament_name=None):

        self.p1 = p1
        self.p2 = p2
        self.date = date
        self.surface = None
        self.tournament_name = tournament_name

    def __str__(self):

        string = '{} is playing {} on {}.'.format(self.p1, self.p2, self.date)
        return string


class CompletedMatch(Match):

    def __init__(self, p1, p2, date, winner, surface=None, stats=None,
                 points=None, tournament_name=None):

        super(CompletedMatch, self).__init__(
            p1, p2, date, surface=surface, tournament_name=tournament_name)

        assert(winner in [p1, p2])

        if stats is not None:

            assert(p1 in stats and p2 in stats)

        self.stats = stats
        self.points = points
        self.winner = winner
        self.loser = self.p2 if self.winner == self.p1 else self.p1

    def __str__(self):

        string = '{} beat {} in match on {} in {}.'.format(
            self.winner, self.loser, self.date, self.tournament_name)

        if self.stats is not None:
            string += ' '
            for player in self.stats:
                string += str(self.stats[player])
                string += ' '

        return string.strip()
