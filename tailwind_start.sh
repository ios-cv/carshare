#!/usr/bin/env zsh
. ~/.nvm/nvm.sh
nvm use --lts
poetry run python manage.py tailwind start

