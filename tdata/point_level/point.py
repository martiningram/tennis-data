# A wrapper class which adds information about who won the point to the "Score"
# object from the Monte Carlo simulator.


class Point(object):

    def __init__(self, score, server_won):

        self.score = score
        self.server_won = server_won
        self.shot_sequence = None
