# Sweet Crumbs Bakery Bot 🧁

A full-stack web application featuring an AI-powered chatbot for a bakery. Built with Flask, this application allows users to view the menu, ask FAQs, and place orders directly through a conversational interface powered by the Groq API. It also includes an admin dashboard to manage and view incoming orders.

## Features

*   **AI Chatbot Assistant:** Handles customer queries, FAQs (opening hours, location, delivery charges), and order placements natively.
*   **Order Management:** Generates unique order IDs (e.g., SCB1001) and stores them in an SQLite database.
*   **Order Tracking & Cancellation:** Users can ask the bot to track or cancel their orders (within a 1-hour window).
*   **Admin Dashboard:** A backend interface (`/admin`) for bakery owners to view analytics, update order statuses, and track history.

## Tech Stack

*   **Backend:** Python, Flask, SQLite3
*   **Frontend:** HTML, CSS, JavaScript
*   **AI Integration:** Groq API (using the OpenAI Python SDK)

## Setup Instructions

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/botter.git
    cd botter
    ```

2.  **Create a Virtual Environment:**
    ```bash
    python -m venv env
    # Windows
    env\Scripts\activate
    # macOS/Linux
    source env/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Environment Variables:**
    Create a `.env` file in the root directory and add your Groq API key:
    ```
    GROQ_API_KEY=your_groq_api_key_here
    ```

5.  **Run the Application:**
    ```bash
    python app.py
    ```
    The application will run on `http://127.0.0.1:5000`.

## Directory Structure

*   `app.py`: Main Flask application and API routes.
*   `database.py`: SQLite database initialization and helper functions.
*   `bot.py`: Chatbot logic and Groq API integration.
*   `templates/`: HTML files for the chat interface and admin dashboard.
*   `static/`: CSS and JavaScript files for frontend styling and behavior.
