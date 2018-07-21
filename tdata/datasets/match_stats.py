class MatchStats(object):
    """Container class storing all information about a player's performance in
    a match. Add more optional stats as required."""

    def __init__(self, player_name, serve_points_played, serve_points_won,
                 return_points_played, return_points_won, winners=None,
                 ues=None):

        self.player_name = player_name

        self.serve_points_won = server_points_won
        self.serve_points_played = server_points_played

        self.return_points_won = return_points_won
        self.return_points_played = return_points_played

        self.pct_won_serve = serve_points_won / float(serve_points_played)
        self.pct_won_return = return_points_won / float(return_points_played)

        self.winners = winners
        self.ues = ues

    def __str__(self):

        output = "{} won {}% on serve and {}% on return.".format(
            self.player_name, round(self.pct_won_serve, 3) * 100,
            round(self.pct_won_return, 3) * 100 if self.pct_won_return is not
            None else None)

        return output
