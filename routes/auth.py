import re
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from email_validator import validate_email, EmailNotValidError
from extensions import db
from models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Register a new user account with secure password hashing."""
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
            valid = validate_email(email)
            email = valid.normalized
        except (EmailNotValidError, ValueError):
            errors.append("Please enter a valid email address.")

        # Validate password
        if not password or len(password) < 6:
            errors.append("Password must be at least 6 characters long.")
        elif password != confirm_password:
            errors.append("Passwords do not match.")

        # Check existing user
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
            )

        # Create user
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        # Log the newly registered user in automatically
        login_user(new_user)
        flash("Registration successful! Welcome to Cloud QR Generator.", "success")
        return redirect(url_for("history.dashboard"))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Log in an existing user with credential verification."""
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
            if next_page and next_page.startswith("/"):
                return redirect(next_page)
            return redirect(url_for("history.dashboard"))

        flash("Invalid email or password. Please try again.", "danger")
        return render_template("login.html", email=email)

    return render_template("login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    """Clear user session and log out."""
    logout_user()
    flash("You have been successfully logged out.", "info")
    return redirect(url_for("home"))
