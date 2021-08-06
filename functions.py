import os
import requests
import urllib.parse

from flask import redirect, session, render_template 
from functools import wraps
from datetime import time, timedelta, datetime, date

def error_page(message, code=400):
    """Returns a message on the error and what the user should do"""
    return render_template("error_page.html", code=code, message=message), code

# My current application.py relies on calling lookup twice, my tables only store the date bought at
# Could store purchase price in table to save 1 API call per visit
# Same problem in /create, no data on days where exchanges are closed or current day
# Need to rewrite lookup to accomodate lack of data on some days
# e.g. lookup(today) > lookup(nearest weekday)
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
        }
    except (KeyError, TypeError, ValueError, IndexError):
        return None

def scan(symbol, date_input):
    """Scan nearest days for data"""

    # IEX doesn't store historical price info of the current day 
    # or weekends/holidays when exchanges are closed

    todays_date = date.today()
    purchase_date = date_input

    # request for today which is Monday
    if todays_date == purchase_date and purchase_date.weekday() == 0:
        # call lookup using the previous Friday
        scan_date = purchase_date - timedelta(days=3)
        data = lookup(symbol, scan_date)
    
    # Weekends, lookup the nearest weekday

    # Saturday
    elif purchase_date.weekday() == 5:
        scan_date = purchase_date - timedelta(days=1)
        data = lookup(symbol, scan_date)
        if not data:
            scan_date = purchase_date + timedelta(days=3)
            data = lookup(symbol, scan_date)
    
    # Sunday
    elif purchase_date.weekday() == 6:
        scan_date = purchase_date + timedelta(days=1)
        data = lookup(symbol, scan_date)
        if not data:
            scan_date = purchase_date - timedelta(days=3)
            data = lookup(symbol, scan_date)
    
    # Monday to Friday
    # There's a tradeoff between accomodating the user and number of API calls
    # It's not efficient to have 3 API calls per failed lookup with alot of users
    else:
        data = lookup(symbol, purchase_date)
        scan_date = purchase_date
        if not data:
            scan_date = purchase_date - timedelta(days=1)
            data = lookup(symbol, scan_date)
            if not data:
                scan_date = purchase_date + timedelta(days=2)
                data = lookup(symbol, scan_date)
    
    # Return a json object with the new date used
    return {
        "price": data["price"],
        "symbol": data["symbol"],
        "date": scan_date
    }

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