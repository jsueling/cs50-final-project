import os
import requests
import psycopg2
import urllib.parse

from config import config
from flask import redirect, session, render_template 
from functools import wraps
from datetime import time, timedelta, datetime, date

def error_page(message, code=400):
    """Returns a message on the error and what the user should do"""
    return render_template("error_page.html", code=code, message=message), code

# https://www.psycopg.org/docs/usage.html
# https://www.freecodecamp.org/news/connect-python-with-sql/

def db_select(query, data):
    """Connects to the database using config.py and executes a SELECT query"""
    
    # Open connection
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    # Open a cursor
    cur = conn.cursor()
    # Execute SELECT query
    cur.execute(query, data)
    # Store the results
    results = cur.fetchall()
    # Close the cursor and the connection
    cur.close()
    conn.close()
    # Return the results of the query that was called with db_select()
    return results

def db_commit(query, data):
    """
    Connects to the database using config.py, executes a query
    and commmits the changes
    does not return any results 
    """

    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cur = conn.cursor()
    cur.execute(query, data)
    # commit changes made from the query (insert, update, delete)
    conn.commit()
    cur.close()
    conn.close()

def lookup(symbol, date_input):
    """Looks up a symbol on date given"""

    # Contact API
    try:
        # https://stackoverflow.com/a/16511493
        # https://iexcloud.io/docs/api/
        api_key = os.environ.get("API_KEY")
        frmt_date = date_input.strftime("%Y%m%d")
        response = requests.get(f"https://cloud.iexapis.com/v1/stock/{urllib.parse.quote_plus(symbol)}/chart/date/{frmt_date}?token={api_key}&chartByDay=true")
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
    # Error check so we can return none to the user and display
    # error page if something went wrong
    except (KeyError, TypeError, ValueError, IndexError):
        return None

def scan(symbol, date_input):
    """Scans nearest days using lookup() for a purchase price"""

    # IEX doesn't store historical price info of the current day 
    # or weekends/holidays when exchanges are closed

    todays_date = date.today()
    purchase_date = date_input
    
    # 3 Edge cases
    # User inputting he bought shares on:
    
    # Monday which is today
    if todays_date == purchase_date and purchase_date.weekday() == 0:
        # call lookup using the previous Friday
        scan_date = purchase_date - timedelta(days=3)
        data = lookup(symbol, scan_date)
        if not data:
            # Thursday
            scan_date = pruchase_date - timedelta(days=1)
            data = data = lookup(symbol, scan_date)
    
    # Saturday which is today
    if todays_date == purchase_date and purchase_date.weekday() == 6:
        # Friday
        scan_date = purchase_date - timedelta(days=1)
        data = lookup(symbol, scan_date)
        if not data:
            # Thursday
            scan_date = pruchase_date - timedelta(days=2)
            data = data = lookup(symbol, scan_date)
    
    # Sunday which is today
    if todays_date == purchase_date and purchase_date.weekday() == 5:
        # Friday
        scan_date = purchase_date - timedelta(days=2)
        data = lookup(symbol, scan_date)
        if not data:
            # Thursday
            scan_date = pruchase_date - timedelta(days=3)
            data = data = lookup(symbol, scan_date)

    # For weekends, lookup the nearest weekday

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
    # It's not efficient to have lots of API calls with alot of users
    else:
        # lookup using the date entered
        data = lookup(symbol, purchase_date)
        scan_date = purchase_date
        if not data:
            # lookup 1 day before date input
            scan_date = purchase_date - timedelta(days=1)
            data = lookup(symbol, scan_date)
            if not data:
                # lookup 1 day after date input
                scan_date = purchase_date + timedelta(days=2)
                data = lookup(symbol, scan_date)
    

    try:
        return {
            "price": data["price"],
            "symbol": data["symbol"],
            "date": scan_date
        }
    # Error check so we can return none to the user and display
    # error page if something went wrong
    except (KeyError, TypeError, ValueError, IndexError):
        return None

# Since my application depended on calling scan
# Things like /portfolio broke when scan failed to get a current price
# because the user could do nothing but delete his portfolio to stop the error
# or wait until the next day
# I found this problem trying to access a portfolio that tried to get current
# price when today's date was a saturday and friday had no data.
# Instead of hard coding the days where this happens or extending
# if statements to scan more days, we can create another function that
# uses an API call that returns the latest price

def latestprice(symbol):
    """Gets the latest close price without needing a date input"""
    
    # https://iexcloud.io/docs/api/
    try:
        api_key = os.environ.get("API_KEY")
        response = requests.get(f"https://https://cloud.iexapis.com/v1/stock/{urllib.parse.quote_plus(symbol)}/quote?token={api_key}")
        response.raise_for_status()
    except requests.RequestException:
        return None
    
    try:
        quote = response.json()
        return {
            "price": float(quote["latestPrice"]),
            "symbol": quote["symbol"]
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