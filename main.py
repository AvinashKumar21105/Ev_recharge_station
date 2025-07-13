from flask import Flask, render_template, request, redirect, url_for, flash, session
import pyrebase
import random
from twilio.rest import Client

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Firebase Configuration
firebaseConfig = {
    "apiKey": "AIzaSyCI1d6GKJRgrdZdtldchGpZu-raGZs1nPo",
    "authDomain": "ev-recharge-station-eba17.firebaseapp.com",
    "databaseURL": "https://ev-recharge-station-eba17-default-rtdb.asia-southeast1.firebasedatabase.app",
    "projectId": "ev-recharge-station-eba17",
    "storageBucket": "ev-recharge-station-eba17.appspot.com",
    "messagingSenderId": "778963998102",
    "appId": "1:778963998102:web:aaa79b3509a1705e6e39b7",
    "measurementId": "G-MKD2KWQ2TB"
}

firebase = pyrebase.initialize_app(firebaseConfig)
db = firebase.database()

# Twilio Configuration
API_KEY      = "731d090786d32000a454918702c78807"
TWILIO_SID   = "ACdbd49d31c3bcd824aa4bd68eb60e5d5a"
TWILIO_AUTH  = "907472c8430e34489ad3d367bfbb3ddb"
TWILIO_FROM  = "+14752588689"

@app.route('/')
def index():
    return render_template("index.html")


# ------------------ USER AUTH ------------------

@app.route('/user/register', methods=['GET', 'POST'])
def user_register():
    if request.method == 'POST':
        data = {
            "name": request.form['user_name'],
            "email": request.form['user_email'],
            "phone": request.form['user_phone'],
            "password": request.form['user_password']
        }

        users = db.child("users").get().val()
        if users:
            for user in users.values():
                if user['email'] == data['email']:
                    flash("User already registered!", "danger")
                    return redirect(url_for('user_register'))

        db.child("users").push(data)
        flash("User registration successful!", "success")
        return redirect(url_for('user_login'))

    return render_template("user_register.html")


@app.route('/user/login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        email = request.form['user_email']
        password = request.form['user_password']

        users = db.child("users").get().val()
        if users:
            for key, user in users.items():
                if user['email'] == email and user['password'] == password:
                    session['user'] = {
                        "name": user['name'],
                        "email": user['email'],
                        "phone": user['phone']
                    }
                    flash("User login successful!", "success")
                    return redirect(url_for('user_home'))

        flash("Invalid user credentials", "danger")
        return redirect(url_for('user_login'))

    return render_template("user_login.html")


@app.route('/user/home')
def user_home():
    if 'user' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('user_login'))

    bunks_data = db.child("ev_bunks").get().val()
    search_query = request.args.get('search_query', '').lower()

    bunks = {}
    if bunks_data:
        for bunk_id, bunk in bunks_data.items():
            if search_query in bunk.get('address', '').lower() or search_query in bunk.get('bunk_name', '').lower() or not search_query:
                bunks[bunk_id] = bunk

    return render_template("user_home.html", user=session['user'], bunks=bunks)


@app.route("/book-now/<bunk_id>", methods=["POST"])
def book_now(bunk_id):
    if 'user' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('user_login'))

    bunk = db.child("ev_bunks").child(bunk_id).get().val()
    if not bunk:
        flash("Bunk not found!", "danger")
        return redirect(url_for('user_home'))

    slot_count = int(bunk.get("slot_count", 0))
    if slot_count <= 0:
        flash("No available slots at this bunk.", "danger")
        return redirect(url_for('user_home'))

    # Decrease slot count
    db.child("ev_bunks").child(bunk_id).update({
        "slot_count": slot_count - 1
    })

    # Generate 4-digit PIN
    pin = str(random.randint(1000, 9999))

    # Send SMS using Twilio
    try:
        user_phone = session['user']['phone'].strip().replace(" ", "").replace("+91", "")
        client = Client(TWILIO_SID, TWILIO_AUTH)
        message = client.messages.create(
            body=f"Your EV Slot is booked at '{bunk['bunk_name']}'. Your PIN is: {pin}",
            from_=TWILIO_FROM,
            to=f"+91{user_phone}"  # Indian format
        )
        flash(f"✅ Booking confirmed! PIN sent to +91{user_phone}", "success")
    except Exception as e:
        flash(f"Booking confirmed but failed to send SMS. Error: {str(e)}", "warning")

    return redirect(url_for('user_home'))


# ------------------ ADMIN AUTH ------------------

@app.route('/admin/register', methods=['GET', 'POST'])
def admin_register():
    if request.method == 'POST':
        data = {
            "name": request.form['admin_name'],
            "email": request.form['admin_email'],
            "phone": request.form['admin_phone'],
            "password": request.form['admin_password']
        }

        admins = db.child("admins").get().val()
        if admins:
            for admin in admins.values():
                if admin['email'] == data['email']:
                    flash("Admin already registered!", "danger")
                    return redirect(url_for('admin_register'))

        db.child("admins").push(data)
        flash("Admin registration successful!", "success")
        return redirect(url_for('admin_login'))

    return render_template("admin_register.html")


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['admin_email']
        password = request.form['admin_password']

        admins = db.child("admins").get().val()
        if admins:
            for key, admin in admins.items():
                if admin['email'] == email and admin['password'] == password:
                    session['admin'] = {
                        "name": admin['name'],
                        "email": admin['email'],
                        "phone": admin['phone']
                    }
                    flash("Admin login successful!", "success")
                    return redirect(url_for('admin_home'))

        flash("Invalid admin credentials", "danger")
        return redirect(url_for('admin_login'))

    return render_template("admin_login.html")


@app.route('/admin/home')
def admin_home():
    if 'admin' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('admin_login'))

    bunks = db.child("ev_bunks").get().val()
    return render_template("admin_home.html", admin=session['admin'], bunks=bunks)


# ------------------ BUNK MANAGEMENT ------------------

@app.route("/admin/create-bunk", methods=["GET", "POST"])
def create_bunk():
    if 'admin' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('admin_login'))

    if request.method == "POST":
        data = {
            "bunk_name": request.form.get("bunk_name"),
            "slot_count": request.form.get("slot_count"),
            "address": request.form.get("address"),
            "gmap_link": request.form.get("gmap_link"),
            "mobile": request.form.get("phone")
        }

        db.child("ev_bunks").push(data)
        flash("EV Bunk Location created successfully!", "success")
        return redirect(url_for('admin_home'))

    return render_template("create_bunk.html")


@app.route("/admin/edit-bunk/<bunk_id>", methods=["GET", "POST"])
def edit_bunk(bunk_id):
    if 'admin' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('admin_login'))

    bunk = db.child("ev_bunks").child(bunk_id).get().val()
    if not bunk:
        flash("Bunk not found.", "danger")
        return redirect(url_for('admin_home'))

    if request.method == "POST":
        updated_data = {
            "bunk_name": request.form.get("bunk_name"),
            "slot_count": request.form.get("slot_count"),
            "address": request.form.get("address"),
            "gmap_link": request.form.get("gmap_link"),
            "mobile": request.form.get("phone")
        }
        db.child("ev_bunks").child(bunk_id).update(updated_data)
        flash("Bunk updated successfully!", "success")
        return redirect(url_for('admin_home'))

    return render_template("edit_bunk.html", bunk=bunk, bunk_id=bunk_id)


@app.route("/admin/delete-bunk/<bunk_id>")
def delete_bunk(bunk_id):
    if 'admin' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('admin_login'))

    db.child("ev_bunks").child(bunk_id).remove()
    flash("Bunk deleted successfully!", "success")
    return redirect(url_for('admin_home'))


# ------------------ LOGOUT & ERROR ------------------

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for('index'))


@app.errorhandler(404)
def not_found(e):
    return "<h1>404 Page Not Found</h1>", 404


# ------------------ MAIN ------------------

if __name__ == '__main__':
    app.run(debug=True)
