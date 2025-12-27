from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required
)
from flask_cors import CORS
import cloudinary
import cloudinary.uploader
import os

app = Flask(__name__)

# ---------------- CONFIG ---------------- #
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "supersecret")
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "jwtsecret")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///portfolio.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
jwt = JWTManager(app)
CORS(app)

# ---------------- CLOUDINARY CONFIG ---------------- #
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

# ---------------- MODELS ---------------- #
class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(300), nullable=False)
    url = db.Column(db.String(500), nullable=False)

class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    public_id = db.Column(db.String(300), nullable=False)
    url = db.Column(db.String(500), nullable=False)

# ---------------- AUTH ---------------- #
@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json()

    if not data:
        return jsonify({"error": "Invalid request"}), 400

    if data.get("username") == "admin" and data.get("password") == "starosi1249":
        token = create_access_token(identity="admin")
        return jsonify({"access_token": token})

    return jsonify({"error": "Invalid credentials"}), 401

# ---------------- VIDEO ROUTES ---------------- #
@app.route("/api/videos", methods=["POST"])
@jwt_required()
def upload_video():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    result = cloudinary.uploader.upload(
        file,
        resource_type="video",
        folder="portfolio/videos"
    )

    video = Video(
        public_id=result["public_id"],
        url=result["secure_url"]
    )

    db.session.add(video)
    db.session.commit()

    return jsonify({
        "message": "Video uploaded",
        "id": video.id,
        "url": video.url
    })


@app.route("/api/videos", methods=["GET"])
def get_videos():
    videos = Video.query.all()
    return jsonify({
        "videos": [
            {"id": v.id, "url": v.url} for v in videos
        ]
    })


@app.route("/api/videos/<int:video_id>", methods=["DELETE"])
@jwt_required()
def delete_video(video_id):
    video = Video.query.get(video_id)
    if not video:
        return jsonify({"error": "Video not found"}), 404

    cloudinary.uploader.destroy(
        video.public_id,
        resource_type="video"
    )

    db.session.delete(video)
    db.session.commit()

    return jsonify({"message": "Video deleted"})

# ---------------- IMAGE ROUTES ---------------- #
@app.route("/api/images", methods=["POST"])
@jwt_required()
def upload_images():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    files = request.files.getlist("file")
    uploaded_urls = []

    for file in files:
        result = cloudinary.uploader.upload(
            file,
            folder="portfolio/images"
        )

        img = Image(
            public_id=result["public_id"],
            url=result["secure_url"]
        )

        db.session.add(img)
        uploaded_urls.append(result["secure_url"])

    db.session.commit()

    return jsonify({
        "message": "Images uploaded",
        "urls": uploaded_urls
    })


@app.route("/api/images", methods=["GET"])
def get_images():
    images = Image.query.all()
    return jsonify({
        "images": [
            {"id": img.id, "url": img.url} for img in images
        ]
    })


@app.route("/api/images/<int:image_id>", methods=["DELETE"])
@jwt_required()
def delete_image(image_id):
    img = Image.query.get(image_id)
    if not img:
        return jsonify({"error": "Image not found"}), 404

    cloudinary.uploader.destroy(img.public_id)

    db.session.delete(img)
    db.session.commit()

    return jsonify({"message": "Image deleted"})

# ---------------- MAIN ---------------- #
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
