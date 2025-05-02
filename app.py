from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename

from dotenv import load_dotenv
import os

load_dotenv()
app = Flask(__name__)
app.secret_key = 'ma_cle_secrete_123'

# Configuration pour l'upload de fichiers
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Configuration base de données
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ventes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Vérification d'extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Modèles des bien
class Bien(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(50), nullable=False)
    denomination = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    matricule = db.Column(db.String(50), nullable=False)
    etat = db.Column(db.String(255), nullable=True)
    prix_depart = db.Column(db.Float, nullable=False)
    photo = db.Column(db.String(255), nullable=True)
    

#basse de données des offres
class Offre(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bien_id = db.Column(db.Integer, db.ForeignKey('bien.id'), nullable=False)
    nom_complet = db.Column(db.String(100), nullable=False)
    matricule = db.Column(db.String(50), nullable=False)
    telephone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    prix_propose = db.Column(db.Float, nullable=False)
    commentaire = db.Column(db.Text, nullable=True)
    bien = db.relationship('Bien', backref=db.backref('offres', lazy=True))

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), nullable=False, unique=True)
    mot_de_passe = db.Column(db.String(150), nullable=False)

class Utilisateur(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom_complet = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), nullable=False, unique=True)
    mot_de_passe = db.Column(db.String(150), nullable=False)

# Création des tables
with app.app_context():
    db.create_all()
    if not Admin.query.filter_by(email='admin@gmail.com').first():
        admin = Admin(email='admin@gmail.com', mot_de_passe = os.getenv("ADMIN_PASSWORD")
)
        db.session.add(admin)
        db.session.commit()
        print("Admin créé avec succès !")

# Accueil
@app.route('/')
def home():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))
    elif session.get('user_logged_in'):
        return redirect(url_for('liste_biens'))
    return redirect(url_for('login'))

@app.route('/index')
def index():
    return render_template('index.html')

#connexion admin et utilisateur

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        mot_de_passe = request.form.get('mot_de_passe')

        # Vérifie si c'est un admin
        admin = Admin.query.filter_by(email=email, mot_de_passe=mot_de_passe).first()
        if admin:
            session['admin_logged_in'] = True
            session['admin_id'] = admin.id
            flash('Connexion administrateur réussie !', 'success')
            return redirect(url_for('admin_dashboard'))

        # Sinon, vérifie si c'est un utilisateur
        utilisateur = Utilisateur.query.filter_by(email=email, mot_de_passe=mot_de_passe).first()
        if utilisateur:
            session['user_logged_in'] = True
            session['user_id'] = utilisateur.id
            flash('Connexion utilisateur réussie !', 'success')
            return redirect(url_for('liste_biens'))

        # Si aucun trouvé
        flash('Identifiants incorrects.', 'danger')

    return render_template('login.html')


# Déconnexion
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

#profile

@app.route('/profil')
def profil():
    if 'nom_complet' not in session:
        return redirect(url_for('login'))
    return render_template('profil.html', nom_complet=session['nom_complet'])


# Inscription Utilisateur
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nom_complet = request.form.get('nom_complet')
        email = request.form.get('email')
        mot_de_passe = request.form.get('mot_de_passe')

        if Utilisateur.query.filter_by(email=email).first():
            flash('Email déjà utilisé.', 'danger')
            return redirect(url_for('register'))

        nouvel_utilisateur = Utilisateur(
            nom_complet=nom_complet,
            email=email,
            mot_de_passe=mot_de_passe
        )
        db.session.add(nouvel_utilisateur)
        db.session.commit()

        flash('Inscription réussie ! Connectez-vous.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# Liste des biens
@app.route('/biens')
def liste_biens():
    if not session.get('user_logged_in'):
        return redirect(url_for('login'))

    biens = Bien.query.all()
    return render_template('index.html', biens=biens)

# Détail d'un bien + soumission d'une offre
@app.route('/bien/<int:bien_id>', methods=['GET', 'POST'])
def detail(bien_id):
    bien = Bien.query.get_or_404(bien_id)

    if request.method == 'POST':
        nom_complet = request.form.get('nom_complet')
        matricule = request.form.get('matricule')
        telephone = request.form.get('telephone')
        email = request.form.get('email')
        prix_offre = request.form.get('prix_offre')
        commentaire = request.form.get('commentaire')

        try:
            prix_offre = float(prix_offre)
        except (ValueError, TypeError):
            flash("Le prix proposé doit être un nombre valide.", 'danger')
            return render_template('soumettre.html', bien=bien)

        if prix_offre <= bien.prix_depart:
            flash("L'offre est inférieure ou égale au prix de départ. Veuillez proposer un montant plus élevé.", 'warning')
            return render_template('soumettre.html', bien=bien)

        offre = Offre(
            bien_id=bien.id,
            nom_complet=nom_complet,
            matricule=matricule,
            telephone=telephone,
            email=email,
            prix_propose=prix_offre,
            commentaire=commentaire
        )
        db.session.add(offre)
        db.session.commit()

        flash('Offre soumise avec succès.', 'success')
        return redirect(url_for('liste_biens'))

    return render_template('soumettre.html', bien=bien)

#recherche des bien
@app.route('/accueil')
def accueil():
    type_recherche = request.args.get('type', '').strip()
    print("Type recherché :", type_recherche)

    if type_recherche:
        biens = Bien.query.filter(Bien.type.ilike(f"%{type_recherche}%")).all()
    else:
        biens = Bien.query.all()

    print("Biens trouvés :", biens)
    return render_template('index.html', biens=biens, user_name=session.get('user_name'))


# Dashboard Admin
@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    offres = Offre.query.all()
    return render_template('admin_dashboard.html', offres=offres)

# Gestion des biens
@app.route('/admin/gerer_biens')
def gerer_biens():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    biens = Bien.query.all()
    return render_template('gerer_biens.html', biens=biens)

# Ajouter un bien
@app.route('/admin/ajouter_bien', methods=['GET', 'POST'])
def ajouter_bien():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        numero = request.form.get('numero')
        denomination = request.form.get('denomination')
        type_bien = request.form.get('type')
        matricule = request.form.get('matricule')
        etat = request.form.get('etat')
        prix_depart = request.form.get('prix_depart')

        photo_file = request.files.get('photo')
        filename = None

        if photo_file and allowed_file(photo_file.filename):
            filename = secure_filename(photo_file.filename)
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo_file.save(photo_path)
        elif photo_file and photo_file.filename != '':
            flash('Type de fichier non autorisé.', 'danger')
            return redirect(request.url)

        nouveau_bien = Bien(
            numero=numero,
            denomination=denomination,
            type=type_bien,
            matricule=matricule,
            etat=etat,
            prix_depart=float(prix_depart),
            photo=filename
        )
        db.session.add(nouveau_bien)
        db.session.commit()

        flash('Bien ajouté avec succès.', 'success')
        return redirect(url_for('gerer_biens'))

    return render_template('ajouter_bien.html')

# Modifier un bien
@app.route('/admin/modifier_bien/<int:bien_id>', methods=['GET', 'POST'])
def modifier_bien(bien_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    bien = Bien.query.get_or_404(bien_id)

    if request.method == 'POST':
        bien.numero = request.form.get('numero')
        bien.denomination = request.form.get('denomination')
        bien.type = request.form.get('type')
        bien.matricule = request.form.get('matricule')
        bien.etat = request.form.get('etat')
        bien.prix_depart = float(request.form.get('prix_depart'))

        photo_file = request.files.get('photo')
        if photo_file and allowed_file(photo_file.filename):
            filename = secure_filename(photo_file.filename)
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo_file.save(photo_path)
            bien.photo = filename

        db.session.commit()
        flash('Bien modifié avec succès.', 'success')
        return redirect(url_for('gerer_biens'))

    return render_template('modifier_bien.html', bien=bien)

# Supprimer un bien
@app.route('/admin/supprimer_bien/<int:bien_id>', methods=['POST'])
def supprimer_bien(bien_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    bien = Bien.query.get_or_404(bien_id)

    # Supprimer aussi toutes les offres associées au bien
    offres = Offre.query.filter_by(bien_id=bien.id).all()
    for offre in offres:
        db.session.delete(offre)

    db.session.delete(bien)
    db.session.commit()

    flash('Bien (et offres associées) supprimé avec succès.', 'success')
    return redirect(url_for('gerer_biens'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
