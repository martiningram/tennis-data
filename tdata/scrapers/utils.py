"""A collection of utility functions useful for scraping."""
import urllib
import json
import time
import logging
from functools import wraps

from bs4 import BeautifulSoup


def load_json_url(url):
    # Throws a ValueError if cannot decode.
    response = urllib.urlopen(url)
    data = json.loads(response.read())
    return data


def retry(ExceptionToCheck, tries=4, delay=3, backoff=2, logger=None):
    """Retry calling the decorated function using an exponential backoff.

    http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
    original from: http://wiki.python.org/moin/PythonDecoratorLibrary#Retry

    :param ExceptionToCheck: the exception to check. may be a tuple of
        exceptions to check
    :type ExceptionToCheck: Exception or tuple
    :param tries: number of times to try (not retry) before giving up
    :type tries: int
    :param delay: initial delay between retries in seconds
    :type delay: int
    :param backoff: backoff multiplier e.g. value of 2 will double the delay
        each retry
    :type backoff: int
    :param logger: logger to use. If None, print
    :type logger: logging.Logger instance
    """
    def deco_retry(f):

        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except ExceptionToCheck, e:
                    msg = "%s, Retrying in %d seconds..." % (str(e), mdelay)
                    if logger:
                        logger.warning(msg)
                    else:
                        print msg
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)

        return f_retry  # true decorator

    return deco_retry


def fetch_logger(log_name, output_file):
    # log_name is the result of calling __name__

    # Set up logging
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(log_name)

    # Make sure we write to log
    fh = logging.FileHandler(output_file)
    fh.setLevel(logging.DEBUG)
    logger.addHandler(fh)

    return logger


def prettify_json(json_dict):

    return json.dumps(json_dict, indent=4, sort_keys=True)


def load_html_page(url):
    # Uses BeautifulSoup to load the HTML for a page
    response = urllib.urlopen(url)
    soup = BeautifulSoup(response, 'html.parser')
    return soup
