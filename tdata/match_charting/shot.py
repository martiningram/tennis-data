import logging

from tdata.match_charting.exceptions import CodeParsingException
from tdata.match_charting.enums import ReturnDepthEnum, ShotDirectionEnum, \
    ShotTypeEnum, FaultEnum

possible_depth_vals = [str(x.value) for x in ReturnDepthEnum]
possible_directions = [str(x.value) for x in ShotDirectionEnum]
possible_errors = [str(x.value) for x in FaultEnum]


class Shot(object):

    def __init__(self, player_name, shot_type, direction=None, error_type=None,
                 is_winner=False, is_forced_error=False,
                 is_unforced_error=False, is_approach=False,
                 is_unexpected_position=False, clipped_net=False,
                 has_coding_error=False):

        self.player_name = player_name
        self.shot_type = shot_type
        self.direction = direction
        self.is_winner = is_winner
        self.is_forced_error = is_forced_error
        self.is_unforced_error = is_unforced_error
        self.error_type = error_type
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

        if self.error_type is not None:

            output += ' The fault type was: {}'.format(self.error_type.name)

        return output


class ServeReturn(Shot):

    def __init__(self, player_name, shot_type, depth=None, error_type=None,
                 direction=None, is_winner=False, is_forced_error=False,
                 is_unforced_error=False, is_approach=False,
                 is_unexpected_position=False, clipped_net=False):

        self.depth = depth

        super(ServeReturn, self).__init__(
            player_name=player_name, shot_type=shot_type,
            error_type=error_type, direction=direction, is_winner=is_winner,
            is_forced_error=is_forced_error,
            is_unforced_error=is_unforced_error, is_approach=is_approach,
            is_unexpected_position=is_unexpected_position,
            clipped_net=clipped_net)

    def __str__(self):

        shot_info = super(ServeReturn, self).__str__()

        if self.depth is not None:

            shot_info += ' Return depth: {}'.format(self.depth.name)

        return shot_info


logger = logging.getLogger(__name__)
# Make sure we write to log
fh = logging.FileHandler('chart_parse.log')
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)


def get_shot(player_name, shot_code, is_return):

    shot_type = ShotTypeEnum(shot_code[0])

    is_unforced_error = '@' in shot_code
    is_forced_error = '#' in shot_code
    is_winner = '*' in shot_code
    clipped_net = ';' in shot_code
    is_unexpected = '-' in shot_code or '=' in shot_code
    is_approach_shot = '+' in shot_code

    direction_hits = [x for x in shot_code if x in possible_directions]

    # By default, no fault, direction and depth
    error_type = None
    direction = None
    depth = None

    if len(direction_hits) > 1:

        text = 'More than one shot direction specified'

        logger.warning('Failed to parse: {}. Reason: {}'.format(
            shot_code, text))

        raise CodeParsingException(text)

    elif len(direction_hits) == 1:

        direction = ShotDirectionEnum(int(direction_hits[0]))

    if is_forced_error or is_unforced_error:

        fault_hits = [x for x in shot_code if x in possible_errors]

        if len(fault_hits) > 1:

            text = 'More than one shot fault type specified'

            logger.warning('Failed to parse: {}. Reason: {}'.format(
                shot_code, text))

            raise CodeParsingException(text)

        elif len(fault_hits) == 1:

            error_type = FaultEnum(fault_hits[0])

    if is_return:

        # Add depth
        depth_hits = [x for x in shot_code if x in possible_depth_vals]

        if len(depth_hits) > 1:

            text = 'More than one return depth specified'

            logger.warning('Failed to parse: {}. Reason: {}'.format(
                shot_code, text))

            raise CodeParsingException(text)

        elif len(depth_hits) == 1:

            depth = ReturnDepthEnum(int(depth_hits[0]))

        return ServeReturn(player_name, shot_type, depth=depth,
                           direction=direction, error_type=error_type,
                           is_winner=is_winner,
                           is_forced_error=is_forced_error,
                           is_unforced_error=is_unforced_error,
                           is_approach=is_approach_shot,
                           is_unexpected_position=is_unexpected,
                           clipped_net=clipped_net)

    else:

        return Shot(player_name, shot_type, direction=direction,
                    error_type=error_type, is_winner=is_winner,
                    is_forced_error=is_forced_error,
                    is_unforced_error=is_unforced_error,
                    is_approach=is_approach_shot,
                    is_unexpected_position=is_unexpected,
                    clipped_net=clipped_net)
