from datetime import datetime
from typing import List
from google.cloud import storage

import pandas as pd
import os
from airflow.providers.google.cloud.hooks.gcs import GCSHook
from airflow.decorators import dag, task # DAG and task decorators for interfacing with the TaskFlow API

bucket_name = "corise-airflow-scott-week-one"
location = 'US'
storage_class = 'STANDARD'
client = GCSHook()

@dag(
    # This defines how often your DAG will run, or the schedule by which your DAG runs. In this case, this DAG
    # will run daily
    schedule_interval="@daily",
    # This DAG is set to run for the first time on January 1, 2021. Best practice is to use a static
    # start_date. Subsequent DAG runs are instantiated based on scheduler_interval
    start_date=datetime(2021, 1, 1),
    # When catchup=False, your DAG will only run for the latest schedule_interval. In this case, this means
    # that tasks will not be run between January 1, 2021 and 30 mins ago. When turned on, this DAG's first
    # run will be for the next 30 mins, per the schedule_interval
    catchup=False,
    default_args={
        "retries": 2, # If a task fails, it will retry 2 times.
    },
    tags=['example']) # If set, this tag is shown in the DAG view of the Airflow UI
def energy_dataset_dag():
    """
    ### Basic ETL Dag
    This is a simple ETL data pipeline example that demonstrates the use of
    the TaskFlow API using two simple tasks to extract data from a zipped folder
    and load it to GCS.

    """
    @task
    def create_bucket(client, bucket_name, location, storage_class):

        bucket = client.create_bucket(
            bucket_name=bucket_name,
            storage_class=storage_class,
            project_id='airflow-week1',
            location=location
        )

        print(f"Created bucket {bucket_name} in {location} with storage class {storage_class}")

        return bucket


    @task
    def extract() -> List[pd.DataFrame]:
        """
        #### Extract task
        A simple task that loads each file in the zipped file into a dataframe,
        building a list of dataframes that is returned.

        """
        from zipfile import ZipFile
        # TODO Unzip files into pandas dataframes
        files_zipped = ZipFile(f"{os.getenv('AIRFLOW_HOME')}/dags/data/energy-consumption-generation-prices-and-weather.zip")
        files_unzipped = [pd.read_csv(files_zipped.open(file_name)) for file_name in files_zipped.namelist()]
        return files_unzipped



    @task
    def load(bucket_name: str, client: str, unzip_result: List[pd.DataFrame]):
        """
        #### Load task
        A simple "load" task that takes in the result of the "transform" task, prints out the 
        schema, and then writes the data into GCS as parquet files.
        """

        data_types = ['generation', 'weather']

        # GCSHook uses google_cloud_default connection by default, so we can easily create a GCS client using it
        # https://github.com/apache/airflow/blob/207f65b542a8aa212f04a9d252762643cfd67a74/airflow/providers/google/cloud/hooks/gcs.py#L133

        # The google cloud storage github repo has a helpful example for writing from pandas to GCS:
        # https://github.com/googleapis/python-storage/blob/main/samples/snippets/storage_fileio_pandas.py


        for name, data in zip(data_types, unzip_result):
            client.upload(bucket_name=bucket_name,
                          object_name =name,
                          data = data.to_parquet())
            print(f"SUCCESS: {name} written to {bucket_name}")

    # # TODO Add task linking logic here
    create_bucket(client, bucket_name, location, storage_class) 
    data_extract = extract()
    load(bucket_name, client, data_extract)


energy_dataset_dag = energy_dataset_dag()