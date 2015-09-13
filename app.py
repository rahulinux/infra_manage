#!/usr/bin/env python

from flask import Flask
from flask import Flask, render_template, request, json
from flask.ext.mysql import MySQL
from werkzeug import generate_password_hash, check_password_hash

app = Flask(__name__)

mysql = MySQL()

#MySQL Configuration
app.config['MYSQL_DATABASE_USER'] = 'rahul'
app.config['MYSQL_DATABASE_PASSWORD'] = 'x'
app.config['MYSQL_DATABASE_DB'] = 'infra_manage'
app.config['MYSQL_DATABASE_HOME'] = 'localhost'
mysql.init_app(app)

@app.route("/")
def main():
   return render_template("index.html") 


@app.route("/signUp",methods=['POST'])
def signUp():
   try: 
      _name = request.form['inputName']
      _email = request.form['inputEmail']
      _password = request.form['inputPassword']

      if _name and _email and _password: 
        conn = mysql.connect()
        cursor = conn.cursor()
        
        # Created hashed password
        _hashed_password = generate_password_hash(_password)
        cursor.callproc('sp_createUser',(_name,_email,_hashed_password))
        data = cursor.fetchall()

        if len(data) is 0:
            conn.commit()
            return json.dumps({'message':'User created Successfully !'})
        else:
            return json.dumps({'error':str(data[0])})

      else:
          return json.dumps( { "html":"<span>Enter the requred fields</span>"} )   
   except Exception as e:
      return json.dumps({'error':str(e)})
   finally:
      cursor.close()
      conn.close() 


@app.route("/showSignIn")
def showSignin():
    return render_template('signin.html')

@app.route("/validateLogin",methods=['POST'])
def validateLogin():
  try:
    _username = request.form['inputEmail']
    _password = request.form['inputPassword']

    if _username and _password:
      conn = mysql.connect()
      cursor = conn.cursor()
      cursor.callproc('sp_validateLogin',(_username,))
      data = cursor.fetchall()
      if len(data) > 0:
         if check_password_hash(str(data[0][3]),_password):
            return redirect('/userHome')
         else:
            return render_template('error.html',error='Wrong Email Address or Password')
      else:
            return render_template('error.html',error='Wrong Email address or Password')
  except Exception as e:
    return render_template('error.html',error=str(e))
  finally:
    cursor.close()
    conn.close()

@app.route("/userHome")
def userHome():
  return render_template("userHome.html")
 
@app.route("/showSignUp")
def showSignUp():
     return render_template("signup.html")

if __name__ == "__main__":
   app.run(debug=True)
