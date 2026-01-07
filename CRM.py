"""
CRM Data Extraction Module
Extracts structured CRM data from meeting notes using RAG (Retrieval Augmented Generation).
"""

from typing import Dict, Any, List, Optional
from openai import OpenAI
import os
import json
from dotenv import load_dotenv
from vdb import search_pinecone, get_openai_embedding

load_dotenv()

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def extract_crm_data(meeting_notes: str, top_k_examples: int = 3) -> Dict[str, Any]:
    """
    Extract structured CRM data from meeting notes using RAG.
    
    This function:
    1. Retrieves similar past meetings from Pinecone (few-shot examples)
    2. Uses GPT-5 to extract structured CRM data based on patterns from examples
    3. Returns structured CRM fields
    
    Args:
        meeting_notes: Raw, unstructured meeting notes text
        top_k_examples: Number of similar meetings to retrieve for context (default: 3)
    
    Returns:
        Dictionary containing structured CRM data:
        {
            "contact": {"name": str, "title": str},
            "company": str,
            "deal_size": {"quantity": str, "value": str},
            "stage": str,
            "urgency": str,  # HIGH, MEDIUM, LOW
            "close_date": str,
            "pain_points": List[str],
            "key_discussion": str
        }
    """
    
    # Step 1: Retrieve similar meetings from Pinecone (RAG)
    print(f"🔍 Retrieving {top_k_examples} similar meetings from database...")
    similar_meetings = search_pinecone(meeting_notes, top_k=top_k_examples)
    
    # Step 2: Build context from retrieved meetings
    context_examples = []
    for i, meeting in enumerate(similar_meetings, 1):
        metadata = meeting.get('metadata', {})
        example_text = metadata.get('text', '')
        if example_text:
            context_examples.append(f"Example {i}:\n{example_text}\n")
    
    context = "\n".join(context_examples) if context_examples else "No similar meetings found."
    
    # Step 3: Create prompt for GPT-4 with few-shot examples
    system_prompt = """You are an expert at extracting structured CRM data from meeting notes.
Your task is to analyze meeting notes and extract the following CRM fields:

1. Contact: Name and job title/role
2. Company: Company name
3. Deal Size: Quantity (e.g., licenses, seats) and estimated value
4. Stage: Sales stage (e.g., Discovery, Negotiation, Proposal, Closing)
5. Urgency: HIGH, MEDIUM, or LOW
6. Close Date: Timeline or deadline mentioned
7. Pain Points: List of concerns or problems mentioned
8. Key Discussion: Main topics or requirements discussed

Extract this information accurately from the meeting notes. If information is not available, use null or empty values.
Return the data as a JSON object."""

    user_prompt = f"""Based on the following examples of similar meetings and their patterns, extract CRM data from the new meeting notes below.

EXAMPLES OF SIMILAR MEETINGS:
{context}

NEW MEETING NOTES TO ANALYZE:
{meeting_notes}

Extract the CRM data in the following JSON format:
{{
    "contact": {{
        "name": "Full name",
        "title": "Job title or role"
    }},
    "company": "Company name",
    "deal_size": {{
        "quantity": "e.g., 50 licenses, 100 seats",
        "value": "e.g., ~$50K, $60K range"
    }},
    "stage": "Discovery/Negotiation/Proposal/Closing/etc",
    "urgency": "HIGH/MEDIUM/LOW",
    "close_date": "Timeline or deadline",
    "pain_points": ["concern 1", "concern 2"],
    "key_discussion": "Main topics or requirements"
}}"""

    # Step 4: Call GPT-4 to extract structured data
    print("🤖 Generating structured CRM data using GPT-4...")
    try:
        response = openai_client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            #temperature=0.3,  # Lower temperature for more consistent extraction
            response_format={"type": "json_object"}  # Force JSON response
        )
        
        # Parse JSON response
        crm_data = json.loads(response.choices[0].message.content)
        
        # Validate and clean the data
        crm_data = _validate_crm_data(crm_data)
        
        print("✅ CRM data extracted successfully!")
        return crm_data
        
    except json.JSONDecodeError as e:
        print(f"⚠️  Error parsing JSON response: {e}")
        # Return a default structure if JSON parsing fails
        return _get_default_crm_structure()
    except Exception as e:
        print(f"❌ Error extracting CRM data: {e}")
        return _get_default_crm_structure()


def _validate_crm_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate and ensure CRM data has the correct structure.
    
    Args:
        data: Raw CRM data from GPT-4
    
    Returns:
        Validated CRM data with default values for missing fields
    """
    default_structure = _get_default_crm_structure()
    
    # Ensure all required fields exist
    validated = {}
    
    # Contact
    validated["contact"] = {
        "name": data.get("contact", {}).get("name") if isinstance(data.get("contact"), dict) else None,
        "title": data.get("contact", {}).get("title") if isinstance(data.get("contact"), dict) else None
    }
    if not validated["contact"]["name"]:
        validated["contact"] = default_structure["contact"]
    
    # Company
    validated["company"] = data.get("company") or default_structure["company"]
    
    # Deal Size
    if isinstance(data.get("deal_size"), dict):
        validated["deal_size"] = {
            "quantity": data["deal_size"].get("quantity") or default_structure["deal_size"]["quantity"],
            "value": data["deal_size"].get("value") or default_structure["deal_size"]["value"]
        }
    else:
        validated["deal_size"] = default_structure["deal_size"]
    
    # Stage
    validated["stage"] = data.get("stage") or default_structure["stage"]
    
    # Urgency (ensure it's uppercase and valid)
    urgency = data.get("urgency", "").upper()
    if urgency not in ["HIGH", "MEDIUM", "LOW"]:
        urgency = default_structure["urgency"]
    validated["urgency"] = urgency
    
    # Close Date
    validated["close_date"] = data.get("close_date") or default_structure["close_date"]
    
    # Pain Points (ensure it's a list)
    pain_points = data.get("pain_points", [])
    if not isinstance(pain_points, list):
        pain_points = default_structure["pain_points"]
    validated["pain_points"] = pain_points
    
    # Key Discussion
    validated["key_discussion"] = data.get("key_discussion") or default_structure["key_discussion"]
    
    return validated


def _get_default_crm_structure() -> Dict[str, Any]:
    """Return default/empty CRM data structure."""
    return {
        "contact": {
            "name": None,
            "title": None
        },
        "company": None,
        "deal_size": {
            "quantity": None,
            "value": None
        },
        "stage": "Discovery",
        "urgency": "MEDIUM",
        "close_date": None,
        "pain_points": [],
        "key_discussion": None
    }


def format_crm_output(crm_data: Dict[str, Any]) -> str:
    """
    Format CRM data as a human-readable string.
    
    Args:
        crm_data: Structured CRM data dictionary
    
    Returns:
        Formatted string representation
    """
    output = []
    output.append("CRM DATA:")
    output.append("=" * 50)
    
    # Contact
    contact = crm_data.get("contact", {})
    if contact.get("name"):
        contact_str = contact["name"]
        if contact.get("title"):
            contact_str += f", {contact['title']}"
        output.append(f"Contact: {contact_str}")
    
    # Company
    if crm_data.get("company"):
        output.append(f"Company: {crm_data['company']}")
    
    # Deal Size
    deal_size = crm_data.get("deal_size", {})
    if deal_size.get("quantity") or deal_size.get("value"):
        deal_str = ""
        if deal_size.get("quantity"):
            deal_str = deal_size["quantity"]
        if deal_size.get("value"):
            if deal_str:
                deal_str += f" ({deal_size['value']})"
            else:
                deal_str = deal_size["value"]
        output.append(f"Deal Size: {deal_str}")
    
    # Stage
    if crm_data.get("stage"):
        output.append(f"Stage: {crm_data['stage']}")
    
    # Urgency
    if crm_data.get("urgency"):
        output.append(f"Urgency: {crm_data['urgency']}")
    
    # Close Date
    if crm_data.get("close_date"):
        output.append(f"Close Date: {crm_data['close_date']}")
    
    # Pain Points
    pain_points = crm_data.get("pain_points", [])
    if pain_points:
        output.append("Pain Points:")
        for point in pain_points:
            output.append(f"  - {point}")
    
    # Key Discussion
    if crm_data.get("key_discussion"):
        output.append(f"Key Discussion: {crm_data['key_discussion']}")
    
    return "\n".join(output)
