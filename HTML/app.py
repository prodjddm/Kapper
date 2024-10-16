from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
import io
import base64
import matplotlib.pyplot as plt

# Initialiseer Flask en configuraties
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///videos.db'
app.config['SECRET_KEY'] = 'mijngeheimesleutel'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Initialiseer database
db = SQLAlchemy(app)

# Initialiseer Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200), nullable=False)
    filename = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)

# Maak tabellen aan als deze nog niet bestaan
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('employee_dashboard' if current_user.role == 'werknemer' else 'owner_dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('employee_dashboard' if user.role == 'werknemer' else 'owner_dashboard'))
        else:
            flash('Onjuiste inloggegevens.')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']  # rol kan werknemer of eigenaar zijn

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Gebruikersnaam bestaat al.')
            return redirect(url_for('register'))

        # Nieuwe gebruiker aanmaken met pbkdf2:sha256
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_password, role=role)
        db.session.add(new_user)
        db.session.commit()

        flash('Registratie succesvol! Je kunt nu inloggen.')
        return redirect(url_for('login'))

    return render_template('register.html')

# Dashboard werknemer
@app.route('/employee')
@login_required
def employee_dashboard():
    if current_user.role != 'werknemer':
        return redirect(url_for('index'))
    return render_template('employee_dashboard.html')

# Dashboard eigenaar
@app.route('/owner')
@login_required
def owner_dashboard():
    if current_user.role != 'eigenaar':
        return redirect(url_for('index'))
    return render_template('owner_dashboard.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Je bent uitgelogd.', 'success')
    return redirect(url_for('login'))

# Route om video's te uploaden (alleen eigenaar)
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if current_user.role != 'eigenaar':
        return redirect(url_for('index'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        category = request.form['category']
        file = request.files['file']

        if file:
            filename = file.filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            new_video = Video(title=title, description=description, filename=filename, category=category)
            db.session.add(new_video)
            db.session.commit()

            flash('Video geüpload.')
            return redirect(url_for('owner_dashboard'))

    return render_template('upload.html')

# Video-overzichtspagina per categorie
@app.route('/videos/<category>')
def video_overview(category):
    videos = Video.query.filter_by(category=category).all()
    return render_template('video_overview.html', videos=videos, category=category)

# Voortgangspagina
@app.route('/progress')
@login_required
def progress():
    videos = Video.query.all()
    watched = [video.id for video in videos]  # Voeg logica toe om daadwerkelijk de bekeken video's te tracken

    # Staafdiagram genereren
    watched_count = len(watched)
    not_watched_count = len(videos) - watched_count

    plt.bar(['Bekeken', 'Niet Bekeken'], [watched_count, not_watched_count])
    plt.ylabel('Aantal Video\'s')
    plt.title('Voortgang Video\'s')
    
    # Zet de figuur in een PNG-buffer
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode('utf8')
    
    return render_template('progress.html', plot_url=plot_url)

# Start de server
if __name__ == "__main__":
    app.run(debug=True)
