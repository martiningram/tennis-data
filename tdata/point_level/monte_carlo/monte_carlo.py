import numpy as np
from copy import deepcopy
from collections import defaultdict
from importance import ImportanceCalculator


class Score:

    def __init__(self, p1, p2, bo5):

        self.p1 = p1
        self.p2 = p2
        self.bo5 = bo5

        self.set_num = 0

        self.sets = dict()
        self.sets[p1] = 0
        self.sets[p2] = 0

        self.games = defaultdict(dict)
        self.games[self.set_num][p1] = 0
        self.games[self.set_num][p2] = 0

        self.points = dict()
        self.points[self.p1] = 0
        self.points[self.p2] = 0

        self.serve_stats = defaultdict(dict)
        for x in [self.p1, self.p2]:
            self.serve_stats[x]["out_of"] = 0
            self.serve_stats[x]["won"] = 0

        self.service_game_stats = defaultdict(dict)
        for x in [self.p1, self.p2]:
            self.service_game_stats[x]['out_of'] = 0
            self.service_game_stats[x]['won'] = 0

        self.cur_server = p1
        self.match_over = False
        self.last_point_winner = "Nobody"
        self.points_won_set = {self.p1: 0, self.p2: 0}
        self.missed_bp_last_returning = {self.p1: False, self.p2: False}
        self.points_last_game = 0

        self.bp_won = dict()
        self.bp_won[p1] = 0
        self.bp_won[p2] = 0

        self.bps_total = dict()
        self.bps_total[p1] = 0
        self.bps_total[p2] = 0

        self.importance_calculator = ImportanceCalculator()

    def reset_points(self):

        self.points[self.p1], self.points[self.p2] = 0, 0

    def cur_returner(self):

        return self.p1 if self.cur_server == self.p2 else self.p2

    def is_tiebreak(self):
        games_p1 = self.games[self.set_num][self.p1]
        games_p2 = self.games[self.set_num][self.p2]
        return (games_p1 == 6 and games_p1 == games_p2)

    # Maybe turn into static methods for a slight speed boost. Or just
    # functions.
    def is_breakpoint(self):

        if self.is_tiebreak():
            return False

        returner = self.p1 if self.cur_server == self.p2 else self.p2
        difference = self.points[returner] - self.points[self.cur_server]

        if difference < 1:
            return False
        elif self.points[returner] < 3:
            return False
        else:
            return True

    def is_pt_before_bp(self):

        if self.is_tiebreak():
            return False

        returner = self.p1 if self.cur_server == self.p2 else self.p2

        s_pts, r_pts = self.points[self.cur_server], self.points[returner]

        difference = r_pts - s_pts

        if difference == 0 and r_pts >= 2:
            return True
        elif r_pts == 2 and s_pts <= 2:
            return True
        else:
            return False

    def calculate_importance(self, verbose=False):

        if self.is_tiebreak():
            deuce = 6
        else:
            deuce = 3

        pts_server = self.points[self.cur_server]
        pts_returner = self.points[self.cur_returner()]

        # Map points to be 3-3 -- or 6-6 -- at most:
        if (pts_server > deuce or pts_returner > deuce):
            difference = self.points[self.cur_server] - \
                self.points[self.cur_returner()]

            if difference >= 0:
                pts_server = deuce - 1 + difference
                pts_returner = deuce - 1

            else:
                pts_server = deuce - 1
                pts_returner = deuce - 1 + abs(difference)

        calc_importance = self.importance_calculator.calculate_importance

        args = (pts_server, pts_returner,
                self.games[self.set_num][self.cur_server],
                self.games[self.set_num][self.cur_returner()],
                self.sets[self.cur_server],
                self.sets[self.cur_returner()], self.is_tiebreak(),
                not self.bo5)

        if verbose:
            print(args)

        importance = calc_importance(*args)

        return importance

    def total_games(self):

        total_games = 0

        for i in range(self.set_num + 1):

            total_games += self.games[i][self.p1] + self.games[i][self.p2]

        return total_games

    def winner(self):

        assert(self.match_over)

        return self.p1 if self.sets[self.p1] > self.sets[self.p2] else self.p2

    def pct_won_serve(self):

        assert(self.match_over)

        percentages = dict()
        for player in [self.p1, self.p2]:
            percentages[player] = self.serve_stats[player]["won"] / \
                float(self.serve_stats[player]["out_of"])

        return percentages

    def player_wins_set(self, winner):

        # The winner of the service game has won the set
        self.sets[winner] += 1

        max_sets = 3 if self.bo5 else 2

        if self.sets[winner] == max_sets:

            self.match_over = True

        else:

            # Start a new set:
            self.set_num += 1

            self.games[self.set_num][self.p1] = 0
            self.games[self.set_num][self.p2] = 0

            self.points_last_game = 0

            self.points_won_set[self.p1] = 0
            self.points_won_set[self.p2] = 0

            self.missed_bp_last_returning = {self.p1: False, self.p2: False}

    def player_wins_service_game(self, winner, loser):

        # Store points played:
        self.points_last_game = self.points[winner] + self.points[loser]

        # Reset game points:
        self.points[winner] = 0
        self.points[loser] = 0

        # Update set standings:
        cur_games = self.games[self.set_num]
        cur_games[winner] += 1
        difference = cur_games[winner] - cur_games[loser]

        if (cur_games[winner] >= 6 and difference >= 2):

            self.player_wins_set(winner)

    def player_wins_tiebreak(self, winner, loser):

        # Reset game points:
        self.points[winner] = 0
        self.points[loser] = 0

        # Update set standings:
        cur_games = self.games[self.set_num]
        cur_games[winner] += 1

        self.player_wins_set(winner)

    def __str__(self):

        cur_server = self.cur_server
        cur_returner = self.cur_returner()

        s = self.cur_server + " vs. " + cur_returner + ": "

        for i in range(self.set_num+1):

            s += str(self.games[i][cur_server]) + "-" + \
                str(self.games[i][cur_returner]) + " "

        if not self.match_over:
            s += str(self.points[cur_server]) + ":" + \
                str(self.points[cur_returner])

        return s


def service_game_over(points, server, receiver):

    difference = abs(points[server] - points[receiver])

    if difference < 2:
        return False

    elif points[server] < 4 and points[receiver] < 4:
        return False

    else:
        return True


def tiebreak_over(points, server, receiver):

    difference = abs(points[server] - points[receiver])

    if difference < 2:
        return False

    elif points[server] < 7 and points[receiver] < 7:
        return False

    else:
        return True


def play_service_game(score, server, receiver, prob_fun_server):

    returner_had_bp = False

    while not service_game_over(score.points, server, receiver):

        # Increment points played on serve:
        score.serve_stats[server]["out_of"] += 1

        prob_win_server = prob_fun_server(score, server)

        generated_val = np.random.rand(1)

        if generated_val <= prob_win_server:
            score.points[server] += 1
            score.points_won_set[server] += 1
            score.last_point_winner = server
            score.serve_stats[server]["won"] += 1

        else:
            score.points[receiver] += 1
            score.points_won_set[receiver] += 1
            score.last_point_winner = receiver

        if score.is_breakpoint():
            returner_had_bp = True
            score.bps_total[receiver] += 1

    winner = server if score.points[server] > score.points[receiver] \
        else receiver

    loser = server if winner == receiver else receiver

    if loser == server:
        score.bp_won[winner] += 1

    if winner == server:
        score.service_game_stats[server]['won'] += 1

    score.service_game_stats[server]['out_of'] += 1

    # For the predictors:
    score.missed_bp_last_returning[receiver] = \
        returner_had_bp and winner != receiver

    score.player_wins_service_game(winner, loser)

    return score


def play_tiebreak(score, server, receiver, prob_fun_server):

    # Do not carry over missed opportunities into tiebreak:
    score.missed_bp_last_returning = {score.p1: False, score.p2: False}

    while not tiebreak_over(score.points, server, receiver):

        # Increment points played on serve:
        score.serve_stats[server]["out_of"] += 1

        prob_win_server = prob_fun_server(score, server)

        generated_val = np.random.rand(1)

        if generated_val <= prob_win_server:
            score.points[server] += 1
            score.points_won_set[server] += 1
            score.last_point_winner = server
            score.serve_stats[server]["won"] += 1

        else:
            score.points[receiver] += 1
            score.points_won_set[receiver] += 1
            score.last_point_winner = receiver

        point_sum = score.points[server] + score.points[receiver]

        if point_sum % 2 == 1:
            server, receiver = receiver, server
            score.cur_server = server

    winner = server if score.points[server] > score.points[receiver] \
        else receiver

    loser = server if winner == receiver else receiver

    score.player_wins_tiebreak(winner, loser)

    return score


def play_match(score, server, receiver, prob_fun_server):

    while not score.match_over:

        if not (score.games[score.set_num][server] == 6
                and score.games[score.set_num][receiver] == 6):
            score = play_service_game(score, server, receiver, prob_fun_server)

        else:
            score = play_tiebreak(score, server, receiver, prob_fun_server)

        server, receiver = receiver, server
        score.cur_server = server

    return score


def iid(score, server, server_win_probs):
    return server_win_probs[server]


# Advances the score by the points and returns the advanced score.
def advance_score(score, points):

    assert(len(points) > 0)

    points_to_advance = deepcopy(points)

    def advancing_scorer(score, server):

        cur_point = points_to_advance.pop(0)

        if cur_point.server_won:
            return 1
        else:
            return 0

    first_point = points[0]

    server, receiver = score.cur_server, score.cur_returner()

    while len(points) > 0:

        if not (score.games[score.set_num][server] == 6
                and score.games[score.set_num][receiver] == 6):
            try:
                score = play_service_game(score, server, receiver,
                                          advancing_scorer)

            except IndexError:
                break

        else:
            try:
                score = play_tiebreak(score, server, receiver,
                                    advancing_scorer)

            except IndexError:
                break

        server, receiver = receiver, server
        score.cur_server = server

    return score


if __name__ == "__main__":

    # Set game parameters:
    p1 = "Roger Federer"
    p2 = "Rafael Nadal"
    bo5 = False

    from pbm.monte_carlo.stage_2 import identify_point_extended

    # Fixed probabilities (just use i.i.d.):
    serve_win_probabilities = {p1: 0.5, p2: 0.55}

    def test_iid(score, server):

        # Not actually used but could be optimised
        identified = identify_point_extended(score, server)

        return iid(score, server, serve_win_probabilities)

    trials = 5000

    win_nums = {p1: 0, p2: 0}

    games = list()

    breaks = list()

    for i in range(trials):

        first_server = p1 if np.random.rand(1) >= 0.5 else p2

        final_score = play_match(Score(p1, p2, bo5), p1, p2, test_iid)

        win_nums[final_score.winner()] += 1

        games.append(final_score.total_games())
        breaks.append(final_score.total_breaks)

        if i % 1000 == 0:

            print('On trial {0} of {1}'.format(i, trials))

    games = np.array(games)

    win_probs = {x: win_nums[x] / float(trials) for x in win_nums}

    print('Average number of games was: {}'.format(np.average(games)))
    print('Average number of breaks was: {}'.format(np.average(breaks)))
    print('Win probabilities: {}'.format(win_probs))
