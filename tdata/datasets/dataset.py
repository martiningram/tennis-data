from abc import abstractmethod


class Dataset(object):

    @abstractmethod
    def get_player_matches(self, player_name, min_date=None, max_date=None,
                           surface=None):
        pass

    @abstractmethod
    def get_tournament_serve_average(self, tournament_name, min_date=None,
                                     max_date=None):
        pass

    @abstractmethod
    def get_stats_df(self):
        pass
