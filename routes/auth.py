import re
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from email_validator import validate_email, EmailNotValidError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from extensions import db, limiter
from models import User, QRCode

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Register a new user account with secure password hashing and robust DB error handling."""
    if request.method == "GET" and current_user.is_authenticated:
        return redirect(url_for("history.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        errors = []

        # Validate username
        if not username or len(username) < 3 or len(username) > 100:
            errors.append("Username must be between 3 and 100 characters.")

        # Validate email
        try:
            valid = validate_email(email, check_deliverability=False)
            email = valid.normalized
        except (EmailNotValidError, ValueError):
            errors.append("Please enter a valid email address.")

        # Validate password (minimum 12 characters)
        if not password or len(password) < 12:
            errors.append("Password must be at least 12 characters long.")
        elif password != confirm_password:
            errors.append("Passwords do not match.")

        # Pre-check existing user
        if not errors:
            if User.query.filter_by(email=email).first():
                errors.append("An account with this email address already exists.")
            elif User.query.filter_by(username=username).first():
                errors.append("This username is already taken. Please choose another.")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template(
                "register.html",
                username=username,
                email=email
            ), 400

        # Create user with atomic rollback handling for concurrent duplicates
        new_user = User(username=username, email=email)
        new_user.set_password(password)

        try:
            db.session.add(new_user)
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            current_app.logger.warning("Duplicate registration collision for %s: %s", email, str(e))
            flash("An account with this email address or username already exists.", "danger")
            return render_template("register.html", username=username, email=email), 400
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.exception("Database error during registration: %s", str(e))
            flash("A database error occurred while creating your account. Please try again later.", "danger")
            return render_template("register.html", username=username, email=email), 500

        # Log the newly registered user in automatically
        login_user(new_user)
        flash("Registration successful! Welcome to Cloud QR Generator.", "success")
        return redirect(url_for("history.dashboard"))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def login():
    """Log in an existing user with credential verification and brute-force throttling."""
    if request.method == "GET" and current_user.is_authenticated:
        return redirect(url_for("history.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user, remember=remember)
            flash(f"Welcome back, {user.username}!", "success")
            next_page = request.args.get("next")
            if next_page and next_page.startswith("/") and not next_page.startswith("//"):
                return redirect(next_page)
            return redirect(url_for("history.dashboard"))

        flash("Invalid email or password. Please try again.", "danger")
        return render_template("login.html", email=email), 401

    return render_template("login.html")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """Clear user session and log out via CSRF-protected POST request."""
    logout_user()
    flash("You have been successfully logged out.", "info")
    return redirect(url_for("home"))


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """User account profile and secure credential management."""
    total_user_qrs = QRCode.query.filter_by(user_id=current_user.id).count()

    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        errors = []

        if not current_user.check_password(current_password):
            errors.append("Current password is incorrect.")

        if not new_password or len(new_password) < 12:
            errors.append("New password must be at least 12 characters long.")
        elif new_password != confirm_password:
            errors.append("Passwords do not match.")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template(
                "profile.html",
                user=current_user,
                total_user_qrs=total_user_qrs
            ), 400

        current_user.set_password(new_password)
        try:
            db.session.commit()
            flash("Your password has been successfully updated.", "success")
            return redirect(url_for("auth.profile"))
        except SQLAlchemyError as e:
            db.session.rollback()
            current_app.logger.exception("Database error updating password: %s", str(e))
            flash("A database error occurred while updating your password. Please try again.", "danger")
            return render_template(
                "profile.html",
                user=current_user,
                total_user_qrs=total_user_qrs
            ), 500

    return render_template(
        "profile.html",
        user=current_user,
        total_user_qrs=total_user_qrs
    )

