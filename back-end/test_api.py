"""
Quick test script for the Password Cracker API v2.0
Tests basic functionality without requiring frontend
"""

import requests
import time
import json

BASE_URL = "http://localhost:5000"

def test_health():
    """Test health check endpoint"""
    print("Testing health check...")
    response = requests.get(f"{BASE_URL}/api/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print()

def test_detect_hash():
    """Test hash detection"""
    print("Testing hash detection...")
    
    test_hashes = [
        "5f4dcc3b5aa765d61d8327deb882cf99",  # MD5
        "5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8",  # SHA1
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",  # SHA256
    ]
    
    for hash_str in test_hashes:
        response = requests.post(
            f"{BASE_URL}/api/detect-hash",
            json={"hash": hash_str}
        )
        result = response.json()
        print(f"Hash: {hash_str[:32]}...")
        print(f"Detected: {result['detected_type']} (Confidence: {result['confidence']})")
        print(f"Description: {result['description']}")
        print()

def test_generate_hash():
    """Test hash generation"""
    print("Testing hash generation...")
    
    password = "password"
    response = requests.post(
        f"{BASE_URL}/api/generate-hash",
        json={"password": password}
    )
    result = response.json()
    print(f"Password: {password}")
    print(f"MD5: {result['hashes']['md5']}")
    print(f"SHA1: {result['hashes']['sha1']}")
    print(f"SHA256: {result['hashes']['sha256'][:32]}...")
    print()

def test_verify():
    """Test password verification"""
    print("Testing password verification...")
    
    password = "password"
    hash_md5 = "5f4dcc3b5aa765d61d8327deb882cf99"
    
    response = requests.post(
        f"{BASE_URL}/api/verify",
        json={
            "password": password,
            "hash": hash_md5,
            "hashType": "md5"
        }
    )
    result = response.json()
    print(f"Password: {password}")
    print(f"Hash: {hash_md5}")
    print(f"Matches: {result['matches']}")
    print()

def test_create_job():
    """Test job creation and monitoring"""
    print("Testing job creation...")
    
    # Create a simple dictionary attack job
    response = requests.post(
        f"{BASE_URL}/api/jobs",
        json={
            "hash": "5f4dcc3b5aa765d61d8327deb882cf99",  # MD5 of "password"
            "hashType": "md5",
            "attackMode": "dictionary",
            "wordlist": "wordlist.txt",
            "autoDetect": True
        }
    )
    
    if response.status_code != 201:
        print(f"Error creating job: {response.json()}")
        return
    
    result = response.json()
    job_id = result['job_id']
    print(f"Job created: {job_id}")
    print(f"Status: {result['status']}")
    print()
    
    # Monitor job progress
    print("Monitoring job progress...")
    max_attempts = 30
    attempt = 0
    
    while attempt < max_attempts:
        time.sleep(1)
        attempt += 1
        
        response = requests.get(f"{BASE_URL}/api/jobs/{job_id}")
        job = response.json()
        
        status = job['status']
        progress = job.get('progress', 0)
        
        print(f"[{attempt}] Status: {status} | Progress: {progress:.1f}%", end="")
        
        if job.get('current_attempt'):
            print(f" | Attempts: {job['current_attempt']}", end="")
        
        if job.get('speed'):
            print(f" | Speed: {job['speed']:.0f}/s", end="")
        
        print()
        
        if status in ['completed', 'failed', 'cancelled']:
            print()
            print("Job finished!")
            print(f"Success: {job['success']}")
            if job['success']:
                print(f"Password found: {job['cracked_password']}")
            print(f"Time elapsed: {job['time_elapsed']:.2f}s")
            print(f"Total attempts: {job['current_attempt']}")
            break
    
    print()

def test_list_jobs():
    """Test listing jobs"""
    print("Testing job listing...")
    
    response = requests.get(f"{BASE_URL}/api/jobs?limit=5")
    result = response.json()
    
    print(f"Found {result['count']} recent jobs:")
    for job in result['jobs']:
        print(f"  - {job['job_id'][:8]}... | {job['status']} | {job['hash_type']}")
    print()

def test_wordlists():
    """Test wordlist listing"""
    print("Testing wordlist listing...")
    
    response = requests.get(f"{BASE_URL}/api/wordlists")
    result = response.json()
    
    print(f"Available wordlists:")
    for wl in result['wordlists']:
        print(f"  - {wl['name']} ({wl['size']} passwords)")
    print()

def main():
    print("=" * 60)
    print("Password Cracker API v2.0 - Test Suite")
    print("=" * 60)
    print()
    
    try:
        # Basic tests
        test_health()
        test_detect_hash()
        test_generate_hash()
        test_verify()
        test_wordlists()
        
        # Job tests
        test_create_job()
        test_list_jobs()
        
        print("=" * 60)
        print("All tests completed!")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to API")
        print("Make sure the server is running:")
        print("  python app_simple.py")
        print("  OR")
        print("  python app.py (with Redis + Celery)")
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()
