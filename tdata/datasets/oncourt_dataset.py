import os
import pandas as pd
from pathlib import Path

from tdata.datasets.match_stats import MatchStats
from tdata.datasets.dataset import Dataset
from tdata.enums.t_type import Tours
from tdata.enums.surface import Surfaces


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
        stats_table = read_with_suffix('stat')
        court_table = pd.read_csv(os.path.join(csv_dir, 'courts.csv'))

        merged = self.merge_tables(player_table, tour_table, games_table,
                                   stats_table, court_table)
        merged['DATE_G'] = pd.to_datetime(merged['DATE_G'])
        merged = merged.rename(columns={'DATE_G': 'start_date',
                                        'RESULT_G': 'score'})
        merged['round_number'] = merged['round']

        # TODO: Replace the round numbers with the enum values
        self.df = merged.sort_values('start_date')

        old_size = self.df.shape[0]

        # We don't want exhibitions
        self.df = self.df[~self.df['tournament_name'].str.contains(
            'Hopman|Mubadala')]

        self.df['year'] = self.df['start_date'].dt.year

        # Drop duplicates
        self.df = self.df.drop_duplicates(
            subset=['winner', 'loser', 'round', 'tournament_name', 'year'])

        new_size = self.df.shape[0]

        if old_size - new_size > 10:
            print(f'Warning: dropping duplicates reduced size from {old_size}'
                  f' to {new_size}.')

        super(OnCourtDataset, self).__init__(start_date_is_exact=True)

        self.df = self.df.set_index(self.df_index, drop=False)

    def calculate_stats(self, winner, loser, row):

        # TODO: Add the odds!
        player_stats = dict()

        for suffix, name in zip([1, 2], [winner, loser]):

            opp_suffix = 1 if suffix == 2 else 2

            opp_rpwof = row['RPWOF_{}'.format(opp_suffix)]
            opp_rpw = row['RPW_{}'.format(opp_suffix)]

            player_spw = opp_rpwof - opp_rpw
            player_sp_played = opp_rpwof

            player_rpof = row['RPWOF_{}'.format(suffix)]
            player_rpw = row['RPW_{}'.format(suffix)]

            ue = row['UE_{}'.format(suffix)]
            ws = row['WIS_{}'.format(suffix)]

            player_stats[name] = MatchStats(
                player_name=name,
                serve_points_played=player_sp_played,
                serve_points_won=player_spw,
                return_points_played=player_rpof,
                return_points_won=player_rpw,
                ues=ue, winners=ws)

        return player_stats

    def get_stats_df(self):

        return self.df

    def merge_tables(self, player_table, tour_table, games_table, stats_table,
                     court_table):

        court_mapping = {1: Surfaces.hard,
                         2: Surfaces.clay,
                         3: Surfaces.indoor_hard,
                         4: Surfaces.carpet,
                         5: Surfaces.grass,
                         6: Surfaces.acrylic}

        player_lookup = {row.ID_P: row.NAME_P for row in
                         player_table.itertuples()}
        tournament_lookup = {row.ID_T: row.NAME_T for row in
                             tour_table.itertuples()}
        t_rank_lookup = {row.ID_T: row.RANK_T for row in
                         tour_table.itertuples()}
        t_court_lookup = {row.ID_T: court_mapping[row.ID_C_T] for row in
                          tour_table.itertuples()}

        with_date = games_table.dropna()

        with_date.loc[:, 'tournament_rank'] = [
            t_rank_lookup[row.ID_T_G] for row in with_date.itertuples()]

        with_date.loc[:, 'surface'] = [
            t_court_lookup[row.ID_T_G].name for row in with_date.itertuples()]

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

        # Try to merge into the stats table
        with_date = with_date.rename(columns={
            'ID1_G': 'ID1',
            'ID2_G': 'ID2',
            'ID_T_G': 'ID_T',
            'ID_R_G': 'ID_R'
        })

        previous_rows = stats_table.shape[0]

        # Drop duplicates on the stats table
        stats_table = stats_table.drop_duplicates(
            subset=['ID1', 'ID2', 'ID_T', 'ID_R'])

        rows_after_dropping_duplicates = stats_table.shape[0]

        if previous_rows - rows_after_dropping_duplicates > 10:
            print(f'Warning: {previous_rows - rows_after_dropping_duplicates}'
                  f' have been dropped.')

        with_date = with_date.merge(stats_table, validate='one_to_one',
                                    on=['ID1', 'ID2', 'ID_T', 'ID_R'],
                                    how='left')

        keep_qualifying = not self.drop_qualifying

        rounds_to_keep = [4, 5, 6, 7, 9, 10, 12]

        # TODO: There's also stuff like pre-qualifying and bronze and so on.
        # Maybe think about what to do about these; dropping for now.
        if keep_qualifying:

            rounds_to_keep += [1, 2, 3]

        with_date = with_date.rename(columns={'ID_R': 'round'})
        with_date = with_date[with_date['round'].isin(rounds_to_keep)]

        # Discard juniors & wildcard events
        with_date = with_date[~with_date['tournament_name'].str.contains(
            'junior|Junior|wildcard|Wildcard')]

        return with_date
