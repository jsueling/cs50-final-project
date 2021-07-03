import os

from flask import Flask, render_template, redirect, request, session

from functions import error_page, login_required, lookup, usd

app = FLask(__name__)

# https://stackoverflow.com/questions/9508667/reload-flask-app-when-template-file-changes
# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached after every request
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# https://flask.palletsprojects.com/en/2.0.x/templating/#registering-filters
app.jinja_env.filters["usd"] = usd
# This filter is now registered for use in html files

@app.route("/")
def index():
    return render_template("index.html")