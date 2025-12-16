from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
from flask_cors import CORS
import os

app = Flask(__name__)

# ---------------- CONFIG ---------------- #
app.config["SECRET_KEY"] = "supersecret"
app.config["JWT_SECRET_KEY"] = "jwtsecret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///portfolio.db"
app.config["UPLOAD_FOLDER"] = "uploads"

db = SQLAlchemy(app)
jwt = JWTManager(app)
CORS(app)  # ✅ Enable CORS

# Create upload folders if missing
os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "videos"), exist_ok=True)
os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "images"), exist_ok=True)

# ---------------- MODELS ---------------- #
class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)

class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)

# ---------------- AUTH ---------------- #
@app.route("/api/admin/login", methods=["POST"])
def login():
    data = request.json
    if data["username"] == "admin" and data["password"] == "starosi1249":
        token = create_access_token(identity="admin")
        return jsonify({"access_token": token})
    return jsonify({"error": "Invalid credentials"}), 401

# ---------------- VIDEO ---------------- #
@app.route("/api/videos", methods=["POST"])
@jwt_required()
def upload_video():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["file"]

    # save to folder
    path = os.path.join(app.config["UPLOAD_FOLDER"], "videos", file.filename)
    file.save(path)

    # add to DB (don’t delete old ones)
    new_video = Video(filename=file.filename)
    db.session.add(new_video)
    db.session.commit()

    return jsonify({"message": "Video uploaded", "id": new_video.id})

@app.route("/api/videos", methods=["GET"])
def get_videos():
    videos = Video.query.all()
    return jsonify({
        "videos": [
            {"id": v.id, "url": f"/uploads/videos/{v.filename}"} for v in videos
        ]
    })

@app.route("/api/videos/<int:video_id>", methods=["DELETE"])
@jwt_required()
def delete_video(video_id):
    video = Video.query.get(video_id)
    if not video:
        return jsonify({"error": "Video not found"}), 404

    # also delete file from uploads folder
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], "videos", video.filename)
    if os.path.exists(filepath):
        os.remove(filepath)

    db.session.delete(video)
    db.session.commit()
    return jsonify({"message": "Video deleted"})

# ---------------- IMAGES ---------------- #
@app.route("/api/images", methods=["POST"])
@jwt_required()
def upload_images():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    files = request.files.getlist("file")
    uploaded = []
    for file in files:
        path = os.path.join(app.config["UPLOAD_FOLDER"], "images", file.filename)
        file.save(path)
        img = Image(filename=file.filename)
        db.session.add(img)
        uploaded.append(file.filename)
    db.session.commit()
    return jsonify({"message": "Images uploaded", "files": uploaded})

@app.route("/api/images", methods=["GET"])
def get_images():
    images = Image.query.all()
    return jsonify({
        "images": [
            {"id": img.id, "url": f"/uploads/images/{img.filename}"} for img in images
        ]
    })

@app.route("/api/images/<int:image_id>", methods=["DELETE"])
@jwt_required()
def delete_image(image_id):
    img = Image.query.get(image_id)
    if not img:
        return jsonify({"error": "Image not found"}), 404

    # also delete file from uploads folder
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], "images", img.filename)
    if os.path.exists(filepath):
        os.remove(filepath)

    db.session.delete(img)
    db.session.commit()
    return jsonify({"message": "Image deleted"})

# ---------------- STATIC FILES ---------------- #
@app.route("/uploads/<path:folder>/<path:filename>")
def uploaded_files(folder, filename):
    return send_from_directory(os.path.join(app.config["UPLOAD_FOLDER"], folder), filename)

# ---------------- MAIN ---------------- #
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)