import os
import psycopg2

from config import config
from flask import Flask, flash, render_template, redirect, request, session
from flask_session import Session
from tempfile import mkdtemp
from functions import error_page, login_required, lookup, usd
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import time
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

# https://www.twilio.com/blog/environment-variables-python
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

    if not names:
        flash("We detected you have no portfolios so you have been redirected here", "primary")
        return redirect("/create")

    else:
        return render_template("index.html", names=names)

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    session.clear()

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

    # Clear user_id
    session.clear()

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
    return redirect("/")

@app.route("/create")
@login_required
def create():
    # TODO
    return render_template("create.html")

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
        current_price = loookup(row["symbol"], date.today())["price"]
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