"""
Database Models for Club Management System
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# Enumeration for user types and statuses
USER_TYPE_STUDENT = 'student'
USER_TYPE_CLUB = 'club'
USER_TYPE_ADMIN = 'admin'

STATUS_PENDING = 'pending'
STATUS_APPROVED = 'approved'
STATUS_REJECTED = 'rejected'
STATUS_ACTIVE = 'active'


class User(db.Model):
    """User model for all user types: students, clubs, and admins"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    user_type = db.Column(db.String(20), nullable=False)  # student, club, admin
    status = db.Column(db.String(20), default=STATUS_ACTIVE)  # active, inactive
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    student_profile = db.relationship('Student', backref='user', uselist=False, cascade='all, delete-orphan')
    club_profile = db.relationship('Club', backref='user', uselist=False, cascade='all, delete-orphan', foreign_keys='Club.user_id')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password"""
        return check_password_hash(self.password_hash, password)
    
    def is_student(self):
        return self.user_type == USER_TYPE_STUDENT
    
    def is_club(self):
        return self.user_type == USER_TYPE_CLUB
    
    def is_admin(self):
        return self.user_type == USER_TYPE_ADMIN


class Student(db.Model):
    """Student profile model"""
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    student_code = db.Column(db.String(50), unique=True, nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.String(255))
    university_year = db.Column(db.Integer)  # Năm học
    major = db.Column(db.String(100))
    avatar_url = db.Column(db.String(255))
    achievement_points = db.Column(db.Integer, default=0)  # Điểm Đoàn
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    club_applications = db.relationship('ClubApplication', backref='student', cascade='all, delete-orphan')
    event_registrations = db.relationship('EventRegistration', backref='student', cascade='all, delete-orphan')
    orders = db.relationship('Order', backref='student', cascade='all, delete-orphan')


class Club(db.Model):
    """Club model"""
    __tablename__ = 'clubs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    club_name = db.Column(db.String(200), nullable=False, unique=True)
    description = db.Column(db.Text)
    field = db.Column(db.String(100))  # Lĩnh vực hoạt động (Culture, Sports, etc.)
    logo_url = db.Column(db.String(255))
    establishment_year = db.Column(db.Integer)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    president_name = db.Column(db.String(200))
    vice_president_name = db.Column(db.String(200))
    status = db.Column(db.String(20), default=STATUS_PENDING)  # pending, approved, rejected
    registered_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # sinh vien dang ky
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    intended_username = db.Column(db.String(80)) # Ten dang nhap do SV yeu cau
    
    # Relationships
    members = db.relationship('ClubMember', backref='club', cascade='all, delete-orphan')
    applications = db.relationship('ClubApplication', backref='club', cascade='all, delete-orphan')
    events = db.relationship('Event', backref='club', cascade='all, delete-orphan')
    products = db.relationship('Product', backref='club', cascade='all, delete-orphan')
    orders = db.relationship('Order', backref='club', cascade='all, delete-orphan')
    posts = db.relationship('ClubPost', backref='club', cascade='all, delete-orphan')


class ClubPost(db.Model):
    """Club posts/news model"""
    __tablename__ = 'club_posts'
    
    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey('clubs.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(255))
    visibility = db.Column(db.String(20), default='public')  # public, members, private
    status = db.Column(db.String(20), default=STATUS_ACTIVE)  # active, inactive
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ClubMember(db.Model):
    """Club members model"""
    __tablename__ = 'club_members'
    
    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey('clubs.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    position = db.Column(db.String(100))  # Vị trí trong CLB
    status = db.Column(db.String(20), default=STATUS_ACTIVE)  # active, inactive
    join_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship for student
    student = db.relationship('Student', backref='club_memberships')


class ClubApplication(db.Model):
    """Club application/registration model"""
    __tablename__ = 'club_applications'
    
    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey('clubs.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    motivation = db.Column(db.Text)  # Lý do muốn tham gia
    status = db.Column(db.String(20), default=STATUS_PENDING)  # pending, approved, rejected
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    decided_at = db.Column(db.DateTime)
    admin_notes = db.Column(db.Text)


class Event(db.Model):
    """Event model"""
    __tablename__ = 'events'
    
    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey('clubs.id'), nullable=False)
    event_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime)
    location = db.Column(db.String(255))
    max_participants = db.Column(db.Integer)
    status = db.Column(db.String(20), default=STATUS_PENDING)  # pending, approved, active, completed, cancelled
    thumbnail_url = db.Column(db.String(255))
    check_in_code = db.Column(db.String(10), unique=True)  # Secret code for CICO
    achievement_points = db.Column(db.Integer, default=5)  # Points rewarded for attendance
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    registrations = db.relationship('EventRegistration', backref='event', cascade='all, delete-orphan')

    @property
    def is_ended(self):
        """Check if event has ended based on end_date (or start_date if no end_date)"""
        now = datetime.utcnow()
        if self.end_date:
            return now > self.end_date
        return now > self.start_date


class EventRegistration(db.Model):
    """Event registration model"""
    __tablename__ = 'event_registrations'
    
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default=STATUS_PENDING)  # pending, approved, rejected, attended
    notes = db.Column(db.Text)
    achievement_points = db.Column(db.Integer, default=0)  # Điểm Đoàn cấp
    check_in_at = db.Column(db.DateTime)
    check_out_at = db.Column(db.DateTime)


class Product(db.Model):
    """Product model for club sales"""
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey('clubs.id'), nullable=False)
    product_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, default=0)
    image_url = db.Column(db.String(255))
    status = db.Column(db.String(20), default=STATUS_PENDING)  # pending, approved, active, inactive
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    order_items = db.relationship('OrderItem', backref='product', cascade='all, delete-orphan')


class Order(db.Model):
    """Order model"""
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    club_id = db.Column(db.Integer, db.ForeignKey('clubs.id'), nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    total_price = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), default=STATUS_PENDING)  # pending, confirmed, shipped, delivered, cancelled
    notes = db.Column(db.Text)
    
    # Shipping & Contact Info
    shipping_name = db.Column(db.String(200))
    shipping_phone = db.Column(db.String(20))
    shipping_email = db.Column(db.String(100))
    shipping_major = db.Column(db.String(100))
    shipping_address = db.Column(db.String(255))
    payment_method = db.Column(db.String(50), default='Tiền mặt')
    
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    order_items = db.relationship('OrderItem', backref='order', cascade='all, delete-orphan')


class OrderItem(db.Model):
    """Order items model"""
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price_per_unit = db.Column(db.Float, nullable=False)


class Notification(db.Model):
    """Notification model"""
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text)
    notification_type = db.Column(db.String(50))  # club_update, event, order, etc.
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref='notifications')


class Report(db.Model):
    """Report model for statistics and analytics"""
    __tablename__ = 'reports'
    
    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey('clubs.id'))
    report_type = db.Column(db.String(50))  # revenue, members, events, products, etc.
    report_date = db.Column(db.DateTime, default=datetime.utcnow)
    data = db.Column(db.JSON)  # Store report data as JSON
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # Admin who created it
    
    # Relationships
class CartItem(db.Model):
    """Shopping cart items for persistent storage"""
    __tablename__ = 'cart_items'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    product = db.relationship('Product')
    user = db.relationship('User', backref=db.backref('cart_items', lazy=True))
