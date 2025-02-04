import os
import openai
import psycopg2
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv()

# Load environment variables
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

# Initialize Slack bot
app = App(token=SLACK_BOT_TOKEN)

# Connect to PostgreSQL database
def get_db_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

# Analyze message sentiment using OpenAI
def analyze_message(text):
    openai.api_key = OPENAI_API_KEY
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": f"Does this message express gratitude or praise? {text}"}]
    )
    return "yes" in response["choices"][0]["message"]["content"].lower()

# Handle message events
@app.event("message")
def handle_message_events(body, say):
    text = body["event"].get("text", "")
    user = body["event"].get("user", "")
    channel = body["event"].get("channel", "")

    if analyze_message(text):
        award_kudos(user)
        say(f"🎉 Kudos! @{user} has received recognition! 🚀")

# Function to award kudos points
def award_kudos(user):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO kudos (user_id, points) VALUES (%s, %s) ON CONFLICT (user_id) DO UPDATE SET points = kudos.points + 1", (user, 1))
    conn.commit()
    cur.close()
    conn.close()

# Flask app to expose leaderboard API
flask_app = Flask(__name__)

@flask_app.route("/leaderboard", methods=["GET"])
def leaderboard():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id, points FROM kudos ORDER BY points DESC LIMIT 10")
    leaderboard_data = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify({"leaderboard": leaderboard_data})

# Start Slack bot
if __name__ == "__main__":
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
    flask_app.run(host="0.0.0.0", port=5000)
