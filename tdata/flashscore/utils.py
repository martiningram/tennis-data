from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup


def wait_for_element_and_parse(driver, element_to_wait_for, max_delay=10,
                               by=By.PARTIAL_LINK_TEXT):

    # Make sure we have loaded properly
    WebDriverWait(
        driver, max_delay).until(
            EC.presence_of_element_located(
                (by, element_to_wait_for)))

    cur_source = BeautifulSoup(driver.page_source, "lxml")

    return cur_source
