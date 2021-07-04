import os

from flask import Flask, render_template, redirect, request, session
from flask_session import Session
from tempfile import mkdtemp
from functions import error_page, login_required, lookup, usd

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
# db = 

# set API_KEY= for windows
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

@app.route("/")
def index():
    # For a user that has used the website (easiest test is to check for rows in SQL table) I want
    # to return to them a list of their portfolios
    return render_template("index.html")

@app.route("/register")
def register():
    return render_template("register.html")

@app.route("/login")
def login():
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
