import os
import requests
import urllib.parse

def lookup(symbol):

    #https://stackoverflow.com/questions/16511337/correct-way-to-try-except-using-python-requests-module
    #Remember to set API_KEY as an environment variable
    try:
        api_key = os.environ.get("API_KEY")
        response = requests.get(f"https://sandbox.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/quote?token={api_key}")
        response.raise_for_status()
    except request.RequestException:
        return None

    #Parse response
    try:
        quote = response.json()
        return {

        }
    except (KeyError, TypeError, ValueError):
        return None