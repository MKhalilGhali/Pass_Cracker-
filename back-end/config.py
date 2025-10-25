import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'True') == 'True'
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///cracker.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Celery / Redis
    CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # Cracking limits
    MAX_BRUTEFORCE_LENGTH = 6
    MAX_ATTEMPTS_PER_JOB = 10_000_000
    WORDLIST_DIR = os.getenv('WORDLIST_DIR', './wordlists')
    
    # Hashcat (optional)
    HASHCAT_PATH = os.getenv('HASHCAT_PATH', None)
    USE_HASHCAT = os.getenv('USE_HASHCAT', 'False') == 'True'
