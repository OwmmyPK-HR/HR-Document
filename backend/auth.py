from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from functools import wraps
from werkzeug.security import generate_password_hash


auth_bp = Blueprint('auth', __name__)

# สร้าง Hash เพื่อความปลอดภัยของรหัสผ่าน
admin_pass = "HRadmin"
user_pass = "HRuser"
# สร้าง Hash
hashed_admin_pass = generate_password_hash(admin_pass)
hashed_user_pass = generate_password_hash(user_pass)
# แสดงรหัสผ่านที่ถูกแฮชในคอนโซล
print(f"ADMIN_PASS_HASH={hashed_admin_pass}")
print(f"USER_PASS_HASH={hashed_user_pass}")
# แสดงรหัสผ่านที่ถูกแฮชในคอนโซลเพื่อใช้ในการตั้งค่า
# ในฐานข้อมูลหรือไฟล์คอนฟิกอื่น ๆ


def login_required(role="any"):
    """Decorator สำหรับตรวจสอบการ login และ role (ถ้ามี)"""
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if 'user_role' not in session:
                flash("กรุณาเข้าสู่ระบบก่อน", "warning")
                return redirect(url_for('auth.login'))
            if role != "any" and session['user_role'] != role:
                flash("คุณไม่มีสิทธิ์เข้าถึงหน้านี้", "danger")
                return redirect(url_for('main.index')) # หรือหน้าอื่นที่เหมาะสม
            return fn(*args, **kwargs)
        return decorated_view
    return wrapper

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == admin_pass:
            session['user_role'] = 'admin'
            session['username'] = 'Admin' # หรือชื่อผู้ใช้จริง
            flash('เข้าสู่ระบบสำเร็จในฐานะ Admin', 'success')
            return redirect(url_for('main.index'))
        elif password == user_pass:
            session['user_role'] = 'user'
            session['username'] = 'User' # หรือชื่อผู้ใช้จริง
            flash('เข้าสู่ระบบสำเร็จในฐานะ User', 'success')
            return redirect(url_for('main.index'))
        else:
            flash('รหัสผ่านไม่ถูกต้อง', 'danger')
    return render_template('login.html', title="เข้าสู่ระบบ")

@auth_bp.route('/logout')
def logout():
    session.pop('user_role', None)
    session.pop('username', None)
    flash('ออกจากระบบสำเร็จ', 'info')
    return redirect(url_for('auth.login'))