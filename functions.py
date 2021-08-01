import os
import requests
import urllib.parse

from flask import redirect, session, render_template 
from functools import wraps
from datetime import time

def error_page(message, code=400):
    """Returns a message on the error and what the user should do"""
    return render_template("error_page.html", code=code, message=message), code

def lookup(symbol, date_input):
    """Look up quote for symbol."""

    # Contact API
    try:
        # https://stackoverflow.com/questions/16511337/correct-way-to-try-except-using-python-requests-module
        api_key = os.environ.get("API_KEY")
        frmt_date = date_input.strftime("%Y%m%d")
        # move this to where I insert into my SQL table
        # https://www.quora.com/Should-dates-be-saved-as-datetime-objects-or-strings-in-a-database
        # Makes sense to store dates as a datetime for future use
        response = requests.get(f"https://sandbox.iexapis.com/stable/stock/{urllib.parse.quote_plus(symbol)}/chart/date/{frmt_date}?token={api_key}&chartByDay=true")
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response into a json object only extracting the information we need
    # Response is returning [{ , , , }] instead of { , , , }
    try:
        quote = response.json()
        return {
            "price": float(quote[0]["close"]),
            "symbol": quote[0]["symbol"],
            "label": quote[0]["label"]
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