from collections import OrderedDict
from flask import Flask, render_template, url_for, redirect, request
from flask import flash, jsonify
from flask import session as login_session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Theme, Painting, User
import random
import string
from flask_uploads import UploadSet, IMAGES, configure_uploads
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests
app = Flask(__name__)


CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Art Portfolio Application"

engine = create_engine('sqlite:///artportfolio.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

# Configure the image uploading via Flask-Uploads
images = UploadSet('images', IMAGES)
configure_uploads(app, images)


# Create anti-forgery state token
@app.route('/login')
def showLogin():
    login_session.clear()
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


#################################
# Google authentification
#################################

@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    print request.args.get('state')
    print login_session['state']
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    print "access token ", access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps
                                 ('Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials.access_token
    login_session['gplus_id'] = gplus_id
    response = make_response(json.dumps('Successfully connected user', 200))

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    login_session['provider'] = 'google'

    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: '
    output += '150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;">'
    flash("You are now logged in as %s" % login_session['username'])
    print "done!"
    return output


# Disconnect - Revoke a current user's token and reset their login_session
@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token')
    print "get access token", access_token
    if access_token is None:
        print 'Access Token is None'
        response = make_response(json.dumps('Current user not connected.'),
                                 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    print "In gdisconnect access token is %s", access_token
    print 'User name is: '
    print login_session['username']
    url = 'https://accounts.google.com/'
    url += 'o/oauth2/revoke?token=%s' % login_session['access_token']
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print 'result is '
    print result
    if result['status'] == '200':
        # del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps
                                 ('Failed to revoke token for given user.',
                                  400))
        response.headers['Content-Type'] = 'application/json'
        return response


#################################
# Facebook authentification
#################################

@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print "access token received %s " % access_token
    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/'
    url += 'oauth/access_token?grant_type=fb_exchange_token&client_id'
    url += '=%s&client_secret=%s&fb_exchange_token=%s' % (
        app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    print " result: %s" % result

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v2.8/me"
    '''
        Due to the formatting for the result from the server token exchange
        we have to split the token first on commas and select the first index
        which gives us the key : value for the server access token then we
        split it on colons to pull out the actual token value and replace
        the remaining quotes with nothing so that it can be used directly
        in the graph api calls
    '''
    token = result.split(',')[0].split(':')[1].replace('"', '')

    url = 'https://graph.facebook.com/'
    url += 'v2.8/me?access_token=%s&fields=name,id,email' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    print "API JSON result: %s" % result
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly logout
    login_session['access_token'] = token

    # Get user picture
    url = 'https://graph.facebook.com/v2.8/me/'
    url += 'picture?access_token=%s&redirect=0&height=200&width=200' % token
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    login_session['picture'] = data["data"]["url"]

    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: '
    output += '150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;">'

    flash("You are now logged in as %s" % login_session['username'])
    return output


@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % \
        (facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "You have logged out"


#################################
# JSON Endpoints
#################################

@app.route('/themes/JSON')
def showThemesJSON():
    themes = session.query(Theme).all()
    return jsonify(j_theme = [i.serialize for i in themes])


@app.route('/themes/<int:theme_id>/paintings/JSON')
def showPaintingsJSON(theme_id):
    theme = session.query(Theme).filter_by(id=theme_id).one()
    paintings = session.query(Painting).filter_by(theme_id=theme_id).all()
    return jsonify(j_paintings=[i.serialize for i in paintings])


@app.route('/themes/<int:theme_id>/paintings/<int:paintings_id>/JSON')
def showOnePaintingJSON(theme_id, paintings_id):
    painting = session.query(Painting).filter_by(theme_id=theme_id, id = paintings_id).one()
    return jsonify(j_painting = painting.serialize)


#################################
# CRUD operations
#################################

# Show all themes
@app.route('/')
@app.route('/themes/')
def showThemes():
    themes = session.query(Theme).all()
    if 'username' not in login_session:
        return render_template('publicthemes.html', themes=themes)
    else:
        return render_template('themes.html', themes=themes)


# Add new theme
@app.route('/themes/new', methods=['GET', 'POST'])
def newTheme():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        theme_to_add = request.form['name']
        print("theme to add", theme_to_add)
        theme_exists = session.query(Theme).filter_by(
                                     name=theme_to_add).first()
        if theme_exists:
            flash("Theme '%s' already exists" % theme_to_add)
            print("Theme %s already exists" % theme_to_add)
            return render_template('newtheme.html')
        else:
            new_theme = Theme(name=request.form['name'],
                              user_id=login_session['user_id'])
            print("new theme", new_theme)
            session.add(new_theme)
            session.commit()
            flash("New theme '%s' has been created" % new_theme.name)
            print("new theme created", new_theme.id)
            return redirect(url_for('showThemes'))
    else:
        return render_template('newtheme.html')


# Edit a theme
@app.route('/themes/<path:theme_name>/edit', methods=['GET', 'POST'])
def editTheme(theme_name):
    if 'username' not in login_session:
        return redirect('/login')
    edited_theme = session.query(Theme).filter_by(name=theme_name).one()
    temp = edited_theme.name
    if request.method == 'POST':
        theme_new_name = request.form['name']
        print("theme to add", theme_new_name)
        theme_exists = session.query(Theme).filter_by(
                                     name=theme_new_name).first()
        if theme_exists:
            flash("Theme '%s' already exists" % theme_new_name)
            print("Theme %s already exists" % theme_new_name)
            return render_template('edittheme.html', edited_theme=edited_theme)
        else:
            if request.form['name']:
                edited_theme.name = request.form['name']
        session.add(edited_theme)
        session.commit()
        flash("Theme '%s' has been edited" % temp)
        return redirect(url_for('showThemes'))
    else:
        return render_template('edittheme.html', edited_theme=edited_theme)


# Delete a theme
@app.route('/themes/<path:theme_name>/delete', methods=['GET', 'POST'])
def deleteTheme(theme_name):
    if 'username' not in login_session:
        return redirect('/login')
    deleted_theme = session.query(Theme).filter_by(name=theme_name).one()
    deleted_paintings = session.query(Painting).filter_by(
                                      theme_id=deleted_theme.id).all()
    print("Paintings to delete", deleted_paintings)
    if request.method == 'POST':
        session.delete(deleted_theme)
        for i in deleted_paintings:
            print("deleting painting", i)
            session.delete(i)
        session.commit()
        flash("Theme '%s' has been deleted" % deleted_theme.name)
        print("theme deleted", deleted_theme.id)
        return redirect(url_for('showThemes'))
    else:
        return render_template('deletetheme.html', deleted_theme=deleted_theme)


# Show all paintings
@app.route('/themes/<path:theme_name>/')
@app.route('/themes/<path:theme_name>/paintings')
def showPaintings(theme_name):
    theme = session.query(Theme).filter_by(name=theme_name).one()
    themes = session.query(Theme).all()
    paintings = session.query(Painting).filter_by(theme_id=theme.id).all()
    creator = getUserInfo(theme.user_id)
    if ('username' not in login_session):
        return render_template('publicpaintings.html',
                               theme=theme, themes=themes, paintings=paintings,
                               creator=creator)
    else:
        current_user_id = login_session['user_id']
        return render_template('paintings.html', theme=theme, themes=themes,
                               paintings=paintings, creator=creator,
                               current_user_id=current_user_id)


# Show one particular painting
@app.route('/themes/<path:theme_name>/paintings/<path:paintings_name>')
def showPainting(theme_name, paintings_name):
    print ("*****theme*****", theme_name)
    theme = session.query(Theme).filter_by(name=theme_name).one()
    painting = session.query(Painting).filter_by(name=paintings_name,
                                                 theme_id=theme.id).one()
    creator = getUserInfo(theme.user_id)
    if ('username' not in login_session or
            creator.id != login_session['user_id']):
        return render_template('publicpainting.html', theme=theme,
                               painting=painting, creator=creator)
    else:
        return render_template('painting.html', theme=theme, painting=painting,
                               creator=creator)


# Add new painting
@app.route('/themes/<path:theme_name>/paintings/new', methods=['GET', 'POST'])
def newPainting(theme_name):
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        themes = session.query(Theme).all()
        painting_to_add = request.form['name']
        painting_exists = \
            session.query(Painting).filter_by(name=painting_to_add).first()
        if painting_exists:
            flash("Painting '%s' already exists" % painting_to_add)
            return render_template('newpainting.html', theme_name=theme_name,
                                   themes=themes)
        else:
            theme_name = request.form['themename']
            theme = session.query(Theme).filter_by(name=theme_name).first()
            theme_id = theme.id
            new_painting = Painting(name=request.form['name'],
                                    theme_id=theme_id,
                                    user_id=login_session['user_id'])
            new_painting.description = request.form['description']
            new_painting.year = request.form['year']
            session.add(new_painting)
            session.commit()
            flash("New painting '%s' has been added" % new_painting.name)
            return redirect(url_for('showPaintings', theme_name=theme_name))
    else:
        themes = session.query(Theme).all()
        return render_template('newpainting.html', theme_name=theme_name,
                               themes=themes)


# Edit a painting
@app.route('/themes/<path:theme_name>/paintings/<path:paintings_name>/edit',
           methods=['GET', 'POST'])
def editPainting(theme_name, paintings_name):
    if 'username' not in login_session:
        return redirect('/login')
    theme = session.query(Theme).filter_by(name=theme_name).one()
    edited_painting = \
        session.query(Painting).filter_by(name=paintings_name,
                                          theme_id=theme.id).one()
    if edited_painting.user_id != login_session['user_id']:
        alert = "<script>function myFunction()"
        alert += " {alert('Sorry, you can only edit paintings added "
        alert += "by you.'); window.history.back();}</script>"
        alert += "<body onload='myFunction()'>"
        return alert
    if request.method == 'POST':
        theme = session.query(Theme).filter_by(id=theme.id).first()
        themes = session.query(Theme).all()
        painting_to_edit = request.form['name']
        painting_exists = \
            session.query(Painting).filter_by(name=painting_to_edit).first()
        if painting_exists:
            flash("Painting '%s' already exists" % painting_to_edit)
            print("Painting %s already exists" % painting_to_edit)
            return render_template('editpainting.html', theme_id=theme.id,
                                   theme_name=theme.name,
                                   edited_painting=edited_painting,
                                   themes=themes)
        else:
            theme_name = request.form['themename']
            theme = session.query(Theme).filter_by(name=theme_name).first()
            theme_id = theme.id
            if request.form['name']:
                edited_painting.name = request.form['name']
            if request.form['description']:
                edited_painting.description = request.form['description']
            if request.form['year']:
                edited_painting.year = request.form['year']
            if request.form['themename']:
                theme_name = request.form['themename']
                theme = session.query(Theme).filter_by(name=theme_name).first()
                edited_painting.theme_id = theme.id
            session.add(edited_painting)
            session.commit()
        flash("Painting '%s' has been edited" % edited_painting.name)
        return redirect(url_for('showPaintings', theme_name=theme_name))
    else:
        theme = session.query(Theme).filter_by(id=theme.id).first()
        themes = session.query(Theme).all()
        return render_template('editpainting.html', theme_id=theme.id,
                               theme_name=theme.name,
                               edited_painting=edited_painting,
                               themes=themes)


# Delete a painting
@app.route('/themes/<path:theme_name>/paintings/<path:paintings_name>/delete',
           methods=['GET', 'POST'])
def deletePainting(theme_name, paintings_name):
    if 'username' not in login_session:
        return redirect('/login')
    theme = session.query(Theme).filter_by(name=theme_name).one()
    deleted_painting = \
        session.query(Painting).filter_by(name=paintings_name,
                                          theme_id=theme.id).one()
    if request.method == 'POST':
        session.delete(deleted_painting)
        session.commit()
        flash("Painting '%s' has been deleted" % deleted_painting.name)
        return redirect(url_for('showPaintings', theme_name=theme_name))
    else:
        return render_template('deletepainting.html', theme_name=theme_name,
                               deleted_painting=deleted_painting)


#################################
# Helper functions for user authentification
#################################

# Retrieve a user ID based on the email address
def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


# Retrieve a user info from the database
def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


# Create a new user in the database
def createUser(login_session):
    newUser = \
        User(name=login_session['username'], email=login_session['email'],
             picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
