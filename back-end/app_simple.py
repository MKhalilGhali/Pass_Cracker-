"""
Simplified version without Celery/Redis - runs jobs synchronously
Use this for quick testing without setting up Redis
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
import uuid
import os
import time
import string
import itertools
from datetime import datetime, timezone

from config import Config
from models import db, CrackJob, Wordlist, JobStatus, AttackMode
from hash_utils import detect_hash_type, get_hash_info, hash_password, verify_password

def utcnow():
    """Helper to get current UTC time without deprecation warning"""
    return datetime.now(timezone.utc).replace(tzinfo=None)

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cracker_simple.db'

# Initialize extensions
CORS(app, resources={r"/api/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
db.init_app(app)

# Create tables
with app.app_context():
    db.create_all()
    
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

def load_wordlist(filename):
    if not os.path.exists(filename):
        return []
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            return [line.strip() for line in f if line.strip()]
    except:
        return []

def crack_dictionary_sync(job_id, target_hash, hash_type, wordlist_path):
    """Synchronous dictionary attack"""
    with app.app_context():
        job = CrackJob.query.filter_by(job_id=job_id).first()
        job.status = JobStatus.RUNNING
        job.started_at = utcnow()
        db.session.commit()
        
        wordlist = load_wordlist(wordlist_path)
        if not wordlist:
            job.status = JobStatus.FAILED
            job.error_message = 'Wordlist not found'
            db.session.commit()
            return
        
        total = len(wordlist)
        job.total_attempts = total
        db.session.commit()
        
        start_time = time.time()
        
        for i, password in enumerate(wordlist):
            if verify_password(password, target_hash, hash_type):
                elapsed = time.time() - start_time
                job.status = JobStatus.COMPLETED
                job.success = True
                job.cracked_password = password
                job.current_attempt = i + 1
                job.time_elapsed = elapsed
                job.speed = (i + 1) / elapsed if elapsed > 0 else 0
                job.progress = 100.0
                job.completed_at = utcnow()
                db.session.commit()
                socketio.emit('job_update', job.to_dict(), room=job_id)
                return
            
            if (i + 1) % 1000 == 0:
                elapsed = time.time() - start_time
                job.current_attempt = i + 1
                job.progress = ((i + 1) / total) * 100
                job.time_elapsed = elapsed
                job.speed = (i + 1) / elapsed if elapsed > 0 else 0
                db.session.commit()
                socketio.emit('job_update', job.to_dict(), room=job_id)
        
        elapsed = time.time() - start_time
        job.status = JobStatus.COMPLETED
        job.success = False
        job.current_attempt = total
        job.time_elapsed = elapsed
        job.speed = total / elapsed if elapsed > 0 else 0
        job.progress = 100.0
        job.completed_at = utcnow()
        db.session.commit()
        socketio.emit('job_update', job.to_dict(), room=job_id)

def crack_bruteforce_sync(job_id, target_hash, hash_type, max_length, charset_option):
    """Synchronous brute force attack"""
    with app.app_context():
        job = CrackJob.query.filter_by(job_id=job_id).first()
        job.status = JobStatus.RUNNING
        job.started_at = utcnow()
        db.session.commit()
        
        charsets = {
            '1': string.ascii_lowercase + string.digits,
            '2': string.ascii_lowercase,
            '3': string.ascii_lowercase + string.ascii_uppercase + string.digits,
            '4': string.ascii_letters + string.digits + string.punctuation
        }
        
        charset = charsets.get(charset_option, string.ascii_lowercase + string.digits)
        total = sum(len(charset) ** length for length in range(1, max_length + 1))
        job.total_attempts = min(total, Config.MAX_ATTEMPTS_PER_JOB)
        db.session.commit()
        
        start_time = time.time()
        attempts = 0
        
        for length in range(1, max_length + 1):
            for combo in itertools.product(charset, repeat=length):
                attempts += 1
                password = ''.join(combo)
                
                if verify_password(password, target_hash, hash_type):
                    elapsed = time.time() - start_time
                    job.status = JobStatus.COMPLETED
                    job.success = True
                    job.cracked_password = password
                    job.current_attempt = attempts
                    job.time_elapsed = elapsed
                    job.speed = attempts / elapsed if elapsed > 0 else 0
                    job.progress = 100.0
                    job.completed_at = utcnow()
                    db.session.commit()
                    socketio.emit('job_update', job.to_dict(), room=job_id)
                    return
                
                if attempts >= Config.MAX_ATTEMPTS_PER_JOB:
                    elapsed = time.time() - start_time
                    job.status = JobStatus.COMPLETED
                    job.success = False
                    job.current_attempt = attempts
                    job.time_elapsed = elapsed
                    job.speed = attempts / elapsed if elapsed > 0 else 0
                    job.progress = 100.0
                    job.error_message = f'Exceeded max attempts'
                    job.completed_at = utcnow()
                    db.session.commit()
                    socketio.emit('job_update', job.to_dict(), room=job_id)
                    return
                
                if attempts % 5000 == 0:
                    elapsed = time.time() - start_time
                    job.current_attempt = attempts
                    job.progress = min((attempts / total) * 100, 99.9)
                    job.time_elapsed = elapsed
                    job.speed = attempts / elapsed if elapsed > 0 else 0
                    db.session.commit()
                    socketio.emit('job_update', job.to_dict(), room=job_id)
        
        elapsed = time.time() - start_time
        job.status = JobStatus.COMPLETED
        job.success = False
        job.current_attempt = attempts
        job.time_elapsed = elapsed
        job.speed = attempts / elapsed if elapsed > 0 else 0
        job.progress = 100.0
        job.completed_at = utcnow()
        db.session.commit()
        socketio.emit('job_update', job.to_dict(), room=job_id)

# ============================================
# API Endpoints
# ============================================

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'message': 'Password Cracker API v2.0 (Simple Mode)',
        'mode': 'synchronous'
    })

@app.route('/api/detect-hash', methods=['POST'])
def detect_hash():
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
    data = request.json
    
    target_hash = data.get('hash', '').strip()
    hash_type = data.get('hashType', 'md5')
    attack_mode = data.get('attackMode', 'dictionary')
    wordlist_name = data.get('wordlist', 'wordlist.txt')
    max_length = data.get('maxLength', 4)
    charset_option = data.get('charset', '1')
    
    if not target_hash:
        return jsonify({'error': 'Hash is required'}), 400
    
    if data.get('autoDetect', False):
        detected_type, _, _ = detect_hash_type(target_hash)
        if detected_type != 'unknown':
            hash_type = detected_type
    
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
    
    # Run synchronously in background thread
    if attack_mode_enum == AttackMode.DICTIONARY:
        socketio.start_background_task(crack_dictionary_sync, job_id, target_hash, hash_type, wordlist_name)
    elif attack_mode_enum == AttackMode.BRUTEFORCE:
        socketio.start_background_task(crack_bruteforce_sync, job_id, target_hash, hash_type, max_length, charset_option)
    
    return jsonify({
        'job_id': job_id,
        'status': 'Job created',
        'job': job.to_dict()
    }), 201

@app.route('/api/jobs/<job_id>', methods=['GET'])
def get_job(job_id):
    job = CrackJob.query.filter_by(job_id=job_id).first()
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(job.to_dict())

@app.route('/api/jobs/<job_id>', methods=['DELETE'])
def cancel_job(job_id):
    job = CrackJob.query.filter_by(job_id=job_id).first()
    
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    
    if job.status in [JobStatus.COMPLETED, JobStatus.FAILED]:
        return jsonify({'error': 'Job already finished'}), 400
    
    # Mark as cancelled (simple mode can't actually stop the thread)
    job.status = JobStatus.FAILED
    job.error_message = 'Cancelled by user'
    job.completed_at = utcnow()
    db.session.commit()
    
    socketio.emit('job_update', job.to_dict(), room=job_id)
    
    return jsonify({'message': 'Job marked as cancelled', 'job': job.to_dict()})

@app.route('/api/jobs', methods=['GET'])
def list_jobs():
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

@app.route('/api/wordlists', methods=['GET'])
def list_wordlists():
    wordlists = Wordlist.query.all()
    return jsonify({'wordlists': [wl.to_dict() for wl in wordlists]})

@app.route('/api/generate-hash', methods=['POST'])
def generate_hash():
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

if __name__ == '__main__':
    print("🚀 Starting Password Cracker API v2.0 (Simple Mode)")
    print("📡 Server running on http://localhost:5000")
    print("🔌 WebSocket support enabled")
    print("⚡ Running in synchronous mode (no Redis/Celery required)")
    print("⚠️  ETHICAL USE ONLY - Educational purposes")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
