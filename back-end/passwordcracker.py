"""
⚠️ DEPRECATED - This is the v1.0 version of the API
Please use app.py (full version with Celery) or app_simple.py (simplified version)
See UPGRADE_GUIDE.md for migration instructions
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import hashlib
import itertools
import string
import time
from datetime import datetime
import os
import re

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# ============================================
# AUTO HASH DETECTION FUNCTION
# ============================================

def detect_hash_type(hash_string):
    """
    Automatically detect hash type from the hash string
    Returns: (hash_type, confidence, description)
    """
    hash_string = hash_string.strip()
    length = len(hash_string)
    
    # Bcrypt detection (highest priority - has unique prefix)
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
    
    # NTLM (Windows) - looks like MD5 but context matters
    if length == 32 and re.match(r'^[a-fA-F0-9]{32}$', hash_string):
        return ('md5', 'Medium', 'MD5 or NTLM - Most likely MD5')
    
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
    
    # If nothing matches
    return ('unknown', 'Low', 'Unknown hash type - Cannot detect')

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
        'ntlm': {
            'name': 'NTLM',
            'speed': 'Very Fast',
            'security': 'Weak',
            'crackable': 'Easy',
            'recommended_attack': 'Dictionary or Brute force',
            'typical_uses': 'Windows authentication',
            'est_speed': '500K-1M passwords/sec'
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

# ============================================
# UTILITY FUNCTIONS
# ============================================

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

def load_wordlist(filename):
    """Load passwords from text file"""
    if not os.path.exists(filename):
        return []
    
    try:
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            return [line.strip() for line in f if line.strip()]
    except:
        return []

def crack_password_dictionary(target_hash, wordlist, hash_type='md5'):
    """Dictionary attack"""
    attempts = 0
    start_time = time.time()
    
    for password in wordlist:
        attempts += 1
        hashed = hash_password(password, hash_type)
        
        if hashed == target_hash:
            elapsed = time.time() - start_time
            return {
                'success': True,
                'password': password,
                'attempts': attempts,
                'time': elapsed,
                'speed': attempts / elapsed if elapsed > 0 else 0
            }
    
    elapsed = time.time() - start_time
    return {
        'success': False,
        'password': None,
        'attempts': attempts,
        'time': elapsed,
        'speed': attempts / elapsed if elapsed > 0 else 0
    }

def crack_password_bruteforce(target_hash, hash_type='md5', max_length=4, charset_option='1'):
    """Brute force attack"""
    charsets = {
        '1': string.ascii_lowercase + string.digits,
        '2': string.ascii_lowercase,
        '3': string.ascii_lowercase + string.ascii_uppercase + string.digits,
        '4': string.ascii_letters + string.digits + string.punctuation
    }
    
    charset = charsets.get(charset_option, string.ascii_lowercase + string.digits)
    attempts = 0
    start_time = time.time()
    
    for length in range(1, max_length + 1):
        for combo in itertools.product(charset, repeat=length):
            attempts += 1
            password = ''.join(combo)
            hashed = hash_password(password, hash_type)
            
            # Limit attempts to prevent timeout
            if attempts > 100000:
                elapsed = time.time() - start_time
                return {
                    'success': False,
                    'password': None,
                    'attempts': attempts,
                    'time': elapsed,
                    'speed': attempts / elapsed if elapsed > 0 else 0,
                    'message': 'Exceeded maximum attempts (100k). Use shorter length or simpler charset.'
                }
            
            if hashed == target_hash:
                elapsed = time.time() - start_time
                return {
                    'success': True,
                    'password': password,
                    'attempts': attempts,
                    'time': elapsed,
                    'speed': attempts / elapsed if elapsed > 0 else 0
                }
    
    elapsed = time.time() - start_time
    return {
        'success': False,
        'password': None,
        'attempts': attempts,
        'time': elapsed,
        'speed': attempts / elapsed if elapsed > 0 else 0
    }

def analyze_password_strength(password):
    """Analyze password strength"""
    length = len(password)
    has_lower = any(c.islower() for c in password)
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_symbol = any(c in string.punctuation for c in password)
    
    charset_size = 0
    if has_lower: charset_size += 26
    if has_upper: charset_size += 26
    if has_digit: charset_size += 10
    if has_symbol: charset_size += 32
    
    combinations = charset_size ** length
    attempts_per_second = 1_000_000_000
    seconds_to_crack = combinations / attempts_per_second
    
    if seconds_to_crack < 1:
        time_str = "Instantly"
        strength = "Very Weak"
        score = 1
    elif seconds_to_crack < 60:
        time_str = f"{seconds_to_crack:.2f} seconds"
        strength = "Weak"
        score = 2
    elif seconds_to_crack < 3600:
        time_str = f"{seconds_to_crack/60:.2f} minutes"
        strength = "Moderate"
        score = 3
    elif seconds_to_crack < 86400:
        time_str = f"{seconds_to_crack/3600:.2f} hours"
        strength = "Good"
        score = 4
    elif seconds_to_crack < 31536000:
        time_str = f"{seconds_to_crack/86400:.2f} days"
        strength = "Strong"
        score = 5
    else:
        years = seconds_to_crack / 31536000
        time_str = f"{years:.2e} years" if years > 1000000 else f"{years:.2f} years"
        strength = "Very Strong"
        score = 6
    
    return {
        'length': length,
        'charset_size': charset_size,
        'combinations': combinations,
        'time_to_crack': time_str,
        'strength': strength,
        'score': score,
        'has_lower': has_lower,
        'has_upper': has_upper,
        'has_digit': has_digit,
        'has_symbol': has_symbol
    }

# ============================================
# API ENDPOINTS
# ============================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'Password Cracker API is running'})

@app.route('/api/detect-hash', methods=['POST'])
def detect_hash():
    """Auto-detect hash type from hash string"""
    data = request.json
    hash_string = data.get('hash', '')
    
    if not hash_string:
        return jsonify({'error': 'Hash is required'}), 400
    
    # Detect hash type
    hash_type, confidence, description = detect_hash_type(hash_string)
    
    # Get detailed info
    hash_info = get_hash_info(hash_type)
    
    return jsonify({
        'detected_type': hash_type,
        'confidence': confidence,
        'description': description,
        'info': hash_info,
        'hash_length': len(hash_string.strip())
    })

@app.route('/api/smart-crack', methods=['POST'])
def smart_crack():
    """Auto-detect hash type and use best cracking strategy"""
    data = request.json
    target_hash = data.get('hash', '')
    
    if not target_hash:
        return jsonify({'error': 'Hash is required'}), 400
    
    # Auto-detect hash type
    hash_type, confidence, description = detect_hash_type(target_hash)
    
    if hash_type == 'unknown':
        return jsonify({
            'error': 'Could not detect hash type',
            'suggestion': 'Please select hash type manually'
        }), 400
    
    # Get hash info
    hash_info = get_hash_info(hash_type)
    
    # Load wordlist
    wordlist = load_wordlist('wordlist.txt')
    
    if not wordlist:
        return jsonify({'error': 'Wordlist not found'}), 400
    
    # Choose attack strategy based on hash type
    if hash_type == 'bcrypt':
        result = crack_password_dictionary(target_hash, wordlist, hash_type)
        result['attack_used'] = 'Dictionary Attack'
        result['reason'] = 'Bcrypt is too slow for brute force'
    
    elif hash_type in ['md5', 'sha1', 'ntlm']:
        result = crack_password_dictionary(target_hash, wordlist, hash_type)
        
        if not result['success']:
            result = crack_password_bruteforce(target_hash, hash_type, 4, '1')
            result['attack_used'] = 'Dictionary → Brute Force'
            result['reason'] = 'Dictionary failed, tried brute force (4 chars)'
        else:
            result['attack_used'] = 'Dictionary Attack'
            result['reason'] = 'Found in wordlist'
    
    elif hash_type in ['sha256', 'sha512']:
        result = crack_password_dictionary(target_hash, wordlist, hash_type)
        result['attack_used'] = 'Dictionary Attack'
        result['reason'] = 'SHA-256/512 too slow for brute force'
    
    else:
        result = crack_password_dictionary(target_hash, wordlist, hash_type)
        result['attack_used'] = 'Dictionary Attack'
        result['reason'] = 'Default strategy'
    
    # Add detection info to result
    result['detected_type'] = hash_type
    result['confidence'] = confidence
    result['hash_info'] = hash_info
    
    return jsonify(result)

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

@app.route('/api/analyze-strength', methods=['POST'])
def analyze_strength():
    """Analyze password strength"""
    data = request.json
    password = data.get('password', '')
    
    if not password:
        return jsonify({'error': 'Password is required'}), 400
    
    analysis = analyze_password_strength(password)
    return jsonify(analysis)

@app.route('/api/crack-dictionary', methods=['POST'])
def crack_dictionary():
    """Crack hash using dictionary attack"""
    data = request.json
    target_hash = data.get('hash', '')
    hash_type = data.get('hashType', 'md5')
    wordlist_name = data.get('wordlist', 'wordlist.txt')
    
    if not target_hash:
        return jsonify({'error': 'Hash is required'}), 400
    
    wordlist = load_wordlist(wordlist_name)
    
    if not wordlist:
        return jsonify({'error': f'Wordlist {wordlist_name} not found or empty'}), 400
    
    result = crack_password_dictionary(target_hash, wordlist, hash_type)
    return jsonify(result)

@app.route('/api/crack-bruteforce', methods=['POST'])
def crack_bruteforce():
    """Crack hash using brute force attack"""
    data = request.json
    target_hash = data.get('hash', '')
    hash_type = data.get('hashType', 'md5')
    max_length = data.get('maxLength', 4)
    charset = data.get('charset', '1')
    
    if not target_hash:
        return jsonify({'error': 'Hash is required'}), 400
    
    if max_length > 6:
        return jsonify({'error': 'Max length cannot exceed 6 for performance reasons'}), 400
    
    result = crack_password_bruteforce(target_hash, hash_type, max_length, charset)
    return jsonify(result)

@app.route('/api/wordlists', methods=['GET'])
def list_wordlists():
    """List available wordlist files"""
    wordlists = []
    common_wordlists = ['wordlist.txt', 'common_passwords.txt', 'rockyou.txt']
    
    for wl in common_wordlists:
        if os.path.exists(wl):
            wordlist = load_wordlist(wl)
            wordlists.append({
                'name': wl,
                'size': len(wordlist)
            })
    
    return jsonify({'wordlists': wordlists})

@app.route('/api/save-result', methods=['POST'])
def save_result():
    """Save cracking result to file"""
    data = request.json
    
    try:
        filename = "crack_results.json"
        timestamp = datetime.now().isoformat()
        
        result_entry = {
            'timestamp': timestamp,
            'mode': data.get('mode'),
            'hash_type': data.get('hashType'),
            'target_hash': data.get('hash'),
            'success': data.get('success'),
            'password': data.get('password'),
            'attempts': data.get('attempts'),
            'time': data.get('time'),
            'speed': data.get('speed')
        }
        
        results = []
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                import json
                results = json.load(f)
        
        results.append(result_entry)
        
        with open(filename, 'w') as f:
            import json
            json.dump(results, f, indent=2)
        
        return jsonify({'message': 'Result saved successfully'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/results', methods=['GET'])
def get_results():
    """Get all saved results"""
    try:
        filename = "crack_results.json"
        
        if not os.path.exists(filename):
            return jsonify({'results': []})
        
        with open(filename, 'r') as f:
            import json
            results = json.load(f)
        
        return jsonify({'results': results})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# RUN SERVER
# ============================================

if __name__ == '__main__':
    print("🚀 Starting Password Cracker API...")
    print("📡 Server running on http://localhost:5000")
    print("⚠️  ETHICAL USE ONLY - Educational purposes")
    app.run(debug=True, host='0.0.0.0', port=5000)