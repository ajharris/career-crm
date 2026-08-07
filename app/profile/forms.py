"""Modular onboarding and career-profile forms."""

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DecimalField,
    IntegerField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
    TextAreaField,
    DateField,
)
from wtforms.validators import DataRequired, NumberRange, Optional, URL


class BackgroundForm(FlaskForm):
    highest_education_level = SelectField("Highest education", choices=[("", "Select"), ("high_school", "High School"), ("college", "College"), ("bachelors", "Bachelor's"), ("masters", "Master's"), ("doctorate", "Doctorate")], validators=[Optional()])
    years_of_experience = IntegerField("Years of experience", validators=[Optional(), NumberRange(min=0, max=80)])
    management_interest = BooleanField("Interested in management")
    technical_leadership_preference = BooleanField("Interested in technical leadership")
    submit = SubmitField("Save and Continue")


class EducationForm(FlaskForm):
    institution = StringField("Institution", validators=[DataRequired()])
    degree_type = StringField("Degree type")
    degree_name = StringField("Degree name")
    field_of_study = StringField("Field of study")
    start_year = IntegerField("Start year", validators=[Optional(), NumberRange(1900, 2200)])
    graduation_year = IntegerField("Graduation year", validators=[Optional(), NumberRange(1900, 2200)])
    completed = BooleanField("Completed")
    notes = TextAreaField("Notes")
    submit = SubmitField("Save")


class SkillForm(FlaskForm):
    name = StringField("Skill", validators=[DataRequired()])
    category = SelectField("Category", choices=[("programming_language", "Programming Language"), ("framework", "Framework"), ("database", "Database"), ("cloud_platform", "Cloud Platform"), ("ai_ml", "AI/ML"), ("medical_imaging", "Medical Imaging"), ("domain_expertise", "Domain Expertise"), ("soft_skill", "Soft Skill"), ("other", "Other")])
    proficiency = SelectField("Proficiency", choices=[("basic", "Basic"), ("intermediate", "Intermediate"), ("advanced", "Advanced"), ("expert", "Expert")])
    years_experience = DecimalField("Years of experience", validators=[Optional(), NumberRange(min=0)])
    interest_level = IntegerField("Interest level", validators=[Optional(), NumberRange(1, 5)])
    notes = TextAreaField("Notes")
    submit = SubmitField("Save")


class CertificationForm(FlaskForm):
    name = StringField("Certification", validators=[DataRequired()])
    issuing_organization = StringField("Issuing organization")
    issue_date = DateField("Issue date", validators=[Optional()])
    expiration_date = DateField("Expiration date", validators=[Optional()])
    credential_id = StringField("Credential ID")
    credential_url = StringField("Credential URL", validators=[Optional(), URL()])
    notes = TextAreaField("Notes")
    submit = SubmitField("Save")


class LanguageForm(FlaskForm):
    language_name = StringField("Language", validators=[DataRequired()])
    proficiency = SelectField("Proficiency", choices=[("basic", "Basic"), ("conversational", "Conversational"), ("professional", "Professional"), ("fluent", "Fluent"), ("native_bilingual", "Native / Bilingual")])
    submit = SubmitField("Save")


class LocationForm(FlaskForm):
    city = StringField("City")
    region = StringField("Province / state")
    country = StringField("Country", validators=[DataRequired()])
    submit = SubmitField("Save")


class InterestsForm(FlaskForm):
    industries = SelectMultipleField(
        "Industries of interest",
        choices=[(x, x) for x in ("Healthcare", "Medical Imaging", "Biotechnology", "Software", "AI/ML", "Government", "Aerospace", "Research")],
    )
    job_families = SelectMultipleField(
        "Job families",
        choices=[(x, x) for x in ("Software Engineering", "Data Science", "Research", "Scientific Computing", "Medical Physics", "Imaging Informatics", "Technical Operations")],
    )
    preferred_roles = StringField("Preferred roles", description="Separate roles with commas.")
    submit = SubmitField("Save and Continue")


class WorkPreferencesForm(FlaskForm):
    remote = BooleanField("Remote")
    hybrid = BooleanField("Hybrid")
    on_site = BooleanField("On-site")
    full_time = BooleanField("Full Time")
    part_time = BooleanField("Part Time")
    contract = BooleanField("Contract")
    temporary = BooleanField("Temporary")
    internship = BooleanField("Internship")
    willing_to_relocate = BooleanField("Willing to relocate")
    willing_to_travel = BooleanField("Willing to travel")
    city = StringField("Preferred city")
    region = StringField("Province / state")
    country = StringField("Country")
    submit = SubmitField("Save and Continue")


class PriorityForm(FlaskForm):
    factor = SelectField("Factor", choices=[(x, x) for x in ("Compensation", "Stability", "Interesting Work", "Career Growth", "Work-Life Balance", "Mission / Social Impact", "Prestige", "Flexible Schedule", "Technical Challenge", "Advancement", "Location", "Remote Flexibility")])
    weight = IntegerField("Weight", validators=[DataRequired(), NumberRange(1, 5)])
    notes = TextAreaField("Notes")
    submit = SubmitField("Save")


class PortfolioForm(FlaskForm):
    item_type = SelectField("Type", choices=[(x, x) for x in ("GitHub", "LinkedIn", "Personal Website", "Publication", "Patent", "Open Source", "Portfolio Project", "Other")])
    title = StringField("Title", validators=[DataRequired()])
    url = StringField("URL", validators=[Optional(), URL()])
    description = TextAreaField("Description")
    submit = SubmitField("Save")


class StrategyForm(FlaskForm):
    applications_per_week_target = IntegerField("Applications per week", validators=[Optional(), NumberRange(min=0, max=100)])
    interested_in_networking = BooleanField("Networking")
    interested_in_cold_outreach = BooleanField("Cold outreach")
    interested_in_recruiter_outreach = BooleanField("Recruiter outreach")
    interested_in_conferences = BooleanField("Conferences")
    interested_in_government_roles = BooleanField("Government roles")
    interested_in_academic_roles = BooleanField("Academic roles")
    submit = SubmitField("Save and Continue")


class CompleteForm(FlaskForm):
    submit = SubmitField("Complete Onboarding")
