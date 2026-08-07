# Career CRM

Career CRM is a multi-user web application for managing professional job searches, networking, applications, career development, and job-market intelligence.

It is designed to go beyond a basic application tracker. Career CRM combines traditional CRM workflows with career profiling, job matching, reminders, reporting, document management, and optional AI assistance.

The application is intended to support both individual job seekers and, over time, multiple users sharing selected employer and job-posting data while keeping personal career information private.

---

# Core Goals

Career CRM is designed to provide a single source of truth for a job search.

It should help users:

* Track organizations and employers
* Maintain professional contacts
* Save and manage job postings
* Track applications through hiring stages
* Record recruiting and networking activity
* Manage follow-ups and tasks
* Track interviews and outcomes
* Maintain career-profile information
* Identify relevant skills and gaps
* Compare jobs against career preferences
* Manage resumes, cover letters, and other documents
* Search across all job-search data
* Export and analyze search activity
* Import job postings from external sources
* Use optional AI assistance
* Access the application from desktop and mobile devices

---

# Technology Stack

Primary application stack:

* Python
* Flask
* SQLAlchemy 2.x
* Flask-Migrate
* Flask-Login
* Flask-WTF
* Jinja2
* Bootstrap 5
* PostgreSQL
* pytest

Development and deployment infrastructure:

* Docker
* Docker Compose
* Gunicorn
* Nginx
* Environment-based configuration
* Alembic migrations

The application is designed to remain portable across macOS and Linux development environments.

---

# Architecture

Career CRM uses a modular Flask architecture based on:

* Application Factory pattern
* Blueprints
* SQLAlchemy models
* Service layers
* Reusable authorization helpers
* Jinja templates
* Responsive Bootstrap UI
* Database migrations
* Automated tests

Business logic should remain outside route handlers wherever practical.

## Optional Career Profile and AI

The Career Profile is private, progressively editable, and never required to use
the dashboard or any core CRM workflow. Its dashboard card reports a weighted
completion score and can be snoozed or dismissed without sending email.

AI assistance is also optional. Providers implement the stable `AIProvider`
interface and are selected through **AI Settings**; routes and profile services do
not contain vendor-specific client code. OpenAI and the built-in deterministic
provider are included. Anthropic, Gemini, Ollama, LM Studio, or another backend can
be added by implementing and registering the same interface.

OpenAI uses each user's own API key and account. The key is encrypted with Fernet
before it is stored, is never rendered back to the browser, and is decrypted only
while constructing that user's provider for an explicit request. Set
`CREDENTIAL_ENCRYPTION_KEY` at runtime using a Fernet key; never commit it or bake
it into an image. Deterministic assistance requires no account or network access.

Generated output is always a suggestion. It is displayed for review and never
modifies profile records automatically. Career CRM remains fully functional when
AI is disabled or disconnected.

Routes handle HTTP interaction.

Services handle application logic.

Models represent persistent data.

Authorization rules are centralized rather than duplicated throughout the codebase.

---

# Authentication

Authentication is required.

Users may:

* Register
* Log in
* Log out
* Edit their profile
* Change their password
* Use persistent login where enabled

Passwords are securely hashed and never stored in plaintext.

Unauthenticated users cannot access CRM functionality.

---

# Multi-User Data Model

Career CRM separates data into two major categories:

## Shared Data

Shared entities may be viewed by authenticated users.

Examples:

* Organizations
* Job Postings
* Skills

Shared records may include audit information such as:

* created_by
* updated_by
* created_at
* updated_at

Shared records can be reused by multiple users without duplicating employer or job-posting information.

## Private Data

Private entities belong to an individual user.

Examples:

* Contacts
* Applications
* Activities
* Tasks
* Career Profiles
* Education records
* Certifications
* User Skills
* Career Priorities
* Portfolio information
* Documents
* Private reports

Private records are scoped to their owner.

Users cannot access another user's private records through lists, searches, guessed URLs, or direct object IDs.

---

# Authorization

Career CRM enforces object-level permissions.

Private data:

* visible only to the owner
* editable only by the owner
* deletable only by the owner

Where administrator privileges exist, administrative overrides may be supported.

Unauthorized attempts to access private records should not reveal whether those records exist.

Shared records may use creator/editor permissions.

---

# Organizations

Organizations represent employers, research institutes, universities, companies, government agencies, recruiters, and other entities relevant to a job search.

Organization functionality includes:

* Create
* Read
* Update
* Delete
* Search
* Sort
* Filter
* Pagination
* Priority
* Organization type
* Location
* Website
* Notes

Organizations may be linked to:

* Contacts
* Job Postings
* Activities
* Tasks

Organizations are designed as shared reference entities.

---

# Contacts

Contacts represent individuals involved in professional networking or hiring.

Examples:

* Hiring managers
* Recruiters
* Principal investigators
* Engineering managers
* HR representatives
* Research coordinators
* Professional contacts

Contact information may include:

* Name
* Organization
* Title
* Department
* Email
* Phone
* LinkedIn
* Notes
* Last-contact date

Contacts are private to each user.

---

# Job Postings

Job Postings represent specific employment opportunities.

Fields may include:

* Organization
* Title
* Department
* Location
* Employment type
* Work mode
* Salary range
* Currency
* Posting URL
* Source
* Date posted
* Closing date
* Priority
* Status
* Description
* Notes

Supported workflows include:

* Search
* Sorting
* Filtering
* Pagination
* Organization integration
* Shared visibility

Job Postings are intended to be reusable shared reference records.

---

# Applications

Applications track a user's interaction with a specific Job Posting.

Application stages may include:

* Planned
* Preparing
* Applied
* Screening
* Phone Interview
* Technical Interview
* Panel Interview
* Final Interview
* Offer
* Accepted
* Rejected
* Withdrawn

Application records may include:

* Application date
* Resume version
* Cover-letter version
* Recruiter information
* Interview dates
* Salary requested
* Offer salary
* Rejection reason
* Notes

Applications are private to each user.

---

# Activities

Activities provide a chronological history of job-search interactions.

Examples:

* Email sent
* Email received
* LinkedIn message
* Phone call
* Interview
* Networking conversation
* Recruiter contact
* Application submission
* Follow-up
* Research note
* Meeting

Activities may be associated with:

* Organization
* Contact
* Job Posting
* Application

Activities create a CRM-style timeline for each relationship and opportunity.

---

# Tasks and Follow-Ups

Tasks represent actions that still need to be completed.

Examples:

* Follow up with a hiring manager
* Submit an application
* Prepare for an interview
* Send a thank-you email
* Research an organization
* Check an application portal
* Update a resume

Tasks support:

* Priority
* Status
* Due date
* Due time
* Completion
* Reopening
* Overdue detection
* Search
* Filtering
* Pagination

Tasks may be associated with:

* Organizations
* Contacts
* Job Postings
* Applications

Activities can be used to create follow-up tasks.

---

# Dashboard and Analytics

The Dashboard acts as the user's command center.

It can display:

* Organization count
* Contact count
* Active job postings
* Application count
* Open tasks
* Overdue tasks
* Pipeline status
* Upcoming interviews
* Recent activities
* Recent applications
* Tasks due today
* Tasks due this week
* Productivity metrics
* Organization activity summaries

Private dashboard metrics are scoped to the current user.

Shared metrics may summarize shared entities where appropriate.

---

# Optional Career Profile

Career CRM includes an optional Career Profile.

Completing the Career Profile is never required to use the CRM.

Users may complete it gradually over time.

The profile helps enable:

* Better job matching
* Skill-gap analysis
* Career recommendations
* Personalized analytics
* Future AI assistance

Users may:

* Complete profile sections in any order
* Save progress
* Return later
* Dismiss reminders
* Edit sections independently

---

# Profile Completeness

Career CRM may calculate profile completeness based on sections such as:

* Education
* Skills
* Career interests
* Work preferences
* Career priorities
* Languages
* Certifications
* Portfolio
* Job-search strategy

The Dashboard may display a completion percentage and suggest useful sections to complete next.

Profile completeness is informational and never blocks normal use.

---

# Education

Users may record multiple education entries.

Possible fields:

* Institution
* Degree
* Field of study
* Start year
* Graduation year
* Completion status
* Notes

---

# Certifications

Certification records may include:

* Name
* Issuing organization
* Issue date
* Expiration date
* Credential ID
* Credential URL
* Notes

---

# Languages

Users may record spoken languages and proficiency levels.

Example levels:

* Basic
* Conversational
* Professional
* Fluent
* Native/Bilingual

---

# Skills

Skills use a shared/private model.

## Skill

Shared reference entity.

Possible categories:

* Programming Language
* Framework
* Database
* Cloud Platform
* AI/ML
* Medical Imaging
* Scientific Computing
* Domain Expertise
* Soft Skill
* Other

## UserSkill

Private user association.

May include:

* Proficiency
* Years of experience
* Interest level
* Notes

Duplicate user/skill combinations are prevented.

---

# Career Interests

The Career Profile may include:

* Industries of interest
* Job families
* Preferred roles
* Research vs. industry preference
* Startup vs. enterprise preference
* Management interest
* Technical vs. leadership preference

These values are intended to feed future job matching.

---

# Work Preferences

Users may specify:

* Remote
* Hybrid
* On-site
* Preferred locations
* Willingness to relocate
* Willingness to travel
* Employment types
* Security clearance
* Work authorization
* Salary expectations

---

# Weighted Career Priorities

Users may assign importance values to career factors.

Examples:

* Compensation
* Stability
* Interesting work
* Career growth
* Work-life balance
* Mission or social impact
* Prestige
* Flexible schedule
* Technical challenge
* Advancement
* Location
* Remote flexibility

Weights may use a scale such as 1–5.

These values can later influence job-match scoring.

---

# Portfolio

Users may maintain portfolio records such as:

* GitHub
* LinkedIn
* Personal website
* Publications
* Patents
* Open-source work
* Portfolio projects

---

# Job Search Strategy

The Career Profile may store job-search strategy preferences such as:

* Applications per week
* Networking interest
* Cold outreach
* Recruiter outreach
* Conference interest
* Government roles
* Academic roles

These settings may influence future recommendations and dashboard guidance.

---

# Job Matching

Career CRM is designed to compare Job Postings against a user's Career Profile.

Matching may use:

* Skills
* Experience
* Preferred industries
* Job families
* Preferred roles
* Work mode
* Location
* Career priorities
* Salary expectations

Potential outputs include:

* Match score
* Matching skills
* Missing skills
* Preference alignment
* Areas of concern

Matching should remain deterministic and explainable wherever possible.

AI may later enhance explanations but should not be required.

---

# Document Management

Career CRM may manage documents such as:

* Resumes
* Cover letters
* Certifications
* Portfolio files
* Supporting documents

Document functionality may include:

* Versioning
* Association with applications
* Metadata
* Upload validation
* Ownership enforcement
* Secure retrieval

Private documents must not be accessible to other users.

---

# Global Search

Career CRM may provide global search across:

* Organizations
* Contacts
* Job Postings
* Applications
* Activities
* Tasks
* Profile data

Search must respect private-data ownership boundaries.

---

# Reporting and Export

Reporting features may support:

* CSV
* Excel
* PDF

Possible reports:

* Applications by month
* Interview conversion
* Response rates
* Activity history
* Task completion
* Organization activity
* Job-search pipeline
* Career-profile summaries

Exports must only include data the current user is authorized to access.

---

# Notifications and Reminders

Career CRM may provide local reminders for:

* Overdue tasks
* Upcoming interviews
* Application deadlines
* Follow-ups
* Career-profile reminders

External email or push notifications may be added later.

---

# Job Import Framework

Career CRM may support modular job importers.

Possible sources:

* Company career pages
* Applicant tracking systems
* RSS feeds
* Structured exports
* Manual imports

Importers should support:

* Normalization
* Duplicate detection
* Organization matching
* Idempotent imports
* Invalid-record handling

Automated tests should use fixtures rather than live scraping.

---

# AI Assistance

AI is optional.

Career CRM must continue to function normally if AI is disabled or unavailable.

AI may assist with:

* Skill suggestions
* Industry suggestions
* Job-family suggestions
* Role suggestions
* Profile completion
* Job-match explanations
* Resume analysis
* Career guidance
* Interview preparation
* Future document generation

AI must not automatically modify persistent user data.

All suggested profile changes require explicit approval.

---

# AI Provider Architecture

AI functionality should use a provider abstraction.

Possible providers may eventually include:

* OpenAI
* Other hosted providers
* Local models
* Deterministic/offline suggestion engines

Application logic should not depend directly on one vendor.

---

# Per-User OpenAI Integration

Users may optionally connect their own OpenAI API credentials.

Career CRM should not require users to consume a shared server-owned OpenAI account.

Each user's OpenAI usage and billing should belong to that user's own account.

Users may:

* Connect OpenAI
* Test the connection
* Select a supported model
* Replace their key
* Disconnect OpenAI
* Disable AI features

Career CRM must remain fully functional without OpenAI.

---

# OpenAI Credential Security

User API credentials must never be stored in plaintext.

Credentials should be:

* Submitted over HTTPS
* Encrypted before persistence
* Scoped to the authenticated user
* Decrypted only when required server-side
* Never returned to the browser after storage
* Never logged
* Never included in exports
* Never exposed in templates

The application should use a server-side credential-encryption secret supplied through environment configuration.

Example:

`CREDENTIAL_ENCRYPTION_KEY`

The encryption secret itself must not be stored in the database or committed to Git.

---

# AI Suggestion Workflow

AI suggestions follow this pattern:

User requests suggestions

→ Career CRM selects only relevant profile information

→ AI provider generates structured suggestions

→ Career CRM validates results

→ User reviews them

→ User accepts or rejects each suggestion

→ Only accepted values are persisted

AI providers do not write directly to the database.

---

# Deterministic AI Fallback

Career CRM may include an offline deterministic suggestion provider.

This supports:

* Development
* Testing
* Offline use
* Users without API credentials
* Provider outages

The application should never require a live AI request for normal use.

---

# REST API

Career CRM may expose a documented REST API.

Potential resources include:

* Organizations
* Contacts
* Job Postings
* Applications
* Activities
* Tasks
* Career Profile

API functionality must enforce:

* Authentication
* Authorization
* Ownership
* Shared/private visibility
* Validation
* Pagination
* Object-level permissions

Security tests should explicitly check for IDOR vulnerabilities.

---

# Docker

Career CRM is designed to run in containers.

The deployment stack may include:

* Flask application
* PostgreSQL
* Gunicorn
* Nginx

Docker Compose should orchestrate local deployment.

Persistent volumes should protect PostgreSQL data across container restarts.

Secrets should be supplied at runtime rather than built into images.

---

# PostgreSQL

PostgreSQL is the production database target.

The application should maintain compatibility with SQLAlchemy migrations and avoid unnecessary SQLite-specific behavior.

---

# Production Deployment

A production deployment may include:

Client

↓

HTTPS

↓

Reverse Proxy

↓

Gunicorn

↓

Flask

↓

SQLAlchemy

↓

PostgreSQL

Secure remote access may be provided through a tunnel or similar reverse-proxy service.

---

# Mobile Access

Career CRM is intended to work well on:

* Desktop browsers
* macOS
* Linux
* iPhone
* Other mobile devices

The interface should use responsive Bootstrap layouts.

Mobile UX priorities include:

* Large touch targets
* Responsive forms
* Card-based layouts
* Collapsible navigation
* Minimal horizontal scrolling

---

# Testing

Career CRM uses pytest.

Tests should include:

* Model tests
* Service tests
* Route tests
* Authentication tests
* Authorization tests
* Ownership tests
* Security regression tests
* Dashboard tests
* Career-profile tests
* Matching tests
* Document tests
* API tests
* Importer tests
* AI-provider tests
* Migration smoke tests

External systems must be mocked.

Automated tests must not:

* call live OpenAI APIs
* send real email
* scrape live websites
* depend on production infrastructure

---

# Security Testing

Security-critical testing should cover:

* Password hashing
* Authentication
* CSRF
* Open redirects
* Object-level authorization
* IDOR attempts
* Owner spoofing
* API access controls
* File path traversal
* Credential isolation
* Cross-user data access
* Secret exposure

Private records must remain isolated even when users manipulate URLs or request payloads directly.

---

# Code Quality

The project aims to maintain:

* Strong type hints
* SQLAlchemy 2.x style
* PEP 8
* Ruff
* Black
* mypy
* pytest
* High-value test coverage
* Clean service boundaries
* Thin routes
* Reusable templates
* Database portability

---

# Development Workflow

Development is milestone-driven.

Each milestone should:

1. Introduce a focused capability.
2. Preserve prior behavior.
3. Add tests.
4. Add migrations when required.
5. Update documentation.
6. Run the complete test suite before completion.

Large architectural changes should be separated from feature additions wherever practical.

---

# Milestone Roadmap

Major milestones include:

1. Foundation
2. Organizations
3. Contacts
4. Job Postings
5. Applications
6. Activities
7. Tasks & Follow-Ups
8. Dashboard & Analytics
9. Authentication & User Accounts
10. Multi-User Ownership & Authorization
    10.5. Optional Career Profile, Progressive Onboarding & Per-User AI
11. Skills & Job Matching
12. Document Management
13. Global Search
14. Reporting & Exports
15. Notifications & Reminders
16. PostgreSQL Migration
17. Docker & Docker Compose
18. Production Deployment
19. Mobile UX Optimization
20. Job Import Framework
21. AI Assistance
22. Collaboration & Community Features
23. REST API
24. Performance & Scalability
25. Version 1.0 Release

The roadmap may continue evolving as Career CRM develops.

---

# Privacy Principles

Career CRM should minimize unnecessary collection and sharing of user data.

Private career information should never become shared automatically.

AI providers should receive only the information necessary for a specific request.

Users should remain in control of:

* their career profile
* their documents
* their applications
* their contacts
* their AI provider
* their API credentials
* their AI suggestions

---

# Long-Term Vision

Career CRM is intended to evolve into a personal career-management and decision-support platform.

Instead of simply recording which jobs a user has applied to, it should help answer questions such as:

* What should I work on today?
* Which jobs best match my background?
* Which employers should I prioritize?
* Which skills appear most often in jobs I want?
* Which skills am I missing?
* Which job-search channels produce interviews?
* Which organizations respond most often?
* Which opportunities best match my priorities?
* Where is my job search getting stuck?
* What should I follow up on next?

The long-term goal is a system that combines CRM workflows, structured career data, analytics, and optional AI assistance while preserving user privacy and control.

---

# License

This project is under active development.

A final license should be selected before public release.
