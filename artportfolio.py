from flask import Flask, render_template, url_for, redirect, request, flash, jsonify
app = Flask(__name__)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Theme, Painting, User

from flask import session as login_session
import random, string

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests


engine = create_engine('sqlite:///artportfolio.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind = engine)
session = DBSession()



#################################
# Making API Endpoints
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
#
#################################

# Show all themes
@app.route('/')
@app.route('/themes/')
def showThemes():
    themes = session.query(Theme).all()
    if 'username' not in login_session:
        return render_template('themes.html', themes=themes)
    else:
        return render_template('themes.html', themes=themes)


# Add new theme
@app.route('/themes/new', methods=['GET', 'POST'])
def newTheme():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        new_theme = Theme(name = request.form['name'],
            user_id = login_session['user_id'])
        print("new theme", new_theme)
        session.add(new_theme)
        session.commit()
        flash("new theme created!")
        print("new theme created")
        return redirect(url_for('showThemes'))
    else:
        return render_template('newtheme.html')


# Edit a theme
@app.route('/themes/<int:theme_id>/edit', methods=['GET', 'POST'])
def editTheme(theme_id):
    if 'username' not in login_session:
        return redirect('/login')
    edited_theme = session.query(Theme).filter_by(id = theme_id).one()
    if edited_theme.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized \
        to edit this theme.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        if request.form['name']:
            edited_theme.name = request.form['name']
        session.add(edited_theme)
        session.commit()
        flash("Theme has been edited!")
        return redirect(url_for('showThemes'))
    else:
        return render_template('edittheme.html', edited_theme=edited_theme)


# Delete a theme
@app.route('/themes/<int:theme_id>/delete', methods=['GET', 'POST'])
def deleteTheme(theme_id):
    if 'username' not in login_session:
        return redirect('/login')
    deleted_theme = session.query(Theme).filter_by(id = theme_id).one()
    if deleted_theme.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized \
        to delete this theme.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        session.delete(deleted_theme)
        session.commit()
        flash("Theme has been deleted!")
        return redirect(url_for('showThemes'))
    else:
        return render_template('deletetheme.html', deleted_theme=deleted_theme)


# Show all paintings
@app.route('/themes/<int:theme_id>/')
@app.route('/themes/<int:theme_id>/paintings')
def showPaintings(theme_id):
    theme = session.query(Theme).filter_by(id = theme_id).one()
    themes = session.query(Theme).all()
    paintings = session.query(Painting).filter_by(theme_id = theme.id).all()
    creator = getUserInfo(theme.user_id)
    if 'username' not in login_session or creator.id != login_session['user_id']:
        return render_template('publicpaintings.html', theme=theme, themes=themes, paintings=paintings,
        creator = creator)
    else:
        return render_template('paintings.html', theme=theme, themes=themes, paintings=paintings,
        creator = creator)


# Add new painting
@app.route('/themes/<int:theme_id>/paintings/new', methods=['GET', 'POST'])
def newPainting(theme_id):
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        new_painting = Painting(name = request.form['name'], theme_id = theme_id,
            user_id = login_session['user_id'])
        new_painting.description = request.form['description']
        new_painting.year = request.form['year']
        session.add(new_painting)
        session.commit()
        flash("new painting created!")
        return redirect(url_for('showPaintings', theme_id = theme_id))
    else:
        return render_template('newpainting.html', theme_id = theme_id)


# Edit a painting
@app.route('/themes/<int:theme_id>/paintings/<int:paintings_id>/edit', methods=['GET', 'POST'])
def editPainting(theme_id, paintings_id):
    if 'username' not in login_session:
        return redirect('/login')
    edited_painting = session.query(Painting).filter_by(id = paintings_id, theme_id = theme_id).one()
    if request.method == 'POST':
        if request.form['name']:
            edited_painting.name = request.form['name']
        session.add(edited_painting)
        session.commit()
        if request.form['description']:
            edited_painting.description = request.form['description']
        session.add(edited_painting)
        session.commit()
        if request.form['year']:
            edited_painting.year = request.form['year']
        session.add(edited_painting)
        session.commit()
        flash("Painting has been edited!")
        return redirect(url_for('showPaintings', theme_id = theme_id))
    else:
        return render_template('editpainting.html', theme_id=theme_id, painting_id=paintings_id, edited_painting = edited_painting)


# Delete a painting
@app.route('/themes/<int:theme_id>/paintings/<int:paintings_id>/delete', methods=['GET', 'POST'])
def deletePainting(theme_id, paintings_id):
    if 'username' not in login_session:
        return redirect('/login')
    deleted_painting = session.query(Painting).filter_by(id = paintings_id, theme_id = theme_id).one()
    if request.method == 'POST':
        session.delete(deleted_painting)
        session.commit()
        flash("Painting has been deleted!")
        return redirect(url_for('showPaintings', theme_id = theme_id))
    else:
        return render_template('deletepainting.html', theme_id=theme_id, painting_id=paintings_id, deleted_painting = deleted_painting)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host = '0.0.0.0', port = 8000)
