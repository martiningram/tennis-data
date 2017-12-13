import tdata.point_level.monte_carlo.monte_carlo as monte_carlo

from copy import deepcopy
from tdata.point_level.point import Point


def generate_points(start_score, win_sequence):

    start_score = deepcopy(start_score)
    point_sequence = list()

    advanced_score = start_score

    for outcome in win_sequence:

        cur_point = Point(deepcopy(advanced_score), outcome)
        point_sequence.append(cur_point)
        start_score_copy = deepcopy(start_score)
        advanced_score = monte_carlo.advance_score(
            start_score_copy, point_sequence)

    return point_sequence, advanced_score
