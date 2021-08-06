import os
import psycopg2

from config import config
from flask import Flask, flash, render_template, redirect, request, session
from flask_session import Session
from tempfile import mkdtemp
from functions import error_page, login_required, lookup, usd, scan
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, date, time, timedelta
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
# Heroku is storing an environment variable of API_KEY=...
# Because the .env is not git committed and heroku is running the git committed vers
# Running locally keys.env is read with flask run
# Added a remote pointing to heroku to deploy to heroku with 'git push heroku master'
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

    no_portfolios = False

    if not names:
        no_portfolios = True

    # The user has 1 porfolio, automatic redirect to that portfolio
    if len(names) == 1:
        return redirect(f"/myportfolios/{names[0][0]}")
    else:
        return render_template("index.html", names=names, no_portfolios=no_portfolios)

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
            return error_page("Passwords do not match (Case sensitive)")

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
            return error_page("Incorrect password (Case sensitive)", 403)
        
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
    today = date.today()
    # https://iexcloud.io/docs/api/#historical-prices
    # Iexcloud API only offers historical data >5years on paid plans
    # 365 * 5 = 1825
    # https://docs.python.org/3/library/datetime.html#timedelta-objects
    min_date = today - timedelta(days=1825)

    if request.method =="POST":
        
        id = session["user_id"]
        portfolio_name = request.form.get("portfolio_name")
        symbol = request.form.get("symbol")
        purchase_quantity = request.form.get("purchase_quantity")

        # Internet explorer doesn't support input="date", degrades to input="text"
        try:
            # Native case with input="date"
            # https://stackoverflow.com/questions/10434599/get-the-data-received-in-a-flask-request
            purchase_date = request.form["purchase_date"]
        except KeyError:
            # KeyError when an element with that name doesn't exist
            # So by elimination fallback:
            purchase_date = request.form["fallback_purchasedate"]

        if not purchase_date:
            return error_page("Enter a date", 403)
        
        # Convert input a datetime object so we can compare
        parsed_datetime = datetime.strptime(purchase_date, "%Y-%m-%d")
        parsed_date = parsed_datetime.date()

        # Prevent the user from entering a date out of these bounds, today and 5 years ago
        if parsed_date < min_date:
            # TODO Test lower bound Live
            return error_page("This application is limited to only support historical price queries up to 5 years (1825 days) past", 403)
        if parsed_date > today:
            return error_page("You've entered a date in the future", 403)

        if not portfolio_name:
            return error_page("Enter a portfolio name", 403)
        if not symbol:
            return error_page("Enter a symbol", 403)
        if not purchase_quantity:
            return error_page("Enter a quantity", 403)

        # https://pynative.com/python-check-user-input-is-number-or-string/
        try:
            # If casting as int fails we get a value error which means the input must be a float or a string
            # No error means the input was an integer or string of an integer
            val = int(purchase_quantity)
        except ValueError:
            try:
                # cast as float
                val = float(purchase_quantity)
                # No error means the input was a float
                return error_page("Quantity must be an integer", 403)
            # By elimination the input is a string
            except ValueError:
                return error_page("Quantity must be in decimal digits, 403")
        
        # convert to int after error checks
        purchase_quantity = int(purchase_quantity)

        if purchase_quantity < 1:
            return error_page("Quantity must be a non-zero positive number", 403)

        params = config()
        conn = psycopg2.connect(**params)
        cur = conn.cursor()
        # We don't want a user to have portfolios with the same name
        cur.execute("SELECT portfolio_name FROM shares WHERE id=(%s) AND portfolio_name=(%s) GROUP BY portfolio_name", (id, portfolio_name))
        rows = cur.fetchall()
        if len(rows) == 1:
            return error_page('You already have a portfolio with this name', 403)
        
        # Check the symbol exists at IEX, whilst checking there is a price for the 
        # given date which are both stored in the database.

        # scan and lookup used after all other checks so we are more efficient with our API calls

        upper_symbol = symbol.upper()
        
        data = scan(upper_symbol, parsed_date)

        if not data:
            return error_page("No data found on the date entered for this symbol. Please refer to the link for supported symbols and check the date", 403)

        # data not empty
        scan_date = data["date"]
        purchase_price = data["price"]

        # All validity checks passed

        cur.execute("INSERT INTO shares (symbol, purchase_quantity, purchase_price, purchase_date, portfolio_name, id) VALUES (%s, %s, %s, %s, %s, %s);",
                    (upper_symbol, purchase_quantity, purchase_price, scan_date, portfolio_name, id))
        conn.commit()
        cur.close()
        conn.close()

        flash(f"{purchase_quantity} shares of {upper_symbol} bought on \U0001F4C5 {scan_date} - saved to {portfolio_name}", "success")
        flash(f"{portfolio_name} has been successfully created.", "success")

        # https://stackoverflow.com/questions/8552675/form-sending-error-flask
        # The buttons do the same thing except redirect to different pages
        if request.form["submit"] == "create":
            return redirect("/")
        else:
            return redirect("/add")

    else:
        return render_template("create.html", today=today, min_date=min_date)

@app.route("/myportfolios/<portfolio_name>")
@login_required
def myportfolios(portfolio_name):

    id = session["user_id"]
    now = datetime.now()
    
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
        purchase_price = lookup(row[0], row[2])["price"]
        current_price = lookup(row[0], now)["price"]
        gain_loss = (purchase_price - current_price)*row[1]

        date_nospace = row[2].strftime("%Y%m%d")
        unique_id = row[0] + date_nospace

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

@app.route("/delete", methods=["GET", "POST"])
@login_required
def delete():

    id = session["user_id"]

    params = config()
    conn = psycopg2.connect(**params)
    cur = conn.cursor()
    cur.execute("SELECT portfolio_name FROM shares where id = (%s) GROUP BY portfolio_name;", (id,))
    names = cur.fetchall()
    cur.close()
    conn.close()

    if not names:
        flash("No portfolios detected - you have been redirected here automatically.", "primary")
        return redirect("/create")

    if request.method =="POST":

        # Gets a list of the values of the checked inputs from the form with name="portfolio"
        portfolios = request.form.getlist("portfolio")

        if not portfolios:
            return error_page("Select portfolios you want to delete", 403)

        params = config()
        conn = psycopg2.connect(**params)
        cur = conn.cursor()

        # For each selected portfolio, delete the corresponding rows in shares
        for portfolio in portfolios:
            cur.execute("DELETE FROM shares where id = (%s) AND portfolio_name = (%s)", (id, portfolio))
            flash(f"{portfolio} was successfully deleted.", success)
        
        conn.commit()
        cur.close()
        conn.close()

        return redirect("/")
    else:
        return render_template("delete.html", names=names)