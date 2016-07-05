class MatchStats(object):
    """Container class storing all information about a player's performance in
    a match. Add more optional stats as required."""

    def __init__(self, player_name, pct_won_serve, pct_won_return, odds=None,
                 pct_first_serve=None, pct_won_first_serve=None,
                 pct_won_second_serve=None, winners=None, ues=None):

        self.player_name = player_name

        self.pct_won_serve = pct_won_serve
        self.pct_won_return = pct_won_return

        self.pct_first_serve = pct_first_serve
        self.pct_won_first_serve = pct_won_first_serve
        self.pct_won_second_serve = pct_won_second_serve

        self.winners = winners
        self.ues = ues

        self.odds = odds

    def __str__(self):

        output = "{} won {}% on serve and {}% on return.".format(
            self.player_name, round(self.pct_won_serve, 3) * 100,
            round(self.pct_won_return, 3) * 100 if self.pct_won_return is not
            None else None)

        return output
