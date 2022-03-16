# MyPortfolios

#### Video Demo: https://www.youtube.com/watch?v=5i8XTZZDeNs

#### Link to deployed application: http://jsl-cs50-final-project.herokuapp.com/

#### https://cs50.harvard.edu/x/2021/

#### Overview:

MyPortfolios is a web-based application using JavaScript, Python, and SQL. I used Bootstrap as a front-end web framework and Flask as the back-end. The app is deployed to Heroku using PostgreSQL as a database. The main inspirations for the app came from CS50's Finance app and my own experience of using investment platforms. I took ideas from CS50's Finance app a step further towards portfolio visualisation which I personally think holds alot of value when deciding which shares you want to buy or sell but also in adding clarity to your portfolio progress. So that's the main purpose of the app with a focus on relative performance between share purchases. It aims to achieve this through the main feature which is the stacked horizontal bar chart of the user's current portfolio that aggregates all share purchases. It's generated using CSS and HTML only. The bar elements are divs that represent each share purchase made in the portfolio. The bar is dynamically generated and shows relative performance between constituents from each purchase date to today. This is done by dividing each element's gain/loss by the largest element's gain/loss and assigning that value to the flex value of its corresponding HTML div. The flex value of an element is increased when the user mouseovers it which makes it grow in size on the page and other bar elements shrink. The app uses the IEX cloud API to fetch current and historical prices of shares. The user can decide how they want to use the app. They can test out hypothetical portfolios or mimic their own portfolio in the real world.

The inspiration for the horizontal stacked bar chart:
https://blog.scottlogic.com/2020/10/09/charts-with-flexbox.html

If I were to continue the project I would add to the portfolio visualisation by allowing the user to see their portfolio progress over time in some way. An idea that I had was to take the earliest share purchase date for a portfolio, count the number of days since purchase, divide that by a number (depends on how specific we want to be/how it will look in a graph) say 10 for example. For each of the 10 dates, check if the share was bought before that date and call the API for a historical price if it was, summing the total portfolio value at each point in time. We could then plot this using a line graph for example. Its not perfect because we would be assuming that the user held all his shares and didn't sell. For that we would likely need to incorporate a history of sales and cash into our model.

#### Files explained:

The application needs DATABASE_URL and API_KEY as environment variables to run. Both are stored in my Heroku config variables. During development in Visual Studio Code, I modified the app to run locally using a database.ini file and a config.py file to access my database. For the API_KEY I used the dotenv module to load the env file containing it.

functions.py contains most of the functions that application.py depends on.

If anything happens in my application that I want to prevent or prevent the user from doing I can use error_page() to stop it and return a message on what to do alongside an error code. db_select() allows me to run a SELECT query on my database using the psycopg2 module without having to repeat code opening and closing the connection. I then decided that I needed a separate query function, db_commit(), because in SELECT queries I want to return results using cur.fetchall() whereas with CREATE, INSERT, UPDATE, DELETE queries I don't need the results but I do need to call conn.commit() to update the database. 

lookup() is used to get the price of the symbol on a date using the IEX API where symbol and date are the 2 inputs to the function.

scan() is an extension of but is also dependent on lookup(). If the historical price on the date given doesn't exist for any reason, then scan() will call lookup() on more days. For example, a holiday where the stock exchange is closed. It also accommodates weekend inputs by calling lookup() on the nearest weekday. I think this is helpful to the user instead of returning an error_page() asking them to choose another date.

Since my application depended on calling scan for a current price, the portfolio route broke when scan returned none so the user could do nothing but delete his portfolio to stop the error or wait until the next day. I found this problem trying to access a portfolio that tried to get current price when today's date was a saturday and friday had no data. Instead of hard coding the days where this happens or extending if statements to scan more days, I created latestprice() that uses a separate API call that returns the latest price for the last available trading day.

login_required is a function decorator that only allows the function it decorates to run if a "user_id" is in session otherwise redirecting the user to login, where login will create a user_id in session. usd() is needed in application.py to declare a jinja filter to convert number values into dollar currency values. The jinja filter is then used in the HTML files.

application.py

The index route shows the list of portfolios that exist in his portfolios table as buttons which redirect to each respective portfolio. If the user has no portfolios in the table, a welcome message is displayed.

/register hashes the password inputted and creates a new user in the users table after some checks, logs the user in and redirects to the index. register.html uses tooltip.js in a script tag which is taken from the bootstrap docs, this allows me to show a tooltip which notifies the user that the 2nd password box is for a confirmation password

/login checks the forms the user submits against the database and logs in if successful. It uses check_password_hash() against the hash in the database to be safe.

/logout clears user_id from session and redirects to /login

/create is how the user creates new portfolios. It does some checks and inserts the new portfolio into the table portfolios

/portfolio/<portfolio_name> takes portfolio_name as part of its url. As said before this is the horizontal stacked bar chart we are creating. We first declare empty list x and 2 variables to count our overall purchase price and overall current price. Then, for every row in the shares query(which is grouping purchases of the same symbol, purchase price and bought on the same date):

- First, create a try except that stops the API from being called more than once for a given share purchase by storing the results in session

- Create a dictionary z which stores that share purchase's unique id and 2 other keys, 'flex' and 'contribution'. Their values will be recalculated using net_change later.

- While iterating over shares we are keeping a count of the total purchase price and total current price for later

We sort the list x using the key 'flex' once all dictionaries have been added and find the largest net_change by absolute value. Then, store it.

Finally, prepare the list of dictionaries, x, for our uses in the HTML. We want positive flex values between 0 and 1 scaled from the largest net_change, y, so we divide all 'flex' values by the 'flex' of y whilst making all values absolute. 'contribution' is the percentage that the individual share purchase contributed to net overall profit of the portfolio. To calculate we this we divide individual net profit of share purchase by overall portfolio purchase price. To get a better idea of what I'm doing for this calculation, to get the total portfolio net profit as a percentage is the same as summing all individual net profits and dividing by the total purchase price. From the perspective of how it looks on the page, I thought it made the most sense to show contribution as a percentage on mouseover because I wanted to show percentage gain for their overall portfolio alongside it. The user can easily understand what they are looking at when they see that the sum of percentage contributions of individual share purchases is equal to the total portfolio percentage gain.

portfolio.html first shows the net profit of the portfolio in dollar and percentage terms next to an upward or downward arrow depending on whether the net profit was positive or negative, they are colored green or red depending on this too. We then iterate over the list x, creating a div, coloring it red or green depending on loss or gain. Then, within that div, creating data-id string used in portfolio_styles.css, creating data-link used in portfolio.js and finally setting inline style flex values for each div. portfolio.html then has a modal button from bootstrap that gives a short tutorial on the page, telling the user that they can mouseover and click the bar elements. Finally, an accordion from bootstrap that gives a breakdown of net profit for that portfolio in the first collapse and a second collapse with a short explanation about how a share's contribution to net profit of a portfolio differs from net profit of a share. The user may not want this much information so a collapse is useful here.

I debated between whether to scale the divs to be either absolute or relative in size. The problem is that we are scaling off the largest gain/loss in a users portfolio which means that the bar always appears the same size on the page which can look strange. Ultimately I decided to use relative scaling based on 2 things:

1. Using absolute sizing, extreme gains/losses can also look strange. I don't know the size of the user's portfolio losses or gains beforehand so I can't estimate how much space they need easily.

2. The largest gain or loss is arguably the most important detail to the user in tracking their relative portfolio progress.

portfolio.js finds every item on the page with class="bar" and adds an onclick eventlistener that sets the window.location.href to the value of the attribute data-link. In short, redirecting to the share purchase corresponding to the element the user clicked on.

portfolio_styles.css contains all the styling necessary for the horizontal stacked bar including colors, transition and pointer on hover, setting flex on hover to grow that element and shrink others, show the data-id string in that element's content on hover, increase opacity on hover.

/delete first gets a list of all portfolios that user has from the portfolios table and displays it to the user. Then, for each checked input the user returns from the form, call db_commit() to delete that portfolio from portfolios

delete.js basically doesn't let the user submit without clicking at least 1 input, checked() will break the for loop and enable the button as soon as 1 input is checked. checked() is run after every click of any input on the page.

I included confirm.js as a script in any html that has a delete button. It prompts the user 'Are you sure?' when the delete button is clicked and if confirm returns false (clicked cancel), then stop the current action of the button.

In /add the user is presented with a radio list of portfolios he can add to and a form to fill. We check for valid user inputs, make sure the date is between now and 5 years past, make sure the quantity is a positive integer, the symbol has data from the IEX API and finally add the share to the user's portfolio with the option to add 1 or add more shares. In add.html I added support for Internet Explorer browsers for input type="date" copied from  https://developer.mozilla.org/en-US/docs/Web/HTML/Element/input/date#javascript.

add.js creates a dummy variable and tries to set its type to date, if it falls back to type="text" then hide the nativedatepicker and show the fallbackdatepicker. I also adjusted my /add to accommodate text inputs. The date picker in add.html is also modified in add.js. If you try to submit a weekend date, you will get a confirm message that asks you if you still want to continue, for reasons explained earlier. The user can still choose to continue, lookup() will be called on the nearest weekday from scan(), but the user is aware now that the date chosen will be from the nearest weekday, not the date the inputted.

In /portfolio/<portfolio_name>/share/<unique_id>, We return a page for the share purchase based on the unique_id in the url, first checking it exists in the user's shares table. We display data about that specific share purchase including the date and performance against itself in dollar and percentage value. Lastly, giving the user the ability to delete that purchase or return to the previous page

In /account the user simply has the option to remove all his data from every table. This can be done with one query because portfolio and shares tables were created using the foreign key id from users that has the property ON DELETE CASCADE

layout.html is the basis for all my html files. It contains dependencies for bootstrap, fontawesome arrows, favicon.ico moneybag icon and css files in the <head> tag. It also contains the navbar from Bootstrap. I edited the nav-links to have the attribute active based on the current page the user is on. The navbar shows different links based on whether the user is logged in or not. I added support for flashed messages that displays a bootstrap alert that can be a success or primary alert. Finally I include disabled.js to be used in all html files which is copied from https://github.com/whatwg/html/issues/5312. This essentially prevents double or multiple form submission by, on first submission, adding 'is-submitting' class to the form. Subsequent submissions will then contain 'is-submitting' class which triggers a preventDefault which stops the form from following its default submit action.

Procfile and Procfile.windows are heroku specific files that tell heroku how to run my application, online and locally

.gitignore for sensitive files that contain information like my API_KEY

.flaskenv contains the FLASK_APP environment variable required by flask according to the docs

styles.css contains all other styling choices including width and max-width to make content responsive and a footer locked to the bottom of the screen.

requirements.txt contains all the modules and their versions used by this directory which is useful if someone is trying to recreate the project from another machine

#### My create table commands:

CREATE TABLE IF NOT EXISTS users (
id SERIAL PRIMARY KEY,
username VARCHAR(50) UNIQUE NOT NULL,
password VARCHAR(200) NOT NULL
);

CREATE TABLE IF NOT EXISTS shares (
symbol VARCHAR(50) NOT NULL,
purchase_quantity INT NOT NULL CHECK (purchase_quantity > 0),
purchase_price NUMERIC NOT NULL CHECK (purchase_price > 0),
purchase_date DATE NOT NULL,
portfolio_name VARCHAR(50) REFERENCES portfolios (portfolio_name) ON DELETE CASCADE ON UPDATE CASCADE,
id INT REFERENCES users (id) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS portfolios (
id INT REFERENCES users (id) ON DELETE CASCADE ON UPDATE CASCADE,
portfolio_name VARCHAR(50) UNIQUE NOT NULL
);
