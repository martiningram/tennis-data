from tdata.match_charting.shot import get_shot
from tdata.match_charting.enums import ShotTypeEnum
from tdata.match_charting.exceptions import CodeParsingException


class Rally(object):

    def __init__(self, shots):

        self.shots = shots
        self.length = len(self.shots)

        assert(self.length > 0)

        self.final_shot = self.shots[-1]

    @classmethod
    def from_code(cls, code, server, returner):

        possible_shots = [x.value for x in ShotTypeEnum]

        # Find shots:
        shot_indices = [i for i, char in enumerate(code) if char in
                        possible_shots]

        # Add last shot:
        shot_indices.append(len(code))

        shots = list()

        # Deal with the rally shot
        for i, (first, second) in enumerate(zip(shot_indices,
                                                shot_indices[1:])):

            cur_code = code[first:second]

            is_return = i == 0

            hit_by = returner if i % 2 == 0 else server

            cur_shot = get_shot(hit_by, cur_code, is_return)

            shots.append(cur_shot)

        if len(shots) == 0:

            raise CodeParsingException(
                'Unable to parse shots from rally code {}'.format(code))

        final_shot = shots[-1]

        if not any([final_shot.is_winner, final_shot.is_forced_error,
                    final_shot.is_unforced_error]):

            raise CodeParsingException(
                'Final shot was not either error or winner. Code: {}'.format(
                    code))

        return Rally(shots)
