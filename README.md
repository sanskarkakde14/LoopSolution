# Store Uptime Monitoring System

A Django-based system for monitoring store uptime and generating reports. This application processes store status data, business hours, and timezone information to calculate store uptime metrics.

## Features

- Store status monitoring and tracking
- Business hours management
- Timezone-aware calculations
- Report generation
- RESTful API endpoints
- Docker containerization
- PostgreSQL database integration

## Prerequisites

- Python 3.9+
- Docker and Docker Compose
- PostgreSQL (if running locally)

## Project Structure

```
LoopSolution/
├── core/                 # Django project settings
├── uptime_monitor/       # Main application
│   ├── models.py        # Database models
│   ├── services.py      # Business logic
│   ├── views.py         # API endpoints
│   └── management/      # Custom management commands
├── store-monitoring-data/# Data files (not tracked in git)
├── media/               # Generated reports
└── docker-compose.yml   # Docker configuration
```

## Data Files

The following data files are required but not included in the repository due to size limitations:

1. `store-monitoring-data/store_status.csv` (134MB)
2. `store-monitoring-data/menu_hours.csv` (1.9MB)
3. `store-monitoring-data/timezones.csv` (238KB)

You can obtain these files from the project maintainer or generate them according to the following schema:

### store_status.csv
```csv
store_id,timestamp_utc,status
```

### menu_hours.csv
```csv
store_id,dayOfWeek,start_time_local,end_time_local
```

### timezones.csv
```csv
store_id,timezone_str
```

## API Endpoints

### Trigger Report Generation
```http
POST /api/trigger_report/
```

### Get Report Status
```http
GET /api/get_report/{report_id}/
```

## Development Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up the database:
   ```bash
   python manage.py migrate
   ```

4. Load the data:
   ```bash
   python manage.py load_csv_data store-monitoring-data
   ```

5. Run the development server:
   ```bash
   python manage.py runserver
   ```

## Database Schema

### Store
- `store_id`: Unique identifier for the store
- `timezone_str`: Store's timezone

### BusinessHours
- `store`: Foreign key to Store
- `day_of_week`: Day of the week (0-6)
- `start_time_local`: Business hours start time
- `end_time_local`: Business hours end time

### StoreStatus
- `store`: Foreign key to Store
- `timestamp_utc`: Status timestamp in UTC
- `status`: Store status (active/inactive)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contact

For any queries or support, please contact the project maintainer.
