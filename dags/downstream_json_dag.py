from datetime import datetime
from airflow import DAG
from airflow.providers.ssh.operators.ssh import SSHOperator
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.providers.ssh.hooks.ssh import SSHHook

"""Loading python dag run scripts"""
# from seq_dags.archive_seq  import archive_scratch_dir_folder
# from seq_dags.demultiplex_seq import run_demultiplex_task
# from seq_dags.email_pre_seq import run_pre_email_task
# from seq_dags.email_post_seq import run_post_email_task
# from seq_dags.submit_qc_workflow_seq import submit_qc_workflow_to_slurm


"""Loading jira module"""
# from nyuad_cgsb_jira_client.jira_client import jira_client


"""Defining dag profiles, schedule_interval is set to None, since it is based on trigger based dagrun"""

dag = DAG('downstream_json', description='Downstream Sequence DAG',
          schedule_interval=None,
          start_date=datetime(2023, 4, 1), catchup=False)

"""Retriving ssh connection parameter"""
ssh_hook = SSHHook(ssh_conn_id='guru_ssh')
ssh_hook.no_host_key_check = True


# rsync_work_to_scratch_command = """
#         mkdir -p {{ dag_run.conf["scratch_dir"] }}
#         rsync -av "{{ dag_run.conf["work_dir"] }}/" "{{ dag_run.conf["scratch_dir"] }}/"
# """

# rsync_work_to_scratch_task = SSHOperator(
#     task_id='rsync_work_to_scratch',
#     ssh_hook=ssh_hook,
#     command=rsync_work_to_scratch_command,
#     dag=dag
# )

def print_message():
    print("This is just a testing dag")

print_message_task = PythonOperator(
    task_id='print_message_task',
    python_callable=print_message,
    dag=dag,
)


"""Defining the DAG workflow"""
print_message_task


"""Procedure ends"""
