import os
import requests
import urllib.parse
import pyEX as pyEX

def lookup(symbol):

    # Contact API
    try:
        #https://stackoverflow.com/questions/16511337/correct-way-to-try-except-using-python-requests-module
        #Remember to set API_KEY as an environment variable
        api_key = os.environ.get("API_KEY")
        date_input = #TODO YYYYMMDD format
        response = requests.get(f"https://sandbox.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/chart/date/{date_input}?token={api_key}&chartByDay=true")
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    try:
        quote = response.json()
        return {
            "price": float(quote["latestPrice"]),
            "symbol": quote["symbol"]
        }
    except (KeyError, TypeError, ValueError):
        return None