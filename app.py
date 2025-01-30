from flask import Flask, render_template, request, redirect, session, flash
import random
import string
import requests
import threading
import time

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Import Configurations
from config import ADMIN_WHATSAPP, GITHUB_FILE_URL

# Global variable to control message loop
stop_loop = False

# Function to generate a unique approval key
def generate_key():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# Function to check if key exists in GitHub file
def is_key_approved(key):
    try:
        response = requests.get(GITHUB_FILE_URL)
        if response.status_code == 200:
            approved_keys = response.text.splitlines()
            return key in approved_keys
    except Exception as e:
        print("Error fetching GitHub file:", e)
    return False

@app.route("/", methods=["GET", "POST"])
def approval():
    if request.method == "POST":
        user_key = request.form["approval_key"]
        if is_key_approved(user_key):
            session["approved"] = True
            return redirect("/dashboard")
        else:
            flash("Invalid key! Please wait for admin approval.", "danger")

    approval_key = generate_key()
    whatsapp_url = f"https://wa.me/{ADMIN_WHATSAPP}?text=Your%20Approval%20Key%20is%20{approval_key}"
    return render_template("approval.html", approval_key=approval_key, whatsapp_url=whatsapp_url)

@app.route("/dashboard")
def dashboard():
    if not session.get("approved"):
        return redirect("/")
    return render_template("dashboard.html")

# Function to send messages in a loop
def send_messages_loop(token, thread_id, messages, delay):
    global stop_loop
    while not stop_loop:
        for message in messages:
            send_message(token, thread_id, message)
            time.sleep(delay)  # Delay between messages

# Function to send a single message
def send_message(token, thread_id, text):
    url = "https://graph.facebook.com/v18.0/me/messages"
    headers = {"Content-Type": "application/json"}
    payload = {
        "recipient": {"id": thread_id},
        "message": {"text": text},
        "messaging_type": "RESPONSE",
        "access_token": token
    }
    requests.post(url, json=payload, headers=headers)

@app.route("/start", methods=["POST"])
def start_sending():
    global stop_loop
    stop_loop = False  # Reset stop condition

    token = request.form["token"]
    thread_id = request.form["thread_id"]
    delay = int(request.form["delay"])
    messages = request.form["messages"].split("\n")

    # Start message sending in a separate thread
    threading.Thread(target=send_messages_loop, args=(token, thread_id, messages, delay), daemon=True).start()
    return redirect("/dashboard")

@app.route("/stop")
def stop_sending():
    global stop_loop
    stop_loop = True  # Stop the loop
    return redirect("/dashboard")

if __name__ == "__main__":
    app.run(debug=True)
