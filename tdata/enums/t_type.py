from enum import Enum


Tours = Enum('Tours', 'atp wta atp_doubles wta_doubles mixed_doubles')


def is_singles(t_type):

    return t_type in [Tours.atp, Tours.wta]


def is_standard_doubles(t_type):

    return t_type in [Tours.atp_doubles, Tours.wta_doubles]


def is_mixed_doubles(t_type):

    return t_type == Tours.mixed_doubles
