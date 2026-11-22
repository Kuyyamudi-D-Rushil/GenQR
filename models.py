from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


class User(UserMixin, db.Model):
    """User account model for cloud authentication."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    # One-to-many relationship: One user can generate multiple QR codes
    qr_codes = db.relationship(
        "QRCode",
        backref="owner",
        cascade="all, delete-orphan",
        lazy="dynamic",
        order_by="desc(QRCode.created_at)"
    )

    def set_password(self, password: str) -> None:
        """Hash and set user password securely."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify candidate password against stored hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User id={self.id} username='{self.username}' email='{self.email}'>"


class QRCode(db.Model):
    """QR Code metadata record stored in the cloud database."""

    __tablename__ = "qr_codes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    title = db.Column(db.String(150), default="My QR Code")
    qr_type = db.Column(db.String(30), nullable=False)  # url, text, email, phone
    content = db.Column(db.Text, nullable=False)
    foreground = db.Column(db.String(7), default="#000000")
    background = db.Column(db.String(7), default="#FFFFFF")
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True
    )

    def to_dict(self) -> dict:
        """Convert QR code record to dictionary for API responses."""
        return {
            "id": self.id,
            "title": self.title,
            "qr_type": self.qr_type,
            "content": self.content,
            "foreground": self.foreground,
            "background": self.background,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "formatted_date": self.created_at.strftime("%b %d, %Y - %I:%M %p") if self.created_at else ""
        }

    def __repr__(self) -> str:
        return f"<QRCode id={self.id} user_id={self.user_id} title='{self.title}' type='{self.qr_type}'>"
