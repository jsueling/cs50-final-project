import os
import requests
import urllib.parse

from flask import redirect, session, render_template 
from functools import wraps

def error_page(message, code=400)
    """Returns a message on the error and what the user should do"""
    return render_template("error_page.html", code=code, message=message), code

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