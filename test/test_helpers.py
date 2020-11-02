"""
Test url path handling and generation
"""

import unittest
# Import module to be tested
import iCook
# Pandas is needed for checking data types
import pandas


class TestTemplate(unittest.TestCase):
    """Test the helper functions for iCook"""

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_case_1(self):
        """Test the cart function
        correctly return a dataframe, name, aisle and cost
        """
        ingredient_dict = [{'name': 'bread flour',
                            'id': 10120129,
                            'aisle': 'Baking',
                            'amount': 4.25,
                            'unit': 'cups',
                            'cost': 0.74},
                           {'name': 'carrots',
                            'id': 10120,
                            'aisle': 'Vegetable',
                            'amount': 4.25,
                            'unit': 'cups',
                            'cost': 0.24}]
        # returns type pandas.core.frame.DataFrame
        self.assertEqual(type(iCook.make_cart(ingredient_dict)),
                         pandas.core.frame.DataFrame)
        self.assertEqual(iCook.make_cart(
            ingredient_dict).at[0, 'name'], 'bread flour')
        self.assertEqual(iCook.make_cart(
            ingredient_dict).at[0, 'aisle'], "Baking")
        self.assertEqual(iCook.make_cart(ingredient_dict).at[0, 'cost'], 0.74)

        # Check that the total was added correctly
        self.assertEqual(iCook.make_cart(
            ingredient_dict).at['Total', 'cost'], 0.98)


if __name__ == '__main__':
    unittest.main()
