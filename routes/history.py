from datetime import datetime, timezone
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
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

    # Time-windowed query: QR codes generated today (since midnight UTC)
    now_utc = datetime.now(timezone.utc)
    today_start = datetime(now_utc.year, now_utc.month, now_utc.day, tzinfo=timezone.utc)
    today_count = QRCode.query.filter(
        QRCode.user_id == user_id,
        QRCode.created_at >= today_start
    ).count()

    # Most recent 5 QR codes with deterministic secondary sort
    recent_qrs = QRCode.query.filter_by(user_id=user_id).order_by(
        QRCode.created_at.desc(),
        QRCode.id.desc()
    ).limit(5).all()

    stats = {
        "total": total_qrs,
        "today": today_count,
        "saved": total_qrs,
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
    """View and search QR generation portfolio with server-side pagination and filters."""
    user_id = current_user.id
    qr_type_filter = request.args.get("type", "all").strip().lower()
    search_query = request.args.get("q", "").strip()
    sort_order = request.args.get("sort", "newest").strip().lower()

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 9, type=int)

    # Sanitize pagination numbers
    if page < 1:
        page = 1
    if per_page < 1 or per_page > 50:
        per_page = 9

    stmt = db.select(QRCode).filter_by(user_id=user_id)

    # Filter by QR type
    if qr_type_filter in ["url", "text", "email", "phone"]:
        stmt = stmt.filter_by(qr_type=qr_type_filter)

    # Filter by search term
    if search_query:
        search_pattern = f"%{search_query}%"
        stmt = stmt.filter(
            or_(
                QRCode.title.ilike(search_pattern),
                QRCode.content.ilike(search_pattern)
            )
        )

    # Deterministic sorting with secondary ID sort
    if sort_order == "oldest":
        stmt = stmt.order_by(QRCode.created_at.asc(), QRCode.id.asc())
    elif sort_order == "title":
        stmt = stmt.order_by(QRCode.title.asc(), QRCode.id.desc())
    else:  # newest default
        stmt = stmt.order_by(QRCode.created_at.desc(), QRCode.id.desc())

    pagination = db.paginate(stmt, page=page, per_page=per_page, error_out=False)
    qr_records = pagination.items
    total_count = QRCode.query.filter_by(user_id=user_id).count()

    return render_template(
        "history.html",
        pagination=pagination,
        qr_records=qr_records,
        total_count=total_count,
        current_type=qr_type_filter,
        search_query=search_query,
        sort_order=sort_order,
        page=page,
        per_page=per_page
    )


@history_bp.route("/api/qr/<int:qr_id>", methods=["DELETE"])
@login_required
def delete_qr(qr_id: int):
    """Delete a QR code belonging strictly to the logged-in user with rollback protection."""
    record = QRCode.query.filter_by(
        id=qr_id,
        user_id=current_user.id
    ).first_or_404()

    try:
        db.session.delete(record)
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.exception("Database error while deleting QR %s: %s", qr_id, str(e))
        return jsonify({"error": "Failed to delete QR code due to a database error."}), 500

    remaining_count = QRCode.query.filter_by(user_id=current_user.id).count()

    return jsonify({
        "success": True,
        "message": f"QR code '{record.title}' deleted successfully.",
        "remaining_count": remaining_count
    })
