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
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response
from collections import defaultdict
from dateutil.parser import parse

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
DB_USER = "yt2822"
DB_PASSWORD = "yt2822"

DB_SERVER = "w4111.cisxo09blonu.us-east-1.rds.amazonaws.com"

DATABASEURI = "postgresql://"+DB_USER+":"+DB_PASSWORD+"@"+DB_SERVER+"/proj1part2"



#
# This line creates a database engine that knows how to connect to the URI above
#
engine = create_engine(DATABASEURI)


# Here we create a test table and insert some values in it
engine.execute("""DROP TABLE IF EXISTS test;""")
engine.execute("""CREATE TABLE IF NOT EXISTS test (
  id serial,
  name text
);""")
engine.execute("""INSERT INTO test(name) VALUES ('grace hopper'), ('alan turing'), ('ada lovelace');""")

message = ""
course_id=[]
login_user = "Guest"



permutations=[]


def check_conflict(day1, time1, day2, time2):
  if day1 is None or time1 is None or day2 is None or time2 is None:
    return False
  conflict = False
  for d in ['M', 'T', 'W', 'R', 'F']:
    if d in day1 and d in day2:
      conflict = True
      break
  if not conflict:
    return False
  start1, end1 = time1.split('-')
  start2, end2 = time2.split('-')
  start1 = parse(start1).time()
  end1 = parse(end1).time()
  start2 = parse(start2).time()
  end2 = parse(end2).time()
  if end1 < start2 or end2 < start1:
    conflict = False
  else:
    conflict = True
  return conflict

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
    print("uh oh, problem connecting to database")
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
@app.route('/')
def index():
  """
  request is a special object that Flask provides to access web request information:
  request.method:   "GET" or "POST"
  request.form:     if the browser submitted a form, this contains the data in the form
  request.args:     dictionary of URL arguments e.g., {a:1, b:2} for http://localhost?a=1&b=2
  See its API: http://flask.pocoo.org/docs/0.10/api/#incoming-request-data
  """

  # DEBUG: this is debugging code to see what request looks like
  print(request.args)


  #
  # example of a database query
  #
  names = []
  for c_id in course_id:
    cmd = 'SELECT * FROM course WHERE course_id=(:name1)'
    cursor = g.conn.execute(text(cmd), name1=c_id)
    for result in cursor:
      names.append(result[0]+' '+result[1])  # can also be accessed using result[0]
    cursor.close()

  list=None
  for c_id in course_id:
    sections=[]
    cmd="SELECT * FROM course AS c, section_course as sc WHERE c.course_id = sc.course_id AND c.course_id=(:name1)"
    cursor=g.conn.execute(text(cmd), name1=c_id)
    for result in cursor:
      sections.append([[c_id,result['course_name'],result['call_number'],result['section_day'],result['section_time'],result['instructor']]])
    for section in sections:
      cmd='SELECT term_name FROM section_term WHERE call_number=(:name1)'
      cursor=g.conn.execute(text(cmd), name1=section[0][2])
      for result in cursor:
        section[0].append(result[0])
      cmd='SELECT exam_date FROM exam WHERE call_number=(:name1)'
      cursor=g.conn.execute(text(cmd),name1=section[0][2])
      exams=[]
      for result in cursor:
        exams.append(result[0])
      section[0].append(exams)
    if list is None:
      list=sections
    else:
      newlist=[]
      for l in list:
        for s in sections:
          match=True
          for ll in l:
            if check_conflict(s[0][3],s[0][4],ll[3],ll[4]) or s[0][6]!=ll[6]:
              match=False
              break
          if match:
            new_set=[]
            for ll in l:
              new_set.append(ll)
            new_set.append(s[0])
            newlist.append(new_set)
      list=newlist
  print(list)
  list_visulized=[]
  if list is not None and len(list)>0:
    for schedule in list:
      l=[]
      for section in schedule:
        sec_dict=dict()
        sec_dict['course_name']=section[1]
        sec_dict['section_day']=section[3]
        sec_dict['section_time']=section[4]
        sec_dict['exam_dates']=section[7]
        l.append(sec_dict)
      visual=format_schedule(l)
      list_visulized.append(visual)



  #
  # Flask uses Jinja templates, which is an extension to HTML where you can
  # pass data to a template and dynamically generate HTML based on the data
  # (you can think of it as simple PHP)
  # documentation: https://realpython.com/blog/python/primer-on-jinja-templating/
  #
  # You can see an example template in templates/index.html
  #
  # context are the variables that are passed to the template.
  # for example, "data" key in the context variable defined below will be
  # accessible as a variable in index.html:
  #
  #     # will print: [u'grace hopper', u'alan turing', u'ada lovelace']
  #     <div>{{data}}</div>
  #
  #     # creates a <div> tag for each element in data
  #     # will print:
  #     #
  #     #   <div>grace hopper</div>
  #     #   <div>alan turing</div>
  #     #   <div>ada lovelace</div>
  #     #
  #     {% for n in data %}
  #     <div>{{n}}</div>
  #     {% endfor %}
  #
  global message
  if list is None:
    list=[]
  elif len(list)==0:
    message="No permutation exist!"
  context = dict(name=login_user, msg = message,data = names,list=list_visulized)
  message=""
  #
  # render_template looks in the templates/ folder for files.
  # for example, the below file reads template/index.html
  #
  return render_template("index.html", **context)

def parse_time(section_time):
  start, end = section_time.split('-')
  start = str(parse(start).time()).split(':')
  end = str(parse(end).time()).split(':')
  start_slot = (int(start[0]) - 8) * 2
  if int(start[1]) >= 30:
    start_slot += 1
  end_slot = (int(end[0]) - 8) * 2
  if int(end[1]) > 0:
    end_slot += 1

  print(start_slot, end_slot)
  return (start_slot, end_slot)

def format_schedule(sections):
  # longest Course name
  longest_course_name = 0
  for section in sections:
    if section['course_name'] is not None:
      longest_course_name = max(longest_course_name, len(section['course_name']))
  div_line = ""
  for i in range(longest_course_name):
    div_line += '-'
  # a schedule placeholder
  MondayToFriday = [[], [], [], [], []]
  for i in range(len(MondayToFriday)):
    for half_hour in range(0, 25):
      MondayToFriday[i].append(div_line)
  # mapping from MTWRF to 012345
  MTWRF_mapping = {'M': 0, 'T': 1, 'W': 2, 'R': 3, 'F': 4}
  # for each section, fill in the either space or class name
  for section in sections:
    if section['section_time'] is None:
      continue
    start_slot, end_slot = parse_time(section['section_time'])
    for weekday in section['section_day']:
      for i in range(start_slot, end_slot):
        space_line = section['course_name']
        for _ in range(len(section['course_name']), longest_course_name):
          space_line += ' '
        print(i, section)
        MondayToFriday[MTWRF_mapping[weekday]][i] = space_line
  # string formatting
  ret_string = ""
  for i in range(len(MondayToFriday[0])):
    cur_time = str(int(i/2)+8)
    if len(cur_time) == 1:
      cur_time = '0' + cur_time
    cur_time += ":"
    if i % 2 == 0:
      cur_time += '00'
    else:
      cur_time += '30'
    time_slot = cur_time + "| "
    for j in range(len(MondayToFriday)):
      time_slot += str(MondayToFriday[j][i]) + " | "
    ret_string += (time_slot + '\n')

  for i in range(len(sections)):
    for j in range(len(sections)):
      if j<=i:
        continue
      exam1=sections[i]['exam_dates']
      exam2=sections[j]['exam_dates']
      for e1 in exam1:
        for e2 in exam2:
          if e1==e2:
            ret_string+="WARNING: "+sections[i]['course_name']+" and "+sections[j]['course_name']+" both have an exam on "+e1+"\n"
  #print(section)
  #print(MondayToFriday)
  #print(ret_string)
  return ret_string

#
# This is an example of a different path.  You can see it at
#
#     localhost:8111/catalog
#
# notice that the functio name is catalog() rather than index()
# the functions for each app.route needs to have different names
#
@app.route('/catalog.html')
def catalog():
  all_courses = defaultdict(lambda: [])
  # all sections from a course
  cursor = g.conn.execute("SELECT * FROM course AS c, section_course as sc WHERE c.course_id = sc.course_id")
  for result in cursor:
    course_key = (result['course_id'], result['course_name'])
    all_courses[course_key].append([result['call_number'], result['section_day'], result['section_time'], result['instructor']])
    if result['section_time'] is not None:
      parse_time(result['section_time'])
    print(result)
  cursor.close()

  context = dict(data = list(all_courses.items()))
  print(context)
  # test format_schedule
  sections = []
  cursor = g.conn.execute("SELECT * FROM course AS c, section_course as sc WHERE c.course_id = sc.course_id")
  for result in cursor:
    sections.append(result)
  cursor.close()
  format_schedule(sections)
  return render_template("catalog.html", **context)


@app.route('/login', methods=['POST'])
def login():
  global login_user
  name = request.form['name']
  # check if name valid
  for letter in name:
    if not (letter == ' ' or letter.isalnum()):
      name = 'Guest'
      return redirect('/')
  # check if it is a log out
  if name == 'Guest':
    login_user = name
    return redirect('/')
  # Look into student table if the name exits
  cursor = g.conn.execute(text('SELECT name FROM student WHERE name=(:name1)'), name1 = name)
  result = cursor.fetchall()
  cursor.close()
  if len(result) == 0:# If not exists, create a new user
    print("NO SUCH USER, CREATE A NEW ONE")
    cursor = g.conn.execute(text('INSERT INTO student(name) VALUES (:name1)'), name1 = name)
    cursor.close()
  else: #if exists, change the login user to login_user
    login_user = name
  
  cursor = g.conn.execute('SELECT * FROM student')
  for result in cursor:
    print(result)
  cursor.close()
  
  return redirect('/')


@app.route('/add', methods=['POST'])
def add():
  name = request.form['name']
  print(name)
  global message
  if name in course_id:
    message=name+" is already in schedule!"
    return redirect('/')
  cmd = 'SELECT * FROM course WHERE course_id=(:name1)'
  cursor = g.conn.execute(text(cmd), name1 = name)
  cname=''
  for result in cursor:
    cname=result['course_id']
    break
  if cname=='':
    message="The course "+name+" does not exist!"
  else:
    course_id.append(name)
    message="Successfully added "+name+" to schedule!"
  return redirect('/')

@app.route('/remove', methods=['POST'])
def remove():
  name = request.form['name']
  if name in course_id:
    course_id.remove(name)
  global message
  message="Successfully removed "+name+" from schedule!"
  return redirect('/')

@app.route('/save', methods=['POST'])
def remove():
  name = request.form['name']
  lst = name.split(',')
  for schedule_id in lst:
    if schedule_id >= len(permutations):
      continue
    permutations[schedule_id]
  return redirect('/')

@app.route('/removeall', methods=['POST'])
def removeall():
  print("removeall")
  course_id.clear()
  global message
  message="Successfully removed all courses!"
  return redirect('/')

'''
@app.route('/login')
def login():
    abort(401)
    this_is_never_executed()
'''

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
    print("running on %s:%d" % (HOST, PORT))
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


  run()