import urllib
import unicodedata
from bs4 import BeautifulSoup


def expected_format(x):

    if len(x) < 3:
        return False

    split_name = x.split(' ')

    if len(split_name) < 2:
        return False

    split_first = split_name[0].split('-')[0]

    if (len(split_first) > 1 and split_first != 'JM' and split_first != 'Kr'
            and split_first != 'PM' and split_first != 'Ka'):
        return False

    for cur_substring in split_name:

        if not cur_substring[0].isupper() and cur_substring != 'del':
            return False

    return True


def scrape_url(url):

    r = urllib.urlopen(url).read()
    soup = BeautifulSoup(r, 'lxml')

    all_tr = soup.find_all('tr')

    draw = list()

    for cur_tr in all_tr:

        dividers = cur_tr.find_all('td')

        if len(dividers) < 3:
            continue

        first_player = dividers[2].getText().strip()

        if expected_format(first_player):
            draw.append(first_player)

    all_expected = [unicodedata.normalize('NFD', x).encode('ascii', 'ignore')
                    for x in draw]

    return all_expected


if __name__ == '__main__':

    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('url')
    args = parser.parse_args()

    draw = scrape_url(args.url)

    print(draw)
    print(len(draw))
