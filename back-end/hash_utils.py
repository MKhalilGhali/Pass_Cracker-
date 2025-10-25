import hashlib
import re
from passlib.hash import bcrypt, sha256_crypt, sha512_crypt, md5_crypt

def detect_hash_type(hash_string):
    """Auto-detect hash type from the hash string"""
    hash_string = hash_string.strip()
    length = len(hash_string)
    
    # Bcrypt detection
    if re.match(r'^\$2[aby]\$\d{2}\$.{53}$', hash_string):
        return ('bcrypt', 'High', 'Bcrypt - Very secure, slow to crack')
    
    # SHA-512 Crypt (Unix)
    if hash_string.startswith('$6$'):
        return ('sha512crypt', 'High', 'SHA-512 Crypt (Unix/Linux)')
    
    # SHA-256 Crypt (Unix)
    if hash_string.startswith('$5$'):
        return ('sha256crypt', 'High', 'SHA-256 Crypt (Unix/Linux)')
    
    # MD5 Crypt (Unix)
    if hash_string.startswith('$1$'):
        return ('md5crypt', 'High', 'MD5 Crypt (Unix/Linux)')
    
    # Length-based detection (hex strings)
    if re.match(r'^[a-fA-F0-9]+$', hash_string):
        if length == 32:
            return ('md5', 'High', 'MD5 - Fast, commonly used')
        elif length == 40:
            return ('sha1', 'High', 'SHA-1 - Git commits, legacy systems')
        elif length == 64:
            return ('sha256', 'High', 'SHA-256 - Bitcoin, modern apps')
        elif length == 128:
            return ('sha512', 'High', 'SHA-512 - High security applications')
    
    return ('unknown', 'Low', 'Unknown hash type - Cannot detect')

def hash_password(password, hash_type='md5'):
    """Hash a password using specified algorithm"""
    try:
        if hash_type == 'md5':
            return hashlib.md5(password.encode()).hexdigest()
        elif hash_type == 'sha1':
            return hashlib.sha1(password.encode()).hexdigest()
        elif hash_type == 'sha256':
            return hashlib.sha256(password.encode()).hexdigest()
        elif hash_type == 'sha512':
            return hashlib.sha512(password.encode()).hexdigest()
        elif hash_type == 'ntlm':
            return hashlib.new('md4', password.encode('utf-16le')).hexdigest()
        else:
            return None
    except:
        return None

def verify_password(password, hash_string, hash_type):
    """Verify password against hash using appropriate method"""
    try:
        if hash_type == 'bcrypt':
            return bcrypt.verify(password, hash_string)
        elif hash_type == 'sha256crypt':
            return sha256_crypt.verify(password, hash_string)
        elif hash_type == 'sha512crypt':
            return sha512_crypt.verify(password, hash_string)
        elif hash_type == 'md5crypt':
            return md5_crypt.verify(password, hash_string)
        else:
            # Simple hash comparison
            computed = hash_password(password, hash_type)
            return computed and computed.lower() == hash_string.lower()
    except:
        return False

def get_hash_info(hash_type):
    """Get detailed information about a hash type"""
    info = {
        'md5': {
            'name': 'MD5',
            'speed': 'Very Fast',
            'security': 'Weak',
            'crackable': 'Easy',
            'recommended_attack': 'Dictionary or Brute force',
            'typical_uses': 'Legacy systems, file checksums',
            'est_speed': '500K-1M passwords/sec'
        },
        'sha1': {
            'name': 'SHA-1',
            'speed': 'Very Fast',
            'security': 'Weak',
            'crackable': 'Easy',
            'recommended_attack': 'Dictionary or Brute force',
            'typical_uses': 'Git, legacy applications',
            'est_speed': '300K-800K passwords/sec'
        },
        'sha256': {
            'name': 'SHA-256',
            'speed': 'Fast',
            'security': 'Medium',
            'crackable': 'Moderate',
            'recommended_attack': 'Dictionary first',
            'typical_uses': 'Bitcoin, modern applications',
            'est_speed': '200K-500K passwords/sec'
        },
        'sha512': {
            'name': 'SHA-512',
            'speed': 'Fast',
            'security': 'Medium',
            'crackable': 'Moderate',
            'recommended_attack': 'Dictionary only',
            'typical_uses': 'High security applications',
            'est_speed': '100K-300K passwords/sec'
        },
        'bcrypt': {
            'name': 'Bcrypt',
            'speed': 'Very Slow',
            'security': 'Very Strong',
            'crackable': 'Very Hard',
            'recommended_attack': 'Dictionary only (brute force impractical)',
            'typical_uses': 'Modern web applications, password storage',
            'est_speed': '50-200 passwords/sec'
        },
        'sha256crypt': {
            'name': 'SHA-256 Crypt',
            'speed': 'Slow',
            'security': 'Strong',
            'crackable': 'Hard',
            'recommended_attack': 'Dictionary only',
            'typical_uses': 'Unix/Linux systems',
            'est_speed': '1K-5K passwords/sec'
        },
        'sha512crypt': {
            'name': 'SHA-512 Crypt',
            'speed': 'Slow',
            'security': 'Strong',
            'crackable': 'Hard',
            'recommended_attack': 'Dictionary only',
            'typical_uses': 'Unix/Linux systems',
            'est_speed': '500-2K passwords/sec'
        },
        'md5crypt': {
            'name': 'MD5 Crypt',
            'speed': 'Moderate',
            'security': 'Moderate',
            'crackable': 'Moderate',
            'recommended_attack': 'Dictionary first',
            'typical_uses': 'Legacy Unix systems',
            'est_speed': '10K-50K passwords/sec'
        },
        'unknown': {
            'name': 'Unknown',
            'speed': 'N/A',
            'security': 'N/A',
            'crackable': 'N/A',
            'recommended_attack': 'Manual selection required',
            'typical_uses': 'N/A',
            'est_speed': 'N/A'
        }
    }
    
    return info.get(hash_type, info['unknown'])
