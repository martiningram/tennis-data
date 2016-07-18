from datetime import date
from tdata.datasets.sackmann_dataset import SackmannDataset


class TestSackmannDataset(object):

    def test_round(self):

        dataset = SackmannDataset()

        # Check the australian open
        # Federer left in R32, which is round number 2. He played R128, R64 and
        # R32.
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

        matches = dataset.get_player_matches(
            'Roger Federer', min_date=date(2015, 1, 19),
            max_date=date(2015, 1, 19), before_round=1)

        assert(len(matches) == 1)

        matches = dataset.get_player_matches(
            'Roger Federer', min_date=date(2015, 1, 19),
            max_date=date(2015, 1, 19), before_round=0)

        assert(len(matches) == 0)
