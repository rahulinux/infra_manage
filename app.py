#!/usr/bin/env python

from flask import Flask, render_template, request, json, redirect, session
from flask.ext.mysql import MySQL
from werkzeug import generate_password_hash, check_password_hash
from ansible import inventory 
import ansible.runner 

app = Flask(__name__)
app.secret_key = 'secret'
mysql = MySQL()

#MySQL Configuration
app.config['MYSQL_DATABASE_USER'] = 'rahul'
app.config['MYSQL_DATABASE_PASSWORD'] = 'x'
app.config['MYSQL_DATABASE_DB'] = 'infra_manage'
app.config['MYSQL_DATABASE_HOME'] = 'localhost'
mysql.init_app(app)

# Inventory file configes
app.config['inv'] = './hosts'
inv = None 

@app.route("/")
def main():
   return render_template("index.html") 

@app.route("/showSignIn")
def showSignin():
    return render_template('signin.html')

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
            return '/showSignIn' 
            #return json.dumps({'message':'User created Successfully !'})
        else:
            return json.dumps({'error':str(data[0])})

      else:
          return json.dumps( { "html":"<span>Enter the requred fields</span>"} )   
   except Exception as e:
      return json.dumps({'error':str(e)})
   finally:
      cursor.close()
      conn.close() 



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
            session['user'] = data[0][0]
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
  if session.get('user'):
     return render_template("userHome.html")
  else:
     return render_template('error.html',error = 'Unauthorized Access')

@app.route("/logout")
def logout():
    session.pop('user',None)
    return redirect('/')
 
@app.route("/showSignUp")
def showSignUp():
     return render_template("signup.html")


def server_status():
    print("Server_Status_Run")
    global inv
    inv = inventory.Inventory(app.config['inv'])
    results = ansible.runner.Runner(
       pattern = '*', forks=10,
       inventory = inv,
       transport = 'local',
       module_name = 'shell', module_args='nc -vzw1 {{ inventory_hostname }} 22'
    ).run()
    return results 

## Features
@app.route("/start-stop-servers")
def startstopservers():
  global inv
  if session.get('user'):
     if inv is None:
        inv = server_status()
     return render_template("start-stop-servers.html",inv=inv)
  else:
     return render_template('error.html',error = 'Unauthorized Access')



@app.route("/start-servers",methods=['POST'])
def start_servers():
     value = request.form.getlist('favorite[]')
     inv = inventory.Inventory(app.config['inv'])
     for host in value:
        results = ansible.runner.Runner(
          pattern = host, forks=10,
          inventory = inv,
          transport = 'local',
          module_name = 'debug', module_args='msg={{ project }}'
        ).run()
        print(results['contacted'].items())
     #print request.form.getlist('favorite[]')
     return json.dumps({'value':str(value)})
     #return redirect("/start-stop-servers")


@app.route("/stop-servers",methods=['POST'])
def stop_servers():
    value = request.form.getlist('favorite[]')
    return json.dumps({'value':str(value)})

@app.route("/start-all-servers",methods=['POST'])
def start_all_servers():
    value = request.form.getlist('favorite[]')
    return json.dumps({'value':str(value)})
 
@app.route("/stop-all-servers",methods=['POST'])
def stop_all_servers():
    value = request.form.getlist('favorite[]')
    return json.dumps({'value':str(value)})

@app.route("/reload-servers")
def reload_servers():
   global inv
   inv = server_status()
   return redirect("/start-stop-servers")

@app.route("/add-servers")
def add_servers():
    return render_template("add-servers.html")

@app.route("/add-inventory",methods=['POST'])
def add_inventory():
     server_ip = request.form['serverIP']
     instance_id = request.form['instanceId']
     return json.dumps({ 'serverIP': server_ip, 'instance_id': instance_id} )
        
 
if __name__ == "__main__":
   app.run(host="0.0.0.0",debug=True)
