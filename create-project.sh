#!/bin/bash

# Root files
touch README.md
touch requirements.txt
touch pyproject.toml
touch run.py
touch wsgi.py
touch Dockerfile
touch .gitignore
touch .env.example

# Root directories
mkdir -p migrations
mkdir -p instance
mkdir -p uploads
mkdir -p tests

touch instance/.gitkeep
touch uploads/.gitkeep

# App structure
mkdir -p app

touch app/__init__.py
touch app/config.py
touch app/extensions.py

############################
# Models
############################

mkdir -p app/models

touch app/models/__init__.py
touch app/models/organization.py
touch app/models/contact.py
touch app/models/job_posting.py
touch app/models/application.py
touch app/models/activity.py
touch app/models/task.py
touch app/models/skill.py
touch app/models/associations.py

############################
# Feature Blueprints
############################

for module in organizations contacts jobs applications dashboard tasks auth
do
    mkdir -p app/$module

    touch app/$module/__init__.py
    touch app/$module/routes.py
    touch app/$module/forms.py
    touch app/$module/services.py
done

touch app/auth/models.py

############################
# Commands
############################

mkdir -p app/commands

touch app/commands/__init__.py
touch app/commands/seed.py
touch app/commands/import_jobs.py

############################
# Utilities
############################

mkdir -p app/utils

touch app/utils/__init__.py
touch app/utils/dates.py
touch app/utils/enums.py
touch app/utils/pagination.py
touch app/utils/validators.py

############################
# Templates
############################

mkdir -p app/templates

touch app/templates/base.html

mkdir -p app/templates/macros

touch app/templates/macros/forms.html
touch app/templates/macros/tables.html
touch app/templates/macros/status_badges.html

for page in dashboard organizations contacts jobs applications tasks
do
    mkdir -p app/templates/$page
done

touch app/templates/dashboard/index.html

touch app/templates/organizations/index.html
touch app/templates/organizations/detail.html
touch app/templates/organizations/form.html

touch app/templates/contacts/index.html
touch app/templates/contacts/detail.html
touch app/templates/contacts/form.html

touch app/templates/jobs/index.html
touch app/templates/jobs/detail.html
touch app/templates/jobs/form.html

touch app/templates/applications/index.html
touch app/templates/applications/detail.html
touch app/templates/applications/form.html

touch app/templates/tasks/index.html
touch app/templates/tasks/detail.html
touch app/templates/tasks/form.html

############################
# Static
############################

mkdir -p app/static/css
mkdir -p app/static/js
mkdir -p app/static/uploads

touch app/static/css/app.css
touch app/static/js/app.js

############################
# Tests
############################

touch tests/conftest.py
touch tests/test_models.py
touch tests/test_organizations.py
touch tests/test_contacts.py
touch tests/test_jobs.py
touch tests/test_applications.py
touch tests/test_tasks.py
touch tests/test_scoring.py

echo ""
echo "=========================================="
echo "Project structure created successfully."
echo "Location: $(pwd)"
echo "=========================================="