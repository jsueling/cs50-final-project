import os
import requests
import urllib.parse

from flask import redirect, session, render_template 
from functools import wraps

def error_page(message, code=400)
    """Returns a message on the error and what the user should do"""
    return render_template("error_page.html", code=code, message=message), code

def lookup(symbol):
    """Look up quote for symbol."""

    #Contact API
    try:
        #https://stackoverflow.com/questions/16511337/correct-way-to-try-except-using-python-requests-module
        #Remember to set API_KEY as an environment variable
        api_key = os.environ.get("API_KEY")
        date_input = #TODO YYYYMMDD format
        response = requests.get(f"https://sandbox.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/chart/date/{date_input}?token={api_key}&chartByDay=true")
        response.raise_for_status()
    except requests.RequestException:
        return None

    #Parse response
    try:
        quote = response.json()
        return {
            "price": float(quote["close"]),
            "symbol": quote["symbol"]
            "label": quote["label"]
        }
    except (KeyError, TypeError, ValueError):
        return None


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"