# Demo Application

This is a Flask web application that allows users to register for a demo by filling out a form. The application stores user information in a PostgreSQL database.

## Features

- User registration form with validation
- Password hashing for security
- PostgreSQL database integration
- Responsive design with modern UI
- Success/error message handling

## Prerequisites

- Python 3.7 or higher
- PostgreSQL database
- pip (Python package installer)

## Installation

1. **Clone or download the project files**

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up PostgreSQL database:**
   - Create a PostgreSQL database
   - Update the database connection settings in `app.py`:
     ```python
     DB_HOST = "localhost"
     DB_NAME = "your_database_name"
     DB_USER = "your_username"
     DB_PASS = "your_password"
     ```

4. **Run the database setup script:**
   ```bash
   python setup_database.py
   ```

## Usage

1. **Start the Flask application:**
   ```bash
   python app.py
   ```

2. **Access the application:**
   - Open your web browser and go to `http://localhost:5000`
   - Navigate to the "Join" page to access the demo registration form

3. **Fill out the demo form:**
   - Full Name (required)
   - Business Name (required)
   - Business Type (required - select from dropdown)
   - Phone Number (optional)
   - Email Address (required - must be unique)
   - Password (required)

## Database Schema

The application uses a `demo` table with the following structure:

```sql
CREATE TABLE demo (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    business_name VARCHAR(150) NOT NULL,
    business_type VARCHAR(100) NOT NULL CHECK (business_type IN ('Retail Store', 'Restaurant/Cafe', 'Service Business', 'Healthcare', 'Real Estate', 'Other')),
    phone_number VARCHAR(20),
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## File Structure

```
├── app.py                 # Main Flask application
├── setup_database.py      # Database setup script
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── templates/
│   ├── base.html         # Base template
│   └── join.html         # Demo registration form
└── static/
    └── join.css          # CSS styles for the form
```

## Security Features

- Passwords are hashed using SHA-256 before storage
- Email addresses must be unique
- Form validation on both client and server side
- SQL injection protection using parameterized queries

## Troubleshooting

1. **Database connection issues:**
   - Verify PostgreSQL is running
   - Check database credentials in `app.py`
   - Ensure the database exists

2. **Import errors:**
   - Make sure all dependencies are installed: `pip install -r requirements.txt`

3. **Port already in use:**
   - Change the port in `app.py` or stop other applications using port 5000

## License

This project is for educational purposes. 