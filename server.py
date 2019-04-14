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

# DB_USER = "jmg2338"
# DB_PASSWORD = "09AcAIiCnF"
DB_USER = "ms5488"
DB_PASSWORD = "ihtXu8PHsp"
DB_SERVER = "w4111.cisxo09blonu.us-east-1.rds.amazonaws.com"
DATABASEURI = "postgresql://"+DB_USER+":"+DB_PASSWORD+"@"+DB_SERVER+"/w4111"
engine = create_engine(DATABASEURI)

# Here we create a test table and insert some values into it
engine.execute("""DROP TABLE IF EXISTS test;""")
engine.execute("""CREATE TABLE IF NOT EXISTS test (id serial, name text);""")
engine.execute("""INSERT INTO test(name) VALUES ('grace hopper'), ('alan turing'), ('ada lovelace');""")

default_person_id = 0
default_person_name = "Anonymous"

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
  print session

  if not session.get('logged_in'):

    return render_template("Login.html")

  else:
    q = """
      SELECT
        O.name, O.phone, O.email, O.picture
      FROM
        owner O
      WHERE
        O.owner_id = %s
      LIMIT 10
      """
    cursor = g.conn.execute(q, [session['person_id']])

    df_owner = pd.DataFrame(cursor.fetchall())
    df_owner.columns = cursor.keys()
    cursor.close()

    cursor = g.conn.execute(
      """
      SELECT
        D.name, D.breed, D.age, D.weight, D.play_intensity, D.picture1, D.picture2
      FROM
        owner O
        LEFT JOIN dog_owned_by DOB on O.owner_id = DOB.owner_id
        LEFT JOIN dog D on DOB.dog_id = D.dog_id
      WHERE
        O.owner_id = %s
      LIMIT 10
      """,
      session['person_id']
    )

    df_dog = pd.DataFrame(cursor.fetchall())
    df_dog.columns = cursor.keys()
    cursor.close()

    cursor = g.conn.execute(
      """
      SELECT
        O.review_id, O.positive, O.feedback
      FROM
        owner_review O
      WHERE
        O.reviewee = %s
      LIMIT 10
      """,
      session['person_id']
    )

    if cursor.rowcount > 0:
      df_review = pd.DataFrame(cursor.fetchall())
      df_review.columns = cursor.keys()
    else:
      df_review = pd.DataFrame(columns=['review_id', 'positive', 'feedback'])
    cursor.close()

    context = dict(
      owner_data = [df_owner.to_html(classes='table', header="true", index=False)],
      dog_data = [df_dog.to_html(classes='table', header="true", index=False)],
      review_data = [df_review.to_html(classes='table', header="true", index=False)]
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


@app.route('/matches')
def matches():

    cursor = g.conn.execute(
      """
      WITH
        owner_preferences AS (
          SELECT 
            preference.age_min,
            preference.age_max,
            preference.weight_min,
            preference.weight_max,
            preference.play_intensity_min,
            preference.play_intensity_max
          FROM
            preference
            LEFT JOIN preference_set_by ON preference.preference_id = preference_set_by.preference_id
          WHERE
            preference_set_by.owner_id = %(person_id)s
        )
      SELECT *
      FROM owner_preferences
      """,
      person_id=session['person_id']
    )

    if cursor.rowcount > 0:
      df_preferences  = pd.DataFrame(cursor.fetchall())
      df_preferences.columns = cursor.keys()
    else:
      df_preferences = pd.Dataframe(columns = ['age_min','age_max','weight_min', 'weight_max', 'play_intensity_min', 'play_intensity_max'])
    cursor.close()

    cursor = g.conn.execute(
      """
      WITH
        owner_preferences AS (
          SELECT 
            preference.age_min,
            preference.age_max,
            preference.weight_min,
            preference.weight_max,
            preference.play_intensity_min,
            preference.play_intensity_max
          FROM
            preference
            LEFT JOIN preference_set_by ON preference.preference_id = preference_set_by.preference_id
          WHERE
            preference_set_by.owner_id = %(person_id)s
        )
      SELECT
        owner.owner_id,
        owner.name,
        owner.phone,
        owner.email,
        dog.dog_id,
        dog.name,
        dog.age,
        dog.weight,
        dog.breed,
        dog.play_intensity
      FROM
        dog
        CROSS JOIN owner_preferences
        LEFT JOIN dog_owned_by on dog.dog_id = dog_owned_by.dog_id
        LEFT JOIN owner on dog_owned_by.owner_id = owner.owner_id
      WHERE 
        (dog.age >= owner_preferences.age_min) AND
        (dog.age <= owner_preferences.age_max) AND
        (dog.weight >= owner_preferences.weight_min) AND
        (dog.weight <= owner_preferences.weight_max) AND 
        (dog.play_intensity >= owner_preferences.play_intensity_min) AND
        (dog.play_intensity <= owner_preferences.play_intensity_max);
      """,
      person_id=session['person_id']
    )

    if cursor.rowcount > 0:
      df_matches = pd.DataFrame(cursor.fetchall())
      df_matches.columns = cursor.keys()
    else:
      df_matches = pd.Dataframe(columns = ['owner_id','name','phone','email','dog_id','name', 'age', 'weight', 'breed', 'play_intensity'])
    cursor.close()

    context = dict(
      preference_data = [df_preferences.to_html(classes='table', header="true", index=False)],
      match_data = [df_matches.to_html(classes='table', header="true", index=False)]
    )

    return render_template("Matches.html", **context)


@app.route('/messages')
def messages():

    # debugging
    print '\n'
    print "REQUEST ARGUMENTS:"
    print request.args

    print '\n'
    print "SESSION ARGUMENTS:"
    print session

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
      (session['person_id'], session['person_id'])
    )
    if cursor.rowcount > 0:
      df = pd.DataFrame(cursor.fetchall())
      df.columns = cursor.keys()
    else:
      df = pd.DataFrame(columns=['time', 'sender', 'receiver', 'message'])
    cursor.close()
    context = dict(
      data = [df.to_html(classes='table', header="true", index=False)]
    )

    return render_template("Messages.html", **context)
    

@app.route('/locations')
def locations():

    # debugging
    print '\n'
    print "REQUEST ARGUMENTS:"
    print request.args

    print '\n'
    print "SESSION ARGUMENTS:"
    print session

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

    df = pd.DataFrame(cursor.fetchall())
    df.columns = cursor.keys()
    cursor.close()

    context = dict(
      data = [df.to_html(classes='table', header="true", index=False)]
    )

    return render_template("Locations.html", **context)


@app.route('/playdates')
def playdates():

    q = """
      SELECT *
      FROM owner_meet
      WHERE owner_meet.scheduler = %s OR owner_meet.schedulee = %s
      """
    cursor = g.conn.execute(q, [session['person_id'], session['person_id']])

    if cursor.rowcount > 0:
      df = pd.DataFrame(cursor.fetchall())
      df.columns = cursor.keys()
    else:
      df = pd.DataFrame(cursor.fetchall())
    cursor.close()

    context = dict(
      data = [df.to_html(classes='table', header="true", index=False)]
    )

    return render_template("Playdates.html", **context)


# Example of adding new data to the database
@app.route('/add_profile', methods=['POST'])
def add_profile():

  owner_id = 0
  dog_id = 0
  preference_id = 0
  
  # New owner_id
  cursor = g.conn.execute(
      """
      SELECT owner_id FROM owner ORDER BY cast(owner_id as integer) DESC LIMIT 1
      """
    )
  
  for result in cursor:
    owner_id = str(int(result[0]) + 1)
  cursor.close()

  # New dog_id
  cursor = g.conn.execute(
      """
      SELECT dog_id FROM dog ORDER BY cast(dog_id as integer) DESC LIMIT 1
      """
    )
  
  for result2 in cursor:
    dog_id = str(int(result2[0]) + 1)
  cursor.close()

  # New preference_id
  cursor = g.conn.execute(
      """
      SELECT preference_id FROM preference ORDER BY cast(preference_id as integer) DESC LIMIT 1
      """
    )
  
  for result3 in cursor:
    preference_id = str(int(result3[0]) + 1)
  cursor.close()

  print(owner_id, dog_id, preference_id)

  # Email List
  emails = []
  cursor = g.conn.execute(
      """
      SELECT email FROM owner
      """
    )
  
  for result in cursor:
    emails.append(result[0])
  cursor.close()

  # Check Input
  name = request.form['name']
  phone = request.form['phone']
  email = request.form['email']
  picture = request.form['picture']

  dname = request.form['dname']
  age = request.form['age']
  weight = request.form['weight']
  breed = request.form['breed']
  play_intensity = request.form['play_intensity']
  picture1 = request.form['picture1']
  picture2 = request.form['picture2']

  age_min = request.form['agemin']
  age_max = request.form['agemax']
  weight_min = request.form['wgtmin']
  weight_max = request.form['wgtmax']
  play_intensity_min = request.form['pimin']
  play_intensity_max = request.form['pimax']
  playdate_duration = request.form['playdate_duration']

  if name == "":
    flash('Please enter your name!')
    return redirect('/EnterInfo')
  elif email == "":
    flash("Please enter your email!")
    return redirect('/EnterInfo')
  elif picture == "":
    flash("Please add a picture of yourself!")
    return redirect('/EnterInfo')
  elif email in emails:
    flash('Profile already exists for this email. Please log in with your email!')
    return redirect('/EnterInfo')
  elif dname == "":
    flash("Please enter your dog's name!")
    return redirect('/EnterInfo')
  elif age == "":
    flash("Please enter your dog's age!")
    return redirect('/EnterInfo')
  elif weight == "":
    flash("Please enter your dog's weight!")
    return redirect('/EnterInfo')
  elif picture1 == "":
    flash("Please add a picture in Picture (1)!")
    return redirect('/EnterInfo')
  elif age_max < age_min:
    flash("Age Max must be larger than Age Min!")
    return redirect('/EnterInfo')
  elif weight_max < weight_min:
    flash("Weight Max must be larger than Weight Min!")
    return redirect('/EnterInfo')
  elif play_intensity_max < play_intensity_min:
    flash(" Play Intensity Max must be larger than Play Intensity Min!")
    return redirect('/EnterInfo')
    
  else:
    # Update owner table with new owner record

    q1 ="""
      INSERT INTO
        owner(owner_id, name, phone, email, picture)
      VALUES
        (%s, %s, %s, %s, %s);
      """
    g.conn.execute(q1, [owner_id, name, phone, email, picture])

    # Update dog table with new dog record
    q2 = """
      INSERT INTO
        dog(dog_id, name, age, weight, breed, play_intensity, picture1, picture2)
      VALUES
        (%s, %s, %s, %s, %s, %s, %s, %s);
      """
    g.conn.execute(q2, [dog_id, name, age, weight, breed, play_intensity, picture1, picture2])

    # Update dog_owned_by
    q3 ="""
      INSERT INTO
        dog_owned_by(dog_id, owner_id)
      VALUES
        (%s, %s);
      """
    g.conn.execute(q3, [dog_id, owner_id])
    
    # Update preference table with new preference record
    q4 = """
      INSERT INTO
        preference(preference_id, age_min, age_max, weight_min, weight_max, play_intensity_min, play_intensity_max,  playdate_duration)
      VALUES
        (%s, %s, %s, %s, %s, %s, %s, %s);
      """
    g.conn.execute(q4, [preference_id, age_min, age_max, weight_min, weight_max, play_intensity_min, play_intensity_max, playdate_duration])

    # Update preference_set_by table with new preference_set_by record
    q5 = """
      INSERT INTO
        preference_set_by(preference_id, owner_id)
      VALUES
        (%s, %s);
      """
    g.conn.execute(q5, [preference_id, owner_id])

    session['person_id'] = owner_id
    session['person_name'] = name
    session['logged_in'] = True

    return redirect('/')


# Example of adding new data to the database
@app.route('/add_dog', methods=['POST'])
def add_dog():

  g.conn.execute(
    """
    INSERT INTO
      dog(dog_id, name, age, weight, breed, play_intensity, picture1, picture2)
    VALUES
      (%(dog_id)s, %(name)s, %(age)s, %(weight)s, %(breed)s, %(intensity)s, %(picture1)s, %(picture2)s);
    """,
    request.form
  )

  g.conn.execute(
    """
    INSERT INTO
      dog_owned_by(dog_id, owner_id)
    VALUES
      (%(dog_id)s, %(owner_id)s);
    """,
    dog_id=request.form['dog_id'],
    owner_id=session['person_id']
  )

  return redirect('/')


# Example of adding new data to the database
@app.route('/add_message', methods=['POST'])
def add_message():

  cursor = g.conn.execute(
    """
    SELECT owner.owner_id
    FROM owner
    WHERE owner.email = %(receiver)s;
    """,
    receiver=request.form['receiver']
  )

  df_receiver = pd.DataFrame(cursor.fetchall())
  df_receiver.columns = cursor.keys()
  receiver_id = df_receiver.owner_id.iloc[0]
  cursor.close()

  g.conn.execute(
    """
    INSERT INTO
      owner_contact(contact_id, sender, receiver, time, message)
    VALUES
      (%(contact_id)s, %(sender)s, %(receiver)s, %(time)s, %(message)s);
    """,
    contact_id=str(pd.Timestamp('now').strftime("%Y%m%d%H%M%S")),
    sender=session['person_id'],
    time=pd.Timestamp('now').strftime("%Y-%m-%d %H:%M:%S"),
    receiver=receiver_id,
    message=request.form['message']
  )
  
  return redirect('/messages')

@app.route('/login', methods=['POST'])
def login():

    login_credential = request.form['email']

    cursor = g.conn.execute(
      """
      SELECT email FROM owner
      """
    )

    emails = []
    for result in cursor:
      emails.append(result['email'])  # can also be accessed using result[0]
    cursor.close()

    if login_credential in emails:

      cursor = g.conn.execute(
        """
        SELECT owner_id, name
        FROM owner
        WHERE email = %s
        """,
        (login_credential)
      )

      for result2 in cursor:
        person_id = result2[0]
        person_name = result2['name']
        session['person_id'] = person_id
        session['person_name'] = person_name

      cursor.close()

      session['logged_in'] = True
      return redirect('/')

    else:

      session['person_id'] = default_person_id
      session['person_name'] = default_person_name
      flash('Email Not Recognized')
      return redirect('/')

@app.route('/logout')
def logout():
    session['logged_in'] = False
    flash('You are now logged out, ' + session['person_name'] + '. See you again soon!')
    return redirect('/')



if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    HOST, PORT = host, port
    print "running on %s:%d" % (HOST, PORT)
    app.secret_key = os.urandom(12)
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


  run()
