from airflow.plugins_manager import AirflowPlugin
from airflow.www.app import csrf
from airflow.models import DagBag, DagRun
from airflow.utils.state import State
from airflow.utils import timezone
from flask_appbuilder import expose, BaseView as AppBuilderBaseView
from flask import Flask, Blueprint, render_template, request, flash, jsonify
from flask_jwt_extended import JWTManager, create_access_token
from wtforms.validators import ValidationError, InputRequired, EqualTo
from wtforms import Form, StringField, IntegerField, EmailField, RadioField, SelectField, validators
import os
from pprint import pprint
from datetime import datetime
from flask_jwt_extended import JWTManager, create_access_token
from flask import current_app
from airflow.www.app import csrf

bp = Blueprint(
               "downstream_json",
               __name__,
               template_folder="templates", 
               )
login_bp = Blueprint('login', __name__)

"""Defining the class for each directives"""
class MyForm(Form):
    projname = StringField('Project Name', render_kw={"placeholder": "Enter your Project name"})


@login_bp.route('/login_without_cookies', methods=['POST'])
@csrf.exempt
def login_without_cookies():
    print("Received POST request to /login_without_cookies")
    # Replace this with your actual user authentication logic
    # For simplicity, always generate an access token for demonstration purposes
    access_token = create_access_token(identity='demo_user')
    return jsonify(access_token=access_token)

class DownstreamBasejsonView(AppBuilderBaseView):
    default_view = "downstreamjsonrun"
    @expose("/", methods=['GET', 'POST'])
    @csrf.exempt 
    def downstreamjsonrun(self):
        now = datetime.now()
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
        form = MyForm(request.form)
        if  request.method == 'POST' and form.validate():
            run_id = form.projname.data + dt_string
            dagbag = DagBag('dags')
            dag = dagbag.get_dag('downstream_json')
            dag.create_dagrun(
                run_id=run_id,        
                state=State.RUNNING,
                conf={'projname':form.projname.data}
            )
            data = {}
            data['projname'] = form.projname.data
            data['status_url'] = f"http://{os.environ['AIRFLOW_URL']}:{os.environ['AIRFLOW_PORT']}/dags/downstream_json/graph"
            pprint(dagbag)          
            return self.render_template("downstream_json_response.html", data = data)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{error}')
            return self.render_template("downstream_json.html", form = form)


v_appbuilder_view = DownstreamBasejsonView()
v_appbuilder_package = {
    "name": "Downstream json Analysis",    # this is the name of the link displayed
    "category": "Downstream Runs", # This is the name of the tab under     which we have our view
    "view": v_appbuilder_view
}

if v_appbuilder_view.blueprint is None:
    v_appbuilder_view.blueprint = Blueprint("downstream_json", __name__)

# Register the login Blueprint
v_appbuilder_view.blueprint.register_blueprint(login_bp)

class AirflowPlugin(AirflowPlugin):
    name = "downstream_json"
    operators = []
    flask_blueprints = [bp, login_bp]
    hooks = []
    executors = []
    admin_views = []
    appbuilder_views = [v_appbuilder_package]

