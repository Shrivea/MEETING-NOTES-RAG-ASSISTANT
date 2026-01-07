import os
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Initialize clients
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Index configuration
INDEX_NAME = "meeting-notes"
DIMENSION = 1536  # OpenAI text-embedding-3-small default dimension
DATA_DIR = Path(__file__).parent / "data"

# Check if index exists, create if it doesn't
existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]

if INDEX_NAME not in existing_indexes:
    print(f"Creating index '{INDEX_NAME}'...")
    pc.create_index(
        name=INDEX_NAME,
        dimension=DIMENSION,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )
    # Wait for index to be ready
    print("Waiting for index to be ready...")
    while not pc.describe_index(INDEX_NAME).status["ready"]:
        time.sleep(1)
    print(f"Index '{INDEX_NAME}' is ready!")
else:
    print(f"Index '{INDEX_NAME}' already exists.")

# Get the index
index = pc.Index(INDEX_NAME)


def get_openai_embedding(text: str) -> list:
    """
    Generate embedding for text using OpenAI's text-embedding-3-small model.
    
    Args:
        text: The text to generate an embedding for
        
    Returns:
        List of floats representing the embedding vector (1536 dimensions)
    """
    response = openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding


def upsert_to_pinecone(
    vector_id: str, 
    embedding: list, 
    text: str, 
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Upsert a vector to Pinecone with metadata.
    
    Args:
        vector_id: Unique identifier for the vector (e.g., "acme-2024-01-04")
        embedding: The embedding vector (list of floats)
        text: The original text content (stored in metadata)
        metadata: Additional metadata dictionary (optional)
    
    Example:
        upsert_to_pinecone(
            vector_id="acme-001",
            embedding=[0.1, 0.2, ...],
            text="Meeting notes...",
            metadata={"company": "ACME", "contact": "Sarah Chen"}
        )
    """
    # Prepare metadata - always include the original text
    vector_metadata = {"text": text}
    if metadata:
        vector_metadata.update(metadata)
    
    # Upsert to Pinecone
    # Format: (id, vector, metadata)
    index.upsert(
        vectors=[{
            "id": vector_id,
            "values": embedding,
            "metadata": vector_metadata
        }]
    )


def search_pinecone(
    query_text: str, 
    top_k: int = 5,
    include_metadata: bool = True
) -> List[Dict[str, Any]]:
    """
    Search Pinecone for similar meeting notes using semantic similarity.
    
    Args:
        query_text: The search query text (will be embedded automatically)
        top_k: Number of results to return (default: 5)
        include_metadata: Whether to include metadata in results (default: True)
    
    Returns:
        List of dictionaries containing:
        - id: Vector ID
        - score: Similarity score (higher = more similar)
        - metadata: Dictionary with text and other metadata
    
    Example:
        results = search_pinecone("ACME Corp quote deadline", top_k=3)
        for result in results:
            print(f"Score: {result['score']}, Text: {result['metadata']['text']}")
    """
    # Generate embedding for the query text
    query_embedding = get_openai_embedding(query_text)
    
    # Search Pinecone
    response = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=include_metadata
    )
    
    # Format results
    results = []
    for match in response.matches:
        results.append({
            "id": match.id,
            "score": match.score,
            "metadata": match.metadata if include_metadata else {}
        })
    
    return results


def read_meeting_notes(data_dir: Path = DATA_DIR) -> Dict[str, str]:
    """
    Read all .txt files from the data directory.
    
    Args:
        data_dir: Path to the data directory (default: ./data)
    
    Returns:
        Dictionary mapping filename (without extension) to file content
    """
    meeting_notes = {}
    
    if not data_dir.exists():
        print(f"Warning: Data directory {data_dir} does not exist!")
        return meeting_notes
    
    # Read all .txt files
    for txt_file in data_dir.glob("*.txt"):
        filename = txt_file.stem  # filename without extension
        with open(txt_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
            meeting_notes[filename] = content
            print(f"✓ Read {filename}.txt ({len(content)} characters)")
    
    return meeting_notes


def populate_database(data_dir: Path = DATA_DIR, overwrite: bool = False) -> None:
    """
    Populate Pinecone database with meeting notes from data directory.
    
    This function:
    1. Reads all .txt files from the data directory
    2. Generates embeddings for each meeting note
    3. Upserts them to Pinecone with metadata
    
    Args:
        data_dir: Path to the data directory (default: ./data)
        overwrite: If True, will delete existing vectors before upserting (default: False)
    
    Example:
        populate_database()  # Populate with all meeting notes
    """
    print("\n" + "="*50)
    print("POPULATING PINECONE DATABASE")
    print("="*50 + "\n")
    
    # Read all meeting notes
    meeting_notes = read_meeting_notes(data_dir)
    
    if not meeting_notes:
        print("No meeting notes found to populate!")
        return
    
    print(f"\nFound {len(meeting_notes)} meeting note files\n")
    
    # Process each meeting note
    for filename, text in meeting_notes.items():
        print(f"Processing {filename}...")
        
        # Generate embedding
        print(f"  → Generating embedding...")
        embedding = get_openai_embedding(text)
        
        # Create metadata
        metadata = {
            "filename": filename,
            "source": "meeting_notes"
        }
        
        # Create unique ID (using filename as base)
        vector_id = f"meeting-{filename.lower()}"
        
        # Upsert to Pinecone
        print(f"  → Upserting to Pinecone (ID: {vector_id})...")
        upsert_to_pinecone(
            vector_id=vector_id,
            embedding=embedding,
            text=text,
            metadata=metadata
        )
        
        print(f"  ✓ Successfully added {filename}\n")
    
    print("="*50)
    print(f"✓ Database population complete! Added {len(meeting_notes)} meeting notes.")
    print("="*50 + "\n")


if __name__ == "__main__":
    # Populate database when script is run directly
    populate_database()