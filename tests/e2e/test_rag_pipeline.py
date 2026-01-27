import requests
import json
import time
import os

BASE_URL = "http://127.0.0.1:8000"
USERNAME = "admin"
PASSWORD = "password123"

def run_test():
    s = requests.Session()
    
    # 1. Login
    print("Step 1: Logging in...")
    login_url = f"{BASE_URL}/login/"
    r = s.get(login_url)
    if 'csrftoken' in s.cookies:
        csrftoken = s.cookies['csrftoken']
    else:
        # Fallback if cookie not set on GET
        csrftoken = ""
    
    login_data = {
        'username': USERNAME,
        'password': PASSWORD,
        'csrfmiddlewaretoken': csrftoken
    }
    r = s.post(login_url, data=login_data)
    
    if "admin" in r.url or "chat" in r.url:
        print("Login Successful")
    else:
        print(f"Login Failed: {r.url}")
        # Proceeding might fail, but let's try to verify session
    
    # Update CSRF token from after login if changed
    if 'csrftoken' in s.cookies:
        csrftoken = s.cookies['csrftoken']

    # 2. Create Policy File
    filename = "test_leave_policy.txt"
    content = "The company allows 20 days of paid annual leave and 12 days of casual leave per year. Sick leave is unlimited with a medical certificate."
    with open(filename, "w") as f:
        f.write(content)
        
    # 3. Upload Policy
    print("Step 2: Uploading Policy...")
    policies_url = f"{BASE_URL}/api/policies/"
    
    with open(filename, 'rb') as policy_file:
        files = {'uploaded_file': policy_file}
        data = {
            'title': 'Test Leave Policy',
            'source_type': 'upload',
            # DRF SessionAuth requires CSRF token in X-CSRFToken header usually
        }
        headers = {'X-CSRFToken': csrftoken, 'Referer': policies_url}
        
        r = s.post(policies_url, files=files, data=data, headers=headers)
    
    
    if r.status_code == 201:
        policy_data = r.json()
        policy_id = policy_data['id']
        print(f"Policy Created: {policy_id}")
    else:
        print(f"Policy Upload Failed: {r.status_code} - {r.text}")
        return

    # 4. Index Policy
    print("Step 3: Indexing Policy...")
    index_url = f"{BASE_URL}/api/policies/{policy_id}/index/"
    r = s.post(index_url, headers=headers)
    
    if r.status_code == 202:
        print("Indexing started successfully.")
    else:
        print(f"Indexing Failed: {r.status_code} - {r.text}")
    
    print("Waiting 5 seconds for indexing to complete...")
    time.sleep(5)
    
    # 5. Query Chat
    print("Step 4: Querying Agent...")
    chat_url = f"{BASE_URL}/chat/"
    # chat endpoint expects JSON body
    query = {"prompt": "How many casual leave days do I have?"}
    
    r = s.post(chat_url, json=query) # chat_with_llm is csrf_exempt so headers might not be strictly needed for csrf, but session is needed
    
    if r.status_code == 200:
        response = r.json()
        print("\n--- LLM Response ---")
        print(response.get('response'))
        print("--------------------")
    else:
        print(f"Chat Query Failed: {r.status_code} - {r.text}")

    # Cleanup
    os.remove(filename)

if __name__ == "__main__":
    run_test()
