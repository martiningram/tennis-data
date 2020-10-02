import os
import pandas as pd
from pathlib import Path

from tdata.datasets.match_stats import MatchStats
from tdata.datasets.dataset import Dataset
from tdata.enums.t_type import Tours
from tdata.enums.surface import Surfaces


class OnCourtDataset(Dataset):

    # TODO: Maybe switch over to SQL.

    def __init__(
        self,
        t_type=Tours.atp,
        drop_challengers=True,
        drop_qualifying=True,
        drop_doubles=True,
    ):

        exec_dir = Path(os.path.abspath(__file__)).parents[2]

        self.t_type = t_type
        self.drop_challengers = drop_challengers
        self.drop_qualifying = drop_qualifying
        self.drop_doubles = drop_doubles

        csv_dir = os.path.join(str(exec_dir), "data", "oncourt")

        def read_with_suffix(table_name, suffix=t_type.name):
            return pd.read_csv(
                os.path.join(csv_dir, "{}_{}.csv".format(table_name, suffix))
            )

        player_table = read_with_suffix("players")
        tour_table = read_with_suffix("tours")
        games_table = read_with_suffix("games")
        stats_table = read_with_suffix("stat")
        court_table = pd.read_csv(os.path.join(csv_dir, "courts.csv"))
        rankings_table = read_with_suffix("ratings")
        odds_table = read_with_suffix('odds')

        merged = self.merge_tables(
            player_table,
            tour_table,
            games_table,
            stats_table,
            court_table,
            rankings_table,
            odds_table
        )
        merged["DATE_G"] = pd.to_datetime(merged["DATE_G"])
        merged = merged.rename(columns={"DATE_G": "start_date", "RESULT_G": "score"})
        merged["round_number"] = merged["round"]

        # TODO: Replace the round numbers with the enum values
        self.df = merged.sort_values("start_date")

        old_size = self.df.shape[0]

        # We don't want exhibitions
        self.df = self.df[
            ~self.df["tournament_name"].str.contains("Hopman|Mubadala World Tennis")
        ]

        self.df["year"] = self.df["start_date"].dt.year

        # Drop duplicates
        self.df = self.df.drop_duplicates(
            subset=["winner", "loser", "round", "tournament_name", "year"]
        )

        new_size = self.df.shape[0]

        if old_size - new_size > 10:
            print(
                f"Warning: dropping duplicates reduced size from {old_size}"
                f" to {new_size}."
            )

        super(OnCourtDataset, self).__init__(start_date_is_exact=True)

        self.df = self.df.set_index(self.df_index, drop=False)

    def calculate_stats(self, winner, loser, row):

        # TODO: Add the odds!
        player_stats = dict()

        for suffix, name in zip([1, 2], [winner, loser]):

            opp_suffix = 1 if suffix == 2 else 2

            opp_rpwof = row["RPWOF_{}".format(opp_suffix)]
            opp_rpw = row["RPW_{}".format(opp_suffix)]

            player_spw = opp_rpwof - opp_rpw
            player_sp_played = opp_rpwof

            player_rpof = row["RPWOF_{}".format(suffix)]
            player_rpw = row["RPW_{}".format(suffix)]

            ue = row["UE_{}".format(suffix)]
            ws = row["WIS_{}".format(suffix)]

            player_stats[name] = MatchStats(
                player_name=name,
                serve_points_played=player_sp_played,
                serve_points_won=player_spw,
                return_points_played=player_rpof,
                return_points_won=player_rpw,
                ues=ue,
                winners=ws,
            )

        return player_stats

    def get_stats_df(self):

        return self.df

    @staticmethod
    def merge_odds_and_games(odds_table, games_table):

        lookup = odds_table.set_index(
            ['ID1_O', 'ID2_O', 'ID_T_O', 'ID_R_O', 'ID_B_O'])
        lookup = lookup.to_dict()

        all_odds = list()

        for sample_row in games_table.itertuples():

            winner_odds, loser_odds = None, None

            try:
                index = (sample_row.ID1_G, sample_row.ID2_G, sample_row.ID_T_G,
                         sample_row.ID_R_G, 2)
                winner_odds = lookup['K1'][index]
                loser_odds = lookup['K2'][index]
            except KeyError:
                try:
                    index = (sample_row.ID2_G, sample_row.ID1_G,
                             sample_row.ID_T_G, sample_row.ID_R_G, 2)
                    winner_odds = lookup['K2'][index]
                    loser_odds = lookup['K1'][index]
                except KeyError:
                    pass

            all_odds.append({'winner_odds': winner_odds,
                             'loser_odds': loser_odds})

        all_odds = pd.DataFrame(all_odds, index=games_table.index)

        games_table['winner_odds'] = all_odds['winner_odds']
        games_table['loser_odds'] = all_odds['loser_odds']

        return games_table

    def merge_tables(
        self,
        player_table,
        tour_table,
        games_table,
        stats_table,
        court_table,
        rankings_table,
        odds_table
    ):

        court_mapping = {
            1: Surfaces.hard,
            2: Surfaces.clay,
            3: Surfaces.indoor_hard,
            4: Surfaces.carpet,
            5: Surfaces.grass,
            6: Surfaces.acrylic,
        }

        player_table["DATE_P"] = pd.to_datetime(player_table["DATE_P"])
        rankings_table["DATE_R"] = pd.to_datetime(rankings_table["DATE_R"])
        games_table["DATE_G"] = pd.to_datetime(games_table["DATE_G"])

        # TODO: This is not very good. Find a better way!
        # Maybe merge somehow. This is terrible.
        # TODO: Maybe add prize money (and transform it)
        player_lookup = {row.ID_P: row.NAME_P for row in player_table.itertuples()}
        player_nationality_lookup = {
            row.ID_P: row.COUNTRY_P for row in player_table.itertuples()
        }
        tournament_lookup = {row.ID_T: row.NAME_T for row in tour_table.itertuples()}
        tournament_nationality_lookup = {
            row.ID_T: row.COUNTRY_T for row in tour_table.itertuples()
        }
        t_rank_lookup = {row.ID_T: row.RANK_T for row in tour_table.itertuples()}
        t_court_lookup = {
            row.ID_T: court_mapping[row.ID_C_T] for row in tour_table.itertuples()
        }
        player_birthdate_lookup = {
            row.ID_P: row.DATE_P for row in player_table.itertuples()
        }

        with_date = games_table.dropna()

        with_date = self.merge_odds_and_games(odds_table, games_table)

        with_date.loc[:, "tournament_rank"] = [
            t_rank_lookup[row.ID_T_G] for row in with_date.itertuples()
        ]

        with_date.loc[:, "winner_nationality"] = [
            player_nationality_lookup[row.ID1_G] for row in with_date.itertuples()
        ]

        with_date.loc[:, "loser_nationality"] = [
            player_nationality_lookup[row.ID2_G] for row in with_date.itertuples()
        ]

        with_date.loc[:, "winner_birthdate"] = [
            player_birthdate_lookup[row.ID1_G] for row in with_date.itertuples()
        ]

        with_date.loc[:, "loser_birthdate"] = [
            player_birthdate_lookup[row.ID2_G] for row in with_date.itertuples()
        ]

        with_date.loc[:, "tournament_country"] = [
            tournament_nationality_lookup[row.ID_T_G] for row in with_date.itertuples()
        ]

        with_date.loc[:, "surface"] = [
            t_court_lookup[row.ID_T_G].name for row in with_date.itertuples()
        ]

        if self.drop_challengers:

            with_date = with_date[with_date["tournament_rank"] > 1]

        with_date.loc[:, "winner"] = [
            player_lookup[row.ID1_G] for row in with_date.itertuples()
        ]
        with_date.loc[:, "loser"] = [
            player_lookup[row.ID2_G] for row in with_date.itertuples()
        ]
        with_date.loc[:, "tournament_name"] = [
            tournament_lookup[row.ID_T_G] for row in with_date.itertuples()
        ]

        # No doubles
        if self.drop_doubles:
            with_date = with_date[~with_date["winner"].str.contains("/")]

        # Try to merge into the stats table
        with_date = with_date.rename(
            columns={"ID1_G": "ID1", "ID2_G": "ID2", "ID_T_G": "ID_T", "ID_R_G": "ID_R"}
        )

        previous_rows = stats_table.shape[0]

        # Drop duplicates on the stats table
        stats_table = stats_table.drop_duplicates(subset=["ID1", "ID2", "ID_T", "ID_R"])

        rows_after_dropping_duplicates = stats_table.shape[0]

        if previous_rows - rows_after_dropping_duplicates > 10:
            print(
                f"Warning: {previous_rows - rows_after_dropping_duplicates}"
                f" have been dropped."
            )

        with_date = with_date.merge(
            stats_table,
            validate="one_to_one",
            on=["ID1", "ID2", "ID_T", "ID_R"],
            how="left",
        )

        keep_qualifying = not self.drop_qualifying

        rounds_to_keep = [4, 5, 6, 7, 8, 9, 10, 12]

        # TODO: There's also stuff like pre-qualifying and bronze and so on.
        # Maybe think about what to do about these; dropping for now.
        if keep_qualifying:

            rounds_to_keep += [1, 2, 3]

        with_date = with_date.rename(columns={"ID_R": "round"})
        with_date = with_date[with_date["round"].isin(rounds_to_keep)]

        # Discard juniors & wildcard events
        with_date = with_date[
            ~with_date["tournament_name"].str.contains(
                "junior|Junior|wildcard|Wildcard"
            )
        ]

        # Add ranking
        weeks = with_date["DATE_G"].dt.isocalendar().week
        years = with_date["DATE_G"].dt.year

        winner_ids = with_date["ID1"].values
        loser_ids = with_date["ID2"].values

        rank_years = rankings_table["DATE_R"].dt.year
        rank_weeks = rankings_table["DATE_R"].dt.isocalendar().week

        rank_lookup = {
            (player_id, year, week): position
            for player_id, year, week, position in zip(
                rankings_table["ID_P_R"].values,
                rank_years.values,
                rank_weeks.values,
                rankings_table["POS_R"].values,
            )
        }

        winner_ranks = pd.Series(
            [
                rank_lookup.get((cur_winner, cur_year, cur_week), None)
                for cur_winner, cur_year, cur_week in zip(
                    winner_ids, years.values, weeks.values
                )
            ],
            index=with_date.index,
        )

        loser_ranks = pd.Series(
            [
                rank_lookup.get((cur_loser, cur_year, cur_week), None)
                for cur_loser, cur_year, cur_week in zip(
                    loser_ids, years.values, weeks.values
                )
            ],
            index=with_date.index,
        )

        with_date["winner_ranking"] = winner_ranks
        with_date["loser_ranking"] = loser_ranks

        return with_date


# A number of utility functions. These _could_ be made static functions.
def is_slam(tournament_column):

    return tournament_column.str.contains(
        "Australian Open|French Open|Wimbledon|U.S. Open"
    )


def was_retirement(score_column):

    return score_column.str.contains("ret|w/o")


def calculate_spw(oncourt_df):

    rpw_1 = oncourt_df["RPW_1"]
    rpwof_1 = oncourt_df["RPWOF_1"]

    rpw_2 = oncourt_df["RPW_2"]
    rpwof_2 = oncourt_df["RPWOF_2"]

    # Number of serve points won by 2 is the total number of return points for
    # 1 minus the ones they won.
    spw_2 = rpwof_1 - rpw_1
    spw_1 = rpwof_2 - rpw_2

    sp_played_1 = rpwof_2
    sp_played_2 = rpwof_1

    return spw_1, sp_played_1, spw_2, sp_played_2


def calculate_sp_proportion(oncourt_df):

    spw_1, sp_played_1, spw_2, sp_played_2 = calculate_spw(oncourt_df)

    return spw_1 / sp_played_1, spw_2 / sp_played_2
