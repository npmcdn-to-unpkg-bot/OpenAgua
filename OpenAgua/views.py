from flask import session, redirect, url_for, render_template
from flask_user import login_required
from flask_login import current_user

from OpenAgua import app

from .connection import connection

app.secret_key = app.config['SECRET_KEY']

@app.route('/')
def index():
    
    session['ti'] = '1/2000'
    session['tf'] = '12/2019'
    session['date_format'] = '%m/%Y'    
    
    if current_user.is_authenticated:
        return redirect(url_for('user_home.home'))
    else:
        return render_template('index.html')

@app.route('/template')
@login_required
def template():    
    return render_template('template.html')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404