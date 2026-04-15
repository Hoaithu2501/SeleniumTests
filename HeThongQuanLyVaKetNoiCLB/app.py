"""
Main Flask Application for Club Management System
Hệ thống quản lý và kết nối CLB - Sinh viên NEU
"""
from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
from werkzeug.security import generate_password_hash
from models import (
    db, User, Student, Club, ClubMember, ClubApplication, Event, EventRegistration,
    Product, Order, OrderItem, Notification, Report, ClubPost, CartItem,
    USER_TYPE_STUDENT, USER_TYPE_CLUB, USER_TYPE_ADMIN,
    STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED, STATUS_ACTIVE
)
import os
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from datetime import datetime
import random
import string

load_dotenv()

app = Flask(__name__)
# Serializer for temporary CICO tokens
serializer = URLSafeTimedSerializer(os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production'))

# Configuration
# Ensure db folder exists for SQLite
db_folder = os.path.join(app.root_path, 'db')
if not os.path.exists(db_folder):
    os.makedirs(db_folder)

# Database path in db folder
db_path = os.path.join(db_folder, 'club_management.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour 

# Upload Configuration
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads', 'posts')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Initialize database and login manager
db.init_app(app)

# Database initialization logic
with app.app_context():
    db.create_all()
    
    # Simple migration for 'notes' column if it doesn't exist
    try:
        import sqlite3
        conn = sqlite3.connect(os.path.join(app.root_path, 'db', 'club_management.db'))
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(event_registrations)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'notes' not in columns:
            cursor.execute("ALTER TABLE event_registrations ADD COLUMN notes TEXT")
            conn.commit()
            print("Added 'notes' column to event_registrations table")
        conn.close()
    except Exception as e:
        print(f"Migration error: {e}")

    # Create default admin if it doesn't exist
    admin = User.query.filter_by(user_type=USER_TYPE_ADMIN).first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@neu.edu.vn',
            user_type=USER_TYPE_ADMIN,
            status=STATUS_ACTIVE
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("Default admin created: admin/admin123")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# User loader for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Helper Functions
def create_notification(user_id, title, message, n_type='info'):
    """Create a new notification for a specific user"""
    try:
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=n_type
        )
        db.session.add(notif)
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error creating notification: {e}")
        return False


@app.context_processor
def inject_global_data():
    """Inject unread notification count and cart count into all templates"""
    unread_count = 0
    cart_count = 0
    if current_user.is_authenticated:
        unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        if current_user.is_student():
            cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
        elif 'cart' in session:
            cart_count = sum(session['cart'].values())
    return dict(unread_count=unread_count, cart_count=cart_count)


# Make User compatible with Flask-Login
User.is_authenticated = True
User.is_active = property(lambda self: self.status == 'active')
User.get_id = lambda self: str(self.id)


@app.route('/')
def index():
    """Home page"""
    if current_user.is_authenticated:
        if current_user.is_student():
            return redirect(url_for('student_dashboard'))
        elif current_user.is_club():
            return redirect(url_for('club_dashboard'))
        elif current_user.is_admin():
            return redirect(url_for('admin_dashboard'))
    
    clubs = Club.query.filter_by(status=STATUS_APPROVED).limit(6).all()
    events = Event.query.filter_by(status=STATUS_APPROVED).limit(6).all()
    return render_template('index.html', clubs=clubs, events=events)


# ============ AUTHENTICATION ROUTES ============

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        user_type = request.form.get('user_type')
        
        # Validate input
        if not username or not email or not password or not user_type:
            flash('Vui lòng điền đầy đủ thông tin', 'danger')
            return redirect(url_for('register'))
            
        # Check email domain
        if not email.endswith('@neu.edu.vn'):
            flash('Email phải có đuôi @neu.edu.vn', 'danger')
            return redirect(url_for('register'))
            
        # Check password length
        if len(password) < 6:
            flash('Mật khẩu phải có ít nhất 6 ký tự', 'danger')
            return redirect(url_for('register'))
        
        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash('Tên đăng nhập đã tồn tại', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email đã được sử dụng', 'danger')
            return redirect(url_for('register'))
        
        # Create new user
        user = User(username=username, email=email, user_type=user_type)
        user.set_password(password)
        
        try:
            db.session.add(user)
            db.session.flush()
            
            # Create profile based on user type
            if user_type == USER_TYPE_STUDENT:
                student_code = request.form.get('student_code')
                full_name = request.form.get('full_name')
                
                student = Student(
                    user_id=user.id,
                    student_code=student_code,
                    full_name=full_name
                )
                db.session.add(student)
            
            elif user_type == USER_TYPE_CLUB:
                club_name = request.form.get('club_name')
                field = request.form.get('field')
                president_name = request.form.get('president_name')
                
                club = Club(
                    user_id=user.id,
                    club_name=club_name,
                    field=field,
                    president_name=president_name
                )
                db.session.add(club)
            
            db.session.commit()
            flash('Đăng ký thành công! Vui lòng đăng nhập', 'success')
            return redirect(url_for('login'))
        
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi đăng ký: {str(e)}', 'danger')
            return redirect(url_for('register'))
    
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            # Capture cart from session before clearing it
            session_cart = session.get('cart', {})
            
            # Clear existing session data before logging in new user
            session.clear()
            login_user(user)
            
            # Merge session cart into database if login is successful and it's a student
            if user.is_student() and session_cart:
                for p_id, qty in session_cart.items():
                    cart_item = CartItem.query.filter_by(user_id=user.id, product_id=int(p_id)).first()
                    if cart_item:
                        cart_item.quantity += qty
                    else:
                        new_item = CartItem(user_id=user.id, product_id=int(p_id), quantity=qty)
                        db.session.add(new_item)
                db.session.commit()
                
            flash(f'Chào mừng {user.username}!', 'success')
            
            # Redirect based on user type
            if user.is_student():
                return redirect(url_for('student_dashboard'))
            elif user.is_club():
                return redirect(url_for('club_dashboard'))
            elif user.is_admin():
                return redirect(url_for('admin_dashboard'))
        else:
            flash('Tên đăng nhập hoặc mật khẩu không chính xác', 'danger')
    
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    session.clear()  # Clear transient session data (Cart is persisted in DB)
    flash('Bạn đã đăng xuất', 'info')
    return redirect(url_for('index'))


@app.route('/account/change-credentials', methods=['GET', 'POST'])
@login_required
def change_credentials():
    """Change username and/or password for any user type"""
    if request.method == 'POST':
        new_username = request.form.get('new_username', '').strip()
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not current_password:
            flash('Vui lòng nhập mật khẩu hiện tại', 'danger')
            return redirect(url_for('change_credentials'))

        if not current_user.check_password(current_password):
            flash('Mật khẩu hiện tại không chính xác', 'danger')
            return redirect(url_for('change_credentials'))

        changed = False

        # Doi ten dang nhap
        if new_username and new_username != current_user.username:
            existing = User.query.filter_by(username=new_username).first()
            if existing:
                flash('Tên đăng nhập này đã được sử dụng', 'danger')
                return redirect(url_for('change_credentials'))
            current_user.username = new_username
            changed = True

        # Doi mat khau
        if new_password:
            if new_password != confirm_password:
                flash('Mật khẩu xác nhận không khớp', 'danger')
                return redirect(url_for('change_credentials'))
            if len(new_password) < 6:
                flash('Mật khẩu mới phải có ít nhất 6 ký tự', 'danger')
                return redirect(url_for('change_credentials'))
            current_user.set_password(new_password)
            changed = True

        if changed:
            try:
                db.session.commit()
                flash('Cập nhật thông tin đăng nhập thành công!', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Lỗi: {str(e)}', 'danger')
        else:
            flash('Không có thay đổi nào được thực hiện', 'info')

        return redirect(url_for('change_credentials'))

    return render_template('change_credentials.html')


# ============ STUDENT ROUTES ============

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    """Student dashboard"""
    if not current_user.is_student():
        flash('Truy cập từ chối', 'danger')
        return redirect(url_for('index'))
    
    student = current_user.student_profile
    
    # Get actual counts
    club_count = len(student.club_memberships)
    event_count = len(student.event_registrations)
    order_count = len(student.orders)
    
    # Notifications count
    unread_notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    
    # Get upcoming events (not registered yet)
    registered_event_ids = [r.event_id for r in student.event_registrations]
    upcoming_events = Event.query.filter(
        Event.status == STATUS_APPROVED,
        Event.id.not_in(registered_event_ids if registered_event_ids else [0]),
        Event.start_date > datetime.utcnow()
    ).order_by(Event.start_date).limit(6).all()
    
    # Get news from joined clubs
    joined_club_ids = [m.club_id for m in student.club_memberships]
    club_posts = ClubPost.query.filter(
        ClubPost.club_id.in_(joined_club_ids if joined_club_ids else [0]),
        ClubPost.visibility.in_(['public', 'members']),
        ClubPost.status == STATUS_ACTIVE
    ).order_by(ClubPost.created_at.desc()).limit(5).all()
        
    # Clubs the student is a member of
    my_club_memberships = student.club_memberships
    my_clubs = [m.club for m in my_club_memberships]
    
    # Add clubs registered by this student (if not already in my_clubs)
    registered_clubs = Club.query.filter_by(registered_by_user_id=current_user.id, status=STATUS_APPROVED).all()
    for rc in registered_clubs:
        if rc not in my_clubs:
            my_clubs.append(rc)
            club_count += 1

    return render_template('student/dashboard.html',
                         student=student,
                         club_count=club_count,
                         event_count=event_count,
                         order_count=order_count,
                         unread_notifications=unread_notifications,
                         upcoming_events=upcoming_events,
                         my_clubs=my_clubs,
                         club_posts=club_posts)


@app.route('/student/profile')
@login_required
def student_profile():
    """Student profile view"""
    if not current_user.is_student():
        return redirect(url_for('index'))
    
    student = current_user.student_profile
    return render_template('student/profile.html', student=student)


@app.route('/student/activities')
@login_required
def student_activities():
    """View student applications and registered events"""
    if not current_user.is_student():
        return redirect(url_for('index'))
    
    student = current_user.student_profile
    applications = ClubApplication.query.filter_by(student_id=student.id).order_by(ClubApplication.applied_at.desc()).all()
    registrations = EventRegistration.query.filter_by(student_id=student.id).order_by(EventRegistration.registration_date.desc()).all()
    
    return render_template('student/activities.html', 
                          applications=applications, 
                          registrations=registrations)


@app.route('/notifications')
@login_required
def notifications_list():
    """List of user notifications"""
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template('notifications.html', notifications=notifications)


@app.route('/notifications/read-all', methods=['POST'])
@login_required
def read_all_notifications():
    """Mark all notifications as read"""
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return redirect(url_for('notifications_list'))


@app.route('/student/profile/edit', methods=['GET', 'POST'])
@login_required
def student_profile_edit():
    """Edit student profile"""
    if not current_user.is_student():
        return redirect(url_for('index'))
    
    student = current_user.student_profile
    
    if request.method == 'POST':
        student.full_name = request.form.get('full_name', student.full_name)
        student.phone = request.form.get('phone', student.phone)
        student.address = request.form.get('address', student.address)
        student.university_year = request.form.get('university_year', student.university_year)
        student.major = request.form.get('major', student.major)
        student.avatar_url = request.form.get('avatar_url', student.avatar_url)
        
        try:
            db.session.commit()
            flash('Cập nhật hồ sơ thành công', 'success')
            return redirect(url_for('student_profile'))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi: {str(e)}', 'danger')
    
    return render_template('student/profile_edit.html', student=student)


@app.route('/student/clubs')
@login_required
def student_clubs():
    """View available clubs"""
    if not current_user.is_student():
        return redirect(url_for('index'))
    
    approved_clubs = Club.query.filter_by(status=STATUS_APPROVED).all()
    return render_template('student/clubs.html', clubs=approved_clubs)


@app.route('/student/clubs/<int:club_id>/apply', methods=['POST'])
@login_required
def student_apply_club(club_id):
    """Apply to join a club"""
    if not current_user.is_student():
        return redirect(url_for('index'))
    
    student = current_user.student_profile
    club = Club.query.get_or_404(club_id)
    motivation = request.form.get('motivation', '')
    
    # Check if this student is the one who registered the club (Founder)
    if club.registered_by_user_id == current_user.id:
        flash('Bạn là người sáng lập CLB này, không thể nộp đơn tham gia như thành viên.', 'warning')
        return redirect(url_for('student_clubs'))

    # Check if already a member
    is_member = ClubMember.query.filter_by(
        club_id=club_id,
        student_id=student.id,
        status=STATUS_ACTIVE
    ).first()
    
    if is_member:
        flash('Bạn đã là thành viên của CLB này.', 'info')
        return redirect(url_for('student_clubs'))
    
    # Check if already applied
    existing_app = ClubApplication.query.filter_by(
        club_id=club_id,
        student_id=student.id
    ).first()
    
    if existing_app:
        if existing_app.status == STATUS_PENDING:
            flash('Bạn đã nộp đơn tham gia CLB này và đang chờ duyệt.', 'warning')
        elif existing_app.status == STATUS_APPROVED:
            flash('Bạn đã được duyệt vào CLB này.', 'success')
        else:
            flash('Đơn tham gia của bạn đã bị từ chối.', 'danger')
        return redirect(url_for('student_clubs'))
    
    try:
        application = ClubApplication(
            club_id=club_id,
            student_id=student.id,
            motivation=motivation
        )
        db.session.add(application)
        
        # Thong bao cho CLB
        create_notification(
            club.user_id,
            "Đơn ứng tuyển mới",
            f"Sinh viên {student.full_name} đã nộp đơn gia nhập CLB của bạn.",
            'info'
        )
        
        db.session.commit()
        flash('Nộp đơn thành công. Vui lòng chờ duyệt', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi: {str(e)}', 'danger')
    
    return redirect(url_for('student_clubs'))


@app.route('/student/events')
@login_required
def student_events():
    """View available events"""
    if not current_user.is_student():
        return redirect(url_for('index'))
    
    events = Event.query.filter_by(status=STATUS_APPROVED).all()
    return render_template('student/events.html', events=events)


@app.route('/student/club/register', methods=['GET', 'POST'])
@login_required
def student_club_register():
    """Form to request club establishment"""
    if not current_user.is_student():
        flash('Truy cập từ chối', 'danger')
        return redirect(url_for('index'))
    
    student = current_user.student_profile
    
    if request.method == 'POST':
        club_name = request.form.get('club_name')
        field = request.form.get('field')
        description = request.form.get('description')
        president_name = request.form.get('president_name')
        phone = request.form.get('phone')
        email = request.form.get('email')
        intended_username = request.form.get('intended_username', '').strip().lower()
        
        # Validation
        if not club_name or not field or not intended_username:
            flash('Vui lòng điền đủ thông tin bắt buộc, bao gồm tên đăng nhập dự kiến', 'danger')
            return redirect(url_for('student_club_register'))
            
        if Club.query.filter_by(club_name=club_name).first():
            flash('Tên Câu lạc bộ này đã tồn tại', 'danger')
            return redirect(url_for('student_club_register'))

        if User.query.filter_by(username=intended_username).first():
            flash('Tên đăng nhập này đã có người sử dụng. Vui lòng chọn tên khác.', 'danger')
            return redirect(url_for('student_club_register'))

        try:
            # Create a virtual user for the club
            username = intended_username
            club_user = User(
                username=username,
                email=f"{username}@neu.edu.vn",
                user_type=USER_TYPE_CLUB,
                status='inactive' # Inactive until admin approves
            )
            club_user.set_password('neuclub123')
            db.session.add(club_user)
            db.session.flush()
            
            # Create the club registration request
            new_club = Club(
                user_id=club_user.id,
                club_name=club_name,
                field=field,
                description=description,
                president_name=president_name or student.full_name,
                phone=phone,
                email=email or f"{username}@neu.edu.vn",
                status=STATUS_PENDING,
                registered_by_user_id=current_user.id,  # luu lai sinh vien da dang ky
                intended_username=intended_username
            )
            db.session.add(new_club)
            db.session.commit()
            
            # Notify Admin (Optional but good practice)
            # Find admin user
            admin_user = User.query.filter_by(user_type=USER_TYPE_ADMIN).first()
            if admin_user:
                create_notification(
                    admin_user.id,
                    "Yêu cầu thành lập CLB mới",
                    f"Sinh viên {student.full_name} đã gửi yêu cầu thành lập CLB '{club_name}'.",
                    'info'
                )
                
            flash('Gửi đơn đăng ký thành công! Vui lòng đợi Ban quản lý xem xét và phê duyệt.', 'success')
            return redirect(url_for('student_dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Có lỗi xảy ra: {str(e)}', 'danger')
            
    return render_template('student/club_register.html', student=student)


# ============ CLUB ROUTES ============

@app.route('/club/dashboard')
@login_required
def club_dashboard():
    """Club dashboard"""
    if not current_user.is_club():
        flash('Truy cập từ chối', 'danger')
        return redirect(url_for('index'))
    
    club = current_user.club_profile
    
    return render_template('club/dashboard.html', club=club)


@app.route('/club/profile')
@login_required
def club_profile():
    """Club profile"""
    if not current_user.is_club():
        return redirect(url_for('index'))
    
    club = current_user.club_profile
    return render_template('club/profile.html', club=club)


@app.route('/club/profile/edit', methods=['GET', 'POST'])
@login_required
def club_profile_edit():
    """Edit Club profile"""
    if not current_user.is_club():
        return redirect(url_for('index'))
    
    club = current_user.club_profile
    
    if request.method == 'POST':
        # Update fields
        club.club_name = request.form.get('club_name', club.club_name)
        club.field = request.form.get('field', club.field)
        club.president_name = request.form.get('president_name', club.president_name)
        club.vice_president_name = request.form.get('vice_president_name', club.vice_president_name)
        club.email = request.form.get('email', club.email)
        club.phone = request.form.get('phone', club.phone)
        club.logo_url = request.form.get('logo_url', club.logo_url)
        club.description = request.form.get('description', club.description)
        
        year = request.form.get('establishment_year')
        if year and year.isdigit():
            club.establishment_year = int(year)
            
        try:
            db.session.commit()
            flash('Cập nhật thông tin Câu lạc bộ thành công!', 'success')
            return redirect(url_for('club_profile'))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi khi lưu thông tin: {e}', 'danger')
            
    return render_template('club/profile_edit.html', club=club)


@app.route('/club/members')
@login_required
def club_members():
    """View club members"""
    if not current_user.is_club():
        return redirect(url_for('index'))
    
    club = current_user.club_profile
    members = club.members
    return render_template('club/members.html', club=club, members=members)


@app.route('/club/members/remove/<int:member_id>', methods=['POST'])
@login_required
def remove_member(member_id):
    """Remove a student from the club"""
    if not current_user.is_club():
        flash('Truy cập từ chối', 'danger')
        return redirect(url_for('index'))
    
    member = ClubMember.query.get_or_404(member_id)
    
    # Check if this member belongs to the current club
    if member.club_id != current_user.club_profile.id:
        flash('Bạn không có quyền thực hiện hành động này', 'danger')
        return redirect(url_for('club_members'))

    try:
        student_user_id = member.student.user_id
        student_name = member.student.full_name
        club_name = member.club.club_name
        
        db.session.delete(member)
        
        # Notify the student
        create_notification(
            student_user_id,
            f"Thông báo từ CLB {club_name}",
            f"Bạn đã được xóa khỏi danh sách thành viên của CLB {club_name}.",
            'warning'
        )
        
        db.session.commit()
        flash(f'Đã xóa thành viên {student_name} khỏi CLB', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi khi xóa thành viên: {str(e)}', 'danger')
        
    return redirect(url_for('club_members'))


@app.route('/club/applications')
@login_required
def club_applications():
    """View club applications"""
    if not current_user.is_club():
        return redirect(url_for('index'))
    
    club = current_user.club_profile
    applications = ClubApplication.query.filter_by(club_id=club.id).order_by(ClubApplication.applied_at.desc()).all()
    return render_template('club/applications.html', club=club, applications=applications)


@app.route('/club/applications/<int:app_id>/<action>', methods=['POST'])
@login_required
def process_application(app_id, action):
    """Process a student's application to join the club"""
    if not current_user.is_club():
        return redirect(url_for('index'))
    
    application = ClubApplication.query.get_or_404(app_id)
    
    # Ensure this application belongs to the current user's club
    if application.club_id != current_user.club_profile.id:
        flash('Bạn không có quyền thực hiện hành động này', 'danger')
        return redirect(url_for('club_applications'))
    
    if application.status != STATUS_PENDING:
        flash('Đơn này đã được xử lý', 'warning')
        return redirect(url_for('club_applications'))

    if action == 'approve':
        application.status = STATUS_APPROVED
        application.decided_at = datetime.utcnow()
        
        # Add to club members
        new_member = ClubMember(
            club_id=application.club_id,
            student_id=application.student_id,
            position='Thành viên',
            join_date=datetime.utcnow()
        )
        db.session.add(new_member)
        
        # Send notification
        create_notification(
            application.student.user_id,
            f"Đã được duyệt vào {application.club.club_name}",
            f"Chúc mừng! Đơn gia nhập của bạn vào CLB {application.club.club_name} đã được phê duyệt.",
            'success'
        )
        flash('Đã duyệt đơn đăng ký tham gia', 'success')
        
    elif action == 'reject':
        application.status = STATUS_REJECTED
        application.decided_at = datetime.utcnow()
        
        # Send notification
        create_notification(
            application.student.user_id,
            f"Đơn gia nhập {application.club.club_name} bị từ chối",
            f"Rất tiếc, đơn gia nhập của bạn vào CLB {application.club.club_name} hiện không được phê duyệt.",
            'danger'
        )
        flash('Đã từ chối đơn đăng ký', 'info')
    else:
        flash('Hành động không hợp lệ', 'danger')
        
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi khi xử lý đơn: {str(e)}', 'danger')
        
    return redirect(url_for('club_applications'))


@app.route('/club/reports')
@login_required
def club_reports():
    """Club Analytics & Reports"""
    if not current_user.is_club():
        return redirect(url_for('index'))
        
    club = current_user.club_profile
    
    # Calculate stats
    total_members = len(club.members)
    active_events = Event.query.filter_by(club_id=club.id).filter(Event.status.in_([STATUS_APPROVED, 'active'])).count()
    total_products = len(club.products)
    
    # Calculate Revenue (Completed orders)
    completed_orders = Order.query.filter_by(club_id=club.id, status='delivered').all()
    total_revenue = sum(order.total_price for order in completed_orders)
    
    return render_template('club/reports.html', 
                           club=club, 
                           total_members=total_members, 
                           active_events=active_events,
                           total_products=total_products,
                           total_revenue=total_revenue,
                           completed_orders=completed_orders)


# ============ ADMIN ROUTES ============

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """Admin dashboard"""
    if not current_user.is_admin():
        flash('Truy cập từ chối', 'danger')
        return redirect(url_for('index'))
    
    # Get statistics
    total_students = Student.query.count()
    total_clubs = Club.query.count()
    total_events = Event.query.count()
    pending_clubs = Club.query.filter_by(status=STATUS_PENDING).count()
    pending_events = Event.query.filter_by(status=STATUS_PENDING).count()
    
    return render_template('admin/dashboard.html',
                         total_students=total_students,
                         total_clubs=total_clubs,
                         total_events=total_events,
                         pending_clubs=pending_clubs,
                         pending_events=pending_events)


@app.route('/admin/reports')
@login_required
def admin_reports():
    """Admin global reports"""
    if not current_user.is_admin():
        flash('Truy cập từ chối', 'danger')
        return redirect(url_for('index'))
    
    # Global Statistics
    total_students = Student.query.count()
    total_clubs = Club.query.count()
    active_clubs = Club.query.filter_by(status=STATUS_APPROVED).count()
    total_events = Event.query.count()
    active_events = Event.query.filter_by(status=STATUS_APPROVED).count()
    
    # System-wide Revenue (All delivered orders)
    completed_orders = Order.query.filter_by(status='delivered').all()
    total_revenue = sum(order.total_price for order in completed_orders)
    
    # Recent global activity
    recent_orders = Order.query.order_by(Order.order_date.desc()).limit(10).all()
    
    return render_template('admin/reports.html',
                          total_students=total_students,
                          total_clubs=total_clubs,
                          active_clubs=active_clubs,
                          total_events=total_events,
                          active_events=active_events,
                          total_revenue=total_revenue,
                          recent_orders=recent_orders)


@app.route('/admin/clubs', methods=['GET', 'POST'])
@login_required
def admin_clubs():
    """Admin manage clubs"""
    if not current_user.is_admin():
        flash('Truy cập từ chối', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        club_id = request.form.get('club_id')
        action = request.form.get('action')

        if not club_id or not action:
            flash('Yêu cầu không hợp lệ', 'danger')
            return redirect(url_for('admin_clubs'))

        club = Club.query.get(club_id)
        if not club:
            flash('CLB không tồn tại', 'danger')
            return redirect(url_for('admin_clubs'))

        if action == 'approve':
            club.status = STATUS_APPROVED
            # Kich hoat tai khoan nguoi dung cua CLB
            if club.user:
                club.user.status = 'active'
            
            # Tu dong them nguoi dang ky lam Chu nhiem (neu la sinh vien)
            if club.registered_by_user_id:
                founder_user = User.query.get(club.registered_by_user_id)
                if founder_user and founder_user.is_student() and founder_user.student_profile:
                    # Kiem tra xem da la thanh vien chua
                    existing_member = ClubMember.query.filter_by(
                        club_id=club.id, 
                        student_id=founder_user.student_profile.id
                    ).first()
                    
                    if not existing_member:
                        new_member = ClubMember(
                            club_id=club.id,
                            student_id=founder_user.student_profile.id,
                            status=STATUS_ACTIVE,
                            position='Chủ nhiệm',
                            join_date=datetime.utcnow()
                        )
                        db.session.add(new_member)
                        
                    # Create notification for founder with credentials
                    create_notification(
                        club.registered_by_user_id,
                        f"CLB {club.club_name} đã được phê duyệt!",
                        f"Chúc mừng! Đơn thành lập CLB '{club.club_name}' đã được phê duyệt. Tên đăng nhập: {club.user.username}, Mật khẩu mặc định: 'neuclub123'. Vui lòng đăng nhập và đổi mật khẩu ngay.",
                        'success'
                    )
            
            flash(f'Đã phê duyệt câu lạc bộ: {club.club_name}', 'success')
            
        elif action == 'reject':
            club.status = STATUS_REJECTED
            # Gui thong bao tu choi toi sinh vien da dang ky
            notify_user_id = club.registered_by_user_id or club.user_id
            create_notification(
                notify_user_id,
                f"Yêu cầu thành lập CLB đã bị từ chối",
                f"Rất tiếc, đơn đăng ký thành lập '{club.club_name}' chưa được phê duyệt. Vui lòng liên hệ Ban quản lý để biết thêm chi tiết.",
                'danger'
            )
            flash(f'Đã từ chối câu lạc bộ: {club.club_name}', 'warning')
        else:
            flash('Hành động không hợp lệ', 'danger')
            return redirect(url_for('admin_clubs'))

        db.session.commit()
        return redirect(url_for('admin_clubs'))

    clubs = Club.query.order_by(Club.created_at.desc()).all()
    return render_template('admin/clubs.html', clubs=clubs)


@app.route('/admin/events', methods=['GET', 'POST'])
@login_required
def admin_events():
    """Admin manage events"""
    if not current_user.is_admin():
        flash('Truy cập từ chối', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        event_id = request.form.get('event_id')
        action = request.form.get('action')

        if not event_id or not action:
            flash('Yêu cầu không hợp lệ', 'danger')
            return redirect(url_for('admin_events'))

        event = Event.query.get(event_id)
        if not event:
            flash('Sự kiện không tồn tại', 'danger')
            return redirect(url_for('admin_events'))

        if action == 'approve':
            event.status = STATUS_APPROVED
            create_notification(
                event.club.user_id,
                "Sự kiện đã được duyệt",
                f"Sự kiện '{event.event_name}' của bạn đã được Admin phê duyệt.",
                'success'
            )
            flash(f'Đã phê duyệt sự kiện: {event.event_name}', 'success')
        elif action == 'reject':
            event.status = STATUS_REJECTED
            create_notification(
                event.club.user_id,
                "Sự kiện bị từ chối",
                f"Rất tiếc, sự kiện '{event.event_name}' của bạn không được phê duyệt.",
                'danger'
            )
            flash(f'Đã từ chối sự kiện: {event.event_name}', 'warning')
        else:
            flash('Hành động không hợp lệ', 'danger')
            return redirect(url_for('admin_events'))

        event.updated_at = datetime.utcnow()
        db.session.commit()
        return redirect(url_for('admin_events'))

    events = Event.query.order_by(Event.created_at.desc()).all()
    return render_template('admin/events.html', events=events)


@app.route('/admin/products', methods=['GET', 'POST'])
@login_required
def admin_products():
    """Admin manage products"""
    if not current_user.is_admin():
        flash('Truy cập từ chối', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        product_id = request.form.get('product_id')
        action = request.form.get('action')

        if not product_id or not action:
            flash('Yêu cầu không hợp lệ', 'danger')
            return redirect(url_for('admin_products'))

        product = Product.query.get(product_id)
        if not product:
            flash('Sản phẩm không tồn tại', 'danger')
            return redirect(url_for('admin_products'))

        if action == 'approve':
            product.status = STATUS_APPROVED
            create_notification(
                product.club.user_id,
                "Sản phẩm đã được duyệt",
                f"Sản phẩm '{product.product_name}' của bạn đã được Admin phê duyệt.",
                'success'
            )
            flash(f'Đã phê duyệt sản phẩm: {product.product_name}', 'success')
        elif action == 'reject':
            product.status = STATUS_REJECTED
            create_notification(
                product.club.user_id,
                "Sản phẩm bị từ chối",
                f"Rất tiếc, sản phẩm '{product.product_name}' của bạn không được phê duyệt.",
                'danger'
            )
            flash(f'Đã từ chối sản phẩm: {product.product_name}', 'warning')
        else:
            flash('Hành động không hợp lệ', 'danger')
            return redirect(url_for('admin_products'))

        product.updated_at = datetime.utcnow()
        db.session.commit()
        return redirect(url_for('admin_products'))

    products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template('admin/products.html', products=products)






# ============ EVENTS ROUTES (STUDENT) ============

@app.route('/events/<int:event_id>')
def event_detail(event_id):
    """View event details"""
    event = Event.query.get_or_404(event_id)
    
    # Allow access if approved, or if user is admin, or if user is the organizing club
    can_view = (event.status == STATUS_APPROVED or 
               (current_user.is_authenticated and (current_user.is_admin() or 
                (current_user.is_club() and current_user.club_profile.id == event.club_id))))
    
    if not can_view:
        flash('Sự kiện này chưa được phê duyệt hoặc không khả dụng', 'warning')
        return redirect(url_for('student_events'))
    
    # Ensure legacy events have a check-in code
    if not event.check_in_code:
        event.check_in_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        db.session.commit()
    
    registered_count = len(event.registrations)
    
    # Check current user registration status
    registration = None
    if current_user.is_authenticated and current_user.is_student():
        registration = EventRegistration.query.filter_by(
            event_id=event_id,
            student_id=current_user.student_profile.id
        ).first()
        
    return render_template('event_detail.html', 
                         event=event, 
                         registered_count=registered_count,
                         registration=registration)

@app.route('/events/<int:event_id>/check-in', methods=['POST'])
@login_required
def event_check_in(event_id):
    """Event check-in for students"""
    if not current_user.is_student():
        flash('Chỉ sinh viên mới có thể điểm danh', 'danger')
        return redirect(url_for('index'))
    
    event = Event.query.get_or_404(event_id)
    registration = EventRegistration.query.filter_by(
        event_id=event_id,
        student_id=current_user.student_profile.id
    ).first()
    
    if not registration or registration.status == STATUS_REJECTED:
        flash('Bạn chưa được duyệt tham gia sự kiện này', 'danger')
        return redirect(url_for('event_detail', event_id=event_id))
    
    input_code = request.form.get('check_in_code', '').upper()
    if input_code != event.check_in_code:
        flash('Mã điểm danh không chính xác', 'danger')
        return redirect(url_for('event_detail', event_id=event_id))
    
    registration.check_in_at = datetime.utcnow()
    db.session.commit()
    flash('Điểm danh thành công! Đừng quên check-out khi kết thúc để nhận điểm Đoàn.', 'success')
    return redirect(url_for('event_detail', event_id=event_id))

@app.route('/events/<int:event_id>/check-out', methods=['POST'])
@login_required
def event_check_out(event_id):
    """Event check-out and point addition"""
    if not current_user.is_student():
        return redirect(url_for('index'))
    
    registration = EventRegistration.query.filter_by(
        event_id=event_id,
        student_id=current_user.student_profile.id
    ).first()
    
    if not registration or not registration.check_in_at:
        flash('Bạn cần check-in trước khi check-out', 'warning')
        return redirect(url_for('event_detail', event_id=event_id))
    
    if registration.check_out_at:
        flash('Bạn đã hoàn thành sự kiện này rồi', 'info')
        return redirect(url_for('event_detail', event_id=event_id))
    
    registration.check_out_at = datetime.utcnow()
    registration.status = 'attended'
    
    # Auto-add points
    if not registration.achievement_points:
        registration.student.achievement_points = (registration.student.achievement_points or 0) + 5
        registration.achievement_points = 5
        create_notification(
            registration.student.user_id,
            "Cộng điểm Đoàn tự động",
            f"Chúc mừng! Bạn đã hoàn thành sự kiện {registration.event.event_name} và nhận được +5 điểm Đoàn.",
            'success'
        )
    
    db.session.commit()
    flash('Check-out thành công! Bạn đã được cộng +5 điểm Đoàn.', 'success')
    return redirect(url_for('event_detail', event_id=event_id))

# --- New Dynamic QR CICO Routes ---

@app.route('/events/<int:event_id>/get_cico_token/<action>')
@login_required
def get_cico_token(event_id, action):
    """API for BTC to get a temporary token for either check-in or check-out"""
    if not current_user.is_club():
        return jsonify({'error': 'Unauthorized'}), 403
    
    event = Event.query.get_or_404(event_id)
    if event.club_id != current_user.club_profile.id:
        return jsonify({'error': 'Unauthorized'}), 403
        
    if action not in ['check-in', 'check-out']:
        return jsonify({'error': 'Invalid action'}), 400
        
    # Standard check-in code as salt + timestamp + action
    token = serializer.dumps({
        'event_id': event_id, 
        'action': action,
        'ts': datetime.utcnow().timestamp()
    }, salt='cico-salt')
    return jsonify({'token': token})

@app.route('/events/<int:event_id>/verify_cico_token/<action>', methods=['POST'])
@login_required
def verify_cico_token(event_id, action):
    """API for Students to scan and verify the dynamic QR token"""
    if not current_user.is_student():
        return jsonify({'error': 'Chỉ sinh viên mới có thể điểm danh'}), 403
    
    token = request.json.get('token')
    if not token:
        return jsonify({'error': 'Mã QR không hợp lệ'}), 400
        
    try:
        # Token valid for 30 seconds
        data = serializer.loads(token, salt='cico-salt', max_age=30)
        if data.get('event_id') != event_id:
            return jsonify({'error': 'Mã QR này không thuộc về sự kiện này'}), 400
            
        if data.get('action') != action:
            act_name = 'Check-in' if data.get('action') == 'check-in' else 'Check-out'
            return jsonify({'error': f'Mã QR này dành cho {act_name}, không phải cho hành động hiện tại.'}), 400
            
        # Standard CICO business logic
        registration = EventRegistration.query.filter_by(
            event_id=event_id,
            student_id=current_user.student_profile.id
        ).first()
        
        if not registration or registration.status == STATUS_REJECTED:
            return jsonify({'error': 'Bạn chưa được duyệt tham gia sự kiện này'}), 400
            
        if action == 'check-in':
            if registration.check_in_at:
                return jsonify({'success': True, 'message': 'Bạn đã check-in rồi'})
            registration.check_in_at = datetime.utcnow()
            msg = 'Điểm danh (Check-in) thành công!'
        elif action == 'check-out':
            if not registration.check_in_at:
                return jsonify({'error': 'Bạn cần check-in trước khi check-out'}), 400
            if registration.check_out_at:
                return jsonify({'success': True, 'message': 'Bạn đã hoàn thành sự kiện này rồi'})
            
            registration.check_out_at = datetime.utcnow()
            registration.status = 'attended'
            
            # Point logic
            if not registration.achievement_points:
                points_to_add = registration.event.achievement_points or 5
                registration.student.achievement_points = (registration.student.achievement_points or 0) + points_to_add
                registration.achievement_points = points_to_add
                create_notification(
                    registration.student.user_id,
                    "Cộng điểm Đoàn tự động",
                    f"Chúc mừng! Bạn đã hoàn thành sự kiện {registration.event.event_name} và nhận được +{points_to_add} điểm Đoàn.",
                    'success'
                )
            msg = f'Check-out thành công! +{registration.achievement_points} điểm Đoàn đã được cộng.'
        else:
            return jsonify({'error': 'Hành động không hợp lệ'}), 400
            
        db.session.commit()
        return jsonify({'success': True, 'message': msg})
        
    except SignatureExpired:
        return jsonify({'error': 'Mã QR đã hết hạn, vui lòng quét mã mới'}), 400
    except BadTimeSignature:
        return jsonify({'error': 'Mã QR không hợp lệ hoặc đã bị thay đổi'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Lỗi hệ thống: {str(e)}'}), 500


@app.route('/events/<int:event_id>/register', methods=['POST'])
@login_required
def register_event(event_id):
    """Register for an event"""
    if not current_user.is_student():
        flash('Chỉ sinh viên mới có thể đăng ký sự kiện', 'danger')
        return redirect(url_for('index'))
    
    event = Event.query.get_or_404(event_id)
    
    if event.is_ended:
        flash('Sự kiện này đã kết thúc, bạn không thể đăng ký thêm', 'warning')
        return redirect(url_for('event_detail', event_id=event_id))
        
    student = current_user.student_profile
    
    # Check if already registered
    existing = EventRegistration.query.filter_by(
        event_id=event_id,
        student_id=student.id
    ).first()
    
    if existing:
        flash('Bạn đã đăng ký sự kiện này rồi', 'warning')
        return redirect(url_for('event_detail', event_id=event_id))
    
    try:
        notes = request.form.get('notes', '')
        registration = EventRegistration(
            event_id=event_id,
            student_id=student.id,
            notes=notes
        )
        db.session.add(registration)
        
        # Thong bao cho CLB
        create_notification(
            event.club.user_id,
            "Đăng ký sự kiện mới",
            f"Sinh viên {student.full_name} đã đăng ký tham gia sự kiện '{event.event_name}'. Ghi chú: {notes[:50]}...",
            'info'
        )
        
        db.session.commit()
        flash('Đăng ký tham gia sự kiện thành công', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi: {str(e)}', 'danger')
    
    return redirect(url_for('event_detail', event_id=event_id))


# ============ PRODUCTS ROUTES ============

@app.route('/products')
def products_list():
    """View all products"""
    products = Product.query.filter_by(status=STATUS_APPROVED).all()
    return render_template('products.html', products=products)


@app.route('/products/<int:product_id>')
def product_detail(product_id):
    """View product details"""
    product = Product.query.get_or_404(product_id)
    
    # Allow access if approved, or if user is admin, or if user is the owning club
    can_view = (product.status == STATUS_APPROVED or 
               (current_user.is_authenticated and (current_user.is_admin() or 
                (current_user.is_club() and current_user.club_profile and current_user.club_profile.id == product.club_id))))
    
    if not can_view:
        flash('Sản phẩm này chưa được phê duyệt hoặc không khả dụng', 'warning')
        return redirect(url_for('products_list'))
    
    return render_template('product_detail.html', product=product)


# ============ SHOPPING CART & ORDERS ============

@app.route('/cart')
@login_required
def cart():
    """View shopping cart"""
    if not current_user.is_student():
        flash('Chỉ sinh viên mới có thể xem giỏ hàng', 'danger')
        return redirect(url_for('index'))
    
    student = current_user.student_profile
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total_price = sum(item.product.price * item.quantity for item in cart_items)
                
    return render_template('cart.html', student=student, cart_items=cart_items, total_price=total_price)


@app.route('/cart/add', methods=['POST'])
@login_required
def add_to_cart():
    """Add product to cart"""
    if not current_user.is_student():
        flash('Chỉ sinh viên mới có thể mua hàng', 'danger')
        return redirect(url_for('index'))
    
    product_id = request.form.get('product_id')
    quantity = int(request.form.get('quantity', 1))
    
    product = Product.query.get_or_404(product_id)
    if product.status != STATUS_APPROVED or product.quantity < quantity:
        flash('Sản phẩm không khả dụng hoặc không đủ số lượng', 'danger')
        return redirect(url_for('product_detail', product_id=product_id))

    # Check if item already in persistent cart
    cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    
    if cart_item:
        if cart_item.quantity + quantity > product.quantity:
            flash(f'Chỉ còn {product.quantity} sản phẩm trong kho', 'danger')
            return redirect(url_for('product_detail', product_id=product_id))
        cart_item.quantity += quantity
    else:
        cart_item = CartItem(user_id=current_user.id, product_id=product_id, quantity=quantity)
        db.session.add(cart_item)
        
    try:
        db.session.commit()
        flash('Đã thêm sản phẩm vào giỏ hàng', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi khi thêm vào giỏ hàng: {str(e)}', 'danger')
        
    return redirect(url_for('cart'))


@app.route('/cart/remove/<int:product_id>', methods=['POST'])
@login_required
def remove_from_cart(product_id):
    """Remove product from cart"""
    cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if cart_item:
        try:
            db.session.delete(cart_item)
            db.session.commit()
            flash('Đã xóa khỏi giỏ', 'info')
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi: {str(e)}', 'danger')
    return redirect(url_for('cart'))


@app.route('/cart/update/<int:product_id>/<string:action>', methods=['POST'])
@login_required
def update_cart(product_id, action):
    """Update product quantity in cart"""
    cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    
    if cart_item:
        product = Product.query.get_or_404(product_id)
        if action == 'increase':
            if cart_item.quantity + 1 <= product.quantity:
                cart_item.quantity += 1
            else:
                flash(f'Chỉ còn {product.quantity} sản phẩm trong kho', 'warning')
        elif action == 'decrease':
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
            else:
                db.session.delete(cart_item)
                flash('Sản phẩm đã được xóa khỏi giỏ', 'info')
        
        try:
            db.session.commit()
        except:
            db.session.rollback()
            
    return redirect(url_for('cart'))


@app.route('/cart/checkout', methods=['POST'])
@login_required
def checkout_cart():
    """Process checkout process generating orders"""
    if not current_user.is_student():
        return redirect(url_for('index'))
    
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash('Giỏ hàng trống', 'danger')
        return redirect(url_for('cart'))
        
    # Map for easy lookup
    cart_dict = {str(item.product_id): item.quantity for item in cart_items}
    
    # Get selected items from the form
    selected_item_ids = request.form.getlist('selected_items')
    if not selected_item_ids:
        flash('Vui lòng chọn ít nhất 1 sản phẩm để thanh toán', 'warning')
        return redirect(url_for('cart'))
        
    # Filter the cart to only include selected items
    selected_cart = {p_id: qty for p_id, qty in cart_dict.items() if p_id in selected_item_ids}
    
    # Validate single club for selected items
    club_ids = set()
    for p_id in selected_cart.keys():
        product = Product.query.get(int(p_id))
        if product:
            club_ids.add(product.club_id)
            
    if len(club_ids) > 1:
        flash('Bạn chỉ có thể đặt hàng từ 1 CLB trong mỗi lần thanh toán. Vui lòng bỏ chọn các món từ CLB khác!', 'warning')
        return redirect(url_for('cart'))
        
    student = current_user.student_profile
    
    # Extract shipping info
    shipping_name = request.form.get('shipping_name', student.full_name)
    shipping_phone = request.form.get('shipping_phone', student.phone)
    shipping_email = request.form.get('shipping_email', current_user.email)
    shipping_major = request.form.get('shipping_major', student.major)
    shipping_address = request.form.get('shipping_address', student.address)
    payment_method = request.form.get('payment_method', 'Tiền mặt')
    shipping_method = request.form.get('shipping_method', 'at_neu')
    notes = request.form.get('notes', '')
    
    # Calculate shipping fee per club
    shipping_fee = 15000 if shipping_method == 'delivery' else 0
    
    club_orders = {}
    
    try:
        for p_id_str, qty in selected_cart.items():
            product = Product.query.get(int(p_id_str))
            if not product or product.quantity < qty:
                raise ValueError(f"Sản phẩm {product.product_name if product else 'ẩn'} không đủ số lượng.")
                
            club_id = product.club_id
            if club_id not in club_orders:
                # Add shipping fee for this club's order if applicable
                club_orders[club_id] = {
                    'order': Order(
                        student_id=student.id, 
                        club_id=club_id, 
                        status=STATUS_PENDING, 
                        notes=f"{notes} (Phí ship: {shipping_fee:,.0f}đ - {shipping_method})" if shipping_fee > 0 else notes,
                        shipping_name=shipping_name,
                        shipping_phone=shipping_phone,
                        shipping_email=shipping_email,
                        shipping_major=shipping_major,
                        shipping_address=shipping_address,
                        payment_method=payment_method,
                        total_price=shipping_fee  # Start with shipping fee
                    ),
                    'items': []
                }
                
            price = product.price * qty
            club_orders[club_id]['order'].total_price += price
            club_orders[club_id]['items'].append({
                'product': product,
                'qty': qty,
                'price_per_unit': product.price
            })
            
            # Deduct inventory
            product.quantity -= qty
            
        for club_id, data in club_orders.items():
            db.session.add(data['order'])
            db.session.flush() # To get order.id before creating items
            for item in data['items']:
                order_item = OrderItem(
                    order_id=data['order'].id,
                    product_id=item['product'].id,
                    quantity=item['qty'],
                    price_per_unit=item['price_per_unit']
                )
                db.session.add(order_item)
                
        db.session.commit()
        # Remove only selected items from persistent cart
        for p_id in selected_item_ids:
            item_to_delete = CartItem.query.filter_by(user_id=current_user.id, product_id=int(p_id)).first()
            if item_to_delete:
                db.session.delete(item_to_delete)
        db.session.commit()
        flash('Đặt hàng thành công!', 'success')
        return redirect(url_for('orders_list'))
        
    except ValueError as e:
        db.session.rollback()
        flash(str(e), 'danger')
        return redirect(url_for('cart'))
    except Exception as e:
        db.session.rollback()
        flash(f"Lỗi hệ thống: {e}", 'danger')
        return redirect(url_for('cart'))


@app.route('/orders')
@login_required
def orders_list():
    """View user orders"""
    if not current_user.is_student():
        flash('Chỉ sinh viên mới có thể xem đơn hàng', 'danger')
        return redirect(url_for('index'))
    
    student = current_user.student_profile
    orders = Order.query.filter_by(student_id=student.id).order_by(Order.order_date.desc()).all()
    return render_template('orders.html', orders=orders)


@app.route('/club/orders')
@login_required
def club_orders():
    """View orders for club's products"""
    if not current_user.is_club():
        return redirect(url_for('index'))
    club = current_user.club_profile
    orders = Order.query.filter_by(club_id=club.id).order_by(Order.order_date.desc()).all()
    return render_template('club/orders.html', orders=orders)


@app.route('/club/orders/<int:order_id>/<action>', methods=['POST'])
@login_required
def update_order_status(order_id, action):
    """Update order status from club"""
    if not current_user.is_club():
        return redirect(url_for('index'))
    order = Order.query.get_or_404(order_id)
    if order.club_id != current_user.club_profile.id:
        flash('Không có quyền', 'danger')
        return redirect(url_for('club_orders'))
        
    if action == 'confirm':
        order.status = 'confirmed'
        msg = f"Đơn hàng #{order.id} của bạn đã được CLB xác nhận."
    elif action == 'ship':
        order.status = 'shipped'
        msg = f"Đơn hàng #{order.id} đang trên đường giao đến bạn."
    elif action == 'deliver':
        order.status = 'delivered'
        msg = f"Đơn hàng #{order.id} đã được giao thành công. Cảm ơn bạn!"
    elif action == 'cancel':
        if order.status != 'cancelled':
            order.status = 'cancelled'
            msg = f"Đơn hàng #{order.id} đã bị hủy."
            for item in order.order_items:
                item.product.quantity += item.quantity
    
    try:
        db.session.commit()
        # Send notification
        create_notification(
            order.student.user_id,
            f"Cập nhật đơn hàng #{order.id}",
            msg,
            'info'
        )
        flash(f"Đã cập nhật đơn hàng thành {order.status}", 'success')
    except Exception as e:
        db.session.rollback()
        flash(f"Lỗi: {e}", 'danger')
        
    return redirect(url_for('club_orders'))


# ============ CLUB PRODUCT MANAGEMENT ============

@app.route('/club/products', methods=['GET', 'POST'])
@login_required
def club_products():
    """Club manage products"""
    if not current_user.is_club():
        flash('Chỉ CLB mới có thể quản lý sản phẩm', 'danger')
        return redirect(url_for('index'))
    
    club = current_user.club_profile
    products = Product.query.filter_by(club_id=club.id).all()
    return render_template('club/products.html', products=products)


@app.route('/club/products/create', methods=['GET', 'POST'])
@login_required
def create_product():
    """Create new product"""
    if not current_user.is_club():
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        product = Product(
            club_id=current_user.club_profile.id,
            product_name=request.form.get('product_name'),
            description=request.form.get('description'),
            price=float(request.form.get('price') or 0),
            quantity=int(request.form.get('quantity') or 0),
            image_url=request.form.get('image_url')
        )
        
        try:
            db.session.add(product)
            db.session.commit()
            
            # Notify all Admins about new product pending approval
            admins = User.query.filter_by(user_type=USER_TYPE_ADMIN).all()
            for admin in admins:
                create_notification(
                    admin.id, 
                    'Sản phẩm mới chờ duyệt', 
                    f'CLB {current_user.club_profile.club_name} vừa thêm sản phẩm "{product.product_name}". Vui lòng xem xét duyệt.',
                    'product_approval'
                )
                
            flash('Thêm sản phẩm thành công. Chờ duyệt từ Admin.', 'success')
            return redirect(url_for('club_products'))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi: {str(e)}', 'danger')
    
    return render_template('club/create_product.html')


@app.route('/club/products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
def edit_product(product_id):
    """Edit a product"""
    if not current_user.is_club():
        return redirect(url_for('index'))
        
    product = Product.query.get_or_404(product_id)
    if product.club_id != current_user.club_profile.id:
        flash('Bạn không có quyền', 'danger')
        return redirect(url_for('club_products'))
        
    if request.method == 'POST':
        product.product_name = request.form.get('product_name')
        product.description = request.form.get('description')
        product.price = float(request.form.get('price') or 0)
        product.quantity = int(request.form.get('quantity') or 0)
        image_url = request.form.get('image_url')
        if image_url:
            product.image_url = image_url
            
        try:
            db.session.commit()
            flash('Cập nhật sản phẩm thành công', 'success')
            return redirect(url_for('club_products'))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi: {str(e)}', 'danger')
            
    return render_template('club/edit_product.html', product=product)


@app.route('/club/products/delete/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    """Delete a product"""
    if not current_user.is_club():
        return redirect(url_for('index'))
        
    product = Product.query.get_or_404(product_id)
    if product.club_id != current_user.club_profile.id:
        flash('Không có quyền', 'danger')
        return redirect(url_for('club_products'))
        
    try:
        db.session.delete(product)
        db.session.commit()
        flash('Đã xóa sản phẩm', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi: {str(e)}', 'danger')
        
    return redirect(url_for('club_products'))


# ============ CLUB EVENT MANAGEMENT ============

@app.route('/club/events', methods=['GET', 'POST'])
@login_required
def club_events():
    """Club manage events"""
    if not current_user.is_club():
        return redirect(url_for('index'))
    
    club = current_user.club_profile
    events = Event.query.filter_by(club_id=club.id).all()
    return render_template('club/events.html', events=events)


@app.route('/club/events/create', methods=['GET', 'POST'])
@login_required
def create_event():
    """Create new event"""
    if not current_user.is_club():
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Generate unique check-in code
        check_in_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
        event = Event(
            club_id=current_user.club_profile.id,
            event_name=request.form.get('event_name'),
            description=request.form.get('description'),
            location=request.form.get('location'),
            start_date=datetime.strptime(request.form.get('start_date'), '%Y-%m-%dT%H:%M'),
            max_participants=int(request.form.get('max_participants') or 0),
            achievement_points=int(request.form.get('achievement_points') or 5),
            check_in_code=check_in_code
        )
        
        try:
            db.session.add(event)
            db.session.commit()
            
            # Notify all Admins about new event pending approval
            admins = User.query.filter_by(user_type=USER_TYPE_ADMIN).all()
            for admin in admins:
                create_notification(
                    admin.id, 
                    'Sự kiện mới chờ duyệt', 
                    f'CLB {current_user.club_profile.club_name} vừa tạo sự kiện "{event.event_name}". Vui lòng xem xét duyệt.',
                    'event_approval'
                )
                
            flash('Tạo sự kiện thành công. Chờ Admin duyệt để hiển thị công khai.', 'success')
            return redirect(url_for('club_events'))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi: {str(e)}', 'danger')
    
    return render_template('club/create_event.html')


@app.route('/club/events/edit/<int:event_id>', methods=['GET', 'POST'])
@login_required
def edit_event(event_id):
    """Edit an event"""
    if not current_user.is_club():
        return redirect(url_for('index'))
    
    event = Event.query.get_or_404(event_id)
    if event.club_id != current_user.club_profile.id:
        flash('Bạn không có quyền sửa sự kiện này', 'danger')
        return redirect(url_for('club_events'))
    
    if request.method == 'POST':
        from datetime import datetime
        event.event_name = request.form.get('event_name')
        event.description = request.form.get('description')
        event.location = request.form.get('location')
        event.start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%dT%H:%M')
        event.max_participants = int(request.form.get('max_participants') or 0)
        event.achievement_points = int(request.form.get('achievement_points') or 5)
        
        try:
            db.session.commit()
            flash('Cập nhật sự kiện thành công', 'success')
            return redirect(url_for('club_events'))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi: {str(e)}', 'danger')
            
    return render_template('club/edit_event.html', event=event)


@app.route('/club/events/delete/<int:event_id>', methods=['POST'])
@login_required
def delete_event(event_id):
    """Delete an event"""
    if not current_user.is_club():
        return redirect(url_for('index'))
        
    event = Event.query.get_or_404(event_id)
    if event.club_id != current_user.club_profile.id:
        flash('Không có quyền', 'danger')
        return redirect(url_for('club_events'))
        
    try:
        db.session.delete(event)
        db.session.commit()
        flash('Đã xóa sự kiện', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi: {str(e)}', 'danger')
        
    return redirect(url_for('club_events'))


@app.route('/club/events/<int:event_id>/registrations')
@login_required
def event_registrations(event_id):
    """View event registrations"""
    if not current_user.is_club():
        return redirect(url_for('index'))
        
    event = Event.query.get_or_404(event_id)
    if event.club_id != current_user.club_profile.id:
        flash('Không có quyền', 'danger')
        return redirect(url_for('club_events'))
        
    registrations = EventRegistration.query.filter_by(event_id=event.id).all()
    return render_template('club/event_registrations.html', event=event, registrations=registrations)


@app.route('/club/events/registrations/<int:reg_id>/<action>', methods=['POST'])
@login_required
def process_event_registration(reg_id, action):
    """Process event registration status"""
    if not current_user.is_club():
        return redirect(url_for('index'))
        
    reg = EventRegistration.query.get_or_404(reg_id)
    if reg.event.club_id != current_user.club_profile.id:
        flash('Không có quyền', 'danger')
        return redirect(url_for('club_events'))
        
    if action == 'approve':
        reg.status = STATUS_APPROVED
        create_notification(
            reg.student.user_id,
            f"Đăng ký sự kiện thành công",
            f"Bạn đã được duyệt tham gia sự kiện: {reg.event.event_name}",
            'success'
        )
        flash('Đã duyệt đăng ký tham gia sự kiện', 'success')
    elif action == 'reject':
        reg.status = STATUS_REJECTED
        create_notification(
            reg.student.user_id,
            f"Từ chối đăng ký sự kiện",
            f"Rất tiếc, đăng ký của bạn cho sự kiện {reg.event.event_name} không được phê duyệt.",
            'danger'
        )
        flash('Đã từ chối đăng ký tham gia', 'info')
    elif action == 'attend':
        reg.status = 'attended'
        if not reg.achievement_points:
            points_to_add = reg.event.achievement_points or 5
            reg.student.achievement_points = (reg.student.achievement_points or 0) + points_to_add
            reg.achievement_points = points_to_add
        create_notification(
            reg.student.user_id,
            f"Xác nhận tham gia sự kiện",
            f"Bạn đã được xác nhận tham gia {reg.event.event_name}. Chúc mừng bạn nhận được +{points_to_add} điểm Đoàn!",
            'success'
        )
        flash(f'Đã đánh dấu có mặt (+{points_to_add} điểm Đoàn)', 'success')
        
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi: {str(e)}', 'danger')
        
    return redirect(url_for('event_registrations', event_id=reg.event_id))


# ============ PUBLIC VIEW (STUDENTS/ALL) ============

@app.route('/clubs/<int:club_id>')
def club_detail(club_id):
    """Public detail view for a club"""
    club = Club.query.get_or_404(club_id)
    if club.status != STATUS_APPROVED and not (current_user.is_authenticated and (current_user.is_admin() or (current_user.is_club() and current_user.club_profile.id == club.id))):
        flash('CLB chưa được phê duyệt', 'warning')
        return redirect(url_for('index'))
        
    events = Event.query.filter_by(club_id=club_id, status=STATUS_APPROVED).order_by(Event.start_date.desc()).all()
    # Get posts with visibility filtering
    is_member = False
    if current_user.is_authenticated:
        if current_user.is_admin():
            is_member = True # Admin sees everything
        elif current_user.is_student():
            is_member = ClubMember.query.filter_by(club_id=club_id, student_id=current_user.student_profile.id, status=STATUS_ACTIVE).first() is not None
        elif current_user.is_club() and current_user.club_profile.id == club_id:
            is_member = True
            
    query = ClubPost.query.filter_by(club_id=club_id, status=STATUS_ACTIVE)
    if not current_user.is_authenticated:
        query = query.filter_by(visibility='public')
    elif current_user.is_admin() or (current_user.is_club() and current_user.club_profile.id == club_id):
        # Admin or owner sees all
        pass
    elif is_member:
        query = query.filter(ClubPost.visibility.in_(['public', 'members']))
    else:
        query = query.filter_by(visibility='public')
        
    posts = query.order_by(ClubPost.created_at.desc()).all()
    products = Product.query.filter_by(club_id=club_id, status=STATUS_APPROVED).all()
    
    # Fetch members for the club
    members = ClubMember.query.filter_by(club_id=club_id, status=STATUS_ACTIVE).all()
    
    # Ensure founder is in the members list for display if they are a student
    founder_included = False
    if club.registered_by_user_id:
        for m in members:
            if m.student.user_id == club.registered_by_user_id:
                founder_included = True
                break
        
        if not founder_included:
            founder_user = User.query.get(club.registered_by_user_id)
            if founder_user and founder_user.is_student() and founder_user.student_profile:
                # Add a synthetic member object for display
                class MockMember:
                    def __init__(self, student, position):
                        self.student = student
                        self.position = position
                
                members.insert(0, MockMember(founder_user.student_profile, 'Chủ nhiệm'))

    return render_template('club_detail.html', 
                          club=club, 
                          events=events, 
                          products=products, 
                          posts=posts,
                          members=members,
                          is_member=is_member)


# ============ CLUB POST MANAGEMENT ============

@app.route('/club/posts')
@login_required
def club_posts():
    """Club manage posts"""
    if not current_user.is_club():
        return redirect(url_for('index'))
    
    club = current_user.club_profile
    posts = ClubPost.query.filter_by(club_id=club.id).order_by(ClubPost.created_at.desc()).all()
    return render_template('club/posts.html', posts=posts)


@app.route('/club/posts/create', methods=['GET', 'POST'])
@login_required
def create_post():
    """Create a club post"""
    if not current_user.is_club():
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        image_url = request.form.get('image_url')
        
        # Handle file upload
        if 'image_file' in request.files:
            file = request.files['image_file']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(f"post_{current_user.club_profile.id}_{int(datetime.utcnow().timestamp())}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_url = url_for('static', filename='uploads/posts/' + filename)

        post = ClubPost(
            club_id=current_user.club_profile.id,
            title=request.form.get('title'),
            content=request.form.get('content'),
            image_url=image_url,
            visibility=request.form.get('visibility', 'public')
        )
        try:
            db.session.add(post)
            db.session.commit()
            flash('Đăng bài viết thành công!', 'success')
            return redirect(url_for('club_posts'))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi: {e}', 'danger')
            
    return render_template('club/create_post.html')


@app.route('/club/posts/edit/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    """Edit a club post"""
    if not current_user.is_club():
        return redirect(url_for('index'))
        
    post = ClubPost.query.get_or_404(post_id)
    if post.club_id != current_user.club_profile.id:
        flash('Bạn không có quyền chỉnh sửa bài viết này!', 'danger')
        return redirect(url_for('club_posts'))
        
    if request.method == 'POST':
        post.title = request.form.get('title')
        post.content = request.form.get('content')
        post.visibility = request.form.get('visibility', 'public')
        
        # Handle file upload
        if 'image_file' in request.files:
            file = request.files['image_file']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(f"post_{current_user.club_profile.id}_{int(datetime.utcnow().timestamp())}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                post.image_url = url_for('static', filename='uploads/posts/' + filename)
            elif request.form.get('image_url'):
                post.image_url = request.form.get('image_url')
        elif request.form.get('image_url'):
            post.image_url = request.form.get('image_url')
        
        try:
            db.session.commit()
            flash('Cập nhật bài viết thành công!', 'success')
            return redirect(url_for('club_posts'))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi: {e}', 'danger')
            
    return render_template('club/edit_post.html', post=post)


@app.route('/club/posts/delete/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    """Delete a club post"""
    if not current_user.is_club():
        return redirect(url_for('index'))
        
    post = ClubPost.query.get_or_404(post_id)
    if post.club_id != current_user.club_profile.id:
        flash('Không có quyền', 'danger')
        return redirect(url_for('club_posts'))
        
    try:
        db.session.delete(post)
        db.session.commit()
        flash('Đã xóa bài viết', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Lỗi: {e}', 'danger')
        
    return redirect(url_for('club_posts'))


# ============ ERROR HANDLERS ============

@app.errorhandler(404)
def not_found(error):
    """404 error handler"""
    return render_template('error.html', error_code=404, error_message='Trang không tìm thấy'), 404


@app.errorhandler(500)
def server_error(error):
    """500 error handler"""
    return render_template('error.html', error_code=500, error_message='Lỗi máy chủ'), 500


@app.shell_context_processor
def make_shell_context():
    """Make database models available in shell"""
    return {
        'db': db,
        'User': User,
        'Student': Student,
        'Club': Club,
        'Event': Event,
    }


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("Database tables created!")
        
        # Create admin user if doesn't exist
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@neu.edu.vn',
                user_type=USER_TYPE_ADMIN
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Admin user created! Username: admin, Password: admin123")
    
    app.run(debug=True, host='0.0.0.0', port=5002)