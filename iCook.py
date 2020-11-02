#!/usr/bin/env python

# System level imports
from os import environ
from sys import exit

# We will log to terminal user interaction and responses
import logging

# requests library is used for HTTP GET requests
import requests
from requests.exceptions import HTTPError

# Pandas will be used for dataframe generation
# and handling cart data
import pandas as pd

# Dash framework will be used to handle user interaction
# and generating the html to be displayed to the user
import dash
import dash_table
from dash.exceptions import PreventUpdate
import dash_core_components as dcc
import dash_html_components as html

# Initialize the logger
logging.basicConfig(level=logging.INFO)

# Get the API key from the environment variable ICOOK_KEY
# If it is undefined set it as 'missing_key'
API_SECRET = environ.get("ICOOK_KEY", 'missing_key')

# If key is missing notify user and exit
if API_SECRET == 'missing_key':
    logging.error(
        f'Please supply a key as an environment variable ICOOK_KEY: {API_SECRET}')
    exit(1)

# These are the API Docs pertaining to this application
# -----------------
# Response for *finding ingredients*
# https://spoonacular.com/food-api/docs#Autocomplete-Recipe-Search
# Response for *finding recipies*
# https://spoonacular.com/food-api/docs#Search-Recipes-by-Ingredients
# Response for *recipe steps*
# https://spoonacular.com/food-api/docs#Get-Analyzed-Recipe-Instructions
# Response for *price of ingredients*
# https://spoonacular.com/food-api/docs#Get-Recipe-Price-Breakdown-by-ID

# Use stylesheets for dash components
external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

# Define the generated html layout
app.layout = html.Div(
    [
        html.Label(
            [
                "Enter Ingredients",
                dcc.Dropdown(id="ingredients-dropdown", multi=True),
            ]
        ),
        html.Button("Search", id="search-recipe", n_clicks_timestamp=1),
        html.Button("Clear", id="clear-ingredients", n_clicks_timestamp=1),

        # This div shall be hidden until ingredients have been selected
        html.Div(id='recipe_sub', style={'display': 'none'}, children=[
            html.Div(id='current-recipe-count', children=0,
                     style={'display': 'none'}),
            dcc.Store(id='cached-recipes', data=None),
            html.Div(id='recipe-title', children=None),
            html.Img(id='recipe-img'),
            html.Br(),
            html.H5("Ingredients you already have:"),
            html.Div(id='recipe-ingredients', children='ingredients'),
            dcc.Store(id='missing-ingredients'),
            html.Button("Save missing ingredients to cart",
                        id="save-missing", n_clicks_timestamp=1),
            html.Button("Skip", id="skip-recipe", n_clicks_timestamp=1),
        ]),

        # This div shall be hidden until save missing ingredients has been selected
        html.Div(id='shopping-sub', style={'display': 'none'}, children=[
            html.Div(id='shopping-list', children='shopping list'),
            html.Br(),
            html.Br(),
            html.Button("Empty Cart", id="empty-cart", n_clicks_timestamp=1)
        ]),
        dcc.Store(id='cart', storage_type='local')
    ], style={'width': '600px'}
)


"""
INPUT
    populate_ingredient_options will execute when user types in search box
    populate_ingredient_options reads the current value of the ingredients selected
        in order to keep prior selections visible when moving to new ingredients

OUTPUT (Return values)
    populate_ingredient_options will return a list of available options including
        current ingredients already selected
"""
@app.callback(
    dash.dependencies.Output("ingredients-dropdown", "options"),
    [dash.dependencies.Input("ingredients-dropdown", "search_value")],
    [dash.dependencies.State("ingredients-dropdown", "value")],
)
def populate_ingredient_options(search_value, value):
    """populate_ingredient_options
    --
    This callback will query the spoonacular server once user
    has entered characters
    Alternatively we could auto fill the options with
    ingredients from this long list that will become outdated
    https://spoonacular.com/food-api/docs#List-of-Ingredients
    """
    if not search_value:
        raise PreventUpdate
    logging.debug(f'Doing a ingredient query on \'{search_value}\'')
    logging.debug(f'Current value is \'{value}\'')

    # Here we will update ingredients with a real query result
    try:
        response = requests.get('https://api.spoonacular.com/food/ingredients/autocomplete?query=' +
                                search_value + '&number=8' +
                                "&apiKey=" + API_SECRET)
        # check that requests didn't receive api related errors:
        # 401 status code
        if response.status_code == 401:
            logging.error("API Key related error")
        response.raise_for_status()
        ingredients = response.json()
        logging.debug(f"Response is:  {ingredients}")
    except HTTPError as http_err:
        logging.error(f'HTTP error occurred: {http_err}')
    except Exception as err:
        logging.error(f'Other error occurred: {err}')
    options = [{'label': i['name'].title(), 'value':i['name']}
               for i in ingredients]

    # Here we need to extend the options to include our already selected items
    # Otherwise previous selections will dissappear
    if value:
        options.extend([{'label': k, 'value': k} for k in value])
    logging.debug(f"New options are {options}")

    # Make sure that the set values are in the option list, else they will disappear
    # from the shown select list, but still part of the `value`.
    return [
        o for o in options if search_value.title() in o["label"] or o["value"] in (value or [])
    ]


"""
INPUT:
    This callback will fire on:
        search recipe button
        skip recipe button
        clear ingredients

    This callback will read values of:
        selected ingredients dropdown
        recipe index counter
        data store of cached recipies

OUTPUT (return values):
    The callback will modify:
        anything on the page relating to recipies and recipe caching
"""
@app.callback(
    [dash.dependencies.Output("recipe_sub", "style"),
     dash.dependencies.Output("recipe-title", "children"),
     dash.dependencies.Output("recipe-img", 'src'),
     dash.dependencies.Output("recipe-ingredients", "children"),
     dash.dependencies.Output("missing-ingredients", "data"),
     dash.dependencies.Output("save-missing", "children"),
     dash.dependencies.Output("cached-recipes", "data"),
     dash.dependencies.Output("current-recipe-count", "children"),
     dash.dependencies.Output("ingredients-dropdown", "value")],
    [dash.dependencies.Input("search-recipe", "n_clicks_timestamp"),
     dash.dependencies.Input("skip-recipe", "n_clicks_timestamp"),
     dash.dependencies.Input("clear-ingredients", "n_clicks_timestamp")],
    [dash.dependencies.State("ingredients-dropdown", "value"),
     dash.dependencies.State("current-recipe-count", "children"),
     dash.dependencies.State("cached-recipes", "data")],
)
def generate_recipies(search_btn, skip_btn, clear_btn, ingredients_selected,
                      cur_recipe_idx, cached_recipes):
    """generate_recipies
    --
    Here the recipe is parsed, displayed on the screen
        other recipies are stored as a browser data element
    """
    # Stop dash from firing this callback until we are ready
    if not ingredients_selected:
        raise PreventUpdate

    recipe_buffer = 30

    # Check that search button was clicked not skip or clear
    if search_btn > clear_btn and search_btn > skip_btn:
        logging.info(f"search clicked, ingredients selected are: {','.join(ingredients_selected)}")

        # Here we should fire the search recipe with ingredients_selected query
        # to update the recipies variable
        # https://api.spoonacular.com/recipes/findByIngredients?ingredients=apples,+flour,+sugar&number=2
        try:
            response = requests.get('https://api.spoonacular.com/recipes/findByIngredients?ingredients=' + ','.join(
                ingredients_selected) + '&number=' + str(recipe_buffer) + "&apiKey=" + API_SECRET)
            # check that requests didn't receive api related errors:
            # 401 status code
            if response.status_code == 401:
                logging.error("API Key related error")
            response.raise_for_status()
            # store json response as recipe data
            recipies = response.json()
            logging.debug(f"Response is:  {recipies}")
        except HTTPError as http_err:
            logging.error(f'HTTP error occurred: {http_err}')
        except Exception as err:
            logging.error(f'Other error occurred: {err}')

    # When clearing we will hide the recipe div and blank recipe elements
    # rename the save ingredients button to clear the number value
    # return the current recipe index
    # empty the ingredients dropdown selection
    if clear_btn > search_btn and clear_btn > skip_btn:
        logging.info("clear clicked")
        return [{'display': 'none    '}, '', '', '', '', 'Save ingredients', '', cur_recipe_idx, '']
    if skip_btn > clear_btn and skip_btn > search_btn:
        logging.info("skip clicked")

        # Use the cached list and iterate to the next element
        recipies = cached_recipes

        # TODO: Return a "Last recipe message"
        # this is a quick fix that will wrap the user back
        # to the first recipe to prevent a index error on recipies
        if cur_recipe_idx < recipe_buffer-1:
            cur_recipe_idx = cur_recipe_idx + 1
        else:
            cur_recipe_idx = 0

    # recipe title
    recipe_title = html.H4(recipies[cur_recipe_idx]['title'])

    # recipe image
    cur_recipe_image = recipies[cur_recipe_idx]['image']

    # recipe ingredients we have
    used_ingredients_images = [html.Img(src=n['image'])
                               for n in
                               recipies[cur_recipe_idx]['usedIngredients']]

    # TODO: Make 'recipe steps' a first-class class
    # Quick fix: Append to our ingredients photo a header and list of steps
    current_id = recipies[cur_recipe_idx]['id']

    logging.info(f"Current recipe id: {current_id}")

    try:
        response = requests.get('https://api.spoonacular.com/recipes/' + str(
            current_id) + '/analyzedInstructions' +
            "?stepBreakdown=true&apiKey=" + API_SECRET)
        # check that requests didn't receive api related errors:
        # 401 status code
        if response.status_code == 401:
            logging.error("API Key related error")
        response.raise_for_status()
        # access JSOn content
        recipe_steps = response.json()
    except HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')
    except Exception as err:
        print(f'Other error occurred: {err}')

    if len(recipe_steps) > 0:
        recipe_steps = [html.H5("Steps:"), html.Ol([html.Li(
            children=recipe_steps[0]['steps'][n]['step']) for n in range(len(recipe_steps[0]['steps']))])]
        used_ingredients_images = used_ingredients_images + recipe_steps

    # recipe missing ingredients
    recipe_missing_ingredients = [{'name': n['name'], 'id':n['id'], 'aisle':n['aisle'], 'amount':n['amount'],
                                  'unit':n['unit']} for n in
                                  recipies[cur_recipe_idx]['missedIngredients']]
    logging.debug(f"Writing missing ingredients as {recipe_missing_ingredients}")

    # update button title
    save_recipe_btn = "Save " + \
        str(recipies[cur_recipe_idx]['missedIngredientCount']
            ) + " Missing ingredients to cart"
    return [{'display': 'block', 'border-radius': '25px',
             'border': '15px solid #73AD21', 'padding': '20px', },
            recipe_title, cur_recipe_image, used_ingredients_images,
            recipe_missing_ingredients, save_recipe_btn, recipies,
            cur_recipe_idx, ingredients_selected]


"""
save_to_cart
This callback handles displaying and clearing of cart data

INPUT
    This callback will fire on:
    -save missing items button being clicked
    -empty cart being clicked

    This callback will read values of:
    -the cart long term data storage
    -missing ingredients storage

OUTPUT (Return values)
    This callback can change:
    -The visability of the shopping cart div
    -the shopping cart table
    -shopping cart long term storage

"""
@app.callback(
    [dash.dependencies.Output("shopping-sub", "style"),
     dash.dependencies.Output("shopping-list", "children"),
     dash.dependencies.Output("cart", "data")],
    [dash.dependencies.Input("save-missing", "n_clicks_timestamp"),
     dash.dependencies.Input("empty-cart", "n_clicks_timestamp")],
    [dash.dependencies.State("cart", "data"),
     dash.dependencies.State("missing-ingredients", "data")],
)
def save_to_cart(save_cart, empty_cart, current_cart, missing_ing):

    # Our cart does exist lets print it now
    if current_cart is not None and len(current_cart) > 0:
        logging.debug(f"The current cart looks like: {current_cart}")

    # Empty cart was clicked recently
    # Check with button timestamps for which was clicked most recent
    # When clearing cart we need to hide the cart div, clear the cart table
    # wipe out the cart data store
    if int(empty_cart) > int(save_cart):
        logging.info("Empty cart was clicked")
        return [{'display': 'none'}, '', None]

    # Save cart was clicked more recently
    # Check with button timestamps for which was clicked most recent
    # Calculate missing ingredient price, generate a cart dataframe
    # Display the dataframe as a table
    if int(empty_cart) < int(save_cart):
        logging.info(
            f"Save to cart clicked, missing ingredients are {','.join([n['name'] for n in missing_ing])}")

        # We will need to iterate over each ingredeint to get price
        # we already have aisle data
        # https://spoonacular.com/food-api/docs#Get-Ingredient-Information
        for ingredient in missing_ing:
            try:
                response = requests.get('https://api.spoonacular.com/food/ingredients/' + str(
                    ingredient['id']) + '/information?amount=' + str(ingredient['amount']) + "&apiKey=" + API_SECRET)
                # check that requests didn't receive api related errors:
                # 401 status code
                if response.status_code == 401:
                    logging.error("API Key related error")
                response.raise_for_status()
                # access JSOn content
                ing_cost = response.json()
                logging.debug(f"Response is:  {ing_cost}")
                ingredient.update({'cost': ing_cost['estimatedCost']['value']})
            except HTTPError as http_err:
                logging.error(
                    f'HTTP error occurred getting prices: {http_err}')
                ingredient.update({'cost': 0.00})
            except Exception as err:
                logging.error(f'Other error occurred: {err}')

        logging.debug(
            f"Prices have been appended now display dataframe {missing_ing}")

    # Lets check if this is a secondary+ run then append current cart
    if current_cart:
        # We have a cart saved but no recent queries
        if missing_ing is None or len(missing_ing) == 0:
            missing_ing = current_cart
        else:
            missing_ing.extend(current_cart)
            logging.debug(
                f"We've appended a old cart, new cart looks like {missing_ing}")
    # We have a empty cart and no current missing ingredients
    if missing_ing is None or len(missing_ing) == 0:
        logging.debug("No prior cart, lets just return")
        return [{'display': 'none'}, '', '']

    logging.debug(f"Missing ingredeints are {missing_ing}")

    # Convert ingredients dictionary into a cart dataframe
    cart = make_cart(missing_ing)

    # Build the table
    missing_prices = dash_table.DataTable(
        id='table',
        columns=[{"name": i, "id": i} for i in cart.columns],
        data=cart.to_dict('records'),
        sort_action="native"
    )

    return [{'display': 'block'}, missing_prices, missing_ing]


def make_cart(ingredient_dict):
    """Make a missing ingredient dictionary
    accepts a ingredient dictionary containing name and aisle
    return: a dataframe cart to be passed into a datatable later
    """

    df = pd.DataFrame.from_dict(ingredient_dict)
    # Remove index
    df.reset_index(drop=True, inplace=True)

    # Make a neat total row
    df.loc['Total', :] = df.sum()

    # Cleanup the total row
    df.iloc[-1, df.columns.get_loc('name')] = 'Total'
    df.iloc[-1, df.columns.get_loc('aisle')] = ''

    # Remove unused columns
    df = df.drop(['unit', 'id', 'amount'], axis=1)
    return df


# When running this script from shell
# the server should be started as follows:
# Debugging set off, access may be limited by host ip, port is defined
if __name__ == "__main__":
    app.run_server(debug=False, host='0.0.0.0', port=8051)
