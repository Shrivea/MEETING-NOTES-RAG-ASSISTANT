from pydantic import BaseModel
import fastapi
from fastapi import HTTPException
from typing import Optional
import json
import os
from dotenv import load_dotenv
import uvicorn
from CRM import extract_crm_data, format_crm_output
from task import get_all_meetings_context, extract_task_priorities, format_task_output
from vdb import index
from question import answer_question, format_qa_output

load_dotenv()

class MeetingInput(BaseModel):
    meeting_notes: Optional[str] = None

class VectorIdInput(BaseModel):
    vector_id: str
class QuestionInput(BaseModel):
    question: str

app = fastapi.FastAPI(
    title="Meeting Notes AI Agent",
    description="Converts meeting notes into structured CRM data, tasks, and Q&A"
)

@app.post("/crm-data")
def get_crm_data(input: VectorIdInput):
    """
    Extract structured CRM data from a meeting stored in the database.
    
    This endpoint:
    1. Fetches meeting notes from Pinecone database using vector_id
    2. Uses RAG to retrieve similar past meetings
    3. Extracts structured CRM data using GPT-4
    
    Args:
        input: VectorIdInput model containing vector_id (e.g., "meeting-acme", "meeting-techstart")
    
    Returns:
        JSON object with structured CRM data
    
    Example:
        POST /crm-data
        Body: {"vector_id": "meeting-acme"}
    """
    try:
        # Validate input
        if not input.vector_id:
            return {
                "status": "error",
                "message": "vector_id is required"
            }
        
        vector_id = input.vector_id
        
        # Step 1: Fetch meeting notes from database using vector_id
        response = index.fetch(ids=[vector_id])
        
        # Fallback: Check if vector exists (invalid ID handling)
        if vector_id not in response.vectors:
            return {
                "status": "error",
                "message": f"Vector ID '{vector_id}' not found in database. Please use a valid ID like: meeting-acme, meeting-buildco, meeting-techstart, meeting-nextgen, or meeting-dataflow"
            }
        
        # Step 2: Extract meeting notes text from metadata
        vector_data = response.vectors[vector_id]
        metadata = vector_data.metadata or {}
        meeting_notes = metadata.get('text', '')
        
        if not meeting_notes:
            return {
                "status": "error",
                "message": f"No meeting notes found for vector ID '{vector_id}'"
            }
        
        # Step 3: Extract CRM data using RAG
        crm_data = extract_crm_data(meeting_notes)
        
        return {
            "status": "success",
            "vector_id": vector_id,
            "data": crm_data,
            "formatted": format_crm_output(crm_data)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@app.post("/task-data")
def get_task_data(request: MeetingInput):
    """
    Extract and prioritize tasks across all companies
    
    Optional: Include new meeting notes to add to analysis
    """
    try:
        # Extract tasks (works with or without new meeting notes)
        task_data = extract_task_priorities(request.meeting_notes)
        
        return {
            "status": task_data["status"],
            "tasks": task_data["tasks"],
            "meetings_analyzed": task_data["meetings_analyzed"],
            "formatted_output": format_task_output(task_data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/question-answer-data")
def get_question_answer_data(input: QuestionInput):
    """
    Answer questions based on meeting notes in the database
    
    This endpoint:
    1. Takes a user question as input
    2. Searches Pinecone for relevant meetings
    3. Uses GPT to answer based on retrieved context
    
    Args:
        input: QuestionInput model containing the question
    
    Returns:
        JSON object with the answer
    
    Example:
        POST /question-answer-data
        Body: {"question": "What companies did we meet with this week?"}
    """
    try:
        err_str = "Question is invalid"
        if not input.question or input.question.strip() == "":
            raise HTTPException(
                status_code=422, 
                detail=err_str
            )
        #answer questions
        qa_data = answer_question(input.question)   
        #we get this as a dictionary
        # now we can exttract the necessary fields 
        return {
            "status": qa_data["status"],
            "question": qa_data["question"],
            "answer": qa_data["answer"],
            "meetings_used": qa_data["meetings_used"],
            "formatted_output": format_qa_output(qa_data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

             

@app.get("/")
def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "endpoints": {
            "crm": "POST /crm-data",
            "tasks": "POST /task-data",
            "qa": "GET /question-answer-data"
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)