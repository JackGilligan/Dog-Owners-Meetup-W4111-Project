#!/usr/bin/env python2.7

"""
Columbia W4111 Intro to databases
Example webserver

To run locally

    python server.py

Go to http://localhost:8111 in your browser


A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""

import os
import pandas as pd

from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, session, flash

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)



# XXX: The Database URI should be in the format of: 
#
#     postgresql://USER:PASSWORD@<IP_OF_POSTGRE_SQL_SERVER>/<DB_NAME>
#
# For example, if you had username ewu2493, password foobar, then the following line would be:
#
#     DATABASEURI = "postgresql://ewu2493:foobar@<IP_OF_POSTGRE_SQL_SERVER>/postgres"
#
# For your convenience, we already set it to the class database

# Use the DB credentials you received by e-mail

# DB_USER = "jmg2338"
# DB_PASSWORD = "09AcAIiCnF"
DB_USER = "ms5488"
DB_PASSWORD = "ihtXu8PHsp"
DB_SERVER = "w4111.cisxo09blonu.us-east-1.rds.amazonaws.com"
DATABASEURI = "postgresql://"+DB_USER+":"+DB_PASSWORD+"@"+DB_SERVER+"/w4111"

#
# This line creates a database engine that knows how to connect to the URI above
#
engine = create_engine(DATABASEURI)


# Here we create a test table and insert some values into it
engine.execute("""DROP TABLE IF EXISTS test;""")
engine.execute("""CREATE TABLE IF NOT EXISTS test (id serial, name text);""")
engine.execute("""INSERT INTO test(name) VALUES ('grace hopper'), ('alan turing'), ('ada lovelace');""")



@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request 
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request

  The variable g is globally accessible
  """
  try:
    g.conn = engine.connect()
  except:
    print "uh oh, problem connecting to database"
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass


#
# @app.route is a decorator around index() that means:
#   run index() whenever the user tries to access the "/" path using a GET request
#
# If you wanted the user to go to e.g., localhost:8111/foobar/ with POST or GET then you could use
#
#       @app.route("/foobar/", methods=["POST", "GET"])
#
# PROTIP: (the trailing / in the path is important)
# 
# see for routing: http://flask.pocoo.org/docs/0.10/quickstart/#routing
# see for decorators: http://simeonfranklin.com/blog/2012/jul/1/python-decorators-in-12-steps/
#

person_id = 0
person_name = "JJ"

@app.route('/')
def index():
  """
  request is a special object that Flask provides to access web request information:

  request.method:   "GET" or "POST"
  request.form:     if the browser submitted a form, this contains the data in the form
  request.args:     dictionary of URL arguments e.g., {a:1, b:2} for http://localhost?a=1&b=2

  See its API: http://flask.pocoo.org/docs/0.10/api/#incoming-request-data
  """

  # debugging
  print '\n'
  print "REQUEST ARGUMENTS:"
  print request.args

  print '\n'
  print "SESSION ARGUMENTS:"
  print person_id
  print person_name
  print session.get('logged_in')

  #
  # example of a database query
  #
  if not session.get('logged_in'):
    return render_template("Login.html")
  else:

    cursor = g.conn.execute(
      """
      SELECT
        O.picture, D.picture1, D.picture2, D.name, D.breed,
        D.age, D.weight, D.play_intensity, O.phone, O.email
      FROM
        owner O
        LEFT JOIN dog_owned_by DOB on O.owner_id = DOB.owner_id
        LEFT JOIN dog D on DOB.dog_id = D.dog_id
      LIMIT 10
      """
    )

    #names = []
    #for result in cursor:
    #  names.append(result)  # can also be accessed using result[0]
    #cursor.close()

    df = pd.DataFrame(cursor.fetchall())
    df.columns = cursor.keys()
    cursor.close()
    context = dict(
      data = [df.to_html(classes='table', header="true", index=False)]
    )

    return render_template("index.html", **context)

#
# This is an example of a different path.  You can see it at
# 
#     localhost:8111/another
#
# notice that the function name is another() rather than index()
# the functions for each app.route needs to have different names
#
@app.route('/EnterInfo')
def EnterInfo():
  return render_template("EnterInfo.html")

@app.route('/locations')
def locations():
    locations = []
    cursor = g.conn.execute(
      """
      SELECT L.name, L.address, tmp.num_meetings
      FROM 
        (
          SELECT OM.location_id, COUNT(*) as num_meetings
          FROM owner_meet as OM
          GROUP BY OM.location_id
        ) as tmp
        LEFT JOIN location as L ON tmp.location_id = L.location_id
      ORDER BY tmp.num_meetings DESC
      LIMIT 5;
      """
    )
    for result in cursor:
      locations.append(result)
    cursor.close()
    context = dict(data = locations)
    return render_template("Locations.html", **context)

@app.route('/messages')
def messages():

    # debugging
    print '\n'
    print "REQUEST ARGUMENTS:"
    print request.args

    print '\n'
    print "SESSION ARGUMENTS:"
    print person_id
    print person_name
    print session.get('logged_in')

    messages = []
    cursor = g.conn.execute(
      """
      SELECT OC.time, O1.name as sender, O2.name as receiver, OC.message
      FROM
        owner_contact as OC
        LEFT JOIN owner as O1 ON OC.sender = O1.owner_id
        LEFT JOIN owner as O2 ON OC.receiver = O2.owner_id
      WHERE 
        OC.sender = %s or
        OC.receiver = %s
      ORDER BY OC.time;
      """,
      (person_id, person_id)
    )

    df = pd.DataFrame(cursor.fetchall())
    df.columns = cursor.keys()
    cursor.close()
    context = dict(
      data = [df.to_html(classes='table', header="true", index=False)]
    )

    return render_template("Messages.html", **context)
    

#@app.route('/Home')
#def Home():
#  return render_template("index.html")


# Example of adding new data to the database
@app.route('/add', methods=['POST'])
def add():
  name = request.form['name']
  print name
  cmd = 'INSERT INTO test(name) VALUES (:name1)';
  g.conn.execute(text(cmd), name1 = name);
  return redirect('/')


@app.route('/login', methods=['POST'])
def login():
    global person_id
    global person_name
    login_credential = request.form['email']
    cursor = g.conn.execute("SELECT email FROM owner")
    emails = []
    for result in cursor:
      emails.append(result['email'])  # can also be accessed using result[0]
    cursor.close()
    if login_credential in emails:
      cursor = g.conn.execute("SELECT owner_id, name FROM owner WHERE email = " + "'" + str(login_credential) + "'")
      for result2 in cursor:
        person_id = result2[0][0]
        person_name = result2['name']
      cursor.close()
      session['logged_in'] = True
      return redirect('/')
    else:
      flash('Email Not Recognized')
      return redirect('/')

@app.route('/logout')
def logout():
    session['logged_in'] = False
    flash(person_name + ', you are now logged out. See you again soon!')
    return redirect('/')



if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using

        python server.py

    Show the help text using

        python server.py --help

    """

    HOST, PORT = host, port
    print "running on %s:%d" % (HOST, PORT)
    app.secret_key = os.urandom(12)
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


  run()
