import requests
import json
import time
import random
import concurrent.futures

BASE_URL = "http://localhost:8000"

# Test Configuration
TEST_LANGUAGES = [
    "English", "Hindi", "Tamil", "Spanish", "French", 
    "German", "Japanese", "Russian", "Portuguese", "Arabic"
]
TEST_VIDEO_URL = "https://www.youtube.com/watch?v=jNQXAC9IVRw" # "Me at the zoo" - short video for fast testing

def register_and_test(user_idx, language):
    """Simulate a complete user flow: Signup -> Login -> Generate Notes"""
    email = f"testuser{user_idx}@example.com"
    password = "password123"
    name = f"Test User {user_idx}"
    
    print(f"🚀 [User {user_idx}] Starting flow for language: {language}")
    
    session = requests.Session()
    
    # 1. Signup
    signup_payload = {"email": email, "password": password, "name": name}
    try:
        res = session.post(f"{BASE_URL}/api/signup", json=signup_payload)
        if res.status_code != 200 and res.status_code != 409:
            print(f"❌ [User {user_idx}] Signup failed: {res.text}")
            return False
    except Exception as e:
        print(f"❌ [User {user_idx}] Connection failed: {e}")
        return False
        
    # 2. Login
    login_payload = {"email": email, "password": password}
    try:
        res = session.post(f"{BASE_URL}/api/login", json=login_payload)
        if res.status_code != 200:
            print(f"❌ [User {user_idx}] Login failed: {res.text}")
            return False
    except Exception as e:
        print(f"❌ [User {user_idx}] Login connection failed: {e}")
        return False
    
    token = res.json().get("token")
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. Generate Notes
    start_time = time.time()
    gen_payload = {"youtube_url": TEST_VIDEO_URL, "output_language": language}
    
    print(f"⏳ [User {user_idx}] Requesting notes (Lang: {language})...")
    
    try:
        res = session.post(
            f"{BASE_URL}/api/generate", 
            json=gen_payload, 
            headers=headers,
            timeout=120 # Long timeout for AI generation
        )
        
        duration = time.time() - start_time
        
        if res.status_code == 200:
            data = res.json()
            model = data.get("ai_model", "unknown")
            print(f"✅ [User {user_idx}] Success! ({duration:.2f}s) | Lang: {language} | Model: {model}")
            return True
        else:
            print(f"❌ [User {user_idx}] Generation failed: {res.status_code} - {res.text}")
            return False
            
    except Exception as e:
        print(f"❌ [User {user_idx}] Generation Exception: {e}")
        return False

def test_fallback():
    """Test specifically for Qwen Fallback verification"""
    print("\n🧪 Testing Qwen Fallback Mechanism (Force Header)...")
    email = "fallback_test@example.com"
    password = "password123"
    
    # Signup/Login
    session = requests.Session()
    session.post(f"{BASE_URL}/api/signup", json={"email": email, "password": password, "name": "Fallback Tester"})
    res = session.post(f"{BASE_URL}/api/login", json={"email": email, "password": password})
    
    if res.status_code != 200:
        print("❌ Fallback Login Failed")
        return

    token = res.json().get("token")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Test-Force-Fallback": "true" # Force Qwen
    }
    
    payload = {"youtube_url": TEST_VIDEO_URL, "output_language": "English"}
    
    try:
        print("⏳ Sending Forced Fallback Request...")
        res = session.post(f"{BASE_URL}/api/generate", json=payload, headers=headers, timeout=120)
        
        if res.status_code == 200:
            data = res.json()
            model = data.get("ai_model")
            if model == "qwen3-235b":
                print(f"✅ Fallback Test Passed! Model used: {model}")
            else:
                print(f"⚠️ Fallback Test Warning: Expected qwen3-235b, got {model}")
        else:
            print(f"❌ Fallback Request Failed: {res.status_code} {res.text}")
    except Exception as e:
        print(f"❌ Fallback Exception: {e}")

def run_stress_test():
    print(f"🔥 Starting Stress Test with {len(TEST_LANGUAGES)} users...")
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(register_and_test, i+1, lang): lang for i, lang in enumerate(TEST_LANGUAGES)}
        
        for future in concurrent.futures.as_completed(futures):
            lang = futures[future]
            try:
                res = future.result()
                results.append(res)
            except Exception as exc:
                print(f"User {lang} generated an exception: {exc}")
                results.append(False)
        
    success_count = sum(results)
    print(f"\n📊 Test Summary: {success_count}/{len(results)} users succeeded.")
    
    # Run Fallback Test
    test_fallback()

if __name__ == "__main__":
    run_stress_test()
