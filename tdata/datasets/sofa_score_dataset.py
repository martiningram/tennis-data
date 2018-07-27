import os
import pandas as pd
from glob import glob
from pathlib import Path

from tdata.datasets.dataset import Dataset
from tdata.enums.t_type import Tours
from tdata.utils.utils import base_name_from_path


class SofaScoreDataset(Dataset):

    def __init__(self, t_type=Tours.atp, min_year=None):

        exec_dir = Path(__file__).parents[2]

        self.t_type = t_type
        self.min_year = min_year

        csv_dir = os.path.join(str(exec_dir), 'data', 'sofa_csv', t_type.name)
        csvs = glob(os.path.join(csv_dir, '*.csv'))
        year_lookup = {int(base_name_from_path(x)): x for x in csvs}

        if min_year is not None:
            keys_to_keep = [x for x in year_lookup.keys() if x >= min_year]
        else:
            keys_to_keep = year_lookup.keys()

        loaded = [pd.read_csv(year_lookup[x]) for x in sorted(keys_to_keep)]
        combined = pd.concat(loaded, axis=0, ignore_index=True)
        combined['date'] = pd.to_datetime(combined['date'])

        # Rename date to start_date
        self.df = combined.rename(columns={'date': 'start_date'})

        super(SofaScoreDataset, self).__init__()

    def get_stats_df(self):

        return self.df


if __name__ == '__main__':

    dataset = SofaScoreDataset()
