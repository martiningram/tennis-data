import os
import json
import numpy as np
import matplotlib.pyplot as plt


def plot_annotated_scatter(labels, xs, ys, plot_line=False):

    plt.subplots_adjust(bottom=0.1)

    plt.scatter(xs, ys, marker='o')

    for label, x, y in zip(labels, xs, ys):
        plt.annotate(
            label,
            xy=(x, y), xytext=(-10, 10),
            textcoords='offset points', ha='right', va='bottom',
            bbox = dict(boxstyle='round,pad=0.3', fc='yellow',
                        alpha=0.5),
            arrowprops = dict(arrowstyle='->', connectionstyle='arc3,rad=0'),
            fontsize = 8)

    if (plot_line):
        coeff = np.polyfit(xs, ys, 1)
        plt.plot(xs, np.polyval(coeff, xs))

    return plt


def load_cached_json(cache_path):

    if os.path.isfile(cache_path):
        with open(cache_path) as f:
            return json.load(f)
    else:
        raise IOError('File not found.')


def is_cached(cache_path):

    return os.path.isfile(cache_path)


def save_to_cache(dictionary, cache_path):

    with open(cache_path, 'w') as f:
        json.dump(dictionary, f)


def base_name_from_path(full_path):

    with_ext = os.path.split(full_path)[-1]

    return os.path.splitext(with_ext)[0]


def flatten_nested_dict(nested_dict, accumulator, connector='_'):

    dict_keys = [x for x, y in nested_dict.items() if type(y) == dict]
    non_dict = list(set(nested_dict.keys()) - set(dict_keys))

    if len(non_dict) == len(nested_dict):
        return {accumulator + x: y for x, y in nested_dict.items()}

    # Otherwise:
    already_ok = {accumulator + x: y
                  for x, y in nested_dict.items() if x in non_dict}

    not_ok_keys = set(dict_keys) - set(non_dict)

    for cur_key in not_ok_keys:

        already_ok.update(flatten_nested_dict(
            nested_dict[cur_key],
            accumulator + cur_key + connector,
            connector=connector))

    return already_ok
