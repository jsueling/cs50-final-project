import os
import psycopg2

from config import config
from flask import Flask, render_template, redirect, request, session
from flask_session import Session
from tempfile import mkdtemp
from functions import error_page, login_required, lookup, usd
from werkzeug.security import check_password_hash, generate_password_hash

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
# This filter is now registered for use in html files
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

# set API_KEY= for windows
# env file .gitignore
# TODO https://stackoverflow.com/questions/28323666/setting-environment-variables-in-heroku-for-flask-app
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

@app.route("/")
@login_required
def index():
    # For a user that has used the website (easiest test is to check for rows in SQL table) I want
    # to return to them a list of their portfolios
    id = session["user_id"]

    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    sesssion.clear()

    # User submitting register form
    if request.method == "POST":

        # User inputs
        username = request.form.get("username")
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

        cur.execute("SELECT * FROM users WHERE username = (%s);", (username))
        rows = cur.fetchall()

        # Database check
        if len(rows) == 1:
            return error_page("This username is taken, try another username")

        # Hash user input password
        hashed_password = generate_password_hash(password)

        # Passed error checks, password hashed
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s);", (username, hashed_password))
        
        # Instead of redirecting to login we can be efficient and redirect to the index
        cur.execute("SELECT * FROM users WHERE username = (%s);", (username))
        rows = cur.fetchall()
        
        # After first storing id in session
        # Which satisfies our login_required function
        session["user_id"] = rows[0]["id"]

        conn.commit()
        cur.close()
        conn.close()

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

        # Form checks
        if not request.form.get("username"):
            return error_page("You must enter a username", 403)

        elif not request.form.get("password"):
            return error_page("You must enter a password", 403)

        username =  request.form.get("username")

        # https://www.psycopg.org/docs/usage.html
        # Set paramaters of database connection from the config file
        params = config()
        # Open connection
        conn = pscyop2.connect(**params)
        # Open a cursor
        cur = conn.cursor()
        # Execute my query
        cur.execute("SELECT * FROM users WHERE username = (%s);", (username))
        # Store the results
        rows = cur.fetchall()
        # close the cursor and the connection
        cur.close()
        conn.close()

        # Database checks
        if len(rows) != 1:
            return error_page("An account with this username does not exist", 403)

        if not check_password_hash(rows[0]["password"], request.form.get("password")):
            return error_page("Incorrect password", 403)
        
        # Store current user ID
        session["user_id"] = rows[0]["id"]

        # Redirect the user on successful login
        return redirect("/")

    # User wants to GET the page
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/portfolio")
def portfolio():
    # TODO If the user has previously used the website I want to return to them a list of their portfolios
    # which they can click on to see and edit
    return render_template("portfolio.html")
