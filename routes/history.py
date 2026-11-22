from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_
from extensions import db
from models import QRCode

history_bp = Blueprint("history", __name__)


@history_bp.route("/dashboard")
@login_required
def dashboard():
    """User dashboard displaying usage statistics, quick generator, and recent QR codes."""
    user_id = current_user.id

    # Aggregated stats
    total_qrs = QRCode.query.filter_by(user_id=user_id).count()
    url_count = QRCode.query.filter_by(user_id=user_id, qr_type="url").count()
    text_count = QRCode.query.filter_by(user_id=user_id, qr_type="text").count()
    email_count = QRCode.query.filter_by(user_id=user_id, qr_type="email").count()
    phone_count = QRCode.query.filter_by(user_id=user_id, qr_type="phone").count()

    # Most recent 6 QR codes
    recent_qrs = QRCode.query.filter_by(user_id=user_id).order_by(
        QRCode.created_at.desc()
    ).limit(6).all()

    stats = {
        "total": total_qrs,
        "url": url_count,
        "text": text_count,
        "email": email_count,
        "phone": phone_count,
    }

    return render_template(
        "dashboard.html",
        stats=stats,
        recent_qrs=recent_qrs
    )


@history_bp.route("/history")
@login_required
def history():
    """View and search entire QR generation history with filtering."""
    user_id = current_user.id
    qr_type_filter = request.args.get("type", "all").strip().lower()
    search_query = request.args.get("q", "").strip()
    sort_order = request.args.get("sort", "newest").strip().lower()

    query = QRCode.query.filter_by(user_id=user_id)

    # Filter by QR type
    if qr_type_filter in ["url", "text", "email", "phone"]:
        query = query.filter_by(qr_type=qr_type_filter)

    # Filter by search term
    if search_query:
        search_pattern = f"%{search_query}%"
        query = query.filter(
            or_(
                QRCode.title.ilike(search_pattern),
                QRCode.content.ilike(search_pattern)
            )
        )

    # Sorting
    if sort_order == "oldest":
        query = query.order_by(QRCode.created_at.asc())
    elif sort_order == "title":
        query = query.order_by(QRCode.title.asc())
    else:  # newest default
        query = query.order_by(QRCode.created_at.desc())

    qr_records = query.all()
    total_count = QRCode.query.filter_by(user_id=user_id).count()

    return render_template(
        "history.html",
        qr_records=qr_records,
        total_count=total_count,
        current_type=qr_type_filter,
        search_query=search_query,
        sort_order=sort_order
    )


@history_bp.route("/api/qr/<int:qr_id>", methods=["DELETE"])
@login_required
def delete_qr(qr_id: int):
    """Delete a QR code belonging strictly to the logged-in user."""
    record = QRCode.query.filter_by(
        id=qr_id,
        user_id=current_user.id
    ).first_or_404()

    db.session.delete(record)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"QR code '{record.title}' deleted successfully."
    })
