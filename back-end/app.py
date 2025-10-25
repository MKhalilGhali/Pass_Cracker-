from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, join_room, leave_room
import uuid
import os
from datetime import datetime

from config import Config
from models import db, CrackJob, Wordlist, JobStatus, AttackMode
from hash_utils import detect_hash_type, get_hash_info, hash_password, verify_password
from tasks import crack_dictionary_task, crack_bruteforce_task

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
CORS(app, resources={r"/api/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')
db.init_app(app)

# Create tables
with app.app_context():
    db.create_all()
    
    # Initialize default wordlist if exists
    if os.path.exists('wordlist.txt'):
        existing = Wordlist.query.filter_by(name='wordlist.txt').first()
        if not existing:
            with open('wordlist.txt', 'r', encoding='utf-8', errors='ignore') as f:
                size = sum(1 for line in f if line.strip())
            
            wordlist = Wordlist(
                name='wordlist.txt',
                file_path='wordlist.txt',
                size=size,
                description='Default wordlist'
            )
            db.session.add(wordlist)
            db.session.commit()

# ============================================
# WebSocket Events
# ============================================

@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    print(f'Client disconnected: {request.sid}')

@socketio.on('subscribe_job')
def handle_subscribe(data):
    job_id = data.get('job_id')
    if job_id:
        join_room(job_id)
        print(f'Client {request.sid} subscribed to job {job_id}')

@socketio.on('unsubscribe_job')
def handle_unsubscribe(data):
    job_id = data.get('job_id')
    if job_id:
        leave_room(job_id)
        print(f'Client {request.sid} unsubscribed from job {job_id}')

# ============================================
# API Endpoints
# ============================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'message': 'Password Cracker API v2.0 is running',
        'features': ['async_jobs', 'websockets', 'database', 'celery']
    })

@app.route('/api/detect-hash', methods=['POST'])
def detect_hash():
    """Auto-detect hash type from hash string"""
    data = request.json
    hash_string = data.get('hash', '')
    
    if not hash_string:
        return jsonify({'error': 'Hash is required'}), 400
    
    hash_type, confidence, description = detect_hash_type(hash_string)
    hash_info = get_hash_info(hash_type)
    
    return jsonify({
        'detected_type': hash_type,
        'confidence': confidence,
        'description': description,
        'info': hash_info,
        'hash_length': len(hash_string.strip())
    })

@app.route('/api/jobs', methods=['POST'])
def create_job():
    """Create a new cracking job"""
    data = request.json
    
    target_hash = data.get('hash', '').strip()
    hash_type = data.get('hashType', 'md5')
    attack_mode = data.get('attackMode', 'dictionary')
    wordlist_name = data.get('wordlist', 'wordlist.txt')
    max_length = data.get('maxLength', 4)
    charset_option = data.get('charset', '1')
    
    if not target_hash:
        return jsonify({'error': 'Hash is required'}), 400
    
    # Auto-detect if requested
    if data.get('autoDetect', False):
        detected_type, _, _ = detect_hash_type(target_hash)
        if detected_type != 'unknown':
            hash_type = detected_type
    
    # Create job record
    job_id = str(uuid.uuid4())
    
    try:
        attack_mode_enum = AttackMode[attack_mode.upper()]
    except KeyError:
        attack_mode_enum = AttackMode.DICTIONARY
    
    job = CrackJob(
        job_id=job_id,
        target_hash=target_hash,
        hash_type=hash_type,
        attack_mode=attack_mode_enum,
        wordlist_name=wordlist_name if attack_mode_enum == AttackMode.DICTIONARY else None,
        max_length=max_length if attack_mode_enum == AttackMode.BRUTEFORCE else None,
        charset_option=charset_option if attack_mode_enum == AttackMode.BRUTEFORCE else None,
        status=JobStatus.PENDING
    )
    
    db.session.add(job)
    db.session.commit()
    
    # Start async task
    if attack_mode_enum == AttackMode.DICTIONARY:
        crack_dictionary_task.apply_async(
            args=[job_id, target_hash, hash_type, wordlist_name],
            task_id=job_id
        )
    elif attack_mode_enum == AttackMode.BRUTEFORCE:
        crack_bruteforce_task.apply_async(
            args=[job_id, target_hash, hash_type, max_length, charset_option],
            task_id=job_id
        )
    
    return jsonify({
        'job_id': job_id,
        'status': 'Job created and queued',
        'job': job.to_dict()
    }), 201

@app.route('/api/jobs/<job_id>', methods=['GET'])
def get_job(job_id):
    """Get job status and results"""
    job = CrackJob.query.filter_by(job_id=job_id).first()
    
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify(job.to_dict())

@app.route('/api/jobs', methods=['GET'])
def list_jobs():
    """List all jobs with optional filtering"""
    status = request.args.get('status')
    limit = request.args.get('limit', 50, type=int)
    
    query = CrackJob.query
    
    if status:
        try:
            status_enum = JobStatus[status.upper()]
            query = query.filter_by(status=status_enum)
        except KeyError:
            pass
    
    jobs = query.order_by(CrackJob.created_at.desc()).limit(limit).all()
    
    return jsonify({
        'jobs': [job.to_dict() for job in jobs],
        'count': len(jobs)
    })

@app.route('/api/jobs/<job_id>', methods=['DELETE'])
def cancel_job(job_id):
    """Cancel a running job"""
    job = CrackJob.query.filter_by(job_id=job_id).first()
    
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
        return jsonify({'error': 'Job already finished'}), 400
    
    # Revoke Celery task
    from celery_app import celery
    celery.control.revoke(job_id, terminate=True)
    
    # Update job status
    job.status = JobStatus.CANCELLED
    job.completed_at = datetime.utcnow()
    db.session.commit()
    
    # Notify via WebSocket
    socketio.emit('job_update', job.to_dict(), room=job_id)
    
    return jsonify({'message': 'Job cancelled', 'job': job.to_dict()})

@app.route('/api/wordlists', methods=['GET'])
def list_wordlists():
    """List available wordlists"""
    wordlists = Wordlist.query.all()
    return jsonify({
        'wordlists': [wl.to_dict() for wl in wordlists]
    })

@app.route('/api/wordlists', methods=['POST'])
def add_wordlist():
    """Register a new wordlist"""
    data = request.json
    
    name = data.get('name')
    file_path = data.get('file_path')
    description = data.get('description', '')
    
    if not name or not file_path:
        return jsonify({'error': 'Name and file_path are required'}), 400
    
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    # Count lines
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            size = sum(1 for line in f if line.strip())
    except:
        return jsonify({'error': 'Could not read file'}), 400
    
    # Check if already exists
    existing = Wordlist.query.filter_by(name=name).first()
    if existing:
        return jsonify({'error': 'Wordlist with this name already exists'}), 409
    
    wordlist = Wordlist(
        name=name,
        file_path=file_path,
        size=size,
        description=description
    )
    
    db.session.add(wordlist)
    db.session.commit()
    
    return jsonify(wordlist.to_dict()), 201

@app.route('/api/generate-hash', methods=['POST'])
def generate_hash():
    """Generate hashes from a password"""
    data = request.json
    password = data.get('password', '')
    
    if not password:
        return jsonify({'error': 'Password is required'}), 400
    
    hashes = {
        'md5': hash_password(password, 'md5'),
        'sha1': hash_password(password, 'sha1'),
        'sha256': hash_password(password, 'sha256'),
        'sha512': hash_password(password, 'sha512'),
        'ntlm': hash_password(password, 'ntlm')
    }
    
    return jsonify({'password': password, 'hashes': hashes})

@app.route('/api/verify', methods=['POST'])
def verify():
    """Verify a password against a hash"""
    data = request.json
    
    password = data.get('password', '')
    hash_string = data.get('hash', '')
    hash_type = data.get('hashType', 'md5')
    
    if not password or not hash_string:
        return jsonify({'error': 'Password and hash are required'}), 400
    
    matches = verify_password(password, hash_string, hash_type)
    
    return jsonify({
        'matches': matches,
        'password': password,
        'hash': hash_string,
        'hash_type': hash_type
    })

# ============================================
# Run Server
# ============================================

if __name__ == '__main__':
    print("🚀 Starting Password Cracker API v2.0...")
    print("📡 Server running on http://localhost:5000")
    print("🔌 WebSocket support enabled")
    print("⚡ Celery workers required for job processing")
    print("⚠️  ETHICAL USE ONLY - Educational purposes")
    print("\nTo start Celery worker:")
    print("  celery -A celery_app worker --loglevel=info --pool=solo")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
