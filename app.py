import sqlite3
import requests
import pyodbc
import tempfile
import json
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from assistant import login_required, mk_int,reais

#API KEY
key = "2f05e94c"

#application
app = Flask(__name__)

# templates to auto-reload 
# from cs50 - pset8 finance 

app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached - from cs50 - pset8 finance
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["reais"] = reais

# Session will use filesystem, not cookies
app.config["SESSION_FILE_DIR"] = tempfile.mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

#create the database
conn = sqlite3.connect('investsimples.db', check_same_thread=False)
c = conn.cursor()

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "GET":
        try:
            if session["user_id"]:
                db = c.execute("SELECT username, cash FROM users WHERE id = (?)", ([session["user_id"]]))
                result = db.fetchone()
                user = result[0].capitalize()
                user_cash = result[1]
                return render_template("home.html", user=user, cash = user_cash)
        except (KeyError):
            return render_template("layout.html")
    else:
        # ADD CASH
        add_cash = request.form.get("Cash")
        add_cash = float(add_cash)
        db = c.execute("SELECT cash FROM users WHERE id = (?)", ([session["user_id"]]))
        result = db.fetchone()
        cash = result[0] + add_cash
        # UPDATE USERS CASH
        c.execute("""UPDATE users SET cash = {cash} WHERE id = {id}""".format (cash = cash, id = session["user_id"]))
        return redirect ("/")
        conn.commit()  

@app.route("/index")
@login_required
def index():
    #Show Portfólio    
    db = c.execute("SELECT *, SUM(shares) as Total_Shares FROM stocks WHERE user_id = (?) GROUP BY symbol",([session["user_id"]]))
    table = db.fetchall()
    cash = c.execute("SELECT cash FROM users WHERE id = (?)", ([session["user_id"]]))
    cash = cash.fetchone()
    conn.commit()  
    spentonshares = 0
    results = []
    #looping through the table
    for row in table:
        lst = list(row)
        symbol = lst[1]
        req = requests.get(f'https://api.hgbrasil.com/finance/stock_price?key={key}&symbol={symbol}')
        encontrar = req.json()
        lst[4] = encontrar["results"][symbol]["price"]
        price = lst[4]
        total_shares = lst[8]
        total = price * total_shares
        lst[5] = total
        spentonshares += int(total)
        results.append(lst)
        
    #total of cash that hasn't been spent yet
    cash_notspent = float((cash[0]))

    #total of cash user has
    total_cash = cash_notspent + spentonshares
    
    return  render_template("index.html", table = results, cash = reais(cash_notspent), total = reais(total_cash))

@app.route("/login", methods=["GET", "POST"])
def login():
    # LOG
    if request.method == "GET":
        return render_template("login.html")
    
    # SHOW AN ERROR MSG WHEN THE USER LEAVES AN BLANK SPACE 
    else:
        username = request.form.get("username")
        if not username:
            flash("Digite o seu nome de usuário!")
            return render_template("login.html")

        password = request.form.get("password")
        if not password:
            flash("Digite sua senha!")
            return render_template("login.html")
    
    # QUERY DB FOR USERNAME
        rowuser = c.execute("SELECT * FROM users WHERE username = (?)",
                            [username])
    # CHECK IF THE INPUT IS CORRECT
        rowconf = rowuser.fetchone()
        if rowconf == None or not check_password_hash(rowconf[3], password):
            flash("Usuário e/ou Senha Inválidos")
            return render_template("login.html")
    # Remember who logged in 
    # code from CS50 - Finance
        session["user_id"] = rowconf[0]

    # create db for stocks
        c.execute("CREATE TABLE if not exists stocks ('id' INTEGER PRIMARY KEY, 'Symbol' varchar(50), 'Name' VARCHAR(255), 'Shares' INTERGER, 'Price' DECIMAL(18,2),'Total' DECIMAL(38,2), 'Transacted' DATETIME, 'user_id' INTEGER)")

    # Redirect to main page:
        return redirect("/")
@app.route("/register", methods=["GET", "POST"])
def register():    
    # REGISTER USERS
    if request.method == "GET":
        return render_template("register.html")
      
    else:
        #CREATE TABLE IF THERE'S NOT
        c.execute("CREATE TABLE IF NOT EXISTS users ('id' INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, 'username' VARCHAR(50) NOT NULL, 'email' VARCHAR(250) NOT NULL, 'hash' VARCHAR(250) NOT NULL, 'cash' NUMERIC NOT NULL DEFAULT 1000.000)")
        # SHOW AN ERROR MSG WHEN THE USER LEAVES AN BLANK SPACE 
        username = request.form.get("username")
        if not username:
            flash("Digite o seu nome de usuário!")
            return render_template("register.html")

        email = request.form.get("email")
        if not email:
            flash("Digite o seu email!")
            return render_template("register.html")

        password = request.form.get("password")
        if not password:
            flash("Digite uma senha!")
            return render_template("register.html")

        elif (len(password) < 8):
            flash("Sua senha deve conter no mínimo 8 dígitos")
            return render_template("register.html")

        conf_password = request.form.get("conf_password")
        if not conf_password:
            flash("Confirme sua senha!")
            return render_template("register.html")

        elif (password != conf_password):
            flash("As senhas não são iguais!")
            return render_template("register.html")
        
        # CHECK IN THE DB IF THE USERNAME ALREADY EXISTS
        rows = c.execute("SELECT * FROM users WHERE username = (?)",
                          [username])
        rowcount = rows.fetchone()
        if rowcount is not None:
            flash("Nome de usuário já cadastrado!")
            return render_template("register.html")

        # CHECK IN THE DB IF THE EMAIL ALREADY EXISTS
        emailrow = c.execute("SELECT * FROM users WHERE email = (?)",
                          [email])
        emailcount = emailrow.fetchone()
        if emailcount != None:
            flash("Email já cadastrado!")
            return render_template("register.html")    
        
        # INSERT INTO DB
        password=generate_password_hash(password) 
        c.execute("INSERT INTO users (username,email, hash) VALUES (?, ?, ?)", (username, email, password))
        conn.commit() 
        flash("Registrado com sucesso!")
        return render_template("login.html")
        
        redirect ("/login")
#from cs50 - finance
@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")

@app.route("/cotar", methods=["GET", "POST"])
@login_required
def cotar():
    # QUOTATION
    if request.method == "GET":
        return render_template("cotar.html")
    
    else:
        #checking blank fields
        symbol = request.form.get("symbol").upper()
        
        if not symbol:
            flash("Coloque um código de ação")
            return render_template("cotar.html")
        
        #VARIABLES I'LL NEED
        req = requests.get(f'https://api.hgbrasil.com/finance/stock_price?key={key}&symbol={symbol}')
        encontrar = req.json()
        
        try:
            name = encontrar["results"][symbol]["name"]
            price = encontrar["results"][symbol]["price"]
            stock = encontrar["results"][symbol]["symbol"]
            update = encontrar["results"][symbol]["updated_at"]
        except (KeyError, TypeError, ValueError):
            # ERROR MSG
            flash("Ação não encontrada")
            return render_template("cotar.html")
        
    return render_template("cotado.html", nome = name, preço = price, simbolo = stock, atualização = update)

@app.route("/comprar", methods=["GET", "POST"])
@login_required
def comprar():
    """Buy shares of stock"""
    if request.method == "GET":
        return render_template("comprar.html")
    
    # GET STOCK AND QTD OF THAT STOCK
    else:
        symbol = request.form.get("symbol").upper()
        shares = request.form.get('shares')
        shares = mk_int(shares)
        req = requests.get(f'https://api.hgbrasil.com/finance/stock_price?key={key}&symbol={symbol}')
        encontrar = req.json()
    
        # ERROR MESSAGE
        if not symbol or shares < 1:
            flash("Digite um código de ação válido ou uma quantidade válida de ações que você deseja comprar.")
            return render_template("comprar.html")

        else: 
            try:
                name = encontrar["results"][symbol]["name"]
                price = encontrar["results"][symbol]["price"]
                stock = encontrar["results"][symbol]["symbol"]
                time = datetime.now()
                time = time.strftime('%d/%m/%Y %H:%M')
            except (KeyError, TypeError, ValueError):
                # ERROR MSG
                flash("Ação não encontrada")
                return render_template("comprar.html")

            #Query DB for the user's cash
            x = c.execute("SELECT cash  FROM users WHERE id = (?)", [session["user_id"]])
            cashrow = x.fetchone()
            cash = float(cashrow[0]) - ( price * shares)

            # Error if users does not have cash enough
            if cash < 0:
                flash("Saldo insuficiente para efetuar transação")
                return render_template("comprar.html")

            # Update user's cash
            c.execute("""UPDATE users SET cash = {cash} WHERE id = {id}""".format (cash = cash, id = session["user_id"]))

            #insert into DB
            c.execute("INSERT INTO stocks (Symbol, Name, Shares, Price, Total, Transacted, user_id) VALUES (?, ?, ?, ?, ?, ?, ?)", 
            (stock, name, shares, price, price * shares, time, session["user_id"]))

            # Saving History
            c.execute("CREATE TABLE if not exists history ('id' INTEGER PRIMARY KEY, 'Symbol' varchar(50), 'Name' VARCHAR(255), 'Shares' INTEGER, 'Price' DECIMAL(18,2),'Total' DECIMAL(38,2), 'Transacted' DATETIME, 'user_id' INTEGER, 'Activity' VARCHAR(50))")
            c.execute("INSERT into history (Symbol, Name, Shares, Price, Total, Transacted, user_id, Activity) VALUES (?, ?, ?, ?, ?, ?, ?, 'Comprou')", 
            (stock, name, shares, price, price * shares, time, session["user_id"]))

            #Save DB
            conn.commit() 

            # Redirect
            flash("Compra feita com sucesso")
            return render_template("comprar.html")

@app.route("/vender", methods=["GET", "POST"])
@login_required
def vender():
    """Sell shares of stock"""
    if request.method == "GET":
        return render_template("vender.html")

    # GET STOCK AND QTD OF THAT STOCK
    else:
        symbol = request.form.get("symbol").upper()
        shares = request.form.get('shares')
        shares = mk_int(shares)
        req = requests.get(f'https://api.hgbrasil.com/finance/stock_price?key={key}&symbol={symbol}')
        encontrar = req.json()

        # ERROR MESSAGE
        if not symbol or shares < 1:
            flash("Digite um código de ação válido ou uma quantidade válida de ações que você deseja vender.")
            return render_template("vender.html")

        else: 
            try:
                name = encontrar["results"][symbol]["name"]
                price = encontrar["results"][symbol]["price"]
                stock = encontrar["results"][symbol]["symbol"]
                time = datetime.now()
                time = time.strftime('%d/%m/%Y %H:%M')
                Qtdrow = c.execute("""SELECT shares, SUM(shares) as Qtd FROM stocks WHERE user_id = {id} and symbol = '{symbol}'""".format(id = session["user_id"], symbol = symbol))
                qtd = Qtdrow.fetchone()
                Quantity = int(qtd[1])

                if shares > Quantity:
                    flash("Você não possui esta quantidade de ações desta empresa")
                    return render_template("vender.html")

                #Selling
                else:
                    #Query for cash
                    rs = c.execute("SELECT cash  FROM users WHERE id = (?)", [session["user_id"]])
                    cashrow = rs.fetchone()
                    cash = float(cashrow[0]) + (price * shares)

                # Update user's cash
                c.execute("""UPDATE users SET cash = {cash} WHERE id = {id}""".format (cash = cash, id = session["user_id"]))

                 #insert into DB
                c.execute("INSERT INTO stocks (Symbol, Name, Shares, Price, Total, Transacted, user_id) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                (stock, name, -shares, price, -price * shares, time, session["user_id"]))

                 # Saving History
                c.execute("INSERT into history (Symbol, Name, Shares, Price, Total, Transacted, user_id, Activity) VALUES (?, ?, ?, ?, ?, ?, ?, 'Vendeu')", 
                (stock, name, shares, price, price * shares, time, session["user_id"]))

                # delete if no stocks left
                table = c.execute("""SELECT *, SUM(shares) as Total_Shares FROM stocks WHERE user_id = {id} and symbol = '{symbol}' GROUP BY symbol""".format(id = session["user_id"], symbol = symbol))
                table2 = table.fetchall()
                for row in table2:
                    if row[8] <= 0:
                        c.execute("DELETE FROM stocks WHERE symbol = (?)", [symbol])
                 #Save DB
                conn.commit() 

                # Redirect
                flash("Venda feita com sucesso")
                return render_template("vender.html")

            except (KeyError, TypeError, ValueError):
                # ERROR MSG
                flash("Ação não encontrada")
                return render_template("vender.html")

@app.route("/historico")
@login_required
def historico():
    """Show history of transactions"""
    htable = c.execute("SELECT * FROM history WHERE user_id = (?)",  [session["user_id"]])
    history = htable.fetchall()
    return render_template("historico.html", table = history)

@app.route("/alterarsenha", methods=["GET", "POST"])
def alterarsenha():
    if request.method == ("GET"):
        return render_template("alterarsenha.html")
    
    # change password
    else:
        username = request.form.get("username")
        if not username:
            flash("Digite o seu nome de usuário!")
            return render_template("alterarsenha.html")

        password = request.form.get("password")
        if not password:
            flash("Digite sua antiga senha!")
            return render_template("alterarsenha.html")

        new_password = request.form.get("new_password")
        if not new_password:
            flash("Digite uma nova senha!")
            return render_template("alterarsenha.html")
        
        elif new_password == password:
            flash("Sua nova senha não pode ser igual a anterior")
            return render_template("alterarsenha.html")

        elif (len(new_password) < 8):
            flash("Sua nova senha deve conter no mínimo 8 dígitos")
            return render_template("alterarsenha.html")

        confnew_password = request.form.get("confnew_password")
        if not confnew_password:
            flash("Confirme sua nova senha!")
            return render_template("alterarsenha.html")
 
        elif (new_password != confnew_password):
            flash("As senhas não são iguais!")
            return render_template("alterarsenha.html")

        # CHECK IN THE DB IF THE USERNAME EXISTS
        rows = c.execute("SELECT * FROM users WHERE username = (?)",
                          [username])
        # CHECK IF THE INPUT IS CORRECT
        rowconf = rows.fetchone()
        if rowconf == None or not check_password_hash(rowconf[3], password):
            flash("Usuário e/ou Senha Inválidos")
            return render_template("alterarsenha.html")
        
        # CHANGE PASSWORD IN DB
        password=generate_password_hash(new_password) 
        c.execute("""UPDATE users SET hash = '{password}' WHERE username = '{username}'""".format(password = password, username = username))
        conn.commit() 
        flash("Senha alterada com sucesso!")
        return render_template("login.html")
        redirect ("/login")
