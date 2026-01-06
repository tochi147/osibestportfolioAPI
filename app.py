from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

# ---------------- BASIC CONFIG ---------------- #
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "supersecret")
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "jwtsecret")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# ---------------- DATABASE (Postgres on Render / SQLite locally) ---------------- #
database_url = os.getenv("DATABASE_URL")

if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///portfolio.db"

# ---------------- UPLOAD CONFIG ---------------- #
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.getenv(
    "UPLOAD_FOLDER",
    os.path.join(BASE_DIR, "uploads")
)

IMAGE_FOLDER = os.path.join(UPLOAD_FOLDER, "images")
VIDEO_FOLDER = os.path.join(UPLOAD_FOLDER, "videos")

os.makedirs(IMAGE_FOLDER, exist_ok=True)
os.makedirs(VIDEO_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ---------------- INIT EXTENSIONS ---------------- #
db = SQLAlchemy(app)
jwt = JWTManager(app)
CORS(app)

# ---------------- MODELS ---------------- #
class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(300), nullable=False)

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(300), nullable=False)

# ---------------- AUTH ---------------- #
@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json()

    if (
        data
        and data.get("username") == "admin"
        and data.get("password") == "starosi1249"
    ):
        token = create_access_token(identity="admin")
        return jsonify({"access_token": token})

    return jsonify({"error": "Invalid credentials"}), 401

# ---------------- IMAGE ROUTES ---------------- #
@app.route("/api/images", methods=["POST"])
@jwt_required()
def upload_images():
    if "file" not in request.files:
        return jsonify({"error": "No files uploaded"}), 400

    files = request.files.getlist("file")
    uploaded = []

    for file in files:
        filename = secure_filename(file.filename)
        path = os.path.join(IMAGE_FOLDER, filename)
        file.save(path)

        img = Image(filename=filename)
        db.session.add(img)
        uploaded.append(filename)

    db.session.commit()
    return jsonify({"message": "Images uploaded", "files": uploaded})


@app.route("/api/images", methods=["GET"])
def get_images():
    images = Image.query.all()
    return jsonify({
        "images": [
            {
                "id": img.id,
                "url": f"/uploads/images/{img.filename}"
            } for img in images
        ]
    })


@app.route("/api/images/<int:image_id>", methods=["DELETE"])
@jwt_required()
def delete_image(image_id):
    img = Image.query.get(image_id)
    if not img:
        return jsonify({"error": "Image not found"}), 404

    path = os.path.join(IMAGE_FOLDER, img.filename)
    if os.path.exists(path):
        os.remove(path)

    db.session.delete(img)
    db.session.commit()
    return jsonify({"message": "Image deleted"})

# ---------------- VIDEO ROUTES ---------------- #
@app.route("/api/videos", methods=["POST"])
@jwt_required()
def upload_video():
    if "file" not in request.files:
        return jsonify({"error": "No video uploaded"}), 400

    file = request.files["file"]
    filename = secure_filename(file.filename)
    path = os.path.join(VIDEO_FOLDER, filename)
    file.save(path)

    video = Video(filename=filename)
    db.session.add(video)
    db.session.commit()

    return jsonify({
        "message": "Video uploaded",
        "url": f"/uploads/videos/{filename}"
    })


@app.route("/api/videos", methods=["GET"])
def get_videos():
    videos = Video.query.all()
    return jsonify({
        "videos": [
            {
                "id": v.id,
                "url": f"/uploads/videos/{v.filename}"
            } for v in videos
        ]
    })


@app.route("/api/videos/<int:video_id>", methods=["DELETE"])
@jwt_required()
def delete_video(video_id):
    video = Video.query.get(video_id)
    if not video:
        return jsonify({"error": "Video not found"}), 404

    path = os.path.join(VIDEO_FOLDER, video.filename)
    if os.path.exists(path):
        os.remove(path)

    db.session.delete(video)
    db.session.commit()
    return jsonify({"message": "Video deleted"})

# ---------------- SERVE UPLOADS ---------------- #
@app.route("/uploads/<path:filename>")
def serve_uploads(filename):
    return app.send_static_file(f"uploads/{filename}")

# ---------------- MAIN ---------------- #
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
