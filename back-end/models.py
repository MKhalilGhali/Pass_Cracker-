from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, Enum
import enum

db = SQLAlchemy()

class JobStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class AttackMode(enum.Enum):
    DICTIONARY = "dictionary"
    BRUTEFORCE = "bruteforce"
    SMART = "smart"
    HASHCAT = "hashcat"

class CrackJob(db.Model):
    __tablename__ = 'crack_jobs'
    
    id = Column(Integer, primary_key=True)
    job_id = Column(String(36), unique=True, nullable=False, index=True)
    
    # Input
    target_hash = Column(String(512), nullable=False)
    hash_type = Column(String(50), nullable=False)
    attack_mode = Column(Enum(AttackMode), nullable=False)
    
    # Configuration
    wordlist_name = Column(String(255))
    max_length = Column(Integer)
    charset_option = Column(String(10))
    
    # Status
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False, index=True)
    progress = Column(Float, default=0.0)
    current_attempt = Column(Integer, default=0)
    total_attempts = Column(Integer, default=0)
    
    # Results
    success = Column(Boolean, default=False)
    cracked_password = Column(String(255))
    time_elapsed = Column(Float, default=0.0)
    speed = Column(Float, default=0.0)
    
    # Metadata
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'job_id': self.job_id,
            'target_hash': self.target_hash,
            'hash_type': self.hash_type,
            'attack_mode': self.attack_mode.value if self.attack_mode else None,
            'wordlist_name': self.wordlist_name,
            'max_length': self.max_length,
            'charset_option': self.charset_option,
            'status': self.status.value if self.status else None,
            'progress': self.progress,
            'current_attempt': self.current_attempt,
            'total_attempts': self.total_attempts,
            'success': self.success,
            'cracked_password': self.cracked_password,
            'time_elapsed': self.time_elapsed,
            'speed': self.speed,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }

class Wordlist(db.Model):
    __tablename__ = 'wordlists'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    file_path = Column(String(512), nullable=False)
    size = Column(Integer, default=0)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'file_path': self.file_path,
            'size': self.size,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
