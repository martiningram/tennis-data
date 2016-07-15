import pandas as pd
import monte_carlo
import numpy as np
import matplotlib.pyplot as plt
import stage_2
import os
import fnmatch
import sys
from collections import defaultdict


def get_probability(situation_list, result_dict):

    result = result_dict[situation_list]
    return result


def create_match_dict(match_row, df, translation_func):

    # Get the two perspectives:
    p1_perspective = \
        df[(df["serving_match"] == match_row["serving_match"]) &
            (df["returning_match"] == match_row["returning_match"])]

    p2_perspective = \
        df[(df["serving_match"] == match_row["returning_match"]) &
            (df["returning_match"] == match_row["serving_match"])]

    # Make the dictionaries out of the data:
    cur_match_data = translation_func(p1_perspective)
    cur_match_data.update(translation_func(p2_perspective))

    # Pick the first line of the matched data to find the
    # i.i.d. probability:
    iid_p1 = p1_perspective.iloc[0]
    iid_p2 = p2_perspective.iloc[0]

    iid_dict = {iid_p1["serving"]: iid_p1["serveprob_iid"],
                iid_p2["serving"]: iid_p2["serveprob_iid"]}

    return cur_match_data, iid_dict


# df is a dataframe containing the matches to simulate
# translation_func takes the dataframe data for each match and must return a
# dictionary which is then used by
# scoring_func to predict the server's probability of winning the current point
# on serve.
def simulate_predictions(df, translation_func, scoring_func, export_name,
                         num_trials=1):

    # A little bit fudgy. Maybe see whether this could be in the dataframe
    # instead.
    bo5 = "wta" not in export_name

    all_results = list()
    handled_matches = set(frozenset())

    # Find the distinct matches:
    matches = df.drop_duplicates(subset=["serving_match", "returning_match"])

    for j, (i, row) in enumerate(matches.iterrows()):

        print("Processing row " + str(j) + " of " + str(matches.shape[0]))

        server_won_iid, server_won_non_iid = 0, 0

        if (frozenset([row["serving_match"], row["returning_match"]]) in
                handled_matches):
            # Done this one
            continue

        # Add the current match to the handled matches
        handled_matches.add(frozenset([row["serving_match"],
                                       row["returning_match"]]))

        cur_match_data, iid_dict = create_match_dict(row, df, translation_func)

        # Define the scoring function:
        def scorer(x, y):
            return scoring_func(x, y, cur_match_data)

        def iid_scorer(score, server):
            return monte_carlo.iid(score, server, iid_dict)

        num_served_first = {row["serving"]: 0, row["returning"]: 0}

        percentage_sum_iid = defaultdict(lambda: 0)
        percentage_sum_dynamic = defaultdict(lambda: 0)

        # Run trials:
        for i in range(num_trials):

            (server, returner) = (row["serving"], row["returning"]) if \
                                  np.random.rand(1) >= 0.5 else \
                                  (row["returning"], row["serving"])

            num_served_first[server] += 1

            # Run the non-iid trials:
            final_score = monte_carlo.play_match(
                monte_carlo.Score(server, returner, bo5),
                server, returner, scorer)

            # Run the iid trials:
            final_score_iid = monte_carlo.play_match(
                monte_carlo.Score(row["serving"], row["returning"], bo5),
                row["serving"], row["returning"], iid_scorer)

            if i % 1000 == 0:
                print(i)

            if final_score.winner() == row["serving"]:
                server_won_non_iid += 1
            if final_score_iid.winner() == row["serving"]:
                server_won_iid += 1

            dynamic_percentages = final_score.pct_won_serve()
            iid_percentages = final_score_iid.pct_won_serve()

            for key in dynamic_percentages.keys():
                percentage_sum_dynamic[key] += dynamic_percentages[key]

            for key in iid_percentages.keys():
                percentage_sum_iid[key] += iid_percentages[key]

        # Record the results and add them to the series:
        cur_dict = {"p_win_noniid": float(server_won_non_iid) / num_trials,
                    "p_win_iid": float(server_won_iid) / num_trials,
                    "av_serve_dyn_serving":
                    percentage_sum_dynamic[row["serving"]] / num_trials,
                    "av_serve_iid_serving":
                    percentage_sum_iid[row["serving"]] / num_trials,
                    "av_serve_dyn_returning":
                    percentage_sum_dynamic[row["returning"]] / num_trials,
                    "av_serve_iid_returning":
                    percentage_sum_iid[row["returning"]] / num_trials,
                    "bo5": bo5}

        results = pd.concat([row, pd.Series(cur_dict)])

        print(results)

        all_results.append(results)

    # Export:
    all_results = pd.DataFrame(all_results)

    # Remove unnecessary columns:
    columns_to_keep = [x for x in all_results.columns if not any(
        [y in x for y in ["tiebreak", "breakpoint", "before_breakpoint",
                          "set_up", "set_down", "missed_opp", "previous_win",
                          "point_spread", "importance", "points_played"]])]

    all_results = all_results[columns_to_keep]

    all_results.to_csv("simulation_results_" + export_name + ".csv",
                       index=False)


def merge_data(directory):

    all_files = os.listdir(directory)

    serving_data = pd.DataFrame()
    returning_data = pd.DataFrame()

    for filename in all_files:
        if fnmatch.fnmatch(filename, '*.csv'):

            cur_data = pd.read_csv(directory + filename)

            cur_data["t_type"] = "wta" if "wta" in filename else "atp"

            if "ausopen" in filename:
                t_name = "Australian Open"
            elif "frenchopen" in filename:
                t_name = "French Open"
            elif "usopen" in filename:
                t_name = "US Open"
            elif "wimbledon" in filename:
                t_name = "Wimbledon"

            cur_data["tournament"] = t_name

            if "returning" in filename:
                returning_data = pd.concat([returning_data, cur_data])

            elif "serving" in filename:
                serving_data = pd.concat([serving_data, cur_data])

    serving_data = serving_data.set_index([serving_data.index,
                                           'tournament'])

    returning_data = returning_data.set_index([returning_data.index,
                                               'tournament'])

    return {"serving": serving_data, "returning": returning_data}


# Constructs serving and returning matches, assuming the dataframe contains
# unique matchups (i.e. player A only plays player B once.)
def construct_serving_and_returning_match(df):

    df["serving_match"] = df["tournament"] + ":" + df["winner_name"] + \
        ":" + df["loser_name"] + ":" + df["serving"]

    df["returning_match"] = df["tournament"] + ":" + df["winner_name"] + \
        ":" + df["loser_name"] + ":" + df["returning"]

    return df


def assess_convergence(df, scorer, translator):

    trials = [1000, 2000, 3000, 5000, 7500, 10000]

    final_results = list()

    trials_per_run = 10

    for trial in trials:

        results, results_iid = list(), list()

        for x in range(10):

            result = \
                simulate_predictions(df, translator, scorer, trial)

            results.append(result["p_win_noniid"])
            results_iid.append(result["p_win_iid"])

        final_results.append({"trials": trial,
                              "mean_noniid": np.average(results),
                              "mean_iid": np.average(results_iid),
                              "std": np.std(results),
                              "std_iid": np.std(results_iid),
                              "trials_per_run": trials_per_run})

    print(final_results)

    final_results = pd.DataFrame(final_results)
    final_results.to_csv("convergence.csv")

    plt.subplot(2, 2, 1)
    plt.scatter(final_results["trials"], final_results["mean_noniid"])
    plt.title("noniid means")
    plt.subplot(2, 2, 2)
    plt.scatter(final_results["trials"], final_results["mean_iid"])
    plt.title("iid means")
    plt.subplot(2, 2, 3)
    plt.scatter(final_results["trials"], final_results["std"])
    plt.title("noniid stds")
    plt.subplot(2, 2, 4)
    plt.scatter(final_results["trials"], final_results["std_iid"])
    plt.title("iid stds")
    plt.show()


if __name__ == "__main__":

    if len(sys.argv) != 2:
        print("Please provide a target file!")
        exit()

    filename = str(sys.argv[1])
    split_version = filename.split('/')
    last_part = split_version[-1]
    export_base = last_part.split('.')[0]

    df = pd.read_csv(filename)
    df = construct_serving_and_returning_match(df)

    # This is fallible:
    if "wta" in filename:
        df["t_type"] = "wta"
    else:
        df["t_type"] = "atp"

    def translate_average(df):
        return stage_2.translate_stage_two_matrix(
            df, 'data/avg_effect_tables/')

    def translate_dynamic(df):
        return stage_2.translate_stage_two_matrix(
            df, 'data/serve_return_effect_matrices/')

    simulate_predictions(df, translate_dynamic,
                         stage_2.scorer_stage_two_matrix,
                         export_base + "_dynamic")

    simulate_predictions(df, translate_average,
                         stage_2.scorer_stage_two_matrix,
                         export_base + "_fixed")
