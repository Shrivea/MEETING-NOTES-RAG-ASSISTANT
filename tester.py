import time
import requests
BASE_URL = "http://localhost:8000"

def test_crm_data():
    response = requests.post(f"{BASE_URL}/crm-data", json={"vector_id": "meeting-acme"})
    print(response.json())


def test_tasks_endpoint():
    """Test the /task-data endpoint"""
    
    print("\n" + "="*70)
    print("TESTING TASKS ENDPOINT")
    print("="*70)
    
    # Test 1: Get tasks from all existing meetings (no new input)
    t1 = time.time()
    print("\n📋 TEST 1: Analyzing all existing meetings in database...")
    print("-" * 70)
    
    response = requests.post(  # ✅ POST request
        f"{BASE_URL}/task-data",  # ✅ Correct endpoint name
        json={"meeting_notes": None}  # ✅ Valid JSON body
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success!")
        print(f"Meetings Analyzed: {data['meetings_analyzed']}")
        print(f"\n{data['formatted_output']}")
    else:
        print(f"❌ Error: {response.text}")
    
    t2 = time.time()
    diff = t2-t1
    print(diff)
    # Test 2: Add new meeting and re-analyze
    print("\n" + "="*70)
    print("📋 TEST 2: Adding new urgent meeting to analysis...")
    print("-" * 70)
    t1 = time.time()
    new_meeting = """
    # test_tasks.py - Better Test 2
URGENT - ZetaCorp Meeting - Alex Kim (CEO)

Just finished call with ZetaCorp - HOT LEAD!
They need 120 seats ASAP. Budget: $150K approved.

Critical requirements:
- Custom API integration with their legacy system
- Must go live by January 20th (2 weeks!)
- Security certification required before signing

Next steps:
- Send security compliance docs by tomorrow
- Schedule technical scoping call Thursday
- Get Solutions Architect looped in
- Pricing proposal due Monday

Alex has authority to sign - this could close THIS MONTH!
"""
    
    response = requests.post(
        f"{BASE_URL}/task-data",
        json={"meeting_notes": new_meeting}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success!")
        print(f"Meetings Analyzed: {data['meetings_analyzed']}")
        print(f"\n{data['formatted_output']}")
    else:
        print(f"❌ Error: {response.text}")
    
    t2 = time.time()
    diff = t2-t1
    print(diff)
    # Test 3: Empty request (should still work)
    print("\n" + "="*70)
    t1 = time.time()
    print("📋 TEST 3: Testing with empty/no meeting notes...")
    print("-" * 70)
    
    response = requests.post(
        f"{BASE_URL}/task-data",
        json={}  # ✅ Empty but valid JSON
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success! Endpoint handles empty request")
        print(f"Meetings Analyzed: {data['meetings_analyzed']}")
    else:
        print(f"❌ Error: {response.text}")
    
    print("\n" + "="*70)
    print("TESTS COMPLETE")
    print("="*70 + "\n")
    t2 = time.time()
    diff = t2-t1
    print(diff)


if __name__ == "__main__":
    test_tasks_endpoint()