from datetime import date
from tdata.datasets.sackmann_dataset import SackmannDataset
from tdata.datasets.match_stat_dataset import MatchStatDataset


class TestSackmannDataset(object):

    def test_round_ao(self):

        for dataset in [SackmannDataset(), MatchStatDataset()]:

            # Check the Australian Open
            # Federer left in R32, which is round number 2. He played R128, R64
            # and R32.
            # Hence this should give 3 matches.
            matches = dataset.get_player_matches(
                'Roger Federer', min_date=date(2015, 1, 19),
                max_date=date(2015, 1, 19), before_round=3)

            assert(len(matches) == 3)

            # This should give two:
            matches = dataset.get_player_matches(
                'Roger Federer', min_date=date(2015, 1, 19),
                max_date=date(2015, 1, 19), before_round=2)

            assert(len(matches) == 2)

            # Check 1 and 0 too:
            matches = dataset.get_player_matches(
                'Roger Federer', min_date=date(2015, 1, 19),
                max_date=date(2015, 1, 19), before_round=1)

            assert(len(matches) == 1)

            matches = dataset.get_player_matches(
                'Roger Federer', min_date=date(2015, 1, 19),
                max_date=date(2015, 1, 19), before_round=0)

            assert(len(matches) == 0)

    def test_round_preao(self):

        for dataset in [SackmannDataset(), MatchStatDataset()]:

            # Check the Australian Open
            # Federer left in R32, which is round number 2. He played R128, R64
            # and R32.
            # He played 4 matches in Brisbane.
            # Hence this should give 6 matches.
            matches = dataset.get_player_matches(
                'Roger Federer', min_date=date(2015, 1, 1),
                max_date=date(2015, 1, 19), before_round=2)

            assert(len(matches) == 6)
