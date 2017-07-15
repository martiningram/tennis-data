"""This script should only have to be run once: it adds surface information
to the MatchStat csvs."""

import os
import glob
import numpy as np
import pandas as pd
import cPickle as pkl
from tqdm import tqdm
from tdata.matchstat.scrape_matchstat import MatchStatScraper


# Get scraper

scraper = MatchStatScraper()

# Find year csvs:

# Only run recent years -- change if required
csvs = glob.glob('data/year_csvs/2016*.csv')

save_name = 'data/cache/surfaces.pkl'

if os.path.isfile(save_name):

    surface_series = pkl.load(open(save_name, 'rb'))

else:

    surface_series = dict()

for csv in tqdm(csvs):

    cur_df = pd.read_csv(csv, index_col=0)

    if 'surface' in cur_df.columns and np.sum(cur_df['surface'].isnull()) == 0:
        print('Skipping {}'.format(csv))
        continue

    # Otherwise, need to add it
    by_tourney = cur_df.set_index('tournament_link', drop=False)

    unique_tourneys = by_tourney.index.unique()

    cur_year = pd.to_datetime(cur_df['start_date']).dt.year.iloc[0]

    for t in unique_tourneys:

        if t in surface_series:

            surface = surface_series[t]

        else:

            print('Processing {}'.format(t))

            cur_matches = by_tourney.loc[t]

            if len(cur_matches.shape) < 2:
                continue

            sample_match = cur_matches.iloc[0]

            if 'winner' not in sample_match:
                continue

            surface = scraper.find_surface(
                sample_match.winner, sample_match.loser, t)

            surface_series[t] = str(surface)

            print(t, surface_series[t])

            with open(save_name, 'wb') as f:
                pkl.dump(surface_series, f)

        by_tourney.loc[t, 'surface'] = surface

    # Replace index with old index
    by_tourney = by_tourney.set_index(cur_df.index)

    # Replace when done
    by_tourney.to_csv(csv)
