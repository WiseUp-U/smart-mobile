import os, time
from flask import Flask, render_template, request, redirect, session, url_for, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# ------------------ APP CONFIG ------------------
app = Flask(__name__)
load_dotenv()
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max upload

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db = SQLAlchemy(app)

# ------------------ MODELS ------------------
product_images = db.Table('product_images',
    db.Column('product_id', db.Integer, db.ForeignKey('product.id')),
    db.Column('image_id', db.Integer, db.ForeignKey('image.id'))
)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    brand = db.Column(db.String(50))
    price = db.Column(db.Integer)
    ram = db.Column(db.String(20))
    storage = db.Column(db.String(20))
    condition = db.Column(db.String(50))
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default="available")
    images = db.relationship('Image', secondary=product_images, backref='products', cascade="all")

class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200))

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(200))

# ------------------ HELPERS ------------------
def is_admin():
    return session.get('admin')

def save_image(file):
    filename = str(int(time.time())) + "_" + secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    return filename

# ------------------ ROUTES ------------------
@app.route('/')
def index():
    search_query = request.args.get('q', '').strip()
    brand_filter = request.args.get('brand', '').strip()

    products = Product.query

    if search_query:
        products = products.filter(Product.name.ilike(f"%{search_query}%"))
    if brand_filter:
        products = products.filter_by(brand=brand_filter)

    return render_template('index.html', products=products.all())

@app.route('/product/<int:id>')
def product(id):
    product = Product.query.get_or_404(id)
    return render_template('product.html', product=product)

# ------------------ ADMIN ------------------
@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if request.method == 'POST':
        user = Admin.query.filter_by(username=request.form['username']).first()

        if user and check_password_hash(user.password, request.form['password']):
            session['admin'] = True
            return redirect(url_for('dashboard'))

        return render_template('admin/login.html', error="Wrong password")

    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
def dashboard():
    if not is_admin():
        return redirect(url_for('admin_login'))

    products = Product.query.order_by(Product.id.desc()).all()
    return render_template('admin/dashboard.html', products=products)

# ------------------ ADD / EDIT PRODUCT ------------------
@app.route('/admin/product_form', methods=['GET','POST'])
@app.route('/admin/product_form/<int:id>', methods=['GET','POST'])
def product_form(id=None):
    if not is_admin():
        return redirect(url_for('admin_login'))

    product = Product.query.get(id) if id else None

    if request.method == 'POST':
        if not product:
            product = Product()
            db.session.add(product)

        product.name = request.form.get('name')
        product.brand = request.form.get('brand')
        product.price = request.form.get('price')
        product.ram = request.form.get('ram')
        product.storage = request.form.get('storage')
        product.condition = request.form.get('condition')
        product.description = request.form.get('description')
        product.status = request.form.get('status', 'available')

        # DELETE IMAGES
        delete_ids = request.form.getlist('delete_images')
        for img_id in delete_ids:
            img = Image.query.get(int(img_id))
            if img:
                try:
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], img.filename))
                except:
                    pass
                db.session.delete(img)

        # ADD IMAGES
        files = request.files.getlist('images')
        for f in files:
            if f and f.filename:
                filename = save_image(f)
                img = Image(filename=filename)
                db.session.add(img)
                product.images.append(img)

        db.session.commit()
        return redirect(url_for('dashboard'))

    return render_template('admin/product_form.html', product=product)

# ------------------ DELETE PRODUCT ------------------
@app.route('/admin/delete/<int:id>')
def delete_product(id):
    if not is_admin():
        return redirect(url_for('admin_login'))

    product = Product.query.get_or_404(id)

    for img in product.images:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], img.filename))
        except:
            pass
        db.session.delete(img)

    db.session.delete(product)
    db.session.commit()

    return redirect(url_for('dashboard'))

# ------------------ TOGGLE STATUS ------------------
@app.route('/admin/toggle/<int:id>')
def toggle_status(id):
    if not is_admin():
        return redirect(url_for('admin_login'))

    product = Product.query.get_or_404(id)
    product.status = "sold" if product.status == "available" else "available"

    db.session.commit()
    return redirect(url_for('dashboard'))

# ------------------ INIT ------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        if not Admin.query.first():
            admin = Admin(
                username="admin",
                password=generate_password_hash("admin123")
            )
            db.session.add(admin)
            db.session.commit()

    app.run(debug=True)