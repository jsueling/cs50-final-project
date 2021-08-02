import os
import psycopg2

from config import config
from flask import Flask, flash, render_template, redirect, request, session
from flask_session import Session
from tempfile import mkdtemp
from functions import error_page, login_required, lookup, usd
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, time, timedelta
from dotenv import load_dotenv

# Setup the flask app
app = Flask(__name__)

# https://stackoverflow.com/questions/9508667/reload-flask-app-when-template-file-changes
# Ensure templates are auto-reloaded in the app when they are changed
app.config["TEMPLATES_AUTO_RELOAD"] = True

# https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cache-Control
# https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Pragma
# https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Expires
# https://flask.palletsprojects.com/en/2.0.x/api/#flask.Flask.after_request
# Ensure responses aren't cached in the headers of the response after every API request
# Pragma is deprecated in HTTP 1.1 but used for backwards compatibility with HTTP 1.0
# Setting value of 0 in expires means everything inside is now considered stale
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# https://stackoverflow.com/questions/3948975/why-store-sessions-on-the-server-instead-of-inside-a-cookie
# https://flask-session.readthedocs.io/en/latest/#configuration
# Configure session to use filesystem (instead of signed cookies)
# We make a temporary directory to store session files 
# We configure session to be non-permanent (default true)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# https://flask.palletsprojects.com/en/2.0.x/templating/#registering-filters
# This filter is now registered for use in templates
app.jinja_env.filters["usd"] = usd

# TODO setup a postgres db file to be referred to
# db = #https://devcenter.heroku.com/articles/getting-started-with-python#provision-a-database
# https://data.heroku.com/datastores/c27215db-81e8-4cd9-a1bb-f5d89a6b7949#administration
# Access the database using these keys
# Setup tables I need
# Find a way to reference back to the db i.e. db = SQL("sqlite:///finance.db")
# Tables: users: user_id
# CREATE UNIQUE INDEX 'username' ON "users" ("username");
# We must have unique usernames or there is potential to hack other accounts
# when user logs in the program will either retrieve the first row which has the username or there will be an error
# both are bad outcomes for the user
# Best practice: for unique username, check against the hash else reject

# https://www.postgresqltutorial.com/postgresql-python/connect/
# https://www.psycopg.org/docs/usage.html

# params = config()
# conn = psycopg2.connect(**params)
# cur = conn.cursor()
# SQL query cur.execute()
# cur.fetchall()
# conn.commit() for update insert delete
# cur.close()
# conn.close()

# Something to look at maybe
# https://stackoverflow.com/questions/28323666/setting-environment-variables-in-heroku-for-flask-app
# https://stackoverflow.com/questions/41546883/what-is-the-use-of-python-dotenv
# https://www.twilio.com/blog/environment-variables-python
# .flaskenv needs to be added somewhere, add to functions to stop the program from not running

# https://flask.palletsprojects.com/en/2.0.x/cli/
load_dotenv("keys.env")

if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

@app.route("/")
@login_required
def index():
    # For a user that has used the website (easiest test is to check for rows in SQL table) I want
    # to return to them a list of their portfolios

    id = session["user_id"]

    params = config()
    conn = psycopg2.connect(**params)
    cur = conn.cursor()
    cur.execute("SELECT portfolio_name FROM shares where id = (%s) GROUP BY portfolio_name;", (id,))
    names = cur.fetchall()
    cur.close()
    conn.close()

    # I could create a portfolio table only listing the portfolio names but that seems inefficient
    if not names:
        flash("No portfolios detected - you have been redirected here automatically.", "primary")
        return redirect("/create")
    else:
        return render_template("index.html", names=names)

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if session.get("user_id"):
        flash("You are already logged in.", "primary")
        return redirect("/")

    # User submitting register form
    if request.method == "POST":
        # User inputs
        username = request.form.get("username")
        # Case insensitive username for a smoother user experience
        lower_username =  username.lower()
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Form checks
        if not username:
            return error_page("Please enter a username")
        if not password:
            return error_page("Please enter a password")
        if password != confirmation:
            return error_page("Passwords do not match")

        # Connected
        params = config()
        conn = psycopg2.connect(**params)
        cur =  conn.cursor()

        cur.execute("SELECT * FROM users WHERE username = (%s);", (lower_username,))
        rows = cur.fetchall()

        # Database check
        if len(rows) == 1:
            return error_page("This username is taken, try another username")

        # Hash user input password
        hashed_password = generate_password_hash(password)

        # Passed error checks, password hashed
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s);", (lower_username, hashed_password))
        
        # Instead of redirecting to login we can be efficient and redirect to the index
        cur.execute("SELECT * FROM users WHERE username = (%s);", (lower_username,))
        rows = cur.fetchall()
        
        # After first storing id in session
        # Which satisfies our login_required function
        session["user_id"] = rows[0][0]

        conn.commit()
        cur.close()
        conn.close()

        flash(f"Registered and logged in as {username} successfully!", "success")
        return redirect("/")
    
    # User requesting the page (GET)
    else:
        return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    if session.get("user_id"):
        flash("You are already logged in.", "primary")
        return redirect("/")

    # User is submitting the form on trying to login (POST)
    if request.method =="POST":

        # User inputs
        username = request.form.get("username")
        lower_username = username.lower()
        password = request.form.get("password")

        # Form checks
        if not username:
            return error_page("You must enter a username", 403)
        if not password:
            return error_page("You must enter a password", 403)

        # https://www.psycopg.org/docs/usage.html
        # Set paramaters of database connection from the config file
        params = config()
        # Open connection
        conn = psycopg2.connect(**params)
        # Open a cursor
        cur = conn.cursor()
        # Execute my query
        cur.execute("SELECT * FROM users WHERE username = (%s);", (lower_username,))
        # Store the results
        rows = cur.fetchall()
        # close the cursor and the connection
        cur.close()
        conn.close()

        # Database checks
        if len(rows) != 1:
            return error_page("An account with this username does not exist", 403)

        if not check_password_hash(rows[0][2], password):
            return error_page("Incorrect password", 403)
        
        # Passed Checks > Store current user ID
        session["user_id"] = rows[0][0]
        
        flash(f"Logged in as {username} successfully!", "success")
        # Successful login
        return redirect("/")

    # User wants to GET the page
    else:
        return render_template("login.html")

@app.route("/logout")
@login_required
# User must be logged in to logout
def logout():
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect("/login")

@app.route("/create", methods=["GET", "POST"])
@login_required
def create():
    
    # https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input/date
    # Important: Client-side form validation is no substitute for validating on the server.
    # It's easy for someone to modify the HTML, or bypass your 
    # HTML entirely and submit the data directly to your server.
    # If your server fails to validate the received data, disaster could 
    # strike with data that is badly-formatted, too large, of the wrong type, etc.

    # Both methods need access to these variables
    x = datetime.today()
    today = x.strftime("%Y-%m-%d")
    # https://stackoverflow.com/questions/441147/how-to-subtract-a-day-from-a-date
    # Iexcloud API only offers historical data >5years on paid plans
    # 365 * 5 = 1825
    # After testing manually its a few days short sometimes so subtracted 5
    # TODO Weekends

    mindate = x - timedelta(days=1825)

    if request.method =="POST":
        
        id = session["user_id"]
        portfolio_name = request.form.get("portfolio_name")
        lower_pfname = portfolio_name.lower()
        symbol = request.form.get("symbol")
        purchase_quantity = request.form.get("purchase_quantity")

        # Internet explorer doesn't support input="date", degrades to input="text"
        
        # https://stackoverflow.com/questions/10434599/get-the-data-received-in-a-flask-request
        try:
            # Native case with input="date"
            purchase_date = request.form["purchase_date"]
        except KeyError:
            # KeyError is triggered when an element with that name doesn't exist
            # So by elimination fallback:
            purchase_date = request.form["fallback_purchasedate"]
        if not purchase_date:
            return error_page("Enter a date", 403)
        
        # Convert to a datetime object so we can compare likes
        parsed_purchasedate = datetime.strptime(purchase_date, "%Y-%m-%d")

        # Prevent the user from entering, into either the native or fallback input, a date out of these bounds
        if parsed_purchasedate < mindate:
            # TODO
            return error_page("Sorry, This application is limited to only support historical price queries up to ~5 years (1820 days) past", 403)
        
        # 00:00 2021/08/01 -> 23:59 2021/08/01 Need to error check this to not have
        # Iexcloud doesnt store info using my API call for the current day (closing price is obvious)
        # After testing it's at least 1 extra day from current day
        # Weekend, need to write logic that searches for previous days if API call results in null
        # Maximum 3 days in the case that the user has
        # Account for stock exchange closures on Mondays
        # Check 0 (Monday), Check -1 (Sunday), Check -2 (Saturday), Check -3 (Friday)
        # Or just code to check if today is a weekend and return error message / restrict weekend inputs
        # The user could have submitted a buy request on a weekend but it wouldnt be fulfilled until monday

        #TODO if parsed_purchasedate == x:
        #     return error_page("Cannot select today's date", 403)
        if parsed_purchasedate > x:
            return error_page("You've entered a date in the future", 403)

        if not portfolio_name:
            return error_page("Enter a portfolio name", 403)
        if not symbol:
            return error_page("Enter a symbol", 403)
        if not purchase_quantity:
            return error_page("Enter a quantity", 403)

        # https://pynative.com/python-check-user-input-is-number-or-string/
        try:
            # Cast as an int. If this fails we get a value error,
            # so the input is not readable as an integer.
            # Otherwise test passed the input was readable as an integer
            val = int(purchase_quantity)
        except ValueError:
            try:
                # cast as float
                val = float(purchase_quantity)
                # No error, the input was a float return this error message
                return error_page("Quantity must be an integer", 403)
            # The input is neither an int or a float so return this message
            except ValueError:
                return error_page("Quantity must be in decimal digits, 403")
        
        # Convert to int after error checks with relevant messages
        purchase_quantity = int(purchase_quantity)

        if purchase_quantity < 1:
            return error_page("Quantity must be a non-zero positive number", 403)

        params = config()
        conn = psycopg2.connect(**params)
        cur = conn.cursor()
        # We don't want a user to have portfolios with the same name
        cur.execute("SELECT portfolio_name FROM shares WHERE id=(%s) AND portfolio_name=(%s) GROUP BY portfolio_name", (id, lower_pfname))
        rows = cur.fetchall()
        if len(rows) == 1:
            return error_page('You already have a portfolio with this name', 403)
        
        # Check to see that the symbol exists in our API
        # The API call comes after all checks so we are efficient with our resources
        # Prevents unused API calls
        upper_symbol = symbol.upper()
        data = lookup(upper_symbol, parsed_purchasedate)

        # As we have validated the date already it can only be the symbol entered causing the API to return null
        if not data:
            return error_page("The symbol was not recognised, refer to the link for supported symbols", 403)

        # checked purchase date, quantity, portfolio name, symbol

        cur.execute("INSERT INTO shares (symbol, purchase_quantity, purchase_date, portfolio_name, id) VALUES (%s, %s, %s, %s, %s);", (upper_symbol, purchase_quantity, parsed_purchasedate, portfolio_name, id))
        conn.commit()
        cur.close()
        conn.close()

        flash(f"{portfolio_name} has been successfully created.", "success")

        # https://stackoverflow.com/questions/8552675/form-sending-error-flask
        # The buttons are identical but redirect to different pages
        if request.form["submit"] == "create":
            return redirect("/")
        else:
            return redirect("/add")

    else:
        return render_template("create.html", today=today, mindate=mindate)

@app.route("/myportfolios/<portfolio_name>")
@login_required
def myportfolios(portfolio_name):

    id = session["user_id"]

    params = config()
    conn = psycopg2.connect(**params)
    cur = conn.cursor()
    cur.execute("SELECT symbol, SUM(purchase_quantity) AS sum_shares, purchase_date FROM shares WHERE id=(%s) AND portfolio_name=(%s) GROUP BY symbol, purchase_date;", (id, portfolio_name))
    portfolio = cur.fetchall()
    cur.close()
    conn.close()

    x = []

    for row in portfolio:
        # Revisit to look for correct types here for dates
        # Functions.py takes date inputs and formats it as string YYYYMMDD for the URL
        purchase_price = lookup(row["symbol"], row["purchase_date"])["price"]
        current_price = lookup(row["symbol"], datetime.today())["price"]
        gain_loss = (purchase_price - current_price)*row["sum_shares"]

        date_nospace = row["purchase_date"].strftime("%Y%m%d")
        unique_id = row["symbol"] + date_nospace

        z = [{'unique_id': unique_id, 'gain_loss': gain_loss}]

        x += z
    
    # https://www.tutorialspoint.com/How-to-sort-the-objects-in-a-list-in-Python
    def my_key(obj):
        return obj['gain_loss']

    # 2 arrays of objects sorted
    # x when sorted [{'unique_id': 'AAPL20210717', 'gain_loss': 16}, ...10, 9, 5, 4 , 1, 0, -1, -2, -14]
    x = x.sort(key=my_key, reverse=True)

    i = len(x) - 1

    if x[0]["gain_loss"] >= abs(x[i]["gain_loss"]):
        y = x[0]["gain_loss"]
    else:
        y = abs(x[i]["gain_loss"])

    # I pass the largest element of both arrays

    return render_template("portfolio.html", x=x, y=y, portfolio_name=portfolio_name)