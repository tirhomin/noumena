'''single-page web application which takes keywords file and text file,
    and highlights text file according to keywords file and mode'''
from gevent import monkey, wsgi; monkey.patch_all()
import os, csv, hashlib, binascii, sqlite3, highlighter, datetime, tldextract, time
from flask import Flask,g,flash,request,redirect,render_template,session, Response
from nsettings import QUESTIONS
from newspaper import Article
import nsettings
app = Flask(__name__)
app.secret_key = b'\x95W\xed\xed.g\x97((-&\x4b\x92\xf2\x2dGZBMG+O\x919\xe5\xc76A\xcc\x8b\xdb}W';

#-----database stuff for Flask:
DATABASE = 'app.db'
def get_db():
    db = getattr(g, '_database', None)
    if db is None: db = g._database = sqlite3.connect(DATABASE)
    return db

#----utility functions:
def loggedin(): return 'username' in session

def login(username,password,admin=False):
    if password == None: password=''
    salt = b'\xebE\xc5\x87\x80\x817\xde*\xab\xbdX\xe9u;\xdd #\x7f\x0b'
    #should store a unique salt for each user in a later version
    password = str(binascii.hexlify(hashlib.pbkdf2_hmac('sha256',bytes(password,'utf8'),salt,10**5)))
    cur = get_db().execute('SELECT * FROM users WHERE username=?', (username,))
    result = cur.fetchone() 
    if not 'uimode' in session: session['uimode'] = 'simple'
    if result:
        '''user exists, log them in'''
        if result[1] != password and not admin:
            return 'error, wrong password<br><a href="/">Home</a>'
        session['username'] = username
        session['mode'] = result[2]
        session['low'] = result[3]
        session['medium'] = result[4]
        session['high'] = result[5]
        session['risk'] = result[7]
        session['filename'] = result[8]
        session['scrollpos'] = result[9]
        if result[6]:
            session['files'] = True

    else:
        '''user does not exist, create account and log them in'''
        db = get_db()
        db.cursor().execute('''INSERT INTO users(username,password,mode,low,medium,high,risk) VALUES
                            (?,?,?,'ff0','f80','f00','low')''', (username,password,'profile'))

        group_keyword_defaults = {1:'example, example phrase, mail',2:'address',3:'telephone',4:'credit card',5:'location',6:'opt',7:''}
        for group in range(1,8):
            colors = ['ff0','f80','f00','0df','000','000','0f0']
            db.cursor().execute('''INSERT INTO keywords(owner,groupnum,color,kwlist) VALUES
                            (?,?,?,?)''', (username,group,colors[group-1],group_keyword_defaults[group]))
        db.commit()
        session['username'] = username
        session['mode'] = 'keyword'
        session['low'] = 'ff0'
        session['medium'] = 'f80'
        session['high'] = 'f00'
        session['risk'] = 'low'
        session['filename'] = "none"
        session['scrollpos'] = '0'

#per-request database connections for flask and sqlite
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None: db.close()

@app.before_request
def before_request():
    session.permanent = True
    app.permanent_session_lifetime = datetime.timedelta(minutes=30)
    session.modified = True

#----routes:
@app.route('/simple')
def uimodesimple():
    '''switch to simple UI'''
    session['uimode'] = 'simple'
    session['mode'] = 'keyword'
    return redirect('/')

@app.route('/advanced')
def uimodeadvanced():
    '''switch to advanced UI'''
    session['uimode'] = 'advanced'
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/settings/kwcolor', methods=['GET','POST'])
def settings_keywordcolor():
    '''handles js initiated request to change a keyword color for saving in db between sessions'''
    group = int(request.args['colorid'])
    username = session['username']
    color=request.args['color']
    db=get_db()
    db.cursor().execute("UPDATE keywords SET color = ? WHERE owner = ? AND groupnum = ?", (color,username,group))
    db.commit()
    return 'done'

@app.route('/settings/keywords', methods=['GET','POST'])
def settings_keywords():
    username = session['username']
    scrollpos = request.form['scrollpos']

    db=get_db()
    db.cursor().execute("UPDATE users SET scrollpos = ? WHERE username = ?", (scrollpos,username))
    session['scrollpos'] = scrollpos
    session.modified = True
    for group in range(1,7):
        db.cursor().execute("UPDATE keywords SET kwlist = ? WHERE owner = ? AND groupnum = ?", 
        (request.form['keywords'+str(group)],username,group))
    db.commit()
    return redirect('/')

@app.route('/settings/cbox', methods=['GET','POST'])
def settings_cbox():
    username = session['username']
    cboxes = request.args['b']
    db=get_db()
    db.cursor().execute("UPDATE users SET cboxes = ? WHERE username = ?", (cboxes,username))
    db.commit()
    return 'done'

@app.route('/settings')
def settings():
    '''change risk level setting or risk level color'''
    if loggedin():
        username = session['username']
        color = request.args['color']
        risk = request.args['risk']
        db = get_db()
        if risk in ['low','medium','high']:
            if 'mode' in request.args:
                db.cursor().execute("UPDATE users SET risk = ?, %s = ?, mode = ? WHERE username = ?" %risk, (risk,color,request.args['mode'],username,))
            else:
                db.cursor().execute("UPDATE users SET risk = ?, %s = ? WHERE username = ?" %risk, (risk,color,username,))

            db.commit()
            session[risk] = color #session['medium'] = 'f80'
            session['risk'] = risk
        session.modified = True
    return 'done'

@app.route('/login', methods=['POST'])
def loginroute():
    '''if username exists, log user in (displaying error if password is wrong)
    if not, create user account with that username'''
    username = request.form['username'].strip().lower()
    password = request.form['password']
    login(username,password)
    return redirect('/')

@app.route('/addtermsurl', methods=['POST'])
def addtermsurl():
    '''fetch privacy policy or terms of service document from URL; save as user's document'''
    UPLOAD_FOLDER = './uploads'
    username=session['username']
    db = get_db()

    if 'termsurl' in request.form:
        url = request.form['termsurl']
        try:
            article = Article(url)
            article.download()
            article.parse()
            if not article.text:
                flash('Error: site returned no content -- please either switch to Advanced Mode and use file upload, or copy+paste the document into www.pastebin.com and then use the pastebin url here.')    
                return redirect('/')

            tld = tldextract.extract(url)
            #fname = "text from %s.%s" %(tld.domain,tld.suffix)
            fname = url

            filepath=os.path.join(UPLOAD_FOLDER, username+'.corpusfile.txt')
            with open(filepath,'w') as f:
                f.write(article.text)
            session['files'] = True
            session['filename'] = fname
            session['scrollpos'] = '0'
            session.modified = True
            db.cursor().execute("UPDATE users SET files = 1, textfilename = ?, scrollpos = '0' WHERE username = ?", (fname, username,))
            db.commit()           
        except:
            flash('Error: URL invalid; try including the "http://" portion')    
    return redirect('/')

@app.route('/upload', methods=['POST'])
def upload():
    '''upload text file and keywords file to be used as document for user'''
    UPLOAD_FOLDER = './uploads'
    username=session['username']
    db = get_db()

    if 'corpusfile' in request.files:
        c = request.files['corpusfile']
        if len(c.read()) > 0:
            c.seek(0)
            filepath=os.path.join(UPLOAD_FOLDER, username+'.corpusfile.txt')
            unsafefilename = request.files['corpusfile'].filename
            request.files['corpusfile'].save(filepath)
            session['files'] = True
            session['filename'] = unsafefilename
            session['scrollpos'] = '0'
            session.modified = True
            db.cursor().execute("UPDATE users SET files = 1, textfilename = ?, scrollpos = '0' WHERE username = ?", (unsafefilename, username,))
    if 'keywordfile' in request.files:
        k = request.files['keywordfile']
        if len(k.read()) > 0:
            k.seek(0)
            filepath=os.path.join(UPLOAD_FOLDER, username+'.keywordfile.txt')
            unsafefilename = request.files['keywordfile'].filename
            request.files['keywordfile'].save(filepath)
            with open(filepath) as f:
                z = f.read().split('\n')
            for group in range(1,7):
                if len(z)>=group:
                    db.cursor().execute("UPDATE keywords SET kwlist = ? WHERE owner = ? AND groupnum = ?", (z[group-1],username,group))

    db.commit()
    return redirect('/')

@app.route('/viewedvideo')
def viewed_video():
    '''note in DB that user has viewed intro video '''
    if 'username' in session:
        username = session['username']
        db = get_db()
        db.cursor().execute("UPDATE users SET viewedvideo = 1 WHERE username = ?", (username,))
        db.commit()
        return 'updated'
    else: return 'failed'        

@app.route('/updatescroll')
def update_scroll():
    '''save user scroll position, i.e. bookmark their reading position to be resumed on next login'''
    if 'username' in session:
        username=session['username']
        session['scrollpos'] = request.args['scrollpos']
        session.modified = True
        db = get_db()
        db.cursor().execute("UPDATE users SET scrollpos = ? WHERE username = ?", 
                    (request.args['scrollpos'], username,))
        db.commit()
        return 'updated'
    else: return 'failed'

@app.route('/admin/dict', methods=['POST'])
def admin_changedict():
    '''allow admin to change dictionary entries if on-site dictionary isnt good enough'''
    if not session['username'] == 'admin': return redirect('/')
    if 'dictfile' in request.files:
        c = request.files['dictfile']
        if len(c.read()) > 0:
            c.seek(0)
            filepath=os.path.join('./static/', 'admin.dict.txt')
            request.files['dictfile'].save(filepath)
    return redirect('/admin')

@app.route('/admin/delete')
def admin_delete():
    '''let admin delete junk user accounts'''
    if not session['username'] == 'admin': return redirect('/')
    db=get_db()
    db.cursor().execute('delete from users where username = ?', (request.args['user'],))
    db.cursor().execute('delete from keywords where owner = ?', (request.args['user'],))
    db.commit()
    return redirect('/admin')

@app.route('/admin/download')
def admin_download():
    '''let admin download surveys'''
    if not session['username']=='admin': return redirect('/')
    db=get_db()
    db.row_factory = sqlite3.Row
    dbc = db.cursor()
    res=dbc.execute('select * from survey').fetchall()
    scale = {0:'Not Applicable', 1:'Strongly Disagree', 2:'Disagree',3:'Somewhat Disagree', 4:'Neither Agree nor Disagree', 5:'Somewhat Agree', 6:"Agree", 7:"Strongly Agree"}
    csvdata = 'username,prolificid,viewed video,' +''.join(['"%s",' %QUESTIONS[i] for i in range(len(QUESTIONS))]) + '\n'
    for r in res:
        rowner = r['owner']
        res2=dbc.execute('select * from users where username = ?', (rowner,)).fetchone()
        #TODO: delete survey from db when deleting from admin page
        if not res2:continue
        csvdata += "%s,%s,%s," %(r['owner'],(r['prolificid'] or ''), 'True,' if res2['viewedvideo'] else 'False,')

        for i in range(1,len(QUESTIONS)+1):
            ci = 'q%d' %(i)
            csvdata += '%s,' %(scale[r[ci]] if r[ci] in scale else 'did not answer')

        csvdata += '\n%s,%s' %(r['owner'],r['prolificid'] or '')

        for i in range(1,len(QUESTIONS)+1):
            csvdata += '%s,' %str(r['qtext%d' %(i)] or '')

        csvdata+='\n---------------------\n'
    return Response(csvdata, mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=%s" %'surveydata.csv'})

@app.route('/swapuser')
def swapuser():
    if session['username']=='admin':
        login(request.args['user'],None,admin=True)
    return redirect('/')

@app.route('/admin')
def admin():
    '''display admin UI to manage users and feedback / microCRM'''
    if 'username' in session and session['username']=='admin':
        db=get_db()
        db.row_factory = sqlite3.Row
        res = db.cursor().execute('select rowid,* from users')
        results = list()
        for user in res:
            res2=db.cursor().execute("select * from keywords where owner = ?", (user['username'],))
            gdict = {gid:{'color':'','keywords':''} for gid in range(1,8)}
            for group in res2:
                gdict[group['groupnum']]['color'] = group['color']
                gdict[group['groupnum']]['keywords'] = group['kwlist']
            results.append((user,gdict))
        from pprint import PrettyPrinter
        pp = PrettyPrinter(indent=4)
        pp.pprint(results[:4])
        return render_template('admin.html',results=results)
    else:
        return redirect('/')

@app.route('/feedback')
def feedback():return render_template('feedback.html', tvars={"questions":QUESTIONS})

@app.route('/admin/survey/<id>')
def viewsurvey(id):
    '''let admin view user survey'''
    db=get_db()
    db.row_factory = sqlite3.Row
    un=db.cursor().execute('select * from users where ROWID = ?',(id,)).fetchone()
    res=db.cursor().execute('select * from survey where owner = ?',(un[0],)).fetchone()
    tvars=dict()
    for i in range(len(QUESTIONS)):
        tvars['q'+str(i+1)] = res[i]
        tvars['qtext'+str(i+1)] = res['qtext'+str(i+1)]
    tvars['questions'] = QUESTIONS
    tvars['admin'] = True
    tvars['prolificid'] = res[-1]#TODO this will break if adding questions to survey 
    return render_template('feedback.html', tvars=tvars)


@app.route('/feedback', methods=['POST'])
def feedback_post():
    '''save user feedback form'''
    if 'username' in session:
        username=session['username']
        prolificid = request.form['prolificid']
        rf = dict()
        for k in request.form: 
            if not k == 'prolificid' and not 'qtext' in k:
                rf[k] = int(request.form[k])
            else:
                rf[k] = request.form[k]
        for i in range(len(QUESTIONS)):
            if not 'q%d'%(i+1) in rf:
                rf['q%d'%(i+1)] = 0
        db = get_db()
        db.cursor().execute('delete from survey where owner = ?', (username,))
        db.cursor().execute('''INSERT INTO survey(q1,q2,q3,q4,q5,q6,q7,q8,q9,q10,q11,q12,q13,q14,q15,q16,q17,q18,q19,owner,prolificid,
                                qtext1,qtext2,qtext3,qtext4,qtext5,qtext6,qtext7,qtext8,qtext9,qtext10,qtext11,qtext12,qtext13,
                                qtext14,qtext15,qtext16,qtext17,qtext18,qtext19) VALUES
                            (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', 
                            (rf['q1'],rf['q2'],rf['q3'],rf['q4'],rf['q5'],rf['q6'],
                            rf['q7'],rf['q8'],rf['q9'],rf['q10'],rf['q11'],rf['q12'],
                            rf['q13'],rf['q14'],rf['q15'],rf['q16'],rf['q17'],rf['q18'],rf['q19'],
                            username, prolificid,
                            rf['qtext1'],rf['qtext2'],rf['qtext3'],rf['qtext4'],rf['qtext5'],rf['qtext6'],
                            rf['qtext7'],rf['qtext8'],rf['qtext9'],rf['qtext10'],rf['qtext11'],rf['qtext12'],
                            rf['qtext13'],rf['qtext14'],rf['qtext15'],rf['qtext16'],rf['qtext17'],rf['qtext18'],rf['qtext19']))
        db.cursor().execute("UPDATE users SET survey = 1 WHERE username = ?", (username,))
        db.commit()
    return 'Thanks for submitting your survey! <br><a href="/">HOME</a>'

@app.route('/help')
def help():return render_template('help.html')

@app.route('/terms')
def privacyterms():return render_template('terms.html')

@app.route('/')
def home():
    '''display main page (only page, for now, this is a single-page application)'''
    kwcolors,keywords,filename = dict(),dict(),str()
    if not 'uimode' in session: session['uimode'] = 'simple'

    admin= False
    scrollpos='0'
    if 'username' in session:
        if session['username']=='admin':admin=True
        db = get_db()
        res=db.cursor().execute('select * from keywords where owner = ?',(session['username'],)).fetchall()
        kwcolors = {r[1]:r[2] for r in res}
        #kwcolors[7] = '00dd00'
        print('KWCOLORS:',kwcolors)
        keywords = {r[1]:r[3].lower() for r in res}
        filename = session['filename']
        scrollpos = session['scrollpos']

    if 'files' in session and 'username' in session:
        t1=time.time()
        cboxes = res=db.cursor().execute('select cboxes from users where username = ?',(session['username'],)).fetchone()[0]
        print('CBOXES:',cboxes)
        corpus = highlighter.highlight(session['username'],keywords=keywords,uimode=session['uimode'], cboxes=cboxes)
        print('highlight time:',time.time()-t1)
        corpus = corpus.replace('\n','<br>')

    elif 'username' in session:
        corpus = 'No document added yet. Please add one.<br>(you can use the \'fetch document\' button above)'
    else:
        corpus = '''please login or create an account<br><br>
                    <h3>advisory:</h3>
                    when creating an account, please choose a non-personally-identifying username
                    <br><br>e.g. not your real name or email address
                    <br><br><a href="/help">site help</a>'''

    mode = session['mode'] if 'mode' in session else ''
    if session['uimode'] == 'simple':
        template = 'simplehome.html'
    else:
        template = 'home.html'
    return render_template(template,admin=admin,corpus=corpus, scrollpos=scrollpos,
            loggedin=loggedin(), kwcolors=kwcolors, mode=mode, keywords=keywords, filename=filename)

if nsettings.LOCAL:
    app.run(host='0.0.0.0',port=8080, debug=True)
else:
    server = wsgi.WSGIServer(('0.0.0.0',8080), app)
    server.serve_forever()
