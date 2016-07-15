import os
import readline
import rpy2.robjects as robjects


class ImportanceCalculator:

    importance_table = None

    def __init__(self):

        self.path = os.path.dirname(os.path.realpath(__file__))

        if ImportanceCalculator.importance_table is None:

            robjects.r('''
                    source('{0}/r_importance/create_importance.R')
                    source('{0}/r_importance/importance.R')
                    '''.format(self.path))

            self.r_importance = robjects.globalenv['importance']

    def make_importance_table(self):

        importance_dict = dict()

        # Make all possible permutations:
        # Service games:
        for bo3 in [True, False]:
            max_sets = 1 if bo3 else 2
            for sets_x in range(max_sets + 1):
                for sets_y in range(max_sets + 1):
                    for games_x in range(7):
                        for games_y in range(7):
                            if (games_x == 6 and games_y == 6):
                                for points_x in range(7):
                                    for points_y in range(7):
                                        importance_dict[(points_x, points_y,
                                                         games_x, games_y,
                                                         sets_x, sets_y,
                                                         True, bo3)] = \
                                            self.calculate_using_r(
                                                points_x, points_y, games_x,
                                                games_y, sets_x, sets_y,
                                                tiebreak=True, bo3=bo3)

                            for points_x in range(4):
                                for points_y in range(4):
                                    importance_dict[(points_x, points_y,
                                                     games_x, games_y,
                                                     sets_x, sets_y, False,
                                                     bo3)] = \
                                        self.calculate_using_r(
                                            points_x, points_y, games_x,
                                            games_y, sets_x, sets_y,
                                            tiebreak=False, bo3=bo3)

        ImportanceCalculator.importance_table = importance_dict

    def calculate_using_r(self, points_x, points_y, games_x, games_y,
                          sets_x, sets_y, tiebreak=False, bo3=False):

        r_result = self.r_importance(points_x, points_y, games_x, games_y,
                                     sets_x, sets_y, tiebreak, bo3)

        return r_result[0]

    def calculate_importance(self, points_x, points_y, games_x, games_y,
                             sets_x, sets_y, tiebreak=False, bo3=False):

        if ImportanceCalculator.importance_table is None:
            self.make_importance_table()

        return ImportanceCalculator.importance_table[
            (points_x, points_y, games_x, games_y, sets_x, sets_y,
             tiebreak, bo3)]


if __name__ == "__main__":

    c = ImportanceCalculator()

    state = (5, 5, 6, 6, 0, 0, True, False)

    print(c.calculate_importance(*state))
