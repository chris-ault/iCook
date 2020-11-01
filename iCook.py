#!/usr/bin/env python

from os import environ
from sys import exit as exit_dashboard
import logging
import requests
from requests.exceptions import HTTPError
import pandas as pd
import dash
import dash_table
from dash.exceptions import PreventUpdate
import dash_core_components as dcc
import dash_html_components as html


logging.basicConfig(level=logging.ERROR)


API_SECRET = environ.get("ICOOK_KEY", 'missing_key')
if API_SECRET is 'missing_key':
    logging.error(f'Please supply a key as an environment variable ICOOK_KEY: {API_SECRET}')
    exit_dashboard(1)

# Response for autocomplete
# https://spoonacular.com/food-api/docs#Autocomplete-Recipe-Search

# Response for recipe searching by ingredient
# https://spoonacular.com/food-api/docs#Search-Recipes-by-Ingredients

# Response for price of recipe, this unfortunately gives 
# https://spoonacular.com/food-api/docs#Get-Recipe-Price-Breakdown-by-ID


# Use stylesheets for dash components
external_stylesheets = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

# Here we define the interface the user sees
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
            html.Div(id='current-recipe-count',children=0, style= {'display': 'none'}),
            dcc.Store(id='cached-recepies', data=None),
            html.Div(id='recipe-title',children=None),
            html.Img(id='recipe-img'),
            html.Br(),
            "Ingredients we already have:",
            html.Div(id='recipe-ingredients', children='ingredients'),
            dcc.Store(id='missing-ingredients'),
        html.Button("Save missing ingredients to cart", id="save-missing", n_clicks_timestamp=1),
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
    ], style={'width':'600px'}
)



"""
fill_ingredients
This callback will query the spoonacular server once user has entered characters 
Alternatively we could auto fill the options with ingredients from this long list that will become outdated
https://spoonacular.com/food-api/docs#List-of-Ingredients

"""
@app.callback(
    dash.dependencies.Output("ingredients-dropdown", "options"),
    [dash.dependencies.Input("ingredients-dropdown", "search_value")],
    [dash.dependencies.State("ingredients-dropdown", "value")],
)
def fill_ingredients(search_value, value):
    if not search_value:
        raise PreventUpdate
    logging.debug('Doing a ingredeint query on \'{}\''.format(search_value))
    logging.debug('Current value is \'{}\''.format(value))

    # Here we will update sample_ingredients with a real query result
    try:
        response = requests.get('https://api.spoonacular.com/food/ingredients/autocomplete?query=' + search_value + '&number=8' + "&apiKey=" + API_SECRET)
        if response.status_code == 401:
                logging.error("API Key related error")
        response.raise_for_status()
        sample_ingredients = response.json()
        logging.debug("Response is:  {}".format(sample_ingredients))
    except HTTPError as http_err:
        logging.error(f'HTTP error occurred: {http_err}')
    except Exception as err:
        logging.error(f'Other error occurred: {err}')
    options = [{'label':i['name'].title(), 'value':i['name']} for i in sample_ingredients]
    
    # Here we need to extend the options to include our already selected items
    # Otherwise previous selections will dissappear
    if value:
        options.extend([{'label':k,'value':k} for k in value])
    logging.debug("New options are {}".format(options))

    # Make sure that the set values are in the option list, else they will disappear
    # from the shown select list, but still part of the `value`.
    return [
        o for o in options if search_value.title() in o["label"] or o["value"] in (value or [])
    ]


"""
update_recipe_option
Here the recipe is calculated and displayed on the screen

This callback will fire on inputs: 
search recipe button, skip recipe button and clear ingredients

The callback will modify:
anything on the page relating to recipies and recipe caching

The callback will read the state of:
selected ingredients dropdown, recipe index counter, data store of cached recipies
"""

@app.callback(
    [dash.dependencies.Output("recipe_sub","style"),
     dash.dependencies.Output("recipe-title", "children"),
     dash.dependencies.Output("recipe-img", 'src'),
     dash.dependencies.Output("recipe-ingredients", "children"),
     dash.dependencies.Output("missing-ingredients", "data"),
     dash.dependencies.Output("save-missing", "children"),
     dash.dependencies.Output("cached-recepies", "data"),
     dash.dependencies.Output("current-recipe-count","children"),
     dash.dependencies.Output("ingredients-dropdown", "value")],
    [dash.dependencies.Input("search-recipe", "n_clicks_timestamp"),
     dash.dependencies.Input("skip-recipe", "n_clicks_timestamp"),
     dash.dependencies.Input("clear-ingredients", "n_clicks_timestamp")],
    [dash.dependencies.State("ingredients-dropdown", "value"),
    dash.dependencies.State("current-recipe-count", "children"),
    dash.dependencies.State("cached-recepies", "data")],
)
def update_recipe_option(search_btn, skip_btn, clear_btn, ingredients_selected, cur_recipe_idx,cached_recepies):
    if not ingredients_selected:
        raise PreventUpdate
    recipe_buffer = 30

    if search_btn > clear_btn and search_btn > skip_btn:
        logging.info("search clicked")
        # Here we should fire the search recipe with ingredients_selected query 
        # to update the sample_recipies variable
        # https://api.spoonacular.com/recipes/findByIngredients?ingredients=apples,+flour,+sugar&number=2
        try:
            response = requests.get('https://api.spoonacular.com/recipes/findByIngredients?ingredients=' + ','.join(ingredients_selected) + '&number=' + str(recipe_buffer) + "&apiKey=" + API_SECRET)
            if response.status_code == 401:
                logging.error("API Key related error")
            response.raise_for_status()
            # access JSOn content
            sample_recipies = response.json()
            logging.debug("Response is:  {}".format(sample_recipies))
        except HTTPError as http_err:
            logging.error(f'HTTP error occurred: {http_err}')
        except Exception as err:
            logging.error(f'Other error occurred: {err}')
    if clear_btn > search_btn and clear_btn > skip_btn:
        logging.info("clear clicked")
        return [{'display':'none    '}, '', '', '', '', 'Save ingredients','', cur_recipe_idx,'']
    if skip_btn > clear_btn and skip_btn > search_btn:
        logging.info("skip clicked")
        # If we have a skip button, a recipe list should already be loaded
        # Lets just use the cached list and iterate to the next element
        sample_recipies = cached_recepies
        if cur_recipe_idx < recipe_buffer-1:
            cur_recipe_idx = cur_recipe_idx + 1
        else:
            # TODO: this is a quick fix that will wrap the user back to the first recipe
            # Currently just to prevent a index error 31/30 recipies
            cur_recipe_idx = 0
    
    # recipe title
    rtitle = sample_recipies[cur_recipe_idx]['title']
    
    # recipe image
    rimg = sample_recipies[cur_recipe_idx]['image']
    
    # recipe ingredients we have
    ring = [html.Img(src=n['image']) for n in sample_recipies[cur_recipe_idx]['usedIngredients']]
    
    # recipe missing ingredients
    rming = [{'name':n['name'],'id':n['id'],'aisle':n['aisle'],'amount':n['amount'],'unit':n['unit']} for n in sample_recipies[cur_recipe_idx]['missedIngredients']]
    logging.debug("Writing missing ingredients as {}".format(rming))
    
    # update button title
    rbutton = "Save " + str(sample_recipies[cur_recipe_idx]['missedIngredientCount']) + " Missing ingredients to cart"
    return [{'display':'block'}, rtitle, rimg, ring, rming, rbutton, sample_recipies, cur_recipe_idx, ingredients_selected]

"""
save_to_cart
This callback handles displaying and clearing of cart data

This callback will fire on:
-save missing items button being clicked
-empty cart being clicked

This callback will read values of:
-the cart long term data storage
-missing ingredients storage

This callback can change:
-The visability of the shopping cart div
-the shopping cart table
-shopping cart long term storage

"""


@app.callback(
    [dash.dependencies.Output("shopping-sub", "style"),
     dash.dependencies.Output("shopping-list", "children"),
     dash.dependencies.Output("cart","data")],
    [dash.dependencies.Input("save-missing", "n_clicks_timestamp"),
    dash.dependencies.Input("empty-cart", "n_clicks_timestamp")],
    [dash.dependencies.State("cart", "data"),
    dash.dependencies.State("missing-ingredients", "data")],
)
def save_to_cart(save_cart,empty_cart,current_cart, missing_ing):

    # Our cart does exist lets print it now
    if current_cart is not None and len(current_cart) > 0:
        logging.debug("The current cart looks like: {}".format(current_cart))
    
    if int(empty_cart) > int(save_cart):
        logging.info("Empty cart was clicked more recently than save_cart")
        return [{'display':'none'}, '', None]
    if int(empty_cart) < int(save_cart):
        logging.info("Save to cart clicked")

        # We will need to iterate over each ingredeint to get price
        # we already have aisle data
        # Caveat.... This will cost 1 point per loop
        # https://spoonacular.com/food-api/docs#Get-Ingredient-Information
        for ingredient in missing_ing:
            try:
                response = requests.get('https://api.spoonacular.com/food/ingredients/' + str(ingredient['id']) + '/information?amount=' + str(ingredient['amount']) + "&apiKey=" + API_SECRET)
                if response.status_code == 401:
                    logging.error("API Key related error")
                response.raise_for_status()
                # access JSOn content
                ing_cost = response.json()
                logging.debug("Response is:  {}".format(ing_cost))
                ingredient.update({'cost':ing_cost['estimatedCost']['value']})
            except HTTPError as http_err:
                logging.error(f'HTTP error occurred: {http_err}')
            except Exception as err:
                logging.error(f'Other error occurred: {err}')
        logging.debug("Prices have been appended now display dataframe {}".format(missing_ing))
        
    # Lets check if this is a secondary+ run then append current cart
    if current_cart:
        # We have a cart saved but no recent queries
        if missing_ing is None or len(missing_ing) == 0:
            missing_ing = current_cart
        else:
            missing_ing.extend(current_cart)
            logging.debug("We've appended a old cart, new cart looks like {}".format(missing_ing))
    # We have a empty cart and no current missing ingredients
    if missing_ing is None or len(missing_ing) == 0:
        logging.debug("No prior cart, lets just return")
        return [{'display':'none'}, '', '']

    logging.debug("Missing ingredeints are {}".format(missing_ing))
    
    # Convert ingredients dictionary into a cart dataframe
    cart = make_cart(missing_ing)

    # Build the table
    missing_prices = dash_table.DataTable(
    id='table',
    columns=[{"name": i, "id": i} for i in cart.columns],
    data=cart.to_dict('records'),
    sort_action="native"
    )

    return [{'display':'block'}, missing_prices, missing_ing]


def make_cart(ingredient_dict):
    '''Build up a dataframe of our missing ingredients dictionary
    make_cart can take dictionary and return a dataframe cart to be presented'''
    
    df = pd.DataFrame.from_dict(ingredient_dict)
    # Remove index
    df.reset_index(drop=True, inplace=True)

    # Make a neat total row
    df.loc['Total',:] = df.sum()

    # Cleanup the total row
    df.iloc[-1, df.columns.get_loc('name')] = 'Total'
    df.iloc[-1, df.columns.get_loc('aisle')] = ''

    # Remove unused columns
    df = df.drop(['unit','id','amount'],axis=1)
    return df



# When we execute python iCook the server will run
if __name__ == "__main__":
    app.run_server(debug=False, host='0.0.0.0')