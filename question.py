from vdb import search_pinecone, get_openai_embedding
from openai import OpenAI
import os
from typing import Dict

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_relevant_context_for_question(question: str, top_k: int = 5) -> str:
    """
    Retrieve relevant meetings for answering the question
    
    Args:
        question: The user's question (e.g., "Who is our contact at ACME?")
        top_k: Number of relevant meetings to retrieve
    
    Returns:
        Combined context from relevant meetings
    """
    
    print(f"🔍 Searching for meetings relevant to: '{question}'")
    #pass question directly
    results = search_pinecone(query_text=question, top_k=top_k)
    
    # Extract text and filename from each result's metadata
    context_parts = []
    for result in results:
        meeting_text = result['metadata'].get('text', '')
        filename = result['metadata'].get('filename', 'Unknown')
        context_parts.append(f"--- {filename} ---\n{meeting_text}\n")
    return "\n".join(context_parts)
    
    pass


def answer_question(question: str) -> Dict:
    """
    Answer a question based on meeting notes in the database
    
    Args:
        question: The user's question
    
    Returns:
        Dictionary with answer and metadata
    """
    
    #  Validate input
    if not question or question.strip() == "":
        return {
            "status": "error",
            "question": question if question else "None",
            "answer": "Please provide a valid question",
            "meetings_used": 0,
            "error": "Empty or invalid question provided"
        }
    
    #  Get relevant context
    context = get_relevant_context_for_question(question, top_k=5)
    
    #  Build system prompt
    #  Tell GPT it's a helpful assistant that answers based ONLY on provided meetings
    system_prompt = """
    You are a helpful assistant that answers questions based ONLY on the provided meeting notes.
    Rules:
    - Answer based on the context provided
    - If the answer isn't in the meetings, say "I don't have that information"
    - Be concise and direct
    - Cite specific companies/names when relevant
    - OUTPUT your answers:
    QUESTION & ANSWER
    ======================================================================
    Q: What companies did we meet with this week?
    ----------------------------------------------------------------------
    A: We met with five companies this week: ACME Corp (Sarah Chen), 
    TechStart (Mike Patterson), BuildCo Inc. (Jane Martinez), DataFlow 
    Systems (Marcus Johnson), and NexGen Solutions (Rebecca Torres).
    ======================================================================
    Based on 5 relevant meetings"""
    
    # Build user prompt
    # Include both the context and the question
    user_prompt = f"""Context from meetings:\n{context}\n\nQuestion: {question}"""
    
    print("🤖 Generating answer using GPT...")
    
    try:
        response = client.chat.completions.create(
             model="gpt-4o-mini",
             messages=[
                 {"role": "system", "content": system_prompt},
                 {"role": "user", "content": user_prompt}
             ],
             timeout=60
         )
        
        # Extract answer
        answer = response.choices[0].message.content
        
        # Return structured response
        return {
            "status": "success",
             "question": question,
             "answer": answer,
             "meetings_used": len(context.split("---"))
        }
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "meetings_analyzed": 0
        }

def format_qa_output(qa_data: Dict) -> str:
    """
    Format Q&A output for display
    
    Args:
        qa_data: Dictionary containing question and answer
    
    Returns:
        Formatted string
    """
    
 
    output = "QUESTION & ANSWER\n"
    output += "=" * 70 + "\n"
    output += f"Q: {qa_data.get('question', 'N/A')}\n"
    output += "-" * 70 + "\n"
    output += f"A: {qa_data.get('answer', 'N/A')}\n"
    output += "=" * 70 + "\n"
    output += f"Based on {qa_data.get('meetings_used', 0)} relevant meetings"
    return output
    
   