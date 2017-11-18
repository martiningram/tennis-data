import logging
import datetime
import pandas as pd

from tdata.match_charting.match_charting_parser import MatchChartingParser

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Make sure we write to log
fh = logging.FileHandler('chart_parse.log')
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)


def get_final_scores():

    parser = MatchChartingParser()

    sequence_df = parser.get_all_sequences()

    suggested_final_scores = list()

    for i, row in sequence_df.iterrows():

        win_sequence = row['win_sequence']
        first_server = row['Player 1']
        first_receiver = row['Player 2']
        bo5 = row['Best of'] == 5

        points = parser.points_from_sequence(
            first_server, first_receiver, win_sequence, bo5)

        final_score = str(points[-1].score)

        print(final_score)

        suggested_final_scores.append(final_score)

    sequence_df['final_score_suggested'] = suggested_final_scores

    sequence_df.to_csv('sequences_with_scores.csv')


def get_sequences(t_type='atp'):

    parser = MatchChartingParser()
    sequence_df = parser.get_all_sequences(t_type)
    sequence_df.to_csv('{}_sequences.csv'.format(t_type))


def test_match():

    parser = MatchChartingParser()

    match_df = parser.get_match_df('wta')

    logger.info('Started with {} matches'.format(match_df.shape[0]))

    match_df = match_df[match_df['Date'] > datetime.date(1990, 1, 1)]

    logger.info('Left with {} matches more recent than 1990'.format(
        match_df.shape[0]))

    results = list()

    for i, (_, row) in enumerate(match_df.iterrows()):

        if i % 5 == 0:
            print('On match {} of {}'.format(i, match_df.shape[0]))

        cur_id = row['match_id']

        logger.info('Parsing {}'.format(cur_id))

        points = parser.parse_match(cur_id, t_type='wta')

        erroneously_coded = [i for i, x in enumerate(points) if x.shot_sequence
                             is None]

        missed = [i for i, x in enumerate(points) if x.shot_sequence is not
                  None and x.shot_sequence.not_coded]

        logger.info(
            'Parsed {} points. {} raised errors; {} were not coded'.format(
                len(points), len(erroneously_coded), len(missed)))

        cur_data = row.to_dict()

        cur_data.update({'points_erroneously_coded': len(erroneously_coded),
                         'points_missed': len(missed), 'total_points':
                         len(points)})

        results.append(cur_data)

    results = pd.DataFrame(results)

    all_errors = pd.Series(parser.error_messages).value_counts()

    all_errors.to_csv('error_frequencies_wta.csv')

    results.to_csv('parsing_results_wta.csv')


def show_match_parsing(match_id):

    parser = MatchChartingParser()

    points = parser.parse_match(match_id, 'wta')

    exit()

    for point in points:

        if point.shot_sequence is not None:

            print(point.score)
            point.shot_sequence.print_sequence()
            print('')


if __name__ == '__main__':

    # test_match()

    show_match_parsing(
        '20110614-W-Eastbourne-R32-Ana_Ivanovic-Julia_Goerges')
