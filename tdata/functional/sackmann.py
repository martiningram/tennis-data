import numpy as np
from glob import glob
from toolz import pipe, partial
import pandas as pd
from os.path import join, splitext


def get_data(sackmann_dir, tour='atp'):

    all_csvs = glob(join(sackmann_dir, f'*{tour}_matches_????.csv'))
    all_csvs = sorted(all_csvs, key=lambda x: int(splitext(x)[0][-4:]))

    data = pipe(all_csvs,
                lambda y: map(partial(pd.read_csv, encoding="ISO=8859-1"), y),
                lambda y: map(lambda x: x.dropna(
                    subset=['winner_name', 'loser_name', 'score']),
                    y),
                lambda y: map(lambda x:
                              x[~x['score'].astype(str).str.contains(
                                'RET|W/O|DEF|nbsp|Def.')],
                              y),
                lambda y: map(lambda x: x[
                    x['score'].astype(str).str.len() > 4],
                    y),
                lambda y: map(lambda x: x[
                    ~x['tourney_level'].isin(['C', 'S'])],
                    y),
                pd.concat,
                )

    round_numbers = {
        'R128': 1,
        'RR': 1,
        'R64': 2,
        'R32': 3,
        'R16': 4,
        'QF': 5,
        'SF': 6,
        'F': 7
    }

    to_keep = data['round'].isin(round_numbers)
    data = data[to_keep]

    data['round_number'] = data['round'].replace(round_numbers)

    data['tourney_date'] = pd.to_datetime(
        data['tourney_date'].astype(int).astype(str), format='%Y%m%d')

    data = data.sort_values(['tourney_date', 'round_number'])

    data = data.reset_index(drop=True)

    return data


def compute_game_margins(string_scores):

    def compute_margin(sample_set):

        if '[' in sample_set:
            return 0

        try:
            split_set = sample_set.split('-')
            margin = int(split_set[0]) - int(split_set[1].split('(')[0])
        except ValueError:
            margin = np.nan

        return margin

    margins = pipe(string_scores,
                   lambda y: map(lambda x: x.split(' '), y),
                   lambda y: map(lambda x: [compute_margin(z) for z in x], y),
                   lambda y: map(sum, y),
                   partial(np.fromiter, dtype=np.float))

    return margins
