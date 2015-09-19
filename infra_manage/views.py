#!/usr/bin/env python


from infra_manage import app 
from flask import render_template, request, json, redirect, session 
from flask.ext.mysql import MySQL 
from werkzeug import generate_password_hash, check_password_hash 
from ansible import inventory  
import ansible.runner  
import time  

mysql = MySQL() 
mysql.init_app(app) 
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
    inv = inventory.Inventory(app.config['INV'])
    results = ansible.runner.Runner(
       pattern = '*', forks=10,
       inventory = inv,
       transport = 'local',
       module_name = 'shell', module_args='nc -vzw1 {{ inventory_hostname }} 22 2>&1'
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

@app.route("/reload-servers")
def reload_servers():
   global inv
   inv = server_status()
   return redirect("/start-stop-servers")


@app.route("/start-servers",methods=['POST'])
def start_servers():
     value = request.form.getlist('favorite[]')
     inv = inventory.Inventory(app.config['INV'])
     for host in value:
        results = ansible.runner.Runner(
          pattern = host, forks=10,
          inventory = inv,
          transport = 'local',
          module_name = 'debug', module_args='msg={{ project }}'
        ).run()
        print(results['contacted'].items())
     reload_servers()
     return "/start-stop-servers"


@app.route("/stop-servers",methods=['POST'])
def stop_servers():
    value = request.form.getlist('favorite[]')
    reload_servers()
    return "/start-stop-servers"

@app.route("/start-all-servers",methods=['POST'])
def start_all_servers():
    value = request.form.getlist('favorite[]')
    reload_servers()
    return "/start-stop-servers"
 
@app.route("/stop-all-servers",methods=['POST'])
def stop_all_servers():
    value = request.form.getlist('favorite[]')
    reload_servers()
    return "/start-stop-servers"


@app.route("/add-servers")
def add_servers():
  if session.get('user'):
     return render_template("add-servers.html")
  else:
     return render_template('error.html',error = 'Unauthorized Access')

@app.route("/add-auto-start")
def auto_start():
  if session.get('user'):
     return render_template("add-auto-start.html")
  else:
     return render_template('error.html',error = 'Unauthorized Access')

@app.route("/del-servers",methods=['POST'])
def del_servers():
    value = request.form.getlist('favorite[]')
    f = app.config['INV']
    input = open(f,"r")
    lines = input.readlines()
    input.close()
   
    output = open(f,'wb')
    print value
    for line in lines:
       if any(host in line for host in value ):
          print "Deleted :", line
       else:
          output.write(line)
    output.close() 
    reload_servers()
    return "/start-stop-servers"
     

@app.route("/add-inventory",methods=['POST'])
def add_inventory():
   try:
     data = {}
     form = request.form
     for key,value in form.iterlists():
          for n in range(len(value)):
               if n in data.keys():
                  data[n].update({key: value[n]})
               else:
                  data[n] = {key : value[n]}
     for i in data:
         server_ip = data[i]['serverIP'] 
         instance_id = data[i]['InstanceID'] 
         owner = data[i]['Owner'] 
         email_id = data[i]['Email'] 
         project = data[i]['Project']
         line = '{0} project={1} owner={2} email_id={3} instance_id={4}'.format(server_ip,project,owner,email_id,instance_id)
         args = 'dest={0} regexp=^{1} line="{2}"'.format( app.config['INV'],server_ip, line)
         result = ansible.runner.Runner(
              transport = 'local',
              module_name = 'lineinfile',
              module_args = args 
 
              
         ).run()
     reload_servers()     
     return "/start-stop-servers" 
   except Exception as e:
     return json.dumps({'error':str(e)})
        
 
if __name__ == "__main__":
   app.run(host="0.0.0.0",debug=True)
