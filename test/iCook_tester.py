import sys
import unittest
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains


try:
    TEST_ADDRESS = str(sys.argv[1])
except IndexError:
    print("No Test Address given. Defaulting to localhost")
    TEST_ADDRESS = 'http://localhost:8050'

class TestTemplate(unittest.TestCase):
    """Include test cases on a given url"""
    def setUp(self):
        """Start web driver"""
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--headless')
        options.add_argument("--window-size=1920x1080")
        options.add_argument('--disable-gpu')
        self.driver = webdriver.Chrome(options=options)
        self.driver.implicitly_wait(30)

    def tearDown(self):
        """Stop web driver"""
        self.driver.quit()

    def test_case_1(self):
        """Enter 'egg', click 'search', select 'egg' from dropdown, ensure the recipe subsection appears"""
        self.driver.get(TEST_ADDRESS)
        dropdown = WebDriverWait(self.driver, 60).until(
            EC.presence_of_element_located((By.ID, "ingredients-dropdown")))
        dropdown.click()
        dropdown = self.driver.find_element_by_xpath("//input[@id='ingredients-dropdown']")
        dropdown.send_keys('egg')
        el = self.driver.find_element_by_xpath("//div[@class='VirtualizedSelectOption VirtualizedSelectFocusedOption']")
        el.click()
        # Find the search recipe button and click
        el = self.driver.find_element_by_xpath("//button[@id='search-recipe']")
        el.click()
        # Find the div for the recipe section
        el = self.driver.find_element_by_xpath("//div[@id='recipe_sub']")

if __name__ == '__main__':
    suite = unittest.TestSuite()

    # Load entire template of cases
    suite = unittest.TestLoader().loadTestsFromTestCase(TestTemplate)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(not result.wasSuccessful())
