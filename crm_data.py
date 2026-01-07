"""
Simple tests to validate CRM data extraction and endpoint.
Run with: python crm_data.py
"""

import requests
import json
from CRM import extract_crm_data, format_crm_output
from vdb import index

# Test configuration
BASE_URL = "http://localhost:8000"

# Expected vector IDs based on data files (format: meeting-{filename})
EXPECTED_IDS = [
    "meeting-acme",
    "meeting-buildco", 
    "meeting-techstart",
    "meeting-nextgen",
    "meeting-dataflow"
]


def get_meeting_notes_from_db(vector_id: str) -> str:
    """
    Fetch meeting notes from Pinecone database by vector ID.
    
    Args:
        vector_id: The vector ID (e.g., "meeting-acme")
    
    Returns:
        Meeting notes text from the database, or empty string if not found
    """
    try:
        # Fetch vector by ID from Pinecone
        response = index.fetch(ids=[vector_id])
        
        if vector_id in response.vectors:
            vector_data = response.vectors[vector_id]
            metadata = vector_data.metadata or {}
            return metadata.get('text', '')
        return ""
    except Exception as e:
        print(f"⚠️  Error fetching from database: {e}")
        return ""


def get_available_test_ids() -> list:
    """
    Get list of available vector IDs from the database.
    
    Returns:
        List of available vector IDs
    """
    available_ids = []
    for vector_id in EXPECTED_IDS:
        try:
            response = index.fetch(ids=[vector_id])
            if vector_id in response.vectors:
                available_ids.append(vector_id)
        except Exception:
            # ID doesn't exist, skip it
            continue
    return available_ids


def test_extract_crm_data():
    """Test the extract_crm_data function with data from vector database."""
    print("\n" + "="*60)
    print("TEST 1: Testing extract_crm_data() with database data")
    print("="*60)
    
    # Get available IDs from database
    available_ids = get_available_test_ids()
    if not available_ids:
        print("❌ FAILED: No meeting notes found in database!")
        print("   Run: python vdb.py to populate the database")
        return False
    
    # Use first available ID
    test_id = available_ids[0]
    print(f"📋 Using vector ID: {test_id}")
    
    # Fetch meeting notes from database
    meeting_notes = get_meeting_notes_from_db(test_id)
    if not meeting_notes:
        print(f"❌ FAILED: Could not fetch meeting notes for ID: {test_id}")
        return False
    
    print(f"✓ Fetched {len(meeting_notes)} characters from database")
    print(f"   Preview: {meeting_notes[:100]}...")
    
    try:
        result = extract_crm_data(meeting_notes)
        
        # Validate structure
        assert isinstance(result, dict), "Result should be a dictionary"
        assert "contact" in result, "Missing 'contact' field"
        assert "company" in result, "Missing 'company' field"
        assert "deal_size" in result, "Missing 'deal_size' field"
        assert "stage" in result, "Missing 'stage' field"
        assert "urgency" in result, "Missing 'urgency' field"
        
        # Validate contact structure
        assert isinstance(result["contact"], dict), "Contact should be a dictionary"
        assert "name" in result["contact"], "Contact missing 'name'"
        
        # Validate deal_size structure
        assert isinstance(result["deal_size"], dict), "Deal size should be a dictionary"
        
        # Validate urgency value
        assert result["urgency"] in ["HIGH", "MEDIUM", "LOW"], "Invalid urgency value"
        
        print("✅ PASSED: Function returns valid structure")
        print(f"   Vector ID: {test_id}")
        print(f"   Company: {result.get('company')}")
        print(f"   Contact: {result.get('contact', {}).get('name')}")
        print(f"   Urgency: {result.get('urgency')}")
        return True
        
    except AssertionError as e:
        print(f"❌ FAILED: {e}")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def test_format_crm_output():
    """Test the format_crm_output function."""
    print("\n" + "="*60)
    print("TEST 2: Testing format_crm_output() function")
    print("="*60)
    
    try:
        # Create sample CRM data
        sample_data = {
            "contact": {"name": "Sarah Chen", "title": "VP Operations"},
            "company": "Acme Corp",
            "deal_size": {"quantity": "50 licenses", "value": "~$50K"},
            "stage": "Negotiation",
            "urgency": "HIGH",
            "close_date": "Friday",
            "pain_points": ["Budget concerns", "Competitive pressure"],
            "key_discussion": "Salesforce integration"
        }
        
        formatted = format_crm_output(sample_data)
        
        assert isinstance(formatted, str), "Output should be a string"
        assert len(formatted) > 0, "Output should not be empty"
        assert "Acme Corp" in formatted, "Should contain company name"
        
        print("✅ PASSED: Format function works correctly")
        print("\nSample output:")
        print(formatted[:200] + "...")
        return True
        
    except AssertionError as e:
        print(f"❌ FAILED: {e}")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def test_endpoint():
    """Test the /crm-data endpoint with vector_id parameter."""
    print("\n" + "="*60)
    print("TEST 3: Testing /crm-data endpoint with vector_id")
    print("="*60)
    
    # Get available IDs from database
    available_ids = get_available_test_ids()
    if not available_ids:
        print("❌ FAILED: No meeting notes found in database!")
        print("   Run: python vdb.py to populate the database")
        return False
    
    # Use first available ID
    test_id = available_ids[0]
    print(f"📋 Using vector ID: {test_id}")
    
    try:
        # Make POST request to endpoint with vector_id in request body
        response = requests.post(
            f"{BASE_URL}/crm-data",
            json={"vector_id": test_id},
            timeout=30
        )
        
        # Check status code
        if response.status_code != 200:
            error_detail = response.text
            print(f"❌ FAILED: Expected 200, got {response.status_code}")
            print(f"   Error details: {error_detail[:300]}")
            if response.status_code == 422:
                try:
                    error_json = response.json()
                    print(f"   Validation errors: {json.dumps(error_json, indent=2)}")
                except:
                    pass
            return False
        
        # Parse response
        data = response.json()
        
        # Validate response structure
        assert "status" in data, "Response missing 'status' field"
        assert data["status"] == "success", f"Status should be 'success', got '{data['status']}'"
        assert "vector_id" in data, "Response missing 'vector_id' field"
        assert data["vector_id"] == test_id, f"Vector ID mismatch: expected {test_id}, got {data['vector_id']}"
        assert "data" in data, "Response missing 'data' field"
        assert "formatted" in data, "Response missing 'formatted' field"
        
        # Validate CRM data structure
        crm_data = data["data"]
        assert "contact" in crm_data, "CRM data missing 'contact'"
        assert "company" in crm_data, "CRM data missing 'company'"
        
        print("✅ PASSED: Endpoint returns valid response")
        print(f"   Vector ID: {test_id}")
        print(f"   Status: {data['status']}")
        print(f"   Company: {crm_data.get('company')}")
        print(f"   Urgency: {crm_data.get('urgency')}")
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ FAILED: Could not connect to server. Is the app running?")
        print("   Start the server with: python app.py")
        return False
    except AssertionError as e:
        print(f"❌ FAILED: {e}")
        if 'data' in locals():
            print(f"   Response: {json.dumps(data, indent=2)[:200]}")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def test_id_logic():
    """Test that ID-based retrieval works correctly."""
    print("\n" + "="*60)
    print("TEST 4: Testing ID logic - fetch by vector ID")
    print("="*60)
    
    try:
        # Get available IDs
        available_ids = get_available_test_ids()
        if not available_ids:
            print("❌ FAILED: No meeting notes found in database!")
            return False
        
        print(f"✓ Found {len(available_ids)} available vector IDs")
        
        # Test fetching each ID
        success_count = 0
        for vector_id in available_ids:
            meeting_notes = get_meeting_notes_from_db(vector_id)
            if meeting_notes:
                success_count += 1
                print(f"   ✓ {vector_id}: {len(meeting_notes)} chars")
            else:
                print(f"   ❌ {vector_id}: Failed to fetch")
        
        # Validate
        assert success_count > 0, "Should fetch at least one meeting note"
        assert success_count == len(available_ids), f"Should fetch all {len(available_ids)} IDs, got {success_count}"
        
        print(f"✅ PASSED: Successfully fetched {success_count}/{len(available_ids)} vector IDs")
        return True
        
    except AssertionError as e:
        print(f"❌ FAILED: {e}")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def test_endpoint_error_handling():
    """Test endpoint error handling with invalid vector_id."""
    print("\n" + "="*60)
    print("TEST 5: Testing endpoint error handling")
    print("="*60)
    
    try:
        # Test with non-existent vector_id
        response = requests.post(
            f"{BASE_URL}/crm-data",
            json={"vector_id": "meeting-nonexistent"},
            timeout=30
        )
        
        assert response.status_code == 200, "Endpoint should handle invalid ID"
        data = response.json()
        
        # Should return error status
        assert "status" in data, "Response should have status field"
        assert data["status"] == "error", "Should return error status for invalid ID"
        assert "message" in data, "Error response should have message"
        
        print("✅ PASSED: Endpoint handles invalid vector_id gracefully")
        print(f"   Error message: {data.get('message', '')[:100]}")
        return True
        
    except requests.exceptions.ConnectionError:
        print("⚠️  SKIPPED: Server not running")
        return None
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def run_all_tests():
    """Run all tests and print summary."""
    print("\n" + "="*60)
    print("CRM DATA EXTRACTION TESTS")
    print("="*60)
    
    results = []
    
    # Test 1: Function test
    results.append(("extract_crm_data()", test_extract_crm_data()))
    
    # Test 2: Format test
    results.append(("format_crm_output()", test_format_crm_output()))
    
    # Test 3: Endpoint test
    results.append(("/crm-data endpoint", test_endpoint()))
    
    # Test 4: ID logic
    results.append(("ID logic", test_id_logic()))
    
    # Test 5: Error handling
    error_result = test_endpoint_error_handling()
    if error_result is not None:
        results.append(("Error handling", error_result))
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result is True)
    failed = sum(1 for _, result in results if result is False)
    skipped = sum(1 for _, result in results if result is None)
    
    for test_name, result in results:
        status = "✅ PASS" if result is True else "❌ FAIL" if result is False else "⚠️  SKIP"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed} passed, {failed} failed, {skipped} skipped")
    print("="*60 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    run_all_tests()
