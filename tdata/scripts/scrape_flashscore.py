import argparse
from selenium import webdriver
from tdata.scrapers.flashscore.flash_score_scraper import FlashScoreScraper


parser = argparse.ArgumentParser()
parser.add_argument('--year', required=True, type=int)
parser.add_argument('--output-dir', required=True)
parser.add_argument('--t-type', required=True)
parser.add_argument('--no-cache', required=False, action='store_true')
args = parser.parse_args()

print('Starting web driver...')
driver = webdriver.PhantomJS()
driver.set_window_size(1120, 550)
print('Started web driver.')

scraper = FlashScoreScraper(driver)

scraper.scrape_year(args.year, args.output_dir, args.t_type, skip_existing=not
                    args.no_cache)
