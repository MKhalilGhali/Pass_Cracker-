# Password Cracker API v2.0

Enhanced backend with async job processing, WebSocket support, and persistent storage.

## Features

✅ **Async Job Processing** - Uses Celery for background task execution
✅ **Real-time Updates** - WebSocket support via Socket.IO for live progress
✅ **Persistent Storage** - SQLite/PostgreSQL database for jobs and results
✅ **Robust Hash Handling** - Uses passlib for bcrypt and crypt variants
✅ **Job Queue Management** - Cancel, monitor, and track all cracking jobs
✅ **Multiple Wordlists** - Register and manage multiple wordlist files

## Installation

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Redis (Required for Celery)

**Windows:**
- Download Redis from: https://github.com/microsoftarchive/redis/releases
- Or use Docker: `docker run -d -p 6379:6379 redis`

**Linux/Mac:**
```bash
# Ubuntu/Debian
sudo apt-get install redis-server

# Mac
brew install redis
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

### 4. Initialize Database

```bash
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

## Running the Application

You need to run **3 processes**:

### Terminal 1: Redis Server
```bash
redis-server
```

### Terminal 2: Celery Worker
```bash
celery -A celery_app worker --loglevel=info --pool=solo
```

### Terminal 3: Flask API
```bash
python app.py
```

The API will be available at `http://localhost:5000`

## API Endpoints

### Job Management

- `POST /api/jobs` - Create new cracking job
- `GET /api/jobs` - List all jobs
- `GET /api/jobs/<job_id>` - Get job status
- `DELETE /api/jobs/<job_id>` - Cancel job

### Hash Operations

- `POST /api/detect-hash` - Auto-detect hash type
- `POST /api/generate-hash` - Generate hashes from password
- `POST /api/verify` - Verify password against hash

### Wordlists

- `GET /api/wordlists` - List available wordlists
- `POST /api/wordlists` - Register new wordlist

## WebSocket Events

Connect to `http://localhost:5000` with Socket.IO client:

```javascript
const socket = io('http://localhost:5000');

// Subscribe to job updates
socket.emit('subscribe_job', { job_id: 'your-job-id' });

// Listen for updates
socket.on('job_update', (data) => {
  console.log('Job progress:', data);
});
```

## Example Usage

### Create a Dictionary Attack Job

```bash
curl -X POST http://localhost:5000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "hash": "5f4dcc3b5aa765d61d8327deb882cf99",
    "hashType": "md5",
    "attackMode": "dictionary",
    "wordlist": "wordlist.txt",
    "autoDetect": true
  }'
```

### Check Job Status

```bash
curl http://localhost:5000/api/jobs/<job-id>
```

## Architecture

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   React     │◄────►│   Flask     │◄────►│   Celery    │
│  Frontend   │ HTTP │     API     │ Tasks│   Worker    │
│             │◄────►│             │      │             │
└─────────────┘ WS   └─────────────┘      └─────────────┘
                            │                     │
                            ▼                     ▼
                     ┌─────────────┐      ┌─────────────┐
                     │  SQLite/    │      │    Redis    │
                     │  Postgres   │      │   Broker    │
                     └─────────────┘      └─────────────┘
```

## Performance Notes

- Dictionary attacks: 10K-100K passwords/sec (Python)
- Brute force: 5K-50K attempts/sec (Python)
- For production use, consider integrating hashcat for GPU acceleration

## Security Warning

⚠️ **ETHICAL USE ONLY** - This tool is for educational purposes and authorized security testing only.

## Troubleshooting

**Celery won't start:**
- Ensure Redis is running: `redis-cli ping` should return `PONG`
- On Windows, use `--pool=solo` flag

**Database errors:**
- Delete `cracker.db` and reinitialize
- Check file permissions

**WebSocket connection fails:**
- Ensure eventlet is installed
- Check CORS settings in app.py
