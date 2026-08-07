# Career CRM

Career CRM is a web-based customer relationship management (CRM) application designed specifically for managing a professional job search.

Rather than functioning as a simple application tracker, Career CRM serves as a centralized system for organizing organizations, professional contacts, job postings, applications, networking activities, follow-ups, and career analytics.

The project is being developed as a portfolio-quality full-stack application using modern Python web technologies while simultaneously serving as a daily driver for managing a real-world job search.

---

# Project Goals

The primary goals are to:

* Track organizations and employers
* Maintain professional networking contacts
* Organize job postings
* Track applications through the hiring pipeline
* Record networking and recruiting interactions
* Manage follow-up tasks and reminders
* Produce analytics that improve job-search decision making
* Provide a clean, responsive interface for desktop and mobile devices

The application should become the single source of truth for all career-related information.

---

# Long-Term Vision

Career CRM is intended to evolve beyond a personal job tracker into a multi-user platform that enables professionals to organize and manage complex job searches while sharing useful industry information.

The application architecture should remain modular, extensible, and maintainable so that future features can be added without major redesign.

---

# User Model

Authentication is required for all users.

Each authenticated user has a private workspace that contains their own job search information.

Private information includes:

* Applications
* Contacts
* Activities
* Tasks
* Documents
* Personal notes
* Dashboard metrics
* Interview history
* Follow-up history

Users cannot view another user's private information.

---

# Shared Data

Certain reference information is intended to be shared among all authenticated users to reduce duplication and encourage collaboration.

Shared entities include:

* Organizations
* Job Postings
* Skills
* Organization metadata

Shared records should include audit information such as:

* created_by
* updated_by
* created_at
* updated_at

This allows multiple users to benefit from common employer information while maintaining ownership history.

---

# Data Ownership

The project separates data into two categories.

## Shared

Reference information that benefits all users.

Examples:

* Organizations
* Skills
* Job Postings

## Private

Information unique to an individual's job search.

Examples:

* Applications
* Contacts
* Activities
* Tasks
* Notes
* Documents

Private records include an `owner_id` and are accessible only by the owning user.

---

# Technology Stack

Current planned stack:

* Python
* Flask
* SQLAlchemy
* Flask-Migrate
* Flask-WTF
* Bootstrap 5
* Jinja2

SQLite is supported for rapid local iteration and tests. PostgreSQL is the production database, with connection health checks and pooling configured through SQLAlchemy.

The supplied production deployment uses:

* Docker
* Docker Compose
* PostgreSQL
* Gunicorn
* Nginx

---

# Development Philosophy

The application is developed incrementally using milestones.

Each milestone introduces a single major feature while ensuring:

* Existing functionality continues to work.
* Existing tests continue to pass.
* Database migrations remain clean.
* Business logic stays isolated from routes.
* The architecture remains maintainable.

---

# Version 1.0 Features

Version 1.0 includes authentication and onboarding, shared organizations and jobs, private contacts/applications/activities/tasks, dashboard analytics, weighted skill matching, private versioned documents, global and saved search, CSV/XLSX/PDF reports, local notifications, PostgreSQL and Docker deployment, responsive views, importer adapters, optional AI assistance, moderated collaboration, and a bearer-authenticated REST API.

See [Installation](docs/INSTALLATION.md), [Deployment](docs/DEPLOYMENT.md), [API](docs/API.md), [Security](SECURITY.md), and the [Changelog](CHANGELOG.md).

---

# Target Deployment

The initial deployment target is a self-hosted instance running on the developer's home server.

The application should be accessible from:

* macOS
* Linux
* iPhone
* Other devices on the local network

Future deployment should support secure remote access through a reverse proxy and HTTPS without requiring major application changes.

---

# Design Principles

The project emphasizes:

* Clean architecture
* Separation of concerns
* Strong database design
* Test-driven development
* Reusable components
* Responsive user interface
* Maintainable code
* Modular feature development

---

# Long-Term Possibilities

Potential future enhancements include:

* Resume version management
* Cover letter management
* Email integration
* Calendar integration
* AI-assisted job matching
* Career analytics dashboards
* Shared employer intelligence
* Team workspaces
* REST API
* Mobile application
* Browser extension for saving job postings

The versioned importer, AI-provider, background-job, and API boundaries are intended to support these integrations without redesigning core business logic.

---

# License

This project is currently under active development.

A license will be selected prior to public release.
