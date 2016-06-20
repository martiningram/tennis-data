from tdata.match_charting.shot import get_shot
from tdata.match_charting.enums import ShotTypeEnum


class Rally(object):

    def __init__(self, shots):

        self.shots = shots
        self.length = len(self.shots)

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

        return Rally(shots)
