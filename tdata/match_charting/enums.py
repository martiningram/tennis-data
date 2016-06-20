from enum import Enum


class ServeDirectionEnum(Enum):

    out_wide = 4
    body = 5
    down_the_t = 6
    unknown = 0


class FaultEnum(Enum):

    net = 'n'
    wide = 'w'
    deep = 'd'
    wide_and_deep = 'x'
    foot_fault = 'g'
    unknown = 'e'


class ShotTypeEnum(Enum):

    forehand_groundstroke = 'f'
    backhand_groundstroke = 'b'

    forehand_slice = 'r'
    backhand_slice = 's'

    forehand_volley = 'v'
    backhand_volley = 'z'

    forehand_overhead = 'o'
    backhand_overhead = 'p'

    forehand_drop_shot = 'u'
    backhand_drop_shot = 'y'

    forehand_lob = 'l'
    backhand_lob = 'm'

    forehand_half_volley = 'h'
    backhand_half_volley = 'i'

    forehand_drive_volley = 'j'
    backhand_drive_volley = 'k'

    trick_shot = 't'
    unknown = 'q'


class ShotDirectionEnum(Enum):

    to_righthanders_forehand = 1
    to_middle = 2
    to_righthanders_backhand = 3
    unknown = 0


class ReturnDepthEnum(Enum):

    within_service_box = 7
    behind_but_close_to_service_line = 8
    close_to_baseline = 9


class CourtPositionEnum(Enum):

    approach_shot = '+'
    groundstroke_at_net = '-'
    net_shot_at_baseline = '='
