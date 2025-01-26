from datetime import datetime
import os
import json
import random
import requests
# import flask cors
from flask_cors import CORS
from os import environ as env
from urllib.parse import quote_plus, urlencode

from authlib.integrations.flask_client import OAuth
from dotenv import find_dotenv, load_dotenv
from flask import Flask, redirect, render_template, session, url_for, request, jsonify
from ifem_award_api.patients import generate_mock_wait_time, TriageCategory
from loaer import predict, unique_y

import numpy as np

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

from flask_sqlalchemy import SQLAlchemy
from ifem_award_api.patients import generate_mock_patient

app = Flask(__name__)
CORS(app)
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

    for x in range(0, 4):
        test_patient = generate_mock_patient()
        print(test_patient)
        new_patient = Patient(
            hospital_id=random.choice([101, 102, 103, 104, 105]),
            patient_id=int(test_patient.id[5:]),  # Ensure this slice is valid
            arrival_time=test_patient.arrival_time,
            triage_category=str(test_patient.triage_category.value),  # Ensure this is a string
            phase=str(test_patient.status['current_phase'].value),  # Ensure this is a string
            labs="PENDING",  # Confirm it's a string
            imaging="PENDING",  # Confirm it's a string
            time_elapsed=float(test_patient.time_elapsed)  # Ensure this is a float
        )
        db.session.add(new_patient)


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

    # Patient(
        #     hospital_id=random.choice([101, 102, 103, 104, 105]),
        #     patient_id=int(test_patient.id[5:]),  # Ensure this slice is valid
        #     arrival_time=test_patient.arrival_time,
        #     triage_category=str(test_patient.triage_category.value),  # Ensure this is a string
        #     phase=str(test_patient.status['current_phase'].value),  # Ensure this is a string
        #     labs="PENDING",  # Confirm it's a string
        #     imaging="PENDING",  # Confirm it's a string
        #     time_elapsed=float(test_patient.time_elapsed)  # Ensure this is a float
        # )

    # choose a random hospitalid from the list of hospitals
    hospital_id = random.choice([101, 102, 103, 104, 105])

    return {
        'patient_id': int(patient.id[5:]),
        'arrival_time': patient.arrival_time,
        'triage_category': str(patient.triage_category.value),
        # 'queue_position': patient.queue_position,
        'phase': "triaged",#str(patient.status['current_phase'].value),
        'labs': "PENDING",
        'imaging': "PENDING",
        'time_elapsed': float(patient.time_elapsed),
        'hospital_id': hospital_id
    }

# protected
@app.route('/create_new_patient', methods=['GET', 'POST'])
def create_new_patient():
    if request.method == 'GET':
        return render_template('createPatient.html', **generate_patient_data())
    # get the patient details from the request
    # store the patient in the database
    # and return the patient's details as a JSON response, with a custom URL

    # Get the patient details from the request
    data = request.form

    # convert data["arrival_time"] to a datetime object in the format 2025-01-26 00:07:55.948915
    arrival_time = datetime.strptime(data["arrival_time"], "%Y-%m-%d %H:%M:%S.%f")

    # Create a new patient
    new_patient = Patient(
        hospital_id=data['hospital_id'],
        patient_id=data['patient_id'],
        arrival_time=arrival_time,
        triage_category=data['triage_category'],
        phase=data['phase'],
        labs=data['labs'],
        imaging=data['imaging'],
        time_elapsed=data['time_elapsed']
    )

    # Add the new patient to the database
    db.session.add(new_patient)
    db.session.commit()

    # return a redirect to locaalhost:5000
    return redirect(url_for('qrcode', patient_id=data['patient_id']))

@app.route('/qrcode/<patient_id>', methods=['GET'])
def qrcode(patient_id):
    # return a QR code image for the patient with the given patient_id
    qrcode = f'https://api.qrserver.com/v1/create-qr-code/?data=http://localhost:5000/patient/{patient_id}'
    return render_template('qrcode.html', qrcode=qrcode)

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
    if patient is None:
        return {'error': 'Patient not found'}, 404
    return {
        'patient_id': patient.patient_id,
        'arrival_time': patient.arrival_time,
        'triage_category': patient.triage_category,
        'phase': patient.phase,
        'labs': patient.labs,
        'imaging': patient.imaging,
        'time_elapsed': patient.time_elapsed
    }

@app.route('/patient/<patient_id>/wait-time', methods=['GET'])
def wait_time(patient_id):
    # Retrieve the patient from the database
    # and return the patient's wait time as a JSON response

    patient = Patient.query.filter_by(patient_id=patient_id).first()
    # Output: {
    #   estimatedWait: number,
    #   confidenceInterval: number,
    #   queuePosition: number,
    #   totalPatients: number,
    #   triageLevel: string
    # }

    # get all the patients in the same hostipal as the patient, sort them by arrival time, aan get the index of the patient
    patients = Patient.query.filter_by(hospital_id=patient.hospital_id).order_by(Patient.arrival_time).all()
    queue_position = patients.index(patient) + 1

    number_of_patients = len(patients)

    # c = [0, 0, 0, 0, 0]
    # for i in range(idx):
    #     c[queue[i][0].triage_category.value - 1] += 1

    c = [0, 0, 0, 0, 0]
    for i in range(queue_position):
        c[int(patients[i].triage_category) - 1] += 1

    # patientNumberInQueue, triage, number of each triage in front of patient
    output = predict([queue_position, patient.triage_category, *c])

    # probabilities = {int(unique_y[i]) : float(prob) for i, prob in enumerate(output[0])}

    wait_time = max(output, key=output.get)

    return {
        'estimatedWait': wait_time,
        'actual': output,
        'queuePosition': queue_position,
        'totalPatients': number_of_patients,
        'triageLevel': patient.triage_category
    }

@app.route('/hospitals/nearby', methods=['GET'])
def nearby_hospitals():
    # return all the hospitals in the database as a JSON response
    hospitals = Hospital.query.all()
    hospitals_data = []
    for hospital in hospitals:
        hospitals_data.append({
            'hospital_id': hospital.id,
            'hospital_name': hospital.name,
            'hospital_address': hospital.address,
            'wait_time': generate_mock_wait_time(TriageCategory.LESS_URGENT)
        })

    return {'hospitals': hospitals_data}

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

if __name__ == '__main__':
    app.run(port=8000)