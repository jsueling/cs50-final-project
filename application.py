import os
import re

from flask import Flask, flash, render_template, redirect, request, session
from flask_session import Session
from tempfile import mkdtemp
from functions import error_page, login_required, lookup, usd, scan, latestprice, db_commit, db_select
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, date, time, timedelta
from dotenv import load_dotenv

# Setup the flask app
app = Flask(__name__)

# https://stackoverflow.com/a/54852798
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
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# https://flask.palletsprojects.com/en/2.0.x/templating/#registering-filters
# This filter is now registered for use in templates
app.jinja_env.filters["usd"] = usd

# https://flask.palletsprojects.com/en/2.0.x/cli/
load_dotenv("keys.env")

# https://devcenter.heroku.com/articles/heroku-postgresql#connecting-in-python
DATABASE_URL = os.environ['DATABASE_URL']

# Need the API_KEY for the application to function
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")

@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """
    Homepage that shows a welcome message if the user has no portfolios
    or a list of links for all portfolios they have created
    """
    # store current user_id from session
    id = session["user_id"]

    if request.method=="POST":

        # Get value from the page for "portfolio_name"
        portfolio_name = request.form.get("portfolio_name")

        if not portfolio_name:
            return error_page("Select a portfolio", 403)
        
        portfolio = db_select("SELECT portfolio_name FROM shares WHERE id=(%s) AND \
                            portfolio_name=(%s) GROUP BY portfolio_name;", (id, portfolio_name))
        
        # If the user clicked a portfolio that has no shares
        if not portfolio:
            flash("You need to add shares to this portfolio first.", "primary")
            return redirect("/add")
        
        # Else redirect to the portfolio they clicked on
        return redirect(f"/portfolio/{portfolio[0][0]}")

    # request.method=="GET"
    else:
        # Check for any portfolio existing in portfolios table
        portfolios = db_select("SELECT portfolio_name FROM portfolios WHERE id=(%s);", (id,))

        # Create boolean variable
        no_portfolios = False

        if not portfolios:
            no_portfolios = True

        return render_template("index.html", portfolios=portfolios, 
                                no_portfolios=no_portfolios)

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # If there is already a user_id in session
    if session.get("user_id"):
        flash("You are already logged in.", "primary")
        return redirect("/")

    # User is submitting the form on trying to register (POST)
    if request.method == "POST":
        # User inputs
        username = request.form.get("username")
        # Case insensitive username for an easier user experience
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

        # Check the username is unique in the users table
        rows = db_select("SELECT * FROM users WHERE username = (%s);", (lower_username,))

        if len(rows) == 1:
            return error_page("This username is taken, try another username")

        # Hash user input password
        hashed_password = generate_password_hash(password)

        # Passed error checks, password hashed -> register the user
        db_commit("INSERT INTO users (username, password) \
                    VALUES (%s, %s);", (lower_username, hashed_password))
        
        # Get the id from the newly created user
        rows = db_select("SELECT * FROM users WHERE username = (%s);", (lower_username,))
        
        # Storing user_id in session satisfies our login_required function
        session["user_id"] = rows[0][0]

        flash(f"Registered and logged in as {username} successfully!", "success")
        # Instead of redirecting to login we can be efficient and redirect,
        # once login_required is satisifed, to the index
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

    if request.method =="POST":

        username = request.form.get("username")
        lower_username = username.lower()
        password = request.form.get("password")

        if not username:
            return error_page("You must enter a username", 403)
        if not password:
            return error_page("You must enter a password", 403)

        rows = db_select("SELECT * FROM users WHERE username = (%s);", (lower_username,))

        # Database checks
        if len(rows) != 1:
            return error_page("An account with this username does not exist", 403)
        
        if not check_password_hash(rows[0][2], password):
            return error_page("Incorrect password (Case sensitive)", 403)
        
        # Passed Checks -> Store current user ID
        session["user_id"] = rows[0][0]
        
        flash(f"Logged in as {username} successfully!", "success")
        # Successful login
        return redirect("/")

    else:
        return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    """Log user out"""
    # User must be logged in to logout
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect("/login")

@app.route("/create", methods=["GET", "POST"])
@login_required
def create():
    """User can create a new portfolio"""
    if request.method =="POST":

        id = session["user_id"]
        portfolio_name = request.form.get("portfolio_name")

        if not portfolio_name:
            return error_page("Enter a portfolio name", 403)

        lower_pfname = portfolio_name.lower()

        rows = db_select("SELECT portfolio_name FROM portfolios WHERE \
                            portfolio_name=(%s)", (lower_pfname,))
        
        # portfolio_name must be unique because it is referenced as a foreign key in shares
        if len(rows) == 1:
            return error_page('This portfolio name is taken, choose another portfolio name', 403)
        
        # All tests passed, create the portfolio
        db_commit("INSERT INTO portfolios (id, portfolio_name) VALUES (%s, %s);", (id, lower_pfname))

        flash(f"{lower_pfname} has been successfully created!", "success")
        
        # User probably likely wants to add shares once a new portfolio is created
        return redirect("/add")

    else:
        return render_template("create.html")

@app.route("/portfolio/<portfolio_name>")
@login_required
def portfolio(portfolio_name):
    """
    Displays the current portfolio with a stacked horizontal bar chart,
    the overall $ and percentage change of the portfolio aggregating all purchases.
    The bar is dynamically generated to show relative performance
    between constituents. The user can click and mouseover these elements
    to see more details.
    """

    id = session["user_id"]
    today = date.today()

    shares = db_select(
    """
    SELECT symbol, SUM(purchase_quantity) AS sum_shares, purchase_price, purchase_date
    FROM shares WHERE id=(%s) AND portfolio_name=(%s)
    GROUP BY symbol, purchase_price, purchase_date;
    """, 
    (id, portfolio_name))

    names = db_select("SELECT portfolio_name FROM portfolios WHERE id=(%s)", (id,))

    if not names:
        flash("No portfolios detected - you have been redirected here automatically.", "primary")
        return redirect("/create")
    if not shares:
        flash(f"No shares detected in {portfolio_name} - you have been redirected here \
                automatically.", "primary")
        return redirect("/add")

    # https://blog.scottlogic.com/2020/10/09/charts-with-flexbox.html

    x = []

    # We want percentage and $ value
    purchase_overall = 0
    current_overall = 0

    for row in shares:

        date_nospace = row[3].strftime("%Y%m%d")
        # E.g. AAPL20210808
        unique_id = row[0] + date_nospace
        # Unique ID used:
        # 1. As a href to a share route for a more explicit breakdown
        # and also the ability to delete this single purchase from their portfolio
        # 2. As a variable name for session to store current_price rather than calling API again
        
        # https://stackoverflow.com/a/27611281

        # Try to see if this variable is in session
        try:
            # The data we are using only updates once per day (current price) which is slow enough
            # to not affect the user when storing and reusing it in session
            current_price = session[unique_id + '_current']
        
        except KeyError:
            # We are looking up symbols that exist in the database and have been validated before
            data = latestprice(row[0])
            # just to be sure
            if not data:
                return error_page(f"Symbol: {row[0]} has no latest price data", 403)
            
            # Get the latest price cast as float
            current_price = float(data["price"])

            # store in session
            session[unique_id + '_current'] = current_price

        purchase_price = float(row[2])

        # Difference in price * Quantity
        # to get $ change in value
        net_change = (current_price - purchase_price)*row[1]

        # The html will need all of these values
        # the values for 'contribution' and 'flex' are changed further down
        # 'flex' is used to give the flex value of each element in the horizontal stacked bar chart
        # 'contribution' is the contribution of that purchase to the whole portfolio as a percentage.
        # It also separates a gain from a loss because flex cannot take negative values
        
        # Why the duplication here?
        if net_change < 0:
            z = [{'unique_id': unique_id, 'flex': net_change, 'contribution': net_change}]
        else:
            z = [{'unique_id': unique_id, 'flex': net_change, 'contribution': net_change}]

        x += z

        current_overall += current_price*row[1]
        purchase_overall += purchase_price*row[1]

    net_overall = current_overall - purchase_overall
    net_overallpercent = round((net_overall/purchase_overall)*100, 2)

    # https://stackoverflow.com/a/73050
    # https://stackoverflow.com/a/46013151
    x = sorted(x, key=lambda a: a["flex"], reverse=True)
    # x when sorted 
    # [{'unique_id': 'a', 'flex': 16},  ...'flex': 10},  ..9},  ..5},  ..-14}]
    
    # Finding largest element to use as a parent to scale from
    i = len(x) - 1
    
    if x[0]["flex"] >= abs(x[i]["flex"]):
        y = abs(x[0]["flex"])
    else:
        y = abs(x[i]["flex"])

    # Iterate over the list x:

    # Prep j['flex'] for our html as a flex value ranging from 0 to 1
    # so j's bar size on the page relative to the parent is the same as
    # its relative gain/loss

    # j['contribution'] is used in the hover animation in css shown on the page
    # and also 
    # To get a purchase's contribution as a percentage:
    # divide net profit for individual purchase over overall purchase price
    for j in x:

        j["contribution"] = round((j["contribution"]/purchase_overall)*100, 2)

        if j["flex"] > 0:
            j["flex"] = round((j["flex"]/y), 4)
        else:
            j["flex"] = -1 * round((j["flex"]/y), 4)

    # portfolio_name is the argument passed to the route /portfolio/<portfolio_name>
    return render_template("portfolio.html", x=x, portfolio_name=portfolio_name, str=str,
                            net_overall=net_overall, net_overallpercent=net_overallpercent,
                            current_overall=current_overall, purchase_overall=purchase_overall)

@app.route("/delete", methods=["GET", "POST"])
@login_required
def delete():
    """User can delete from 1 to all of their portfolios"""

    id = session["user_id"]

    names = db_select("SELECT portfolio_name FROM portfolios WHERE id = (%s)", (id,))

    # User restricted from this page if he has no portfolios to delete
    if not names:
        flash("No portfolios detected - you have been redirected here automatically.", "primary")
        return redirect("/create")

    if request.method =="POST":

        # Gets a list of the values of the checked inputs from the form with name="portfolio"
        portfolios = request.form.getlist("portfolio")

        if not portfolios:
            return error_page("Select the portfolios you want to delete", 403)

        # For each selected portfolio, delete the corresponding rows in portfolio
        # This delete query will cascade to the shares table deleting any row there with this portfolio_name
        for portfolio in portfolios:
            db_commit("DELETE FROM portfolios WHERE id = (%s) AND portfolio_name = (%s)", (id, portfolio))
            flash(f"{portfolio} was successfully deleted!", "success")

        return redirect("/")
    else:
        return render_template("delete.html", names=names)

@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    """Add shares to a portfolio"""
    
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

    id = session["user_id"]

    if request.method =="POST":

        portfolio_name = request.form.get("portfolio_name")
        symbol = request.form.get("symbol")
        purchase_quantity = request.form.get("purchase_quantity")

        if not portfolio_name:
            return error_page("Choose a portfolio to add shares to", 403)
        
        # Internet explorer doesn't support input="date", degrades to input="text"
        # Native case with input="date"
        # https://stackoverflow.com/questions/10434599/get-the-data-received-in-a-flask-request
        purchase_date = request.form["purchase_date"]

        if not purchase_date:
            # Fallback for Iex browsers
            purchase_date = request.form["fallback_purchasedate"]

        if not purchase_date:
            return error_page("Enter a date", 403)
        
        try:
            # Convert string input to a date object so we can compare
            parsed_datetime = datetime.strptime(purchase_date, "%Y-%m-%d")
            parsed_date = parsed_datetime.date()
        # Error check mainly for Iex browsers when having to type a date
        except ValueError:
           return error_page("Date input must be valid and YYYY-MM-DD format")

        # Prevent the user from entering a date out of these bounds, today and 5 years ago
        if parsed_date < min_date:
            # TODO Test lower bound Live
            return error_page("This application is limited to only support historical \
                                price queries up to 5 years (1825 days) past", 403)
        if parsed_date > today:
            return error_page("You've entered a date in the future", 403)

        if not symbol:
            return error_page("Enter a symbol", 403)
        if not purchase_quantity:
            return error_page("Enter a quantity", 403)

        # https://pynative.com/python-check-user-input-is-number-or-string/
        try:
            # If casting as int fails we get a value error which means 
            # the input must be a float or a string
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

        # lookup() and scan()'s use here:
        # Checks the symbol exists at IEX, whilst checking there is a price for the 
        # given date which are then stored in the database.

        # only call API after all other checks so we are more efficient

        upper_symbol = symbol.upper()
        
        data = scan(upper_symbol, parsed_date)

        if not data:
            return error_page("No data found on the date entered for this symbol. \
                            Please refer to the link for supported symbols and check the date. \
                            You may be trying to access a date before the company was listed", 403)
        
        # data not empty

        # We want the scan date used for our database that matches this price
        # parsed_date is our input which is changed in scan
        scan_date = data["date"]
        purchase_price = data["price"]

        # All validity checks passed
        db_commit("""
        INSERT INTO shares
        (symbol, purchase_quantity, purchase_price, purchase_date, portfolio_name, id)
        VALUES (%s, %s, %s, %s, %s, %s);
        """,
        (upper_symbol, purchase_quantity, purchase_price, scan_date, portfolio_name, id))

        flash(f"{purchase_quantity} shares of {upper_symbol} bought on \U0001F4C5 {scan_date}, \
                saved to {portfolio_name}!", "success")

        # https://stackoverflow.com/questions/8552675/form-sending-error-flask
        # The buttons do the same thing except redirect to different pages
        if request.form["submit"] == "single":
            return redirect("/")
        else:
            return redirect("/add")

    # request.method =="GET"
    else:
        names = db_select("SELECT portfolio_name FROM portfolios WHERE id=(%s)", (id,))

        # User restricted from adding shares to portfolios if he has no portfolios
        if not names:
            flash("No portfolios detected - you have been redirected here automatically.", "primary")
            return redirect("/create")
        else:
            return render_template("add.html", today=today, min_date=min_date, names=names)

@app.route("/portfolio/<portfolio_name>/share/<unique_id>", methods=["GET", "POST"])
@login_required
def share(portfolio_name, unique_id):
    """
    Once a bar element is clicked in /portfolio/<portfolio_name>,
    the user is redirected here for:
    Date of purchase of the element
    Performance against itself in $ and % value
    Ability to delete the element
    """

    # https://stackoverflow.com/a/41369873

    id = session["user_id"]

    # https://docs.python.org/3/library/re.html#re.split
    a = re.split('(\d+)', unique_id)

    # a is now ['AAPL', '20210811']
    symbol = a[0]
    date = a[1]

    try:
        # Create the datetime object lookup() needs
        date_input = datetime.strptime(a[1], "%Y%m%d")
    
    except ValueError:
        return error_page("Date format should be YYYYMMDD", 403)

    # Create formatted string for the html
    # All dates will be 8 digit strings
    purchase_date = a[1][:4] + '-' + a[1][4:-2] + '-' + a[1][-2:]

    # Both Get and post need access to this query
    # Potential error if different prices on the same day but should only be a problem using sandbox
    rows = db_select("""
    SELECT symbol, SUM(purchase_quantity), purchase_price, purchase_date
    FROM shares
    WHERE id=(%s) AND symbol=(%s) AND purchase_date=(%s) AND portfolio_name=(%s)
    GROUP BY symbol, purchase_price, purchase_date;
    """,
    (id, symbol, date_input, portfolio_name))

    if not rows:
        return error_page(f"{portfolio_name} has no record of \
                            buying {symbol} on {date}", 403)
    
    if request.method=="POST":

        delete = request.form.get("delete")

        if delete == "True":
            
            db_commit("""
            DELETE FROM shares WHERE id=(%s) AND symbol=(%s) AND
            purchase_price=(%s) AND purchase_date=(%s) AND portfolio_name=(%s);
            """,
            (id, symbol, rows[0][2], date_input, portfolio_name))
            
            flash(f"Deleted all {symbol} shares bought on \U0001F4C5 {purchase_date} from \
                    {portfolio_name}!", "success")
            
            return redirect(f"/portfolio/{portfolio_name}")

    # GET    
    else:
        
        # Try fetch current price from session
        try:
            current_price = session[unique_id + '_current']

        # Doesn't exist in session
        except KeyError:
            # Get current price using latestprice()
            data = latestprice(symbol)

            if not data:
                return error_page(f"Symbol: {symbol} has no latest price data", 403)
            
            current_price = float(data["price"])

            # store current price in session
            session[unique_id + '_current'] = current_price

        # Cast as a float to subtract from current_price next line
        purchase_price = float(rows[0][2])

        # Difference in current and purchase price * SUM(purchase_quantity)
        dollar_change = (current_price - purchase_price) * rows[0][1]

        # Dollar change as a percentage of purchase price * SUM(purchase_quantity)
        percent_change = round(dollar_change / (purchase_price * rows[0][1]) * 100, 2)

        return render_template("share.html",
                                symbol=symbol,
                                purchase_date=purchase_date, 
                                portfolio_name=portfolio_name,
                                date=date,
                                dollar_change=dollar_change,
                                percent_change=percent_change,
                                current_price=current_price,
                                purchase_price=purchase_price,
                                quantity=rows[0][1])

@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    """Delete user's account details"""
    
    if request.method=="POST":
        
        id = session["user_id"]

        # Portfolios and shares tables have foreign keys with ON CASCADE DELETE
        # Referencing the users table as the root,
        # so we can delete all account information with this 1 line query
        db_commit("DELETE FROM users WHERE id=(%s)", (id,))

        # session still has a user_id
        session.clear()
        flash("All account information deleted!", "success")
        return redirect("/login")

    else:
        return render_template("account.html")