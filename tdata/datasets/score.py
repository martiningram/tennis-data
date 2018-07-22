class BadFormattingException(Exception):
    pass


class Score(object):

    # Provides information about whether the match was best of five, whether
    # the final set went to a long advantage (i.e. longer than a tiebreak), and
    # how many games were won by each player in each set.

    def __init__(self, string_score, winner, loser):

        self.winner = winner
        self.loser = loser
        self.string_score = string_score

        self.sets = self.parse_string_score(string_score)
        self.bo5 = self.find_bo5(self.sets)

    def find_winner_loser_names(self, row):

        (winner, loser) = ((row['server1'], row['server2']) if
                           row['winner'] == 1 else
                           (row['server2'], row['server1']))

        self.winner = winner
        self.loser = loser

    def find_bo5(self, sets):

        assert(len(sets) > 0)

        if len(sets) == 2:
            return False
        elif len(sets) > 3:
            return True
        else:
            # We are left with the three-set case. Either the match's winner
            # won all three sets, in which case it is best of five; or he/she
            # played best of three.
            set_winners = [cur_set['match_winner_won']
                           for cur_set in sets]

            if all(set_winners):
                return True
            else:
                return False

    def was_long_final_set(self):

        assert(len(self.sets) > 0)
        final_set = self.sets[-1]

        if final_set['score'][0] > 7:
            return True

    def parse_string_score(self, string_score):

        result = list()

        # Break by spaces to find sets:
        sets = string_score.split(' ')

        for cur_set in sets:

            # Split on hyphen to find games:
            games = cur_set.split('-')

            # There should be exactly two matches:
            if len(games) != 2:
                print('Bad formatting: ' + str(cur_set))
                raise BadFormattingException()

            # The first is definitely the number of games won by player 1:
            try:
                p1_games = int(games[0])
            except ValueError:
                raise BadFormattingException(string_score)

            # For p2, we need to check whether it went to a tiebreak:
            tb_score = None
            was_tb = (p1_games == 7 and games[1][0] == '6') or \
                (p1_games == 6 and games[1][0] == '7')

            try:

                if was_tb:

                    p2_games = 6 if p1_games == 7 else 7

                    # Find the tiebreak score (and allow it to be missing):
                    bracket_beg = cur_set.find('(')

                    if bracket_beg == -1:

                        tb_score = -1
                    else:

                        bracket_end = cur_set.find(')')
                        tb_result = cur_set[bracket_beg + 1:bracket_end]

                        tb_score = int(tb_result)

                else:

                    # The number of games for p2 is just the second part of the
                    # split:
                    p2_games = int(games[1])

            except ValueError:

                raise BadFormattingException(string_score)

            # Put things together and record:
            cur_set = {'score': (p1_games, p2_games),
                       'match_winner_won': p1_games > p2_games,
                       'tiebreak_score': tb_score}

            result.append(cur_set)

        return result

    def __str__(self):

        return self.string_score
