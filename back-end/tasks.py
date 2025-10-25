import time
import string
import itertools
import os
from datetime import datetime
from celery_app import celery
from hash_utils import verify_password, hash_password
from config import Config

def load_wordlist(filename):
    """Load passwords from text file"""
    if not os.path.exists(filename):
        return []
    
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            return [line.strip() for line in f if line.strip()]
    except:
        return []

@celery.task(bind=True, name='tasks.crack_dictionary')
def crack_dictionary_task(self, job_id, target_hash, hash_type, wordlist_path):
    """Dictionary attack task with progress updates"""
    from app import socketio, db
    from models import CrackJob, JobStatus
    
    # Update job status
    job = CrackJob.query.filter_by(job_id=job_id).first()
    if not job:
        return {'error': 'Job not found'}
    
    job.status = JobStatus.RUNNING
    job.started_at = datetime.utcnow()
    db.session.commit()
    
    # Load wordlist
    wordlist = load_wordlist(wordlist_path)
    if not wordlist:
        job.status = JobStatus.FAILED
        job.error_message = 'Wordlist not found or empty'
        db.session.commit()
        return {'error': 'Wordlist not found'}
    
    total = len(wordlist)
    job.total_attempts = total
    db.session.commit()
    
    start_time = time.time()
    attempts = 0
    
    try:
        for i, password in enumerate(wordlist):
            attempts += 1
            
            # Check if password matches
            if verify_password(password, target_hash, hash_type):
                elapsed = time.time() - start_time
                
                # Update job with success
                job.status = JobStatus.COMPLETED
                job.success = True
                job.cracked_password = password
                job.current_attempt = attempts
                job.time_elapsed = elapsed
                job.speed = attempts / elapsed if elapsed > 0 else 0
                job.progress = 100.0
                job.completed_at = datetime.utcnow()
                db.session.commit()
                
                # Emit success via WebSocket
                socketio.emit('job_update', job.to_dict(), room=job_id)
                
                return {
                    'success': True,
                    'password': password,
                    'attempts': attempts,
                    'time': elapsed,
                    'speed': attempts / elapsed if elapsed > 0 else 0
                }
            
            # Update progress every 1000 attempts
            if attempts % 1000 == 0:
                elapsed = time.time() - start_time
                progress = (i / total) * 100
                
                job.current_attempt = attempts
                job.progress = progress
                job.time_elapsed = elapsed
                job.speed = attempts / elapsed if elapsed > 0 else 0
                db.session.commit()
                
                # Emit progress via WebSocket
                socketio.emit('job_update', job.to_dict(), room=job_id)
                
                # Update Celery task state
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'current': attempts,
                        'total': total,
                        'progress': progress
                    }
                )
        
        # Password not found
        elapsed = time.time() - start_time
        job.status = JobStatus.COMPLETED
        job.success = False
        job.current_attempt = attempts
        job.time_elapsed = elapsed
        job.speed = attempts / elapsed if elapsed > 0 else 0
        job.progress = 100.0
        job.completed_at = datetime.utcnow()
        db.session.commit()
        
        socketio.emit('job_update', job.to_dict(), room=job_id)
        
        return {
            'success': False,
            'password': None,
            'attempts': attempts,
            'time': elapsed,
            'speed': attempts / elapsed if elapsed > 0 else 0
        }
        
    except Exception as e:
        job.status = JobStatus.FAILED
        job.error_message = str(e)
        job.completed_at = datetime.utcnow()
        db.session.commit()
        
        socketio.emit('job_update', job.to_dict(), room=job_id)
        
        return {'error': str(e)}

@celery.task(bind=True, name='tasks.crack_bruteforce')
def crack_bruteforce_task(self, job_id, target_hash, hash_type, max_length, charset_option):
    """Brute force attack task with progress updates"""
    from app import socketio, db
    from models import CrackJob, JobStatus
    
    # Update job status
    job = CrackJob.query.filter_by(job_id=job_id).first()
    if not job:
        return {'error': 'Job not found'}
    
    job.status = JobStatus.RUNNING
    job.started_at = datetime.utcnow()
    db.session.commit()
    
    # Define charsets
    charsets = {
        '1': string.ascii_lowercase + string.digits,
        '2': string.ascii_lowercase,
        '3': string.ascii_lowercase + string.ascii_uppercase + string.digits,
        '4': string.ascii_letters + string.digits + string.punctuation
    }
    
    charset = charsets.get(charset_option, string.ascii_lowercase + string.digits)
    
    # Calculate total combinations
    total = sum(len(charset) ** length for length in range(1, max_length + 1))
    job.total_attempts = min(total, Config.MAX_ATTEMPTS_PER_JOB)
    db.session.commit()
    
    start_time = time.time()
    attempts = 0
    
    try:
        for length in range(1, max_length + 1):
            for combo in itertools.product(charset, repeat=length):
                attempts += 1
                password = ''.join(combo)
                
                # Check if password matches
                if verify_password(password, target_hash, hash_type):
                    elapsed = time.time() - start_time
                    
                    # Update job with success
                    job.status = JobStatus.COMPLETED
                    job.success = True
                    job.cracked_password = password
                    job.current_attempt = attempts
                    job.time_elapsed = elapsed
                    job.speed = attempts / elapsed if elapsed > 0 else 0
                    job.progress = 100.0
                    job.completed_at = datetime.utcnow()
                    db.session.commit()
                    
                    socketio.emit('job_update', job.to_dict(), room=job_id)
                    
                    return {
                        'success': True,
                        'password': password,
                        'attempts': attempts,
                        'time': elapsed,
                        'speed': attempts / elapsed if elapsed > 0 else 0
                    }
                
                # Limit attempts
                if attempts >= Config.MAX_ATTEMPTS_PER_JOB:
                    elapsed = time.time() - start_time
                    
                    job.status = JobStatus.COMPLETED
                    job.success = False
                    job.current_attempt = attempts
                    job.time_elapsed = elapsed
                    job.speed = attempts / elapsed if elapsed > 0 else 0
                    job.progress = 100.0
                    job.error_message = f'Exceeded maximum attempts ({Config.MAX_ATTEMPTS_PER_JOB})'
                    job.completed_at = datetime.utcnow()
                    db.session.commit()
                    
                    socketio.emit('job_update', job.to_dict(), room=job_id)
                    
                    return {
                        'success': False,
                        'password': None,
                        'attempts': attempts,
                        'time': elapsed,
                        'speed': attempts / elapsed if elapsed > 0 else 0,
                        'message': f'Exceeded maximum attempts ({Config.MAX_ATTEMPTS_PER_JOB})'
                    }
                
                # Update progress every 5000 attempts
                if attempts % 5000 == 0:
                    elapsed = time.time() - start_time
                    progress = min((attempts / total) * 100, 99.9)
                    
                    job.current_attempt = attempts
                    job.progress = progress
                    job.time_elapsed = elapsed
                    job.speed = attempts / elapsed if elapsed > 0 else 0
                    db.session.commit()
                    
                    socketio.emit('job_update', job.to_dict(), room=job_id)
                    
                    self.update_state(
                        state='PROGRESS',
                        meta={
                            'current': attempts,
                            'total': total,
                            'progress': progress
                        }
                    )
        
        # Password not found
        elapsed = time.time() - start_time
        job.status = JobStatus.COMPLETED
        job.success = False
        job.current_attempt = attempts
        job.time_elapsed = elapsed
        job.speed = attempts / elapsed if elapsed > 0 else 0
        job.progress = 100.0
        job.completed_at = datetime.utcnow()
        db.session.commit()
        
        socketio.emit('job_update', job.to_dict(), room=job_id)
        
        return {
            'success': False,
            'password': None,
            'attempts': attempts,
            'time': elapsed,
            'speed': attempts / elapsed if elapsed > 0 else 0
        }
        
    except Exception as e:
        job.status = JobStatus.FAILED
        job.error_message = str(e)
        job.completed_at = datetime.utcnow()
        db.session.commit()
        
        socketio.emit('job_update', job.to_dict(), room=job_id)
        
        return {'error': str(e)}
