from flask import Flask, render_template, request, session
from flask_sqlalchemy import SQLAlchemy
from ifem_award_api.patients import generate_mock_patient
app = Flask(__name__)

# Configure the database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

#initaliase the database
# patients -  hotpital ID, patient ID, arrival_time, triage_category, phase, labs, imaging, time_elapsed
# admins - adminID, hostpitalID, name
# hospitals - hospitalID, name, address, numberofdoctors

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

    # Create a new hospital
    new_hospital = Hospital(
        name='St. Michael\'s Hospital',
        address='30 Bond St, Toronto, ON M5B 1W8',
        number_of_doctors=10
    )

@app.route('/')
def app_introduction():
    return render_template('index.html', person='John Doe')

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

# protected
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



if __name__ == '__main__':
    app.run()
