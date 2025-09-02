This was writen by AI. -The person with the AI

# RackNerd VPS Monitor

A Flask-based API service that monitors RackNerd VPS resources through the SolusVM API. This service provides real-time information about your VPS including disk usage, bandwidth consumption, and memory utilization.

## Features

- Real-time VPS resource monitoring
- Caching system to prevent API abuse (60-second cache duration)
- Docker support for easy deployment
- Resource metrics conversion (bytes to GB/TB)
- Environment variable support for configuration
- Thread-safe caching mechanism

## Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose (for containerized deployment)
- RackNerd VPS API credentials

## Configuration

### API Credentials

Create a `tokens.txt` file with your RackNerd API credentials:
```
your_api_key
your_hash_value
```

### Settings

Create a `settings.txt` file with the following format:
```
True    # Enable/disable continuous monitoring
5       # Sleep duration in minutes between checks
```

You can also use environment variables:
- `RACKNERD_KEY`: Your RackNerd API key
- `RACKNERD_HASH`: Your RackNerd API hash

## Installation

### Docker Installation (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/ClanCarney/automatic-barnacle.git
   cd automatic-barnacle
   ```

2. Configure your credentials in `tokens.txt` and settings in `settings.txt`

3. Build and run with Docker Compose:
   ```bash
   docker-compose up -d
   ```

### Manual Installation

1. Clone the repository and install dependencies:
   ```bash
   git clone https://github.com/ClanCarney/automatic-barnacle.git
   cd automatic-barnacle
   pip install -r requirements.txt
   ```

2. Configure your credentials and settings

3. Run the application:
   ```bash
   python src/main.py
   ```

## API Endpoints

The service exposes metrics about your VPS including:
- Disk usage (HDD)
- Bandwidth consumption
- Memory utilization
- Hostname
- IP address

Data is cached for 60 seconds to prevent excessive API requests.

## Security

- Runs as a non-root user in Docker
- Configuration files are mounted as read-only in Docker
- Uses HTTPS for API communication
- Implements proper error handling and input validation

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[Add your chosen license here]