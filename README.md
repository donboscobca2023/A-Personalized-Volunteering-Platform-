# Volunteer Platform Setup Instructions

## Quick Start

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd <repo-name>
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Apply migrations:**
   ```bash
   python manage.py migrate
   ```

5. **Run the development server:**
   ```bash
   python manage.py runserver
   ```

6. **Access the app:**
   - Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser.
   - Admin interface: [http://127.0.0.1:8000/admin/](http://127.0.0.1:8000/admin/)