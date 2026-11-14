import os
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone

import secrets
import joblib
import pandas as pd
import requests
from flask import Flask, jsonify, request
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    get_jwt_identity,
    jwt_required,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

from algorithm import optimize_route

load_dotenv()

app = Flask(__name__)
CORS(app)

# Database and security settings are loaded from .env
database_url = os.getenv('DATABASE_URL')
jwt_secret_key = os.getenv('JWT_SECRET_KEY')

if not database_url:
    raise RuntimeError("DATABASE_URL is missing from the .env file.")

if not jwt_secret_key:
    raise RuntimeError("JWT_SECRET_KEY is missing from the .env file.")

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
app.config['JWT_SECRET_KEY'] = jwt_secret_key
# Access token stays valid for 2 hours
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=2)
jwt = JWTManager(app)


MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'eta_model.pkl')
try:
    eta_model = joblib.load(MODEL_PATH)
    print("✅ ETA model loaded!")
except (FileNotFoundError, EOFError, ValueError, ImportError) as e:
    eta_model = None
    print("ETA model not loaded. Run 'python eta.py' first.", e)


def predict_leg_minutes(distance_km, when):
    features = pd.DataFrame([{
        'distance_km': distance_km,
        'hour': when.hour,
        'day_of_week': when.weekday()
    }])
    return float(eta_model.predict(features)[0])


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    store_lat = db.Column(db.Float, nullable=True)
    store_lng = db.Column(db.Float, nullable=True)
    current_lat = db.Column(db.Float, nullable=True)
    current_lng = db.Column(db.Float, nullable=True)
    location_updated_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<User {self.name}>'

class EmailOTP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), nullable=False, index=True)
    otp_hash = db.Column(db.String(200), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    delivery_boy_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    customer_name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(300), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(20), default='pending')
    delivered_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<Order {self.id} - {self.customer_name}>'


def order_to_dict(order):
    return {
        'id': order.id,
        'vendor_id': order.vendor_id,
        'delivery_boy_id': order.delivery_boy_id,
        'customer_name': order.customer_name,
        'address': order.address,
        'latitude': order.latitude,
        'longitude': order.longitude,
        'status': order.status,
        'delivered_at': order.delivered_at.isoformat() if order.delivered_at else None
    }


def get_current_user():

    return db.session.get(User, int(get_jwt_identity()))

def send_otp_email(to_email, otp):
    smtp_server = os.getenv('BREVO_SMTP_SERVER')
    smtp_port = int(os.getenv('BREVO_SMTP_PORT', 587))
    smtp_login = os.getenv('BREVO_SMTP_LOGIN')
    smtp_key = os.getenv('BREVO_SMTP_KEY')

    sender_email = os.getenv('BREVO_SENDER_EMAIL')
    sender_name = os.getenv('BREVO_SENDER_NAME', 'RouteWise')

    if not all([smtp_server, smtp_login, smtp_key, sender_email]):
        raise ValueError("Brevo SMTP configuration is incomplete.")

    message = EmailMessage()
    message['Subject'] = 'Your RouteWise Email Verification OTP'
    message['From'] = f'{sender_name} <{sender_email}>'
    message['To'] = to_email

    message.set_content(
        f'''Hello,

Your RouteWise verification OTP is: {otp}

This OTP is valid for 2 minutes.

Please do not share this OTP with anyone.

Regards,
RouteWise Team'''
    )

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_login, smtp_key)
        server.send_message(message)

@app.route('/send-otp', methods=['POST'])
def send_otp():
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()

    if not email or '@' not in email:
        return jsonify({'message': 'Please enter a valid email.'}), 400

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({'message': 'Account already exists with this email!'}), 409

    otp = str(secrets.randbelow(900000) + 100000)

    otp_hash = bcrypt.generate_password_hash(otp).decode('utf-8')

    expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=2)

    try:
        EmailOTP.query.filter_by(email=email).delete()

        new_otp = EmailOTP(
            email=email,
            otp_hash=otp_hash,
            expires_at=expires_at
        )

        db.session.add(new_otp)
        db.session.commit()

        send_otp_email(email, otp)

        return jsonify({'message': 'OTP sent successfully! Please check your email.'}), 200

    except Exception as e:
        db.session.rollback()
        print('OTP sending error:', e)
        return jsonify({'message': 'Unable to send OTP. Please try again.'}), 500




def geocode_address(address):
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        'q': address,
        'format': 'jsonv2',
        'limit': 1,
        'countrycodes': 'in'  # bias results to India
    }
    headers = {
        'User-Agent': 'RouteWise-App'
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as e:
        print(" Geocoding failed:", e)
        return None, None

    if not data:
        return None, None

    result = data[0]

    if int(result.get('place_rank', 30)) <= 16:
        return None, None

    return float(result['lat']), float(result['lon'])


@app.route('/')
def home():
    return 'Hello RouteWise'


@app.route('/about')
def about():
    return 'RouteWise - Smart delivery route optimizer'


@app.route('/add-user', methods=['POST'])
def add_user():
    data = request.get_json() or {}

    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    role = data.get('role', '')

    otp = data.get('otp', '').strip()

    if not all([name, email, password, role, otp]):
        return jsonify({'message': 'Please fill all fields and enter OTP.'}), 400

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({'message': 'Account already exists with this email!'}), 409

    otp_record = EmailOTP.query.filter_by(email=email).order_by(EmailOTP.created_at.desc()).first()

    if not otp_record:
        return jsonify({'message': 'Please request an OTP first.'}), 400

    if datetime.utcnow() > otp_record.expires_at:
        db.session.delete(otp_record)
        db.session.commit()
        return jsonify({'message': 'OTP has expired. Please request a new OTP.'}), 400

    if not bcrypt.check_password_hash(otp_record.otp_hash, otp):
        return jsonify({'message': 'Incorrect OTP. Please try again.'}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    new_user = User(
        name=name,
        email=email,
        password=hashed_password,
        role=role
    )

    db.session.add(new_user)
    db.session.delete(otp_record)
    db.session.commit()

    return jsonify({'message': 'User added successfully!'})




@app.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}

    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'message': 'Please enter email and password.'}), 400

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({'message': 'User not found!'}), 404

    if not bcrypt.check_password_hash(user.password, password):
        return jsonify({'message': 'Wrong password!'}), 401

    otp = str(secrets.randbelow(900000) + 100000)
    otp_hash = bcrypt.generate_password_hash(otp).decode('utf-8')

    expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=2)

    try:
        # Remove previous login OTP
        EmailOTP.query.filter_by(email=email).delete()

        new_otp = EmailOTP(
            email=email,
            otp_hash=otp_hash,
            expires_at=expires_at
        )

        db.session.add(new_otp)
        db.session.commit()

        send_otp_email(email, otp)

        return jsonify({
            'message': 'Login OTP sent successfully! Please check your email.'
        }), 200

    except Exception as e:
        db.session.rollback()
        print('Login OTP sending error:', e)

        EmailOTP.query.filter_by(email=email).delete()
        db.session.commit()

        return jsonify({
            'message': 'Unable to send OTP. Please try again.'
        }), 500


@app.route('/login-verify-otp', methods=['POST'])
def login_verify_otp():
    data = request.get_json() or {}

    email = data.get('email', '').strip().lower()
    otp = data.get('otp', '').strip()

    if not email or not otp:
        return jsonify({'message': 'Please enter email and OTP.'}), 400

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({'message': 'User not found!'}), 404

    otp_record = EmailOTP.query.filter_by(email=email).order_by(
        EmailOTP.created_at.desc()
    ).first()

    if not otp_record:
        return jsonify({'message': 'Please request a new OTP.'}), 400

    if datetime.utcnow() > otp_record.expires_at:
        db.session.delete(otp_record)
        db.session.commit()
        return jsonify({'message': 'OTP expired. Please request a new OTP.'}), 400

    if not bcrypt.check_password_hash(otp_record.otp_hash, otp):
        return jsonify({'message': 'Incorrect OTP. Please try again.'}), 400

    db.session.delete(otp_record)
    db.session.commit()

    token = create_access_token(identity=str(user.id))

    return jsonify({
        'message': 'Login successful!',
        'token': token,
        'role': user.role
    }), 200



@app.route('/all-users', methods=['GET'])
@jwt_required()
def get_all_users():
    user = get_current_user()
    if not user or user.role != 'vendor':
        return jsonify({'message': 'Not allowed!'}), 403

    users = User.query.all()
    return jsonify([
        {'id': u.id, 'name': u.name, 'role': u.role} for u in users
    ])


@app.route('/delivery-boys', methods=['GET'])
@jwt_required()
def get_delivery_boys():
    user = get_current_user()
    if not user or user.role != 'vendor':
        return jsonify({'message': 'Only vendors can view delivery boys!'}), 403

    boys = User.query.filter_by(role='delivery_boy').all()
    return jsonify([
        {'id': b.id, 'name': b.name, 'email': b.email} for b in boys
    ])


@app.route('/delivery/update-location', methods=['POST'])
@jwt_required()
def update_delivery_location():
    user = get_current_user()
    if not user or user.role != 'delivery_boy':
        return jsonify({'message': 'Only delivery boys can update location!'}), 403

    data = request.get_json()
    lat = data.get('lat')
    lng = data.get('lng')

    if lat is None or lng is None:
        return jsonify({'message': 'lat and lng are required!'}), 400

    user.current_lat = lat
    user.current_lng = lng
    user.location_updated_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({'message': 'Location updated successfully!'})


@app.route('/delivery-boys/locations', methods=['GET'])
@jwt_required()
def get_delivery_boy_locations():
    user = get_current_user()
    if not user or user.role != 'vendor':
        return jsonify({'message': 'Only vendors can view delivery boy locations!'}), 403

    boys = User.query.filter_by(role='delivery_boy').all()
    result = [{
        'id': b.id,
        'name': b.name,
        'lat': b.current_lat,
        'lng': b.current_lng,
        'updated_at': b.location_updated_at.isoformat() if b.location_updated_at else None
    } for b in boys if b.current_lat is not None]

    return jsonify(result)


@app.route('/vendor/set-location', methods=['POST'])
@jwt_required()
def set_store_location():
    user = get_current_user()
    if not user or user.role != 'vendor':
        return jsonify({'message': 'Only vendors can set store location!'}), 403

    data = request.get_json()
    lat = data.get('lat')
    lng = data.get('lng')

    if lat is None or lng is None:
        return jsonify({'message': 'lat and lng are required!'}), 400

    user.store_lat = lat
    user.store_lng = lng
    db.session.commit()

    return jsonify({
        'message': 'Store location updated successfully!',
        'store_lat': lat,
        'store_lng': lng
    })


@app.route('/vendor/get-location', methods=['GET'])
@jwt_required()
def get_store_location():
    user = get_current_user()
    if not user or user.role != 'vendor':
        return jsonify({'message': 'Only vendors can view store location!'}), 403

    return jsonify({
        'store_lat': user.store_lat,
        'store_lng': user.store_lng
    })


@app.route('/add-order', methods=['POST'])
@jwt_required()
def add_order():
    user = get_current_user()
    if not user or user.role != 'vendor':
        return jsonify({'message': 'Only vendors can add orders!'}), 403

    data = request.get_json()

    lat, lon = geocode_address(data['address'])

    if lat is None:
        return jsonify({
            'message': "We couldn't verify this address. Please enter a real, specific address "
                       "(street or landmark, area, city)."
        }), 400

    new_order = Order(
        vendor_id=user.id,
        customer_name=data['customer_name'],
        address=data['address'],
        latitude=lat,
        longitude=lon
    )

    db.session.add(new_order)
    db.session.commit()

    return jsonify({'message': 'Order added successfully!', 'latitude': lat, 'longitude': lon})


@app.route('/assign-order', methods=['POST'])
@jwt_required()
def assign_order():
    user = get_current_user()
    if not user or user.role != 'vendor':
        return jsonify({'message': 'Only vendors can assign orders!'}), 403

    data = request.get_json()
    order = db.session.get(Order, data.get('order_id'))
    boy = db.session.get(User, data.get('delivery_boy_id'))

    if not order or order.vendor_id != user.id:
        return jsonify({'message': 'Order not found!'}), 404

    if not boy or boy.role != 'delivery_boy':
        return jsonify({'message': 'Delivery boy not found!'}), 404

    order.delivery_boy_id = boy.id
    db.session.commit()

    return jsonify({'message': f'Order {order.id} assigned to {boy.name}!'})


@app.route('/mark-delivered/<int:order_id>', methods=['POST'])
@jwt_required()
def mark_delivered(order_id):
    user = get_current_user()
    order = db.session.get(Order, order_id)

    if not user or not order:
        return jsonify({'message': 'Order not found!'}), 404

    allowed = (
        (user.role == 'delivery_boy' and order.delivery_boy_id == user.id)
        or (user.role == 'vendor' and order.vendor_id == user.id)
    )
    if not allowed:
        return jsonify({'message': 'Not allowed!'}), 403

    order.status = 'delivered'
    order.delivered_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({'message': f'Order {order.id} marked as delivered!'})


@app.route('/undo-delivered/<int:order_id>', methods=['POST'])
@jwt_required()
def undo_delivered(order_id):
    user = get_current_user()
    order = db.session.get(Order, order_id)

    if not user or not order:
        return jsonify({'message': 'Order not found!'}), 404

    allowed = (
        (user.role == 'delivery_boy' and order.delivery_boy_id == user.id)
        or (user.role == 'vendor' and order.vendor_id == user.id)
    )
    if not allowed:
        return jsonify({'message': 'Not allowed!'}), 403

    order.status = 'pending'
    order.delivered_at = None
    db.session.commit()

    return jsonify({'message': f'Order {order.id} moved back to pending.'})


@app.route('/my-deliveries', methods=['GET'])
@jwt_required()
def get_my_deliveries():
    user = get_current_user()
    if not user:
        return jsonify([])

    if user.role == 'delivery_boy':
        query = Order.query.filter_by(delivery_boy_id=user.id, status='delivered')
    else:
        query = Order.query.filter_by(vendor_id=user.id, status='delivered')

    orders = query.order_by(Order.delivered_at.desc()).all()
    return jsonify([order_to_dict(o) for o in orders])


@app.route('/all-orders', methods=['GET'])
@jwt_required()
def get_all_orders():
    user = get_current_user()
    if not user or user.role != 'vendor':
        return jsonify({'message': 'Not allowed!'}), 403

    orders = Order.query.filter_by(vendor_id=user.id).all()
    return jsonify([order_to_dict(o) for o in orders])


@app.route('/my-orders', methods=['GET'])
@jwt_required()
def get_my_orders():
    user = get_current_user()
    if not user:
        return jsonify([])

    if user.role == 'vendor':
        orders = Order.query.filter_by(vendor_id=user.id).all()
    else:
        orders = Order.query.filter_by(delivery_boy_id=user.id).all()

    return jsonify([order_to_dict(o) for o in orders])


@app.route('/optimize-route', methods=['GET'])
@jwt_required()
def get_optimized_route():
    user = get_current_user()

    if not user:
        return jsonify({'message': 'User not found!'}), 404

    if user.role == 'vendor':
        store_owner = user
    else:
        sample_order = Order.query.filter_by(delivery_boy_id=user.id).first()
        store_owner = db.session.get(User, sample_order.vendor_id) if sample_order else None

    if not store_owner or store_owner.store_lat is None or store_owner.store_lng is None:
        return jsonify({
            'message': 'Store location not set yet. Please set your store location first.'
        }), 400

    store_location = (store_owner.store_lat, store_owner.store_lng)

    query = Order.query.filter_by(status='pending')
    if user.role == 'vendor':
        query = query.filter_by(vendor_id=user.id)
    else:
        query = query.filter_by(delivery_boy_id=user.id)
    orders = query.all()

    order_list = []
    for order in orders:
        if order.latitude and order.longitude:
            order_list.append({
                'id': order.id,
                'customer_name': order.customer_name,
                'address': order.address,
                'latitude': order.latitude,
                'longitude': order.longitude
            })

    if not order_list:
        return jsonify({
            'optimized_route': [],
            'total_distance_km': 0,
            'total_eta_minutes': 0,
            'message': 'No pending orders found!'
        }), 200

    best_route, total_distance = optimize_route(store_location, order_list)

    total_eta_minutes = None
    if eta_model is not None:
        now = datetime.now(timezone.utc)
        elapsed = 0
        for stop in best_route:
            arrival_moment = now + timedelta(minutes=elapsed)
            elapsed += predict_leg_minutes(stop['leg_distance_km'], arrival_moment)
            stop['eta_minutes'] = round(elapsed)
            stop['eta_time'] = (now + timedelta(minutes=elapsed)).strftime('%I:%M %p')
        total_eta_minutes = round(elapsed)

    return jsonify({
        'optimized_route': best_route,
        'total_distance_km': total_distance,
        'total_eta_minutes': total_eta_minutes
    })


if __name__ == '__main__':
    with app.app_context():
        try:
            db.engine.connect()
            print("Database connected successfully!")
        except SQLAlchemyError as e:
            print(" Database connection failed:", e)
        db.create_all()
        print(" Tables created!")
    app.run(debug=True)
