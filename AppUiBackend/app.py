from datetime import timedelta
from flask import Flask, jsonify, redirect, render_template, request, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, get_jwt_identity, jwt_required
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-this-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'super-secret-jwt-key-change-me'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)

db = SQLAlchemy(app)
jwt = JWTManager(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='user')
    is_active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'full_name': self.full_name,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
        }


def seed_admin_user():
    if not User.query.filter_by(email='admin@example.com').first():
        admin = User(
            full_name='Admin User',
            email='admin@example.com',
            password_hash=generate_password_hash('Admin@123'),
            role='admin',
            is_active=True,
        )
        db.session.add(admin)
        db.session.commit()


@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


# ---- renamed back to 'login' to match HTML url_for('login') ----
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['user_name'] = user.full_name
            return redirect(url_for('dashboard'))

        flash('Invalid email or password.', 'danger')

    return render_template('login.html')


# ---- renamed back to 'signup' to match HTML url_for('signup') ----
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not all([full_name, email, password, confirm_password]):
            flash('All fields are required.', 'danger')
            return render_template('signup.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('signup.html')

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('signup.html')

        user = User(
            full_name=full_name,
            email=email,
            password_hash=generate_password_hash(password),
            role='user',
            is_active=True,
        )
        db.session.add(user)
        db.session.commit()
        flash('Signup successful. Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please login first.', 'warning')
        return redirect(url_for('login'))
    users = User.query.order_by(User.id.asc()).all()
    return render_template('dashboard.html', users=users)


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))


# ---------------- JWT API ----------------
@app.route('/api/auth/signup', methods=['POST'])
def api_signup():
    data = request.get_json(silent=True) or {}
    required_fields = ['full_name', 'email', 'password', 'confirm_password']
    missing_fields = [field for field in required_fields if not data.get(field)]
    if missing_fields:
        return jsonify({'error': f"Missing fields: {', '.join(missing_fields)}"}), 400

    if data['password'] != data['confirm_password']:
        return jsonify({'error': 'Passwords do not match.'}), 400

    email = data['email'].strip().lower()
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists.'}), 409

    user = User(
        full_name=data['full_name'].strip(),
        email=email,
        password_hash=generate_password_hash(data['password']),
        role=data.get('role', 'user').strip() if data.get('role') else 'user',
        is_active=bool(data.get('is_active', True)),
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'User created successfully.', 'user': user.to_dict()}), 201


@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'Email and password are required.'}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Invalid email or password.'}), 401

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={'email': user.email, 'role': user.role}
    )
    return jsonify({
        'message': 'Login successful.',
        'access_token': access_token,
        'user': user.to_dict()
    }), 200


@app.route('/api/users', methods=['GET'])
@jwt_required()
def get_users():
    users = User.query.order_by(User.id.asc()).all()
    return jsonify([user.to_dict() for user in users]), 200


@app.route('/api/users/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict()), 200


@app.route('/api/users', methods=['POST'])
@jwt_required()
def create_user():
    data = request.get_json(silent=True) or {}
    required_fields = ['full_name', 'email', 'password']
    missing_fields = [field for field in required_fields if not data.get(field)]
    if missing_fields:
        return jsonify({'error': f"Missing fields: {', '.join(missing_fields)}"}), 400

    email = data['email'].strip().lower()
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists.'}), 409

    user = User(
        full_name=data['full_name'].strip(),
        email=email,
        password_hash=generate_password_hash(data['password']),
        role=data.get('role', 'user').strip() if data.get('role') else 'user',
        is_active=bool(data.get('is_active', True)),
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'User created successfully.', 'user': user.to_dict()}), 201


@app.route('/api/users/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user_put(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json(silent=True) or {}

    required_fields = ['full_name', 'email', 'role', 'is_active']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        return jsonify({'error': f"PUT requires all fields: {', '.join(required_fields)}"}), 400

    email = data['email'].strip().lower()
    existing_user = User.query.filter(User.email == email, User.id != user_id).first()
    if existing_user:
        return jsonify({'error': 'Another user already uses this email.'}), 409

    user.full_name = data['full_name'].strip()
    user.email = email
    user.role = data['role'].strip()
    user.is_active = bool(data['is_active'])

    if data.get('password'):
        user.password_hash = generate_password_hash(data['password'])

    db.session.commit()
    return jsonify({'message': 'User updated with PUT.', 'user': user.to_dict()}), 200


@app.route('/api/users/<int:user_id>', methods=['PATCH'])
@jwt_required()
def update_user_patch(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json(silent=True) or {}

    if 'full_name' in data and data['full_name']:
        user.full_name = data['full_name'].strip()

    if 'email' in data and data['email']:
        email = data['email'].strip().lower()
        existing_user = User.query.filter(User.email == email, User.id != user_id).first()
        if existing_user:
            return jsonify({'error': 'Another user already uses this email.'}), 409
        user.email = email

    if 'role' in data and data['role']:
        user.role = data['role'].strip()

    if 'is_active' in data:
        user.is_active = bool(data['is_active'])

    if 'password' in data and data['password']:
        user.password_hash = generate_password_hash(data['password'])

    db.session.commit()
    return jsonify({'message': 'User updated with PATCH.', 'user': user.to_dict()}), 200


@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    current_user_id = int(get_jwt_identity())
    if current_user_id == user_id:
        return jsonify({'error': 'Logged-in user cannot delete self.'}), 400

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'User deleted successfully.'}), 200


@app.errorhandler(404)
def not_found(_error):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Resource not found'}), 404
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(_error):
    db.session.rollback()
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Internal server error'}), 500
    return render_template('500.html'), 500


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_admin_user()
    app.run(debug=True)