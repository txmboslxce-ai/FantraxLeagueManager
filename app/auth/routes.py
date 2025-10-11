from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from urllib.parse import urlparse
from app import db
from app.auth import bp
from app.auth.forms import LoginForm, RegistrationForm
from app.models import User

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = LoginForm()
    if form.validate_on_submit():
        print(f"\n=== Login Attempt ===")
        print(f"Username submitted: {form.username.data}")
        print(f"Password submitted: {form.password.data}")
        
        # Try to find the user
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            print(f"User found in database:")
            print(f"Username from DB: {user.username}")
            print(f"Email from DB: {user.email}")
            print(f"Is admin: {user.is_admin}")
            print(f"Current password hash: {user.password_hash}")
            
            # Try to verify password
            if user.check_password(form.password.data):
                print(f"Password verification successful!")
                login_user(user, remember=form.remember_me.data)
                next_page = request.args.get('next')
                if not next_page or urlparse(next_page).netloc != '':
                    next_page = url_for('main.index')
                return redirect(next_page)
            else:
                print(f"Password verification failed!")
        else:
            print(f"No user found with username: {form.username.data}")
        
        flash('Invalid username or password', 'danger')
        return redirect(url_for('auth.login'))
    return render_template('auth/login.html', title='Sign In', form=form)

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', title='Register', form=form) 