from tdata.match_charting.exceptions import CodeParsingException
from tdata.match_charting.enums import ReturnDepthEnum, ShotDirectionEnum, \
    ShotTypeEnum

possible_depth_vals = [str(x.value) for x in ReturnDepthEnum]
possible_directions = [str(x.value) for x in ShotDirectionEnum]


class Shot(object):

    def __init__(self, player_name, shot_type, direction=None, is_winner=False,
                 is_forced_error=False, is_unforced_error=False,
                 is_approach=False, is_unexpected_position=False,
                 clipped_net=False, has_coding_error=False):

        self.player_name = player_name
        self.shot_type = shot_type
        self.direction = direction
        self.is_winner = is_winner
        self.is_forced_error = is_forced_error
        self.is_unforced_error = is_unforced_error
        self.is_approach = is_approach
        self.is_unexpected_position = is_unexpected_position
        self.clipped_net = clipped_net

    def __str__(self):

        output = '{} hit by {}.'.format(self.shot_type.name, self.player_name)

        if self.is_approach:

            output += ' It is an approach shot.'

        if self.direction is not None:

            output += ' It is hit in direction {}.'.format(self.direction.name)

        if self.clipped_net:

            output += ' It clipped the net.'

        if self.is_unexpected_position:

            output += ' It was hit in an unusual position.'

        if self.is_winner:

            output += ' It was a winner.'

        if self.is_forced_error:

            output += ' It was a forced error.'

        if self.is_unforced_error:

            output += ' It was an unforced error.'

        return output


class ServeReturn(Shot):

    def __init__(self, player_name, shot_type, depth=None, direction=None,
                 is_winner=False, is_forced_error=False,
                 is_unforced_error=False, is_approach=False,
                 is_unexpected_position=False, clipped_net=False):

        self.depth = depth

        super(ServeReturn, self).__init__(player_name, shot_type, direction,
                                          is_winner, is_forced_error,
                                          is_unforced_error, is_approach,
                                          is_unexpected_position, clipped_net)


def get_shot(player_name, shot_code, is_return):

    shot_type = ShotTypeEnum(shot_code[0])

    is_unforced_error = '@' in shot_code
    is_forced_error = '#' in shot_code
    is_winner = '*' in shot_code
    clipped_net = ';' in shot_code
    is_unexpected = '-' in shot_code or '=' in shot_code
    is_approach_shot = '+' in shot_code

    direction_hits = [x for x in shot_code if x in possible_directions]

    if len(direction_hits) > 1:

        raise CodeParsingException('More than one shot direction specified')

    if len(direction_hits) == 1:

        direction = ShotDirectionEnum(int(direction_hits[0]))

    else:

        direction = None

    if is_return:

        # Add depth
        depth_hits = [x for x in shot_code if x in possible_depth_vals]

        if len(depth_hits) > 1:

            raise CodeParsingException('More than one return depth specified')

        if len(depth_hits) == 1:

            depth = ReturnDepthEnum(int(depth_hits[0]))

        else:

            depth = None

        return ServeReturn(player_name, shot_type, depth=depth,
                           direction=direction, is_winner=is_winner,
                           is_forced_error=is_forced_error,
                           is_unforced_error=is_unforced_error,
                           is_approach=is_approach_shot,
                           is_unexpected_position=is_unexpected,
                           clipped_net=clipped_net)

    else:

        return Shot(player_name, shot_type, direction=direction,
                    is_winner=is_winner, is_forced_error=is_forced_error,
                    is_unforced_error=is_unforced_error,
                    is_approach=is_approach_shot,
                    is_unexpected_position=is_unexpected,
                    clipped_net=clipped_net)
