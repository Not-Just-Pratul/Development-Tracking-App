# Development Tracking System

APQP (Advanced Product Quality Planning) project management system with automated workflows, department assignments, and role-based access control.

## 🚀 Portability Features

This application is **100% portable** and works on any computer:
- ✅ No hardcoded paths or absolute file references
- ✅ Uses relative paths automatically
- ✅ Works on Windows, Linux, and Mac
- ✅ Can be placed in any directory
- ✅ Configuration stored in simple config.ini file
- ✅ Database credentials configurable
- ✅ Upload folders created automatically

**Just copy the entire folder to any computer, configure database settings, and run!**

## Features

- **APQP Workflow**: 5 phases, 50 stages with automatic scheduling
- **Department Management**: Auto-assign stages to NPD, QA, and COST departments  
- **Multi-Organization**: Companies, locations, and departments hierarchy
- **Access Control**: Role-based permissions with audit logging
- **Real-time Tracking**: Project progress and status monitoring

## Quick Start

### Prerequisites

- PostgreSQL 12+ installed and running
- Python 3.7+ installed
- pip (Python package installer)

### Easy Setup (Recommended)

Use the automated setup script:

**Windows:**
```bash
setup.bat
```

**Linux/Mac:**
```bash
chmod +x setup.sh
./setup.sh
```

The setup script will:
- Check Python version
- Create config.ini from template
- Create upload directories
- Install Python packages (optional)
- Show database setup instructions

### Manual Installation Steps

1. **Download/Clone the project**
   - Extract or clone the project to any folder on your computer
   - Example: `C:\Projects\development_tracking` or `/home/user/development_tracking`

2. **Setup PostgreSQL Database**
   ```bash
   # Create the database (use your PostgreSQL username)
   createdb -U postgres development_tracking
   
   # Initialize the database schema
   psql -U postgres -d development_tracking -f init.pgsql
   ```
   
   **Note**: If you get a password prompt, enter your PostgreSQL password.

3. **Configure the application**
   ```bash
   # Copy the example config file
   cp config.ini.example config.ini
   
   # Edit config.ini with your settings
   # Windows: notepad config.ini
   # Linux/Mac: nano config.ini
   ```
   
   **Required changes in config.ini**:
   - Set `PASSWORD` to your PostgreSQL password
   - Change `SECRET_KEY` to a random string for security
   - Adjust `PORT` if 5003 is already in use

4. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   
   **Optional**: Use a virtual environment (recommended)
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate
   
   # Linux/Mac
   python3 -m venv venv
   source venv/bin/activate
   
   # Then install requirements
   pip install -r requirements.txt
   ```

5. **Run the server**
   ```bash
   python run_server.py
   ```

6. **Access the application**
   - Open browser: http://localhost:5003
   - Default login: `admin` / `admin123`
   - **Important**: Change admin password after first login!

## Configuration File

The `config.ini` file contains all settings. Edit it for your environment:

```ini
[DATABASE]
HOST = localhost          # Database host (localhost for same machine)
PORT = 5432              # PostgreSQL default port
DBNAME = development_tracking
USER = postgres          # Your PostgreSQL username
PASSWORD = your_password # Your PostgreSQL password

[FLASK]
SECRET_KEY = change_me   # MUST change for security!
DEBUG = False            # Set to True only for development
HOST = 0.0.0.0          # Listen on all network interfaces
PORT = 5003             # Web server port
```

## Important Files

- **config.ini.example** - Template configuration file (copy to config.ini)
- **config.ini** - Your actual configuration (not tracked in git)
- **init.pgsql** - Database schema and initial data
- **requirements.txt** - Python package dependencies
- **uploads/** - Directory for user file uploads (auto-created)

## Project Structure

```
├── run_server.py       # Application entry point
├── models.py           # Database models
├── api.py              # REST API endpoints
├── ui.py               # Web interface
├── auth.py             # Authentication
├── init.pgsql          # Database schema
├── config.ini          # Configuration (create from config.ini.example)
├── templates/          # HTML templates
└── static/             # CSS, JS, images
```

## Validation

Schema validation runs automatically on startup. To run manually:

```bash
python validate_schema.py
```

This ensures database schema matches SQLAlchemy models.

## Troubleshooting

### Database Connection Fails

1. **Check PostgreSQL is running**
   ```bash
   # Windows: Check Services or run
   pg_ctl status
   
   # Linux/Mac
   sudo systemctl status postgresql
   ```

2. **Verify database exists**
   ```bash
   psql -U postgres -l
   ```

3. **Test connection**
   ```bash
   psql -U postgres -d development_tracking
   ```

4. **Check config.ini settings**
   - Ensure HOST, PORT, USER, PASSWORD are correct
   - Default PostgreSQL port is 5432

### Schema Validation Errors

Run manual validation:
```bash
python validate_schema.py
```

If validation fails, reinitialize the database:
```bash
# Backup first if you have data!
dropdb -U postgres development_tracking
createdb -U postgres development_tracking
psql -U postgres -d development_tracking -f init.pgsql
```

### Port Already in Use

If port 5003 is occupied:
1. Edit `config.ini`
2. Change `PORT = 5003` to another port (e.g., 5004, 5005)
3. Restart the server

### File Upload Issues

Uploads folder is auto-created on first file upload. If issues persist:
```bash
# Ensure the app has write permissions
chmod 755 uploads/  # Linux/Mac only
```

## Moving to Another Computer

1. **Copy project folder** - Move entire project directory to new computer
2. **Install PostgreSQL** - Ensure PostgreSQL is installed on new machine
3. **Create database** - Run database creation commands from step 2 above
4. **Copy and edit config.ini** - Copy config.ini.example to config.ini and update credentials
5. **Install Python packages** - Run `pip install -r requirements.txt`
6. **Start server** - Run `python run_server.py`

**No hardcoded paths** - The application uses relative paths and works from any directory!

## Security Notes

- Change the default admin password immediately after first login
- Update `SECRET_KEY` in config.ini to a random string
- Use strong PostgreSQL passwords
- Enable SSL/HTTPS in production environments
- Keep config.ini private (it's in .gitignore)
````
python validate_schema.py
```

**Port in use**
```ini
# Change port in config.ini
PORT = 5004
```

## Security Checklist

- [ ] Change default admin password
- [ ] Set `DEBUG = False` in production
- [ ] Generate new `SECRET_KEY`
- [ ] Use strong database password
- [ ] Enable HTTPS/SSL
- [ ] Configure firewall

## License

Proprietary - MTPL Software Suite
