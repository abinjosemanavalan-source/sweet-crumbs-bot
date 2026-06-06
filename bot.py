from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from openai import OpenAI
import os

app = Flask(__name__)
CORS(app)

# ----------------------------------------
# GROQ API KEY
# ----------------------------------------
from dotenv import load_dotenv
load_dotenv()

client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

# ----------------------------------------
# BAKERY PERSONALITY & RULES
# ---> YOU CAN ADD YOUR RULES HERE <---
# ----------------------------------------
system_prompt = """
You are a bakery assistant for Sweet Crumbs Bakery.

Menu:
- Chocolate Cake - Rs.500
- Black Forest - Rs.550
- Red Velvet - Rs.650
- Vanilla Cake - Rs.450

Rules:
1. Always answer politely and professionally.
2. Recommend products only from the menu.
3. Keep answers extremely short, simple, and direct.
4. Use bullet points or tables when helpful.
5. Do not offer discounts.
6. Do not negotiate or bargain on prices.
7. Home delivery charge is Rs.30.
8. Accepted payment methods: Cash and Online Payment.
9. Opening hours: 9:00 AM to 6:00 PM.
10. If the customer wants delivery, ask for their delivery address.
11. When confirming an order, provide an estimated delivery time.
14. devliery will done in 2 hours
12. Orders cannot be cancelled within 1 hour of the scheduled delivery time.
13. If information is not available in these rules or the menu, politely say that the information is unavailable.
"""

# This fixes the "404 Not Found" error! 
# When you visit http://127.0.0.1:5000/ it will now show your website.
@app.route('/')
def home():
    return send_from_directory('.', 'super.html')

# This is the endpoint the chatbot widget talks to
@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    history = data.get('history', [])

    messages = [{"role": "system", "content": system_prompt}]
    
    # Add conversation history
    for msg in history:
        messages.append({"role": msg['role'], "content": msg['content']})

    # Add new user message
    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages
        )
        reply = response.choices[0].message.content
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)