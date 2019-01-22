import os
import pandas as pd
from pathlib import Path

from tdata.datasets.dataset import Dataset
from tdata.enums.t_type import Tours


class OnCourtDataset(Dataset):

    # TODO: Maybe switch over to SQL.

    def __init__(self, t_type=Tours.atp, drop_challengers=True,
                 drop_qualifying=True):

        exec_dir = Path(os.path.abspath(__file__)).parents[2]

        self.t_type = t_type
        self.drop_challengers = drop_challengers
        self.drop_qualifying = drop_qualifying

        csv_dir = os.path.join(str(exec_dir), 'data', 'oncourt')

        def read_with_suffix(table_name, suffix=t_type.name):
            return pd.read_csv(os.path.join(
                csv_dir, '{}_{}.csv'.format(table_name, suffix)))

        player_table = read_with_suffix('players')
        tour_table = read_with_suffix('tours')
        games_table = read_with_suffix('games')

        merged = self.merge_tables(player_table, tour_table, games_table)
        merged['DATE_T'] = pd.to_datetime(merged['DATE_T'])
        merged = merged.rename(columns={'DATE_T': 'start_date'})

        # TODO: Replace the round numbers with the enum values
        self.df = merged

        super(OnCourtDataset, self).__init__(start_date_is_exact=True)

        self.df = self.df.set_index(self.df_index, drop=False)

    def calculate_stats(self, winner, loser, row):

        raise NotImplementedError('This is not yet implemented!')

    def get_stats_df(self):

        return self.df

    def merge_tables(self, player_table, tour_table, games_table):

        player_lookup = {row.ID_P: row.NAME_P for row in
                         player_table.itertuples()}
        tournament_lookup = {row.ID_T: row.NAME_T for row in
                             tour_table.itertuples()}
        t_rank_lookup = {row.ID_T: row.RANK_T for row in
                         tour_table.itertuples()}

        with_date = games_table.dropna()

        with_date = with_date.rename({'ID_R_G': 'round'})

        with_date.loc[:, 'tournament_rank'] = [
            t_rank_lookup[row.ID_T_G] for row in with_date.itertuples()]

        if self.drop_challengers:

            with_date = with_date[with_date['tournament_rank'] > 1]

        with_date.loc[:, 'winner'] = [
            player_lookup[row.ID1_G] for row in with_date.itertuples()]
        with_date.loc[:, 'loser'] = [
            player_lookup[row.ID2_G] for row in with_date.itertuples()]
        with_date.loc[:, 'tournament_name'] = [
            tournament_lookup[row.ID_T_G] for row in with_date.itertuples()]

        # No doubles
        with_date = with_date[~with_date['winner'].str.contains('/')]

        keep_qualifying = not self.drop_qualifying

        rounds_to_keep = [4, 5, 6, 7, 9, 10, 12]

        # TODO: There's also stuff like pre-qualifying and bronze and so on.
        # Maybe think about what to do about these; dropping for now.
        if keep_qualifying:

            rounds_to_keep += [1, 2, 3]

        with_date = with_date[with_date['round'].isin(rounds_to_keep)]

        return with_date
