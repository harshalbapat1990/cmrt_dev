# Austroads CMRT API

A FastAPI-based REST API for managing Carbon Measurement and Reporting Tool (CMRT) data for Austroads. This application provides endpoints for managing emissions entries, emission factors, and associated lookup data.

## Features

- **Emissions Management**: Create, read, update, and delete emissions entries
- **Lookup Data**: Access standardized lookup tables for emissions categories, sub-categories, sources, measurement units, and emission factors
- **Async Support**: Built with async/await for high performance
- **PostgreSQL Database**: Uses SQLAlchemy ORM with async support
- **CORS Enabled**: Configured for local development with Vite frontend
- **Type Safety**: Full Pydantic schema validation

## Project Structure

```
.
├── app/
│   ├── main.py                 # FastAPI app initialization and middleware setup
│   └── __init__.py
├── core/
│   ├── config.py               # Configuration and settings management
│   ├── session.py              # Database session management
│   ├── base.py                 # Base models and utilities
│   └── __init__.py
├── crud/
│   ├── emissions_entries.py    # CRUD operations for emissions data
│   └── __init__.py
├── models/
│   ├── emissions_entries.py    # SQLAlchemy ORM models for emissions
│   ├── lookup_data.py          # SQLAlchemy ORM models for lookup tables
│   └── __init__.py
├── routers/
│   ├── emissions_entries.py    # API endpoints for emissions entries and summaries
│   ├── lookup_data.py          # API endpoints for lookup data
│   └── __init__.py
├── schemas/
│   ├── emissions_entries.py    # Pydantic schemas for emissions data
│   ├── lookup_data.py          # Pydantic schemas for lookup data
│   └── __init__.py
├── requirements.txt
└── README.md
```

## Installation

### Prerequisites

- Python 3.9 or higher
- PostgreSQL database
- pip or conda

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Austroads_CMRT_Api
   ```

2. **Create a virtual environment** (optional but recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   
   Create a `.env` file in the project root with the following variables:
   ```
   APP_NAME=Austroads CMRT API
   APP_ENV=development
   DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/cmrt_db
   ```

## Running the Application

### Development Server

Start the application with uvicorn:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### Interactive API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Emissions Entries

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/emission_entries/emission-entries` | Create a new emissions entry |
| GET | `/emission_entries/emission-entries` | List all emissions entries (with filtering) |
| GET | `/emission_entries/emission-entries/{emission_entry_id}` | Get a specific emissions entry |
| PATCH | `/emission_entries/emission-entries/{emission_entry_id}` | Update an emissions entry |
| DELETE | `/emission_entries/emission-entries/{emission_entry_id}` | Delete an emissions entry |
| POST | `/emission_entries/emission-entry-summaries` | Create an emissions summary |
| GET | `/emission_entries/emission-entry-summaries` | List emissions summaries |
| GET | `/emission_entries/emission-entry-summaries/{summary_id}` | Get a specific summary |
| PATCH | `/emission_entries/emission-entry-summaries/{summary_id}` | Update a summary |
| DELETE | `/emission_entries/emission-entry-summaries/{summary_id}` | Delete a summary |

**Query Parameters for Emissions Entries:**
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum records to return (default: 50)
- `project_id`: Filter by project ID
- `project_reporting_submission_id`: Filter by submission ID
- `emission_source_id`: Filter by emission source
- `emissions_sub_category_id`: Filter by sub-category

### Lookup Data

| Endpoint | Description |
|----------|-------------|
| `/api/lookup/emissions-categories` | Get emissions categories |
| `/api/lookup/emissions-subcategories` | Get emissions sub-categories |
| `/api/lookup/measurement-units` | Get measurement units |
| `/api/lookup/emission-sources` | Get emission sources |
| `/api/lookup/emission-factors` | Get emission factors |
| `/api/lookup/emission-factor-values` | Get emission factor values |

**Common Query Parameters:**
- `is_active`: Filter by active status (boolean)
- `q`: Search by name (case-insensitive contains)
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum records to return (default: 100)

## Dependencies

- **fastapi**: Web framework
- **uvicorn**: ASGI server
- **sqlalchemy**: ORM and database toolkit
- **asyncpg**: Async PostgreSQL driver
- **pydantic**: Data validation
- **pydantic-settings**: Configuration management
- **python-dotenv**: Environment variable loading

See `requirements.txt` for exact versions.

## Database Configuration

The application uses SQLAlchemy with async PostgreSQL driver. Configuration is managed through `core/config.py` using Pydantic settings, which reads from environment variables and `.env` file.

## Development

### Running Tests

Tests can be added to the project. To run tests:
```bash
pytest
```

### Code Style

Ensure consistent code formatting with black or similar tools:
```bash
black .
```

## CORS Configuration

Currently configured to allow requests from the local Vite dev server (`http://localhost:5173`). Update `app/main.py` to modify allowed origins for production environments.

## License

[Add your license information here]

## Support

For issues or questions, please contact the development team or open an issue in the repository.

## Log in to the Web App (Browser UI)
The backend authenticates browser requests via an access_token cookie. You can log in directly from your browser:

Start both servers:
Backend: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 (in backend)
Frontend: npm run dev (in client)
Open your browser to http://localhost:5173.
Open DevTools Console (<kbd>F12</kbd> or <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>I</kbd> → Console tab) and paste:
await fetch('/api/auth/dev/token', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',
  body: JSON.stringify({ email: '<user_email_id>' })
});
location.reload();

for the api 
run the backend server as described above.
in separate terminal run
python -m tools.dev.mint_token --email <user_email_id>
you will be given a token that you can pass in the headers