from collections import defaultdict, namedtuple
import import_data


PointStageExt = namedtuple("PointStageExt",
                           ['is_tiebreak', 'is_bp', 'is_pt_b_bp',
                            'set_up', 'set_down', 'missed_opp',
                            'missed_opp_return', 'point_spread',
                            'previous_win', 'points_played',
                            'importance'])


def look_up_matrix(serving, returning, tournament, matrix_dir):

    result_dict = defaultdict(dict)

    all_data = import_data.merge_data(matrix_dir)

    # Look up data:
    all_serving_data = all_data["serving"]
    all_returning_data = all_data["returning"]

    cur_serving_data = all_serving_data.loc[(serving, tournament)]
    cur_returning_data = all_returning_data.loc[(returning, tournament)]

    # Turn into dictionary for speed:
    cur_serving_data = cur_serving_data.to_dict()
    cur_returning_data = cur_returning_data.to_dict()

    result_dict[serving] = {"serving": cur_serving_data,
                            "returning": cur_returning_data}

    return result_dict


# This needs to be curried with the matrix directory before use!
def translate_stage_two_matrix(df, matrix_dir):

    row = df.iloc[0]

    server = row["serving"]
    returning = row["returning"]
    tournament = row["tournament"]

    return look_up_matrix(server, returning, tournament, matrix_dir)


def identify_point_extended(score, server):

    point_spread = score.points_won_set[server] - \
        score.points_won_set[score.cur_returner()]

    set_diff = score.sets[server] - score.sets[score.cur_returner()]

    lookup = \
        PointStageExt(is_tiebreak=1 if score.is_tiebreak() else 0,
                      is_bp=1 if score.is_breakpoint() else 0,
                      is_pt_b_bp=1 if score.is_pt_before_bp() else 0,
                      set_up=1 if set_diff >= 1 else 0,
                      set_down=1 if set_diff <= -1 else 0,
                      missed_opp=1 if
                      score.missed_bp_last_returning[server] else 0,
                      missed_opp_return=1 if
                      score.missed_bp_last_returning[score.cur_returner()]
                      else 0,
                      previous_win=1 if
                      score.last_point_winner == server else 0,
                      point_spread=point_spread,
                      points_played=score.points_last_game,
                      importance=score.calculate_importance())

    return lookup


def scorer_stage_two_matrix(score, server, result_dict):

    lookup = identify_point_extended(score, server)

    serving_matrix = result_dict[server]["serving"]
    returning_matrix = result_dict[server]["returning"]

    def calc_sum(lookup, matrix):

        total = matrix["intercept"] + \
            lookup.is_tiebreak * matrix["tiebreak"] + \
            lookup.is_bp * matrix["breakpoint"] + \
            lookup.is_pt_b_bp * matrix["before_breakpoint"] + \
            lookup.set_up * matrix["set_up"] + \
            lookup.set_down * matrix["set_down"] + \
            lookup.point_spread * matrix["point_spread"] + \
            lookup.previous_win * matrix["previous_win"] + \
            lookup.missed_opp * matrix["missed_opp"] + \
            lookup.missed_opp_return * matrix["missed_opp_return"] + \
            lookup.points_played * matrix["points_played"] + \
            lookup.importance * matrix["point_importance"]

        return total

    serving_sum = calc_sum(lookup, serving_matrix)
    returning_sum = calc_sum(lookup, returning_matrix)
    total = serving_sum + returning_sum

    return total
