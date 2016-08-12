from datetime import date
from tdata.datasets.sackmann_dataset import SackmannDataset
from tdata.datasets.match_stat_dataset import MatchStatDataset


class TestSackmannDataset(object):

    def test_round_ao(self):

        for dataset in [SackmannDataset(), MatchStatDataset()]:

            # Check the Australian Open
            for round_number in range(0, 3):

                matches = dataset.get_player_matches(
                    'Roger Federer', min_date=date(2015, 1, 19),
                    max_date=date(2015, 1, 19), before_round=round_number)

                matches = list(matches)

                assert(len(matches) == round_number)

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

            matches = list(matches)

            for match in matches:

                print(match)

            assert(len(matches) == 6)
