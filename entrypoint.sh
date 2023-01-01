#!/usr/bin/env bash
# This is the entrypoint script for the Dockerfile

# Check that what to run is specified.
if [[ $# -eq 0 ]]; then
  echo You must specify what to run.
fi

# Launch the Django webapp.
if [[ "$1" = "app" ]]; then
  # Update the Django static files in the shared volume.
  echo Reinitialising static files...
  rm -rf /usr/src/app/static_root/*
  cp -rf static/* static_root/

  # Run the web server.
  echo Launching web app...
  gunicorn -w 3 -b 0.0.0.0:8000 carshare.wsgi --log-file -
fi
