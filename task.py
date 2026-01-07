from vdb import search_pinecone, get_openai_embedding
from openai import OpenAI
import os
from typing import Dict

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_all_meetings_context(strategy: str = "generic") -> str:
    """
    Retrieve meetings from Pinecone for task analysis
    
    Args:
        strategy: "generic" (single broad query) or "multi" (multiple queries)
    
    Returns:
        Combined context from all retrieved meetings
    """
    
    if strategy == "generic":
        # STRATEGY 1: Single broad query with high top_k
        print("🔍 Retrieving meetings with generic query...")
        results = search_pinecone(
            query_text="meeting action items follow-up tasks deadlines priorities customer",
            top_k=20  # Higher than CRM endpoint
        )
        
    elif strategy == "multi":
        # STRATEGY 2: Multiple diverse queries
        print("🔍 Retrieving meetings with multiple queries...")
        queries = [
            "urgent deadlines tasks priorities",
            "follow-up action items meetings",
            "customer discussions deals",
            "quotes proposals contracts"
        ]
        
        all_results = []
        for query in queries:
            results = search_pinecone(query, top_k=10)
            all_results.extend(results)
        
        # Remove duplicates by ID
        seen_ids = set()
        results = []
        for r in all_results:
            if r['id'] not in seen_ids:
                results.append(r)
                seen_ids.add(r['id'])
    
    # Build context from results
    context_parts = []
    for i, result in enumerate(results):
        meeting_text = result['metadata'].get('text', '')
        filename = result['metadata'].get('filename', 'Unknown')
        
        context_parts.append(
            f"--- Meeting {i+1} [{filename}] (Score: {result['score']:.3f}) ---\n{meeting_text}\n"
        )
    
    print(f"✓ Retrieved {len(results)} meetings")
    return "\n".join(context_parts)


def extract_task_priorities(meeting_notes: str = None) -> Dict:
    """
    Extract and prioritize tasks across ALL companies
    
    Args:
        meeting_notes: Optional new meeting notes to include
    
    Returns:
        Dictionary with prioritized tasks
    """
    
    # Get context from many meetings
    all_meetings_context = get_all_meetings_context(strategy="generic")
    
    # Add new meeting if provided
    if meeting_notes:
        full_context = f"{all_meetings_context}\n\n--- NEW MEETING (TO BE ADDED) ---\n{meeting_notes}"
    else:
        full_context = all_meetings_context
    
    print("🤖 Analyzing meetings and extracting tasks...")
    
    system_prompt = """You are an expert at extracting and prioritizing action items from sales meetings.

Your job:
1. Read through ALL provided meetings
2. Extract EVERY action item/task mentioned
3. Identify which COMPANY each task is for (look at filenames: acme, buildco, techstart, etc.)
4. Categorize by urgency:
   - HIGH: Due this week, critical deadlines, urgent follow-ups
   - MEDIUM: Due next week, important but not urgent
   - LOW: Ongoing tasks, long-term items
5. Sort by deadline within each priority level

Output exactly in this format:

HIGH PRIORITY (This Week)
├─ Task: [Description] - [Company Name]
│  ├─ Deadline: [When]
│  ├─ Owner: [Who]
│  └─ Details: [Context]

MEDIUM PRIORITY (Next Week)  
└─ Task: [Description] - [Company Name]
   ├─ Deadline: [When]
   └─ Owner: [Who]

LOW PRIORITY (Ongoing)
└─ Task: [Description] - [Company Name]
   └─ Owner: [Who]

CRITICAL: Always include company name with each task!"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Extract all tasks:\n\n{full_context}"}
            ]
        )
        
        tasks_output = response.choices[0].message.content
        
        return {
            "status": "success",
            "tasks": tasks_output,
            "meetings_analyzed": len(full_context.split("--- Meeting"))
        }
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "tasks": "Error extracting tasks",
            "meetings_analyzed": 0
        }


def format_task_output(task_data: Dict) -> str:
    """Format task output for display"""
    output = "TASK PRIORITY LIST\n"
    output += "=" * 70 + "\n"
    output += f"Meetings Analyzed: {task_data.get('meetings_analyzed', 0)}\n"
    output += "=" * 70 + "\n\n"
    output += task_data.get('tasks', 'No tasks found')
    
    return output