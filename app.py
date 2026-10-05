from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
from dotenv import load_dotenv
from openai import OpenAI
from werkzeug.security import generate_password_hash, check_password_hash
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-only-key")
MODEL = "gpt-4o-mini"
FALLBACK_REPLY = "Sorry, I couldn't get an answer right now. Please try again."
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "chatbot.db")
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            response TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()
    print("Database initialized at:")
    print(DATABASE)
@app.route("/")
def home():
    return render_template("login.html")
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, password FROM users WHERE email = ?",
            (email,)
        )
        user = cursor.fetchone()
        conn.close()
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            return redirect(url_for("chat"))
        if not user:
            error = "No account found with this email. Please create an account."
        else:
            error = "Incorrect password. Please try again."
        return render_template(
            "login.html",
            error=error,
            email=email
        )
    return render_template("login.html")
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        hashed_password = generate_password_hash(password)
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO users (name, email, password)
                VALUES (?, ?, ?)
                """,
                (name, email, hashed_password)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return render_template(
                "signup.html",
                error="This email is already registered. Please log in.",
                name=name,
                email=email
            )
        conn.close()
        return redirect(url_for("login"))
    return render_template("signup.html")
@app.route("/chat", methods=["GET", "POST"])
def chat():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user_id = session["user_id"]
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == "POST":
        data = request.get_json()
        if not data:
            conn.close()
            return {"response": "Invalid request."}
        message = data.get("message", "").strip()
        if not message:
            conn.close()
            return {"response": "Please enter a message."}
        cursor.execute(
            """
            SELECT message, response
            FROM chats
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 10
            """,
            (user_id,)
        )
        past = cursor.fetchall()
        past = past[::-1]
        messages = [
            {
                "role": "system",
                "content": (
                    "You are a friendly and helpful AI chatbot. "
                    "Give clear and useful answers."
                )
            }
        ]
        for old_chat in past:
            if old_chat["response"] == FALLBACK_REPLY:
                continue
            messages.append({
                "role": "user",
                "content": old_chat["message"]
            })
            messages.append({
                "role": "assistant",
                "content": old_chat["response"]
            })
        messages.append({
            "role": "user",
            "content": message
        })
        try:
            completion = client.chat.completions.create(
                model=MODEL,
                messages=messages
            )
            response = completion.choices[0].message.content
        except Exception as error:
            print("OpenAI error:", error)
            response = FALLBACK_REPLY
        try:
            cursor.execute(
                """
                INSERT INTO chats
                (user_id, message, response)
                VALUES (?, ?, ?)
                """,
                (user_id, message, response)
            )
            conn.commit()
            print("Chat saved successfully! User ID:", user_id)
        except Exception as error:
            print("Database error while saving chat:", error)
        finally:
            conn.close()
        return {
            "response": response
        }
    cursor.execute(
        """
        SELECT message, response
        FROM chats
        WHERE user_id = ?
        ORDER BY id ASC
        """,
        (user_id,)
    )
    history = cursor.fetchall()
    conn.close()
    return render_template(
        "chat.html",
        history=history
    )
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))
if __name__ == "__main__":
    init_db()
    app.run(debug=True)
    