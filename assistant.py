import requests
import json
from functools import wraps
from flask import g, request, redirect, url_for, session
import urllib.parse


#decorar caminho sempre que precisar que o usuário faça login
# fonte:https://flask.palletsprojects.com/en/1.0.x/patterns/viewdecorators/
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

#convert string to int even if string is empty
#src="https://stackoverflow.com/questions/2941681/how-to-make-int-parse-blank-strings/2941975"
def mk_int(s):
    s = s.strip()
    return int(s) if s else 0

# convert to reais
def reais(value):
    return ("R$ {:.2f}".format(value))
