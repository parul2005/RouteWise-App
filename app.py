from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token
from flask_jwt_extended import jwt_required, get_jwt_identity
from algorithm import calculate_distance, optimize_route
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Database se connect karne ki settings
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Parul123@localhost:5432/routewise_db'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
app.config['JWT_SECRET_KEY'] = 'routewise-secret-key-123'
jwt = JWTManager(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'vendor' or 'delivery_boy'

    def __repr__(self):
        return f'<User {self.name}>'


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(300), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending / delivered

    def __repr__(self):
        return f'<Order {self.id} - {self.customer_name}>'


@app.route('/')
def home():
    return 'Hello RouteWise'


@app.route('/about')
def about():
    return 'Yeh mera pehla Flask project hai!'


@app.route('/add-user', methods=['POST'])
def add_user():
    data = request.get_json()

    hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')

    new_user = User(
        name=data['name'],
        email=data['email'],
        password=hashed_password,
        role=data['role']
    )

    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User added successfully!'})


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    user = User.query.filter_by(email=data['email']).first()

    if not user:
        return jsonify({'message': 'User not found!'}), 404

    if not bcrypt.check_password_hash(user.password, data['password']):
        return jsonify({'message': 'Wrong password!'}), 401

    token = create_access_token(identity=str(user.id))

    return jsonify({
        'message': 'Login successful!',
        'token': token,
        'role': user.role
    })


@app.route('/all-users', methods=['GET'])
def get_all_users():
    users = User.query.all()

    result = []
    for user in users:
        result.append({
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'role': user.role
        })

    return jsonify(result)


@app.route('/add-order', methods=['POST'])
def add_order():
    data = request.get_json()

    new_order = Order(
        vendor_id=data['vendor_id'],
        customer_name=data['customer_name'],
        address=data['address'],
        latitude=data.get('latitude'),
        longitude=data.get('longitude')
    )

    db.session.add(new_order)
    db.session.commit()

    return jsonify({'message': 'Order added successfully!'})


@app.route('/all-orders', methods=['GET'])
@jwt_required()
def get_all_orders():
    orders = Order.query.all()

    result = []
    for order in orders:
        result.append({
            'id': order.id,
            'vendor_id': order.vendor_id,
            'customer_name': order.customer_name,
            'address': order.address,
            'latitude': order.latitude,
            'longitude': order.longitude,
            'status': order.status
        })

    return jsonify(result)


@app.route('/my-orders', methods=['GET'])
@jwt_required()
def get_my_orders():
    current_user_id = get_jwt_identity()

    orders = Order.query.filter_by(vendor_id=current_user_id).all()

    result = []
    for order in orders:
        result.append({
            'id': order.id,
            'customer_name': order.customer_name,
            'address': order.address,
            'latitude': order.latitude,
            'longitude': order.longitude,
            'status': order.status
        })

    return jsonify(result)

@app.route('/optimize-route', methods=['GET'])
@jwt_required()
def get_optimized_route():
    current_user_id = get_jwt_identity()

    # Sirf "pending" orders lo, jo abhi tak deliver nahi hue
    orders = Order.query.filter_by(vendor_id=current_user_id, status='pending').all()

    if not orders:
        return jsonify({'message': 'No pending orders found!'}), 404

    # Store ka location - abhi ke liye hardcoded (aage vendor apna store location set kar sakega)
    store_location = (28.7041, 77.1025)

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
        return jsonify({'message': 'No orders with location data found!'}), 404

    best_route, total_distance = optimize_route(store_location, order_list)

    return jsonify({
        'optimized_route': best_route,
        'total_distance_km': total_distance
    })


if __name__ == '__main__':
    with app.app_context():
        try:
            db.engine.connect()
            print("✅ Database connected successfully!")
        except Exception as e:
            print("❌ Database connection failed:", e)
        db.create_all()
        print("✅ Tables created!")
    app.run(debug=True)