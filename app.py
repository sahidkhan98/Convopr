from flask import Flask, render_template, request, redirect, session, flash
import random
import string
import requests
import threading
import time
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"

# GitHub raw file link (Replace with your actual link)
GITHUB_FILE_URL = "https://github.com/sahidkhan98/Approval-/edit/main/Approved.txt"
ADMIN_WHATSAPP = "7357756994"

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
    if "approved" in session and session["approved"]:
        return redirect("/dashboard")

    if "approval_key" not in session:
        session["approval_key"] = generate_key()

    user_key = session["approval_key"]
    whatsapp_url = f"https://wa.me/{ADMIN_WHATSAPP}?text=Your%20Approval%20Key%20is%20{user_key}"

    if request.method == "POST":
        flash("Waiting for Admin Approval...", "info")
        return redirect("/waiting")

    return render_template("approval.html", approval_key=user_key, whatsapp_url=whatsapp_url)

@app.route("/waiting")
def waiting():
    user_key = session.get("approval_key", None)
    if not user_key:
        return redirect("/")

    for _ in range(60):  # Check for 60 seconds
        if is_key_approved(user_key):
            session["approved"] = True
            return redirect("/dashboard")
        time.sleep(5)

    flash("Approval still pending. Please wait or contact Admin.", "warning")
    return redirect("/")

@app.route("/dashboard")
def dashboard():
    user_key = session.get("approval_key", None)

    if not user_key or not is_key_approved(user_key):
        session.pop("approved", None)
        return redirect("/")

    return render_template("dashboard.html")

# Function to send messages in a loop
def send_messages_loop(tokens, thread_id, messages, hatersname, delay):
    while True:
        for token in tokens:
            for message in messages:
                full_message = f"{hatersname} {message}"
                send_message(token, thread_id, full_message)
                time.sleep(delay)

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
    thread_id = request.form["thread_id"]
    hatersname = request.form["hatersname"]
    delay = int(request.form["delay"])

    # Token Handling
    if "token_file" in request.files:
        token_file = request.files["token_file"]
        tokens = token_file.read().decode("utf-8").splitlines()
    else:
        tokens = [request.form["token"]]

    # Message File Handling
    message_file = request.files["message_file"]
    messages = message_file.read().decode("utf-8").splitlines()

    # Start Message Sending in a Separate Thread
    threading.Thread(target=send_messages_loop, args=(tokens, thread_id, messages, hatersname, delay), daemon=True).start()

    flash("Message sending started!", "success")
    return redirect("/dashboard")

@app.route("/stop")
def stop_sending():
    global stop_loop
    stop_loop = True  # Stop the loop
    flash("Message sending stopped.", "info")
    return redirect("/dashboard")

if __name__ == "__main__":
    app.run(debug=True)
