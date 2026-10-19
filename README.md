# SwapShelf

SwapShelf is a campus marketplace web application built with Django, Django Templates, and SQLite. Students post textbooks, chargers, dorm leftovers, and bikes. Buyers can browse, filter by category, and message sellers through private threads. Sellers can manage, edit, mark items as sold, or remove listings.

---

## Features

- **Authentication**: User registration, login, and logout.
- **Public Marketplace Board**: Browse active campus listings with category filters (Books, Electronics, Furniture, Bikes, Other).
- **Listing Management**: Post new listings, edit own listings, mark own listings as sold, or remove listings.
- **Private Messaging**: Direct buyer-seller message threads scoped to specific listings.
- **User Profile**: View and update profile details (first name, last name, email) safely without privilege escalation risks.
- **Department Desk**: Restricted portal for staff accounts (`is_staff=True`) containing department-specific instructions.
- **Responsive Styling**: Polished typography and layout via scoped static CSS (`market/static/market/style.css`).

---

## Local Setup (Windows)

### Prerequisites
- Windows 10/11
- Python 3.11 or 3.12 installed and added to `PATH`
- PowerShell or Command Prompt

### Step 1: Clone or Navigate to the Project Directory
```powershell
cd c:\Users\vijay\Desktop\SwapShelf
```

### Step 2: Set Up Python Virtual Environment
Using the existing `.venv312` or creating a new virtual environment:

**PowerShell:**
```powershell
# If using the existing .venv312 virtual environment:
.\.venv312\Scripts\Activate.ps1

# Or to create and activate a new virtual environment:
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

*Note for PowerShell:* If execution policies restrict script activation, run:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
```

**Command Prompt (cmd.exe):**
```cmd
.\.venv312\Scripts\activate.bat
```

### Step 3: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Run Database Migrations
```powershell
python manage.py migrate
```
*(The initial demo dataset seeds automatically upon migration).*

### Step 5: Run Automated Tests
```powershell
python manage.py test
```
All 14 automated unit and security tests should pass (`OK`).

### Step 6: Start the Development Server
```powershell
python manage.py runserver 0.0.0.0:3000
```
Open your web browser and visit: **[http://localhost:3000](http://localhost:3000)**

---

## Running with Docker

You can also run SwapShelf using Docker and Docker Compose:

```powershell
docker compose up --build
```
The application will be accessible at `http://localhost:3000`. Database data persists in the `swapshelf-data` volume.

---

## Demo Accounts

Sign in using the username (not the email address):

| Username | Password | Role / Details |
|---|---|---|
| `alex` | `campus123` | Active seller (USB-C charger, Campus bike) |
| `jordan` | `campus123` | Active student seller/buyer (CPEG 470 textbook) |
| `sam` | `foundit!` | Seller with sold item (Desk lamp) |

*To create an administrative / staff account for the Department Desk:*
```powershell
python manage.py createsuperuser
```

---

## Project Structure

```
SwapShelf/
├── market/
│   ├── apps.py            # App configuration and conditional seeding signal
│   ├── forms.py           # ListingForm and secured ProfileForm
│   ├── models.py          # Listing, Thread, Message data models
│   ├── seed.py            # Initial demo seed data
│   ├── static/
│   │   └── market/
│   │       └── style.css  # Application styles and responsive theme
│   ├── templates/
│   │   └── market/        # Base layout and feature templates
│   ├── tests.py           # Unit, authorization, and functional tests (14 tests)
│   ├── urls.py            # Marketplace routes
│   └── views.py           # Marketplace views and object-level authorization
├── swapshelf/
│   ├── settings.py        # Django configuration (DEBUG, STATIC, Database)
│   ├── urls.py            # Root URL configuration with staticfiles routing
│   └── wsgi.py            # WSGI application entrypoint
├── data/
│   └── swapshelf.db       # SQLite database file
├── Dockerfile             # Container definition
├── docker-compose.yml     # Multi-container orchestration
├── requirements.txt       # Python dependencies
├── SECURITY-REPORT.md     # Vulnerability analysis, patch documentation, and test audit
└── README.md              # Project documentation and setup guide
```

---

## Testing & Quality Assurance

Run the test suite at any time using:
```powershell
python manage.py test
```
Verify system configuration:
```powershell
python manage.py check
```
Test static asset discovery:
```powershell
python manage.py findstatic market/style.css
```
