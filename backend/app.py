import os
import json
import requests
from os import environ as env
from urllib.parse import quote_plus, urlencode

from authlib.integrations.flask_client import OAuth
from dotenv import find_dotenv, load_dotenv
from flask import Flask, redirect, render_template, session, url_for, request, jsonify
from ifem_award_api.patients import generate_mock_wait_time, TriageCategory


ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

from flask_sqlalchemy import SQLAlchemy
from ifem_award_api.patients import generate_mock_patient

app = Flask(__name__)
app.secret_key = env.get("APP_SECRET_KEY")

oauth = OAuth(app)

oauth.register(
    "auth0",
    client_id=env.get("AUTH0_CLIENT_ID"),
    client_secret=env.get("AUTH0_CLIENT_SECRET"),
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=f'https://{env.get("AUTH0_DOMAIN")}/.well-known/openid-configuration'
)

# Configure the database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define the Patients model
class Patient(db.Model):
    __tablename__ = 'patients'
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=False)
    patient_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    arrival_time = db.Column(db.DateTime, nullable=False)
    triage_category = db.Column(db.String(50), nullable=False)
    phase = db.Column(db.String(50), nullable=False)
    labs = db.Column(db.String(200))
    imaging = db.Column(db.String(200))
    time_elapsed = db.Column(db.Float)  # time in hours, for example

# Define the Admins model
class Admin(db.Model):
    __tablename__ = 'admins'
    admin_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)

# Define the Hospitals model
class Hospital(db.Model):
    __tablename__ = 'hospitals'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    number_of_doctors = db.Column(db.Integer, nullable=False)

# Initialize the database with app context
with app.app_context():
    db.create_all()
    print("Database tables created successfully.")

    # if the number of hospitals in the database is 0, add five hospitals

        # Create new hospitals
    hospitals = [
        Hospital(id=101, name='Montreal General Hospital', address='1650 Cedar Ave, Montreal, QC H3G 1A4',
                 number_of_doctors=50),
        Hospital(id=102, name='Jewish General Hospital',
                 address='3755 Côte-Sainte-Catherine Rd, Montreal, QC H3T 1E2', number_of_doctors=40),
        Hospital(id=103, name='CHUM', address='1000 Saint-Denis St, Montreal, QC H2X 0C1', number_of_doctors=60),
        Hospital(id=104, name='St. Mary\'s Hospital Center', address='3830 Lacombe Ave, Montreal, QC H3T 1M5',
                 number_of_doctors=30),
        Hospital(id=105, name='Shriners Hospitals for Children', address='1003 Decarie Blvd, Montreal, QC H4A 0A9',
                 number_of_doctors=20)
    ]

    # Add the new hospitals to the database
    for hospital in hospitals:
        if Hospital.query.filter_by(id=hospital.id).first() is None:
            db.session.add(hospital)
    db.session.commit()



@app.route("/login")
def login():
    nonce = os.urandom(16).hex()
    session['nonce'] = nonce
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True),
        nonce=nonce
    )

@app.route("/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()
    session["user"] = token

    # Extract user information from the token
    nonce = session.pop('nonce', None)
    user_info = oauth.auth0.parse_id_token(token, nonce=nonce)
    user_email = user_info.get('email')

    # Check if the user is in the admin database
    admin = Admin.query.filter_by(name=user_email).first()
    if admin is None:
        # If the user is not an admin, redirect to addAdmin page
        return redirect(url_for("add_admin"))

    # If the user is an admin, store the hospital_id in the session
    session['hospital_id'] = admin.hospital_id

    return redirect(url_for("home"))


@app.route("/addAdmin", methods=["GET", "POST"])
def add_admin():
    if request.method == 'POST':
        # Get the admin details from the form
        name = request.form.get('name')
        hospital_id = request.form.get('hospital_id')

        # Check if the hospital ID is valid
        hospital = Hospital.query.filter_by(id=hospital_id).first()
        if hospital is None:
            # If the hospital ID is invalid, ask for a valid hospital ID again
            return render_template("addAdmin.html", error="Invalid hospital ID. Please try again.")

        # Create a new admin
        new_admin = Admin(
            hospital_id=hospital_id,
            name=name
        )

        # Add the new admin to the database
        db.session.add(new_admin)
        db.session.commit()

        return redirect(url_for('home'))

    return render_template("addAdmin.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        "https://" + env.get("AUTH0_DOMAIN")
        + "/v2/logout?"
        + urlencode(
            {
                "returnTo": url_for("home", _external=True),
                "client_id": env.get("AUTH0_CLIENT_ID"),
            },
            quote_via=quote_plus,
        )
    )


@app.route("/")
def home():
    return render_template("home.html", session=session.get('user'), pretty=json.dumps(session.get('user'), indent=4))


@app.route('/heatmap')
def heatmap():
    return render_template('heatmap.html')

# protected
@app.route('/generate_patient_data', methods=['GET'])
def generate_patient_data():
    # Generate a mock patient
    # Return the patient's details as a JSON response

    patient = generate_mock_patient()
    return {
        'patient_id': patient.id,
        'arrival_time': patient.arrival_time,
        'triage_category': patient.triage_category.value,
        # 'queue_position': patient.queue_position,
        'phase': patient.status['current_phase'].value,
        'labs': patient.status['investigations']['labs'].value,
        'imaging': patient.status['investigations']['imaging'].value,
        'time_elapsed': patient.time_elapsed
    }

# protected
@app.route('/create_new_patient', methods=['POST'])
def create_new_patient():
    # get the patient details from the request
    # store the patient in the database
    # and return the patient's details as a JSON response, with a custom URL

    # Get the patient details from the request
    data = request.json

    # Create a new patient
    new_patient = Patient(
        hospital_id=session['hospital_id'],
        patient_id=data['patient_id'],
        arrival_time=data['arrival_time'],
        triage_category=data['triage_category'],
        phase=data['phase'],
        labs=data['labs'],
        imaging=data['imaging'],
        time_elapsed=data['time_elapsed']
    )

    # Add the new patient to the database
    db.session.add(new_patient)
    db.session.commit()

@app.route('/patients/<hospital_id>', methods=['GET'])
def patients(hospital_id):
    # Retrieve all patients from the database with the given hospital_id
    # and return the patients' details as a JSON response

    patients = Patient.query.filter_by(hospital_id=hospital_id).all()
    patients_data = []
    for patient in patients:
        patients_data.append({
            'patient_id': patient.patient_id,
            'arrival_time': patient.arrival_time,
            'triage_category': patient.triage_category,
            'phase': patient.phase,
            'labs': patient.labs,
            'imaging': patient.imaging,
            'time_elapsed': patient.time_elapsed
        })

    return {'patients': patients_data}


@app.route('/patient/<patient_id>', methods=['GET'])
def patient(patient_id):
    # Retrieve the patient from the database
    # and return the patient's details as a JSON response

    patient = Patient.query.filter_by(patient_id=patient_id).first()
    return {
        'patient_id': patient.patient_id,
        'arrival_time': patient.arrival_time,
        'triage_category': patient.triage_category,
        'phase': patient.phase,
        'labs': patient.labs,
        'imaging': patient.imaging,
        'time_elapsed': patient.time_elapsed
    }



@app.route('/gethospital/<hospital_id>', methods=['GET'])
def get_number_of_doctors(hospital_id):
    # Retrieve the hospital from the database
    # and return the number as a JSON response
    hospital = Hospital.query.filter_by(id=hospital_id).first()
    return {
        'number_of_doctors': hospital.number_of_doctors,
        'hospital_name': hospital.name,
        'hospital_address': hospital.address,
    }

#protected
@app.route('/setnumberofdoctors', methods=['POST'])
def set_number_of_doctors():
    # Retrieve the number of doctors from the request
    # store the number of doctors in the database
    # and return the number as a JSON response

    data = request.json
    hospital = Hospital.query.filter_by(id=session['hospital_id']).first()
    hospital.number_of_doctors = data['number_of_doctors']

    db.session.commit()
    return {'number_of_doctors': hospital.number_of_doctors}

if __name__ == '__main__'
    app.run(port=8000)