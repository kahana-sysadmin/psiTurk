from flask import Blueprint, render_template, request, jsonify, Response, abort, current_app, flash, session, g, redirect, url_for, abort
from flask_login import UserMixin, login_user, logout_user, current_user
from jinja2 import TemplateNotFound
from functools import wraps
from sqlalchemy import or_

from psiturk.psiturk_config import PsiturkConfig
from psiturk.experiment_errors import ExperimentError, InvalidUsage
from psiturk.user_utils import PsiTurkAuthorization, nocache
from psiturk.models import Participant

from psiturk.amt_services_wrapper import MTurkServicesWrapper
amt_services_wrapper = MTurkServicesWrapper()
# # Database setup
from psiturk.db import db_session, init_db
from psiturk.models import Participant
from json import dumps, loads

# load the configuration options
config = PsiturkConfig()
config.load_config()
# if you want to add a password protect route use this
myauth = PsiTurkAuthorization(config)

# import the Blueprint
dashboard = Blueprint('dashboard', __name__,
                        template_folder='templates', static_folder='static', url_prefix='/dashboard')       

from psiturk.experiment import app
from flask_login import LoginManager, UserMixin
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'dashboard.login'

class DashboardUser(UserMixin):
    def __init__(self, username=''):
        self.id = username

@login_manager.user_loader
def load_user(username):
    return DashboardUser(username=username)


# def check_login(func):
    # @wraps(func)
    # def check_it(*args, **kwargs):
        # g.logged_in = 'logged_in' in session
        # return func(*args, **kwargs)
    # return check_it
    
# @check_login
def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        is_logged_in = current_user.get_id() is not None
        is_static_resource_call = str(request.endpoint) == 'dashboard.static'
        is_login_route = str(request.url_rule) == '/dashboard/login'
        if not (is_static_resource_call or is_login_route or is_logged_in):
            return login_manager.unauthorized()
        return view(**kwargs)
    return wrapped_view

@dashboard.before_request
@login_required
def before_request():
    pass

@dashboard.route('/all_worker_data')
def all_worker_data():
    all_workers = [worker.object_as_dict(filter_these=['datastring']) for worker in Participant.query.filter(Participant.mode != 'debug').all()]
    return render_template('dashboard/all_worker_data.html', data=all_workers)
    

@dashboard.route('/index')
@dashboard.route('/')
@login_required
def index():
    # this should be a db query... or the result of a call to one encapsulated in the wrapper...
    workers_count_response = amt_services_wrapper.count_workers(codeversion=None)
    
    if workers_count_response.success:
        workers_count = [list(worker_count.items()) for worker_count in workers_count_response.data]
        
    all_workers = Participant.query.filter(Participant.mode != 'debug').all()
    
    return render_template('dashboard/index.html', 
        workers_count=workers_count, 
        data_keys= ['codeversion','mode','status','count'],
        all_worker_data=[worker.object_as_dict(filter_these=['datastring']) for worker in all_workers])
    
@dashboard.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username= request.form['username']
        password= request.form['password']
        success = myauth.check_auth(username, password)
        
        if not success:
            error = 'Incorrect username or password'
            flash(error)
        else:
            user = DashboardUser(username=username)
            login_user(user)
            flash("Logged in successfully.")
            next = request.args.get('next')
            return redirect(next or url_for('.index'))
    return render_template('dashboard/login.html')
    
@dashboard.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.')
    return redirect(url_for('.login'))