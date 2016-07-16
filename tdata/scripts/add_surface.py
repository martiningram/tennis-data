"""This script should only have to be run once: it adds surface information
to the MatchStat csvs."""

import glob
import pandas as pd
from tdata.matchstat.scrape_matchstat import MatchStatScraper


# Get scraper

scraper = MatchStatScraper()

# Find year csvs:

csvs = glob.glob('data/year_csvs/*.csv')

for csv in csvs:

    cur_df = pd.read_csv(csv, index_col=0)

    if 'surface' in cur_df.columns:
        print('Skipping {}'.format(csv))
        continue

    # Otherwise, need to add it
    by_tourney = cur_df.set_index('tournament_link', drop=False)

    unique_tourneys = by_tourney.index.unique()

    for t in unique_tourneys:

        print('Processing {}'.format(t))

        cur_matches = by_tourney.loc[t]
        sample_match = cur_matches.iloc[0]

        surface = scraper.find_surface(
            sample_match.winner, sample_match.loser, t)

        by_tourney.loc[t, 'surface'] = surface

    # Replace index with old index
    by_tourney = by_tourney.set_index(cur_df.index)

    # Replace when done
    by_tourney.to_csv(csv)
