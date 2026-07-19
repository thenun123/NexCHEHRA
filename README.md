# NexCHEHRA - AI Influencer Video Generator

NexCHEHRA is a cutting-edge web application for AI influencer generation. Built with Python and Flask, the platform creates photorealistic portraits, seamless product placements, and high-quality, lip-synced videos using the latest models from fal.ai (Flux and Kling).

## 🚀 Features

*   **Photorealistic Portraits:** Generate stunning AI models using the advanced Flux model.
*   **Seamless Product Placement:** Automatically integrate user-uploaded products (bags, cosmetics, jewelry, etc.) into generated portraits with Flux Multi.
*   **Video Generation with Lip-Sync:** Turn portraits into lifelike videos using Kling models with built-in multi-language voice support.
*   **Cloud-Native Architecture:** Configured out-of-the-box for serverless deployment on Render.
*   **Global Asset Delivery:** All images, videos, and static assets are managed and served lightning-fast via ImageKit.
*   **Persistent Database:** Integrated with Supabase (PostgreSQL) for reliable data retention across deployments.

## 🛠️ Technology Stack

*   **Backend:** Python 3, Flask, Gunicorn
*   **Database:** PostgreSQL (via Supabase), Flask-SQLAlchemy
*   **AI Integration:** fal-client (Flux & Kling), Mistral
*   **Storage & CDN:** ImageKit

## 📦 Local Development

### Prerequisites

Ensure you have Python 3.8+ installed.

### Setup

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd NexCHEHRAdeploy
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment Variables:**
    Create a `.env` file in the project root directory. You can use `.env.example` as a template.
    For basic local development, you do not need to configure external databases or CDNs—the app will fall back to local SQLite and disk storage. To utilize all features, configure your API keys for Fal, Mistral, Supabase, and ImageKit.

4.  **Run the application:**
    ```bash
    python run.py
    ```

    The application will start at `http://localhost:5000`.

## ☁️ Deployment

NexCHEHRA is configured for simple, robust deployment to **Render**, leveraging **Supabase** for persistent database storage and **ImageKit** to preserve generated media between redeployments.

For full, step-by-step instructions on setting up your cloud services and deploying to Render, please see the [DEPLOYMENT.md](DEPLOYMENT.md) guide.

## 📜 Project Structure

*   `app/` - Flask application core, including routes, models, and initialization.
*   `clients/` - API wrappers and clients for ImageKit, Fal.ai, etc.
*   `config/` - Configuration settings and environment validation.
*   `static/` - Local CSS, JS, and image assets (mirrored to ImageKit in production).
*   `templates/` - HTML templates for the frontend interface.
*   `run.py` - Application entry point.
*   `DEPLOYMENT.md` - Comprehensive deployment guide.
