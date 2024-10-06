#!/bin/bash
set -e

# Initiate the metadata database
airflow db init

# Create an initial user, if necessary
airflow users create \
    --username admin \
    --firstname Airflow \
    --lastname Admin \
    --role Admin \
    --email admin@example.com \
    --password admin

# Start the Airflow scheduler in the background
airflow scheduler &

# Start the Airflow webserver
exec airflow webserver
