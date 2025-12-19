"""
Quick diagnostic to check quiz/assignment relationship
"""
import requests
from shared.credentials import load_canvas_credentials

canvas_url, canvas_token = load_canvas_credentials()

course_id = 2490206
quiz_id = 5921682  # The ID you entered

headers = {"Authorization": f"Bearer {canvas_token}"}

print(f"Checking Quiz ID: {quiz_id}")
print("=" * 60)

# Get quiz info
quiz_url = f"{canvas_url}/courses/{course_id}/quizzes/{quiz_id}"
response = requests.get(quiz_url, headers=headers)

if response.status_code == 200:
    quiz_data = response.json()
    print("✓ Quiz found!")
    print(f"  Quiz Title: {quiz_data.get('title')}")
    print(f"  Quiz ID: {quiz_data.get('id')}")
    print(f"  Assignment ID: {quiz_data.get('assignment_id')}")  # THIS IS THE KEY!
    
    assignment_id = quiz_data.get('assignment_id')
    
    if assignment_id:
        print(f"\n🎯 USE THIS FOR UPLOADS: {assignment_id}")
        print(f"   Not the quiz ID: {quiz_id}")
    else:
        print("\n⚠️ No assignment_id found - this might not be a quiz")
else:
    print(f"❌ Error: {response.status_code}")
    print(f"   Response: {response.text[:200]}")

# Also check as assignment
print("\n" + "=" * 60)
print("Checking as Assignment...")
assign_url = f"{canvas_url}/courses/{course_id}/assignments/{quiz_id}"
response2 = requests.get(assign_url, headers=headers)

if response2.status_code == 200:
    assign_data = response2.json()
    print("✓ Can access as assignment too")
    print(f"  Assignment ID: {assign_data.get('id')}")
    print(f"  Quiz ID (if quiz): {assign_data.get('quiz_id')}")
else:
    print(f"❌ Cannot access as assignment: {response2.status_code}")