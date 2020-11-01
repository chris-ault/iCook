iCook
====


## Description

We all have ingriedents, but might be missing a few to make delicious recipies, iCook helps solve this issue before your next grocery run.  

- Enter some ingredients you have in the search bar  
- Press 'SEARCH'  
- View the recipe title, image, and ingredients you already have that will be used in this recipe
  - You can skip recipies you don't like with a simple click of the 'skip' button, a new recipe will be displayed.
- When you are happy with a recipe choose 'Save x Missing ingredients to cart'
- A cart table will be displayed with a row containing the total
  - This cart is stored in your browser so feel free to leave and come back it will be there until you press 'Empty cart'


Usage
------
This application must be run via Python 3.7 and we will need to install the accomponying requirements first.:
```
$ python -V
Python 3.7.4
$ pip install -r requirements.txt
...
```
Finally run python iCook.py with your API key as an environment variable titled **ICOOKKEY**
```
$ ICOOK_KEY=your_spoonacular_key_here python iCook.py
```



## Testing
You will need Docker and Docker Compose to start up a test harness.  
- [Docker](https://docs.docker.com/engine/install/ubuntu/)
- [Docker Compose](https://docs.docker.com/compose/install/)

Docker will create a image and container for each a iCook interface and a Selenium test container with a basic test of the interface search ingredient feature.  
## \**Note\**
You'll need to supply your own API key to the **iCook/Dockerfiles/Dockerfile.icook-interface** file under Environment variables replacing *enter_your_key_here* with your own Spoonacular API key.  


**~/iCook/Dockerfiles/Dockerfile.icook-interface**
```
ENV ICOOK_KEY=enter_your_key_here
```
Make an account to get a key here: https://spoonacular.com/food-api/console

Once the iCook key env variable has been set, you're good to start the test harness.

```
$ docker-compose up test
```

In addition to selenium testing we can test the make cart function with unittesting via Python unittest as follows:
```
$ ICOOK_KEY=1 python -m unittest test.test_helpers
```

## Deployment into the wild
To release this beyond localhost we would need to use a WSGI server, examples exist on the [Dash webpage](https://dash.plotly.com/deployment)
