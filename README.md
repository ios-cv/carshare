IOS-CV Car Share
================

This is the server/web application that powers the GO-EV Car Share scheme on the Isles of Scilly.

The project is run by the [Isles of Scilly Community Venture CIC](https://www.ioscv.co.uk) and is
licensed under the GNU AGPL v3 licence. It provides a web application and server component implemented
in python/Django that works with the [MaxBox](https://github.com/ios-cv/maxbox) in vehicle "box" to
provide a fully integrated community car share management system.

## Contributing

We are happy to receive issues and pull requests. If you are interested in exploring substantial changes
or new features, please contact us first to discuss via email or Github Issues. If you are interested in
adopting this stack for your own community car share project (or something else) we'd love to hear from
you.

## Getting Started

This repository contains a single codebase following the standard 
[Django](https://www.djangoproject.com/) patterns. Dependencies are  managed with
[poetry](https://python-poetry.org/). Front-end UI is implemented using Django templates and
[Tailwind](https://tailwindcss.com/).

First, clone this repository, then set up the dependencies with docker by running:

    $ make start-docker

Install dependencies (setting up a virtualenvironment in your preferred way first):

    $ poetry install

Initialise the database, and setup a super user.

    $ poetry run python manage.py migrate
    $ poetry run python manage.py createsuperuser

Install the customised version of `crispy-tailwind`.

    $ make setup-crispy-tailwind

Install the theme JS dependencies.

    $ cd theme/static_src
    $ npm install
    $ cd ../..

To keep the stylesheets up to date, you should have the django tailwind task running while using your
development environment:

    $ poetry run python manage.py tailwind start

Finally, in another terminal, you can start the development server:

    $ poetry run python manage.py runserver

and access the login page through your browser:

    http://localhost:8000/users/login

### Tips & Tricks

The backoffice and Django admin areas can be found at:

    http://localhost:8000/backoffice
    http://localhost:8000/admin

We use the _black_ python code style. You can reformat your code changes before you commit:

    $ make format

Happy hacking!

