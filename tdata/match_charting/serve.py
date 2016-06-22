from tdata.match_charting.exceptions import CodeParsingException
from tdata.match_charting.enums import FaultEnum, ServeDirectionEnum


class Serve(object):

    def __init__(self, server, direction, is_first, fault_type=None, s_v=False,
                 is_ace=False, is_unreturnable=False):

        self.server = server
        self.direction = direction
        self.fault_type = fault_type
        self.s_v = s_v
        self.is_ace = is_ace
        self.is_unreturnable = is_unreturnable
        self.is_first = is_first

    def __str__(self):

        serve_name = 'first' if self.is_first else 'second'

        output = "{} hits {} serve, direction {}".format(
            self.server, serve_name, self.direction.name)

        if self.s_v:

            output += ' followed to the net'

        if self.fault_type is not None:

            output += ' was missed. Fault type: {}'.format(
                self.fault_type.name)

        if self.is_ace:

            output += ' was an ace.'

        if self.is_unreturnable:

            output += ' was unreturnable.'

        return output

    def was_fault(self):

        return self.fault_type is not None

    def had_rally(self):

        return not any([self.was_fault(), self.is_ace, self.is_unreturnable])

    @classmethod
    def from_code(cls, code, server, is_first):

        # Remove lets
        code = code.replace('c', '')

        if len(code) == 1:
            raise CodeParsingException('Code too short')

        try:

            direction = int(code[0])

        except ValueError:

            raise CodeParsingException('Non-integer serve direction.'
                                       ' Full code is: {}'.format(code))

        if direction not in [0, 4, 5, 6]:

            raise CodeParsingException(
                'Unknown serve direction {}'.format(code))

        is_s_v = code[1] == '+'

        # Replace that one
        code = code.replace('+', '', 1)

        is_fault = code[1] in ['n', 'w', 'd', 'x', 'g', 'e', '!']
        is_ace = code[1] == '*'
        is_unreturnable = code[1] == '#'

        if is_fault:

            if len(code) != 2:

                raise CodeParsingException(
                    'Unexpected characters after serve fault.'
                    ' Full code is: {}'.format(code))

            else:

                fault = FaultEnum(code[1])

        else:
            fault = None

        if is_ace or is_unreturnable or is_fault:

            rest_of_code = ''

        else:

            rest_of_code = code[1:]

        return Serve(server, ServeDirectionEnum(direction), is_first, fault,
                     is_s_v, is_ace, is_unreturnable), rest_of_code
