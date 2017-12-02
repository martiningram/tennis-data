import os
import json

from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from tdata.scrapers.flashscore.utils import wait_for_element_and_parse
from tdata.scrapers.flashscore.flash_score_match_info import (
    FlashScoreMatchInfo)


class FlashScoreScraper(object):

    def __init__(self, driver, max_delay=20):

        self.flash_score_site = 'https://www.flashscore.com.au'
        self.driver = driver
        self.max_delay = max_delay
        self.driver.set_page_load_timeout(self.max_delay)

    @staticmethod
    def add_tournament_year(link, year):

        link = link[:-1]
        link = link + '-{}/'.format(year)
        return link

    def get_tournament_links(self, t_type, year):

        # Load the website
        self.driver.get(self.flash_score_site + '/tennis')

        tour_name = FlashScoreScraper.get_tour_name(t_type)

        wait_for_element_and_parse(self.driver, tour_name, self.max_delay)
        self.driver.find_element_by_partial_link_text(tour_name).click()
        page = wait_for_element_and_parse(self.driver, tour_name,
                                          self.max_delay)

        # Now we can extract the links
        links = FlashScoreScraper.find_tournament_links(page, t_type)

        # To get the correct year, format the link
        with_year = {x: FlashScoreScraper.add_tournament_year(y, year)
                     for x, y in links.items()}

        return with_year

    def get_tournament_match_ids(self, tournament_link):

        full_link = ('https://www.flashscore.com.au' + tournament_link +
                     'results')

        # Navigate to this page
        self.driver.get(full_link)

        cur_source = wait_for_element_and_parse(
            self.driver, 'fs-results', by=By.ID)

        match_ids = self.find_match_ids(cur_source)

        return match_ids

    @staticmethod
    def get_tour_name(t_type):

        if t_type == 'atp':
            tour_name = 'ATP - Singles'
        else:
            tour_name = 'WTA - Singles'

        return tour_name

    @staticmethod
    def find_tournament_links(tennis_page, t_type):

        all_vals = [x for x in tennis_page.find_all('a', href=True) if
                    '/tennis/{}-singles/'.format(t_type) in x['href']]

        exclude = FlashScoreScraper.get_tour_name(t_type)

        results = {x['href']: x.text for x in all_vals if x.text != exclude}

        results = {y: x for x, y in results.items()}

        return results

    @staticmethod
    def strip_id_lead(cur_id):

        return cur_id.split('_')[-1]

    @staticmethod
    def find_match_ids(results_page):

        all_odd = results_page.find_all('tr', class_='odd')
        all_even = results_page.find_all('tr', class_='even')

        all_odd_ids = [FlashScoreScraper.strip_id_lead(x['id']) for x in
                       all_odd]
        all_even_ids = [FlashScoreScraper.strip_id_lead(x['id']) for x in
                        all_even]

        return all_odd_ids + all_even_ids

    def scrape_match(self, match_id):

        match_website = self.flash_score_site + '/match/' + match_id

        return FlashScoreMatchInfo(match_website, self.driver,
                                   max_delay=self.max_delay)

    def scrape_year(self, year, output_dir, t_type, skip_existing=True):

        if not os.path.isdir(output_dir):
            os.makedirs(output_dir)

        failed_match_file = open(
            os.path.join(output_dir, 'failed_{}.txt'.format(year)), 'w')

        print('Fetching tournament links...')
        tournament_links = self.get_tournament_links(t_type, year)
        print('Fetched tournament links.')

        for cur_tournament_name, cur_tournament_link in (
                tournament_links.items()):

            if "Davis Cup" in cur_tournament_name:
                print('Skipping {} as not interesting.'.format(
                    cur_tournament_name))
                continue

            print('Scraping {} in {}...'.format(cur_tournament_name, year))

            # Get the match ids
            try:
                match_ids = self.get_tournament_match_ids(cur_tournament_link)
            except TimeoutException:
                print("Fetching tournament match ids for {} timed"
                      " out. Skipping.".format(cur_tournament_link))
                continue

            for cur_match_id in match_ids:

                print('Scraping match with id {}...'.format(cur_match_id))

                target_file = os.path.join(
                    output_dir, '{}.json'.format(cur_match_id))

                if (os.path.isfile(target_file) and skip_existing):
                    # We've scraped this already -- continue
                    print('Already scraped {}. Skipping'.format(cur_match_id))
                    continue

                try:
                    scraped = self.scrape_match(cur_match_id)
                except TimeoutException:
                    print('Failed to scrape match with ID {}.'
                          ' Skipping.'.format(cur_match_id))
                    failed_match_file.write(cur_match_id + '\n')
                    failed_match_file.flush()
                    continue
                except AttributeError:
                    print('Something went wrong when parsing match'
                          ' with ID {}. Skipping.'.format(cur_match_id))
                    failed_match_file.write(cur_match_id + '\n')
                    failed_match_file.flush()
                    continue
                except Exception:
                    print('Unforeseen exception caught in match'
                          ' with ID {}. Skipping.'.format(cur_match_id))
                    failed_match_file.write(cur_match_id + '\n')
                    failed_match_file.flush()
                    continue

                as_dict = scraped.to_dict()

                # Write to disk
                json.dump(as_dict, open(target_file, 'w'))

        failed_match_file.close()
