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
from airflow.providers.ssh.hooks.ssh import SSHHook
from airflow.providers.mysql.hooks.mysql import MySqlHook
import os
import fnmatch
from pprint import pprint
from datetime import datetime
import mysql.connector
import re
from nyuad_cgsb_jira_client.jira_client import jira_client




bp = Blueprint(
               "downstream_sequence",
               __name__,
               template_folder="templates", 
               )


"""Function to select/choose the qc_workflow file from jubail."""
def qc_workflow():    
    # sftp = ssh.open_sftp()
    # Below 3 lines based on airflow ssh connection defined.
    ssh_hook = SSHHook(ssh_conn_id='guru_ssh')
    ssh_client = ssh_hook.get_conn()
    sftp = ssh_client.open_sftp()
    qc_file = [None]
    try:
        dir = os.environ.get('QC_WORKDIR')
        for filename in sftp.listdir(dir):
            if fnmatch.fnmatch(filename, "qc-qt-noconcat*.yml"):
                qc_file.append('{}{}'.format(dir, filename))
        sftp.close()
    except FileNotFoundError as e:
        raise ValidationError('QC_Workflow path not visible, Contact Airflow admin')
    return qc_file



"""Function to check if the work directory given is exist or not."""
def file_validate(form, field):
    # Below 3 lines based on airflow ssh connection defined.
    ssh_hook = SSHHook(ssh_conn_id='guru_ssh')
    ssh_client = ssh_hook.get_conn()
    sftp = ssh_client.open_sftp()
    dir = field.data
    try:
        files = sftp.listdir(dir)
    except FileNotFoundError as e:
        raise ValidationError(f'Directory path {dir} does not exist on the remote server')
    sftp.close()

"""Function to validate multiple email address syntax."""
def validate_emails(form, field):
    emails = field.data
    email_id = field.data.split(',')
    regex = r'^\S+@\S+\.\S+$'
    invalid_emails = []
    for email in email_id:
        if not re.match(regex, email.strip()):
            invalid_emails.append(email.strip())
    if invalid_emails:
        raise ValidationError('Invalid email address format: {}'.format(', '.join(invalid_emails)))

"""Function to check the jira ticket existence"""
def validate_jira_ticket(form, field):
    ticket_id = field.data
    try:
        issue = jira_client.issue(id=ticket_id)
        description = issue.fields.description
        return issue, description
    except Exception as e:
            print(f"Error connecting to Jira: {e}")
            raise ValidationError(f'Jira Ticket ID {ticket_id} not found in the system')



"""Defining the class for each directives"""
class MyForm(Form):
    projname = StringField('Project Name', render_kw={"placeholder": "Enter your Project name"})
    email_address = StringField('Email Address', [InputRequired(),validate_emails], render_kw={"placeholder": "Specify email by one or many seperated by comma"})
    qc_workflow = SelectField('Workflow', choices=[(choice, choice) for choice in qc_workflow()])
    demux_dir = StringField('Demux Directory',[InputRequired(),file_validate], render_kw={"placeholder": "Specify the Demux Directory path - eg:- /scratch/gencore/XXXX/UnAligned"})
    jira_ticket = StringField('Jira Ticket', [InputRequired(),validate_jira_ticket], render_kw={"placeholder": "Enter the Jira ticket number: (eg:- NCS-222)"})
    filepath = StringField('File path ')
    sample_name = StringField('Sample Names')
    scratch_dir = StringField('Scratch Directory')
    archive_dir = StringField('Archive Directory')

class DownstreamBaseView(AppBuilderBaseView):
    default_view = "downstreamrun"
    @expose("/", methods=['GET', 'POST'])
    @csrf.exempt 
    def downstreamrun(self):
        now = datetime.now()
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
        form = MyForm(request.form)
        if  request.method == 'POST' and form.validate():
            run_id = form.projname.data + dt_string
            scratch_dir_value = form.demux_dir.data.replace("/archive/jr5241", "/scratch/jr5241")
            form.scratch_dir.data = scratch_dir_value
            archive_dir_value = form.demux_dir.data.replace("/archive/gencoreseq", "/archive/gencore")
            form.archive_dir.data = archive_dir_value
            issue, description = validate_jira_ticket(form, form.jira_ticket)
            dagbag = DagBag('dags')
            dag = dagbag.get_dag('downstream_sequence')
            dag.create_dagrun(
                run_id=run_id,        
                state=State.RUNNING,
                conf={'scratch_dir':form.scratch_dir.data,  'archive_dir':form.archive_dir.data, 'demux_dir':form.demux_dir.data, 'jira_ticket':form.jira_ticket.data, 'projname':form.projname.data, 'email_id':form.email_address.data,  'qc_workflow':form.qc_workflow.data }
            )
            data = {}
            data['projname'] = form.projname.data
            data['qc_workflow'] = form.qc_workflow.data
            data['email_address'] = form.email_address.data
            data['demux_dir'] = form.demux_dir.data
            data['jira_ticket'] = form.jira_ticket.data
            data['jira_ticket_des'] = description
            data['scratch_dir'] = form.scratch_dir.data
            data['archive_dir'] = form.archive_dir.data
            data['status_url'] = f"http://{os.environ['AIRFLOW_URL']}:{os.environ['AIRFLOW_PORT']}/dags/downstream_sequence/graph"
            pprint(dagbag)          
            return self.render_template("downstream_response.html", data = data)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{error}')
            return self.render_template("downstream.html", form = form)


v_appbuilder_view = DownstreamBaseView()
v_appbuilder_package = {
    "name": "Default Downstream Analysis",    # this is the name of the link displayed
    "category": "Downstream Runs", # This is the name of the tab under     which we have our view
    "view": v_appbuilder_view
}


class AirflowPlugin(AirflowPlugin):
    name = "downstream_sequence"
    operators = []
    flask_blueprints = [bp]
    hooks = []
    executors = []
    admin_views = []
    appbuilder_views = [v_appbuilder_package]
