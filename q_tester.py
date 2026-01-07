import requests

BASE_URL = "http://localhost:8000"

def test_qa_endpoint():
    """Test the /question-answer-data endpoint"""
    
    print("\n" + "="*70)
    print("TESTING Q&A ENDPOINT")
    print("="*70)
    
    # Test questions from your general.md
    questions = [
        "What companies did we meet with this week?",
        "Who is our contact at ACME Corp?",
        "What's the deal size for DataFlow Systems?",
        "When is the ACME Corp quote due?",
        "Which customers need Salesforce integration?"
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n📋 TEST {i}: {question}")
        print("-" * 70)
        
        response = requests.post(
            f"{BASE_URL}/question-answer-data",
            json={"question": question}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success!")
            print(f"\n{data['formatted_output']}")
        else:
            print(f"❌ Error: {response.text}")
    
    # Test error handling
    print("\n" + "="*70)
    print("📋 TEST: Empty question (should fail gracefully)")
    print("-" * 70)
    
    response = requests.post(
        f"{BASE_URL}/question-answer-data",
        json={"question": ""}
    )
    
    if response.status_code != 200:
        print("✅ Correctly rejected empty question")
    else:
        print("❌ Should have rejected empty question")
    
    print("\n" + "="*70)
    print("TESTS COMPLETE")
    print("="*70 + "\n")

if __name__ == "__main__":
    test_qa_endpoint()