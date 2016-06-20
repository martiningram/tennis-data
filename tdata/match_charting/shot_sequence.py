from tdata.match_charting.serve import Serve
from tdata.match_charting.rally import Rally
from tdata.match_charting.exceptions import CodeParsingException


class ShotSequence(object):

    def __init__(self, server, returner, server_won, first_serve=None,
                 second_serve=None, rally=None, not_coded=False,
                 server_lost_outright=False, server_won_outright=False):

        self.server = server
        self.returner = returner
        self.server_won = server_won

        # Either it was not coded, lost outright, won outright, or we must have
        # at least one recorded serve.
        assert(not_coded or server_lost_outright or server_won_outright or
               first_serve is not None)

        self.rally = rally
        self.not_coded = not_coded
        self.first_serve = first_serve
        self.second_serve = second_serve
        self.server_lost_outright = server_lost_outright
        self.server_won_outright = server_won_outright

    @classmethod
    def from_code(cls, server, returner, server_won, first_code,
                  second_code):

        if len(first_code) == 1:

            if first_code in ['S', 'R']:

                return ShotSequence(server, returner, server_won,
                                    not_coded=True)

            elif first_code == 'P':

                return ShotSequence(server, returner, server_won,
                                    server_lost_outright=True)

            elif first_code == 'Q':

                return ShotSequence(server, returner, server_won,
                                    server_won_outright=True)

            else:

                raise CodeParsingException('Unknown single-character code')

        # Parse first serve
        first_serve, remaining_code = Serve.from_code(
            first_code, server, is_first=True)

        rally = None

        if first_serve.was_fault():

            second_serve, remaining_code = Serve.from_code(
                second_code, server, is_first=False)

            if second_serve.had_rally():
                rally = Rally.from_code(remaining_code, server, returner)

        else:

            second_serve = None

            if first_serve.had_rally():
                rally = Rally.from_code(remaining_code, server, returner)

        return ShotSequence(server, returner, server_won,
                            first_serve=first_serve, second_serve=second_serve,
                            rally=rally)
