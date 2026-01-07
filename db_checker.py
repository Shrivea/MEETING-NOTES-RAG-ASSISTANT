"""
Database Validation Script
Checks the validity and integrity of data stored in Pinecone vector database.
Validates that all source files match what's stored in the database.
"""

import os
from pathlib import Path
from typing import Dict, List, Tuple, Any
import numpy as np
from dotenv import load_dotenv
from pinecone import Pinecone
from openai import OpenAI

# Import from vdb to reuse functions
from vdb import (
    DATA_DIR,
    INDEX_NAME,
    DIMENSION,
    get_openai_embedding,
    read_meeting_notes
)

load_dotenv()

# Initialize clients
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
index = pc.Index(INDEX_NAME)


class ValidationResult:
    """Container for validation results."""
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []
        self.stats = {}
    
    def add_pass(self, message: str):
        self.passed.append(message)
    
    def add_fail(self, message: str):
        self.failed.append(message)
    
    def add_warning(self, message: str):
        self.warnings.append(message)
    
    def print_summary(self):
        """Print a formatted summary of validation results."""
        print("\n" + "="*70)
        print("DATABASE VALIDATION SUMMARY")
        print("="*70)
        
        print(f"\n✓ PASSED: {len(self.passed)}")
        print(f"✗ FAILED: {len(self.failed)}")
        print(f"⚠ WARNINGS: {len(self.warnings)}")
        
        if self.stats:
            print("\n📊 STATISTICS:")
            for key, value in self.stats.items():
                print(f"   {key}: {value}")
        
        if self.failed:
            print("\n❌ FAILURES:")
            for i, failure in enumerate(self.failed, 1):
                print(f"   {i}. {failure}")
        
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for i, warning in enumerate(self.warnings, 1):
                print(f"   {i}. {warning}")
        
        if self.passed and len(self.passed) <= 20:
            print("\n✅ PASSED CHECKS:")
            for i, check in enumerate(self.passed, 1):
                print(f"   {i}. {check}")
        
        print("\n" + "="*70)
        
        # Overall status
        if not self.failed:
            print("✅ VALIDATION PASSED - Database is valid!")
        else:
            print("❌ VALIDATION FAILED - Please review the issues above.")
        print("="*70 + "\n")


def get_all_vectors_from_index() -> Dict[str, Any]:
    """
    Fetch all vectors from the Pinecone index.
    Note: Pinecone doesn't have a direct 'list all' operation,
    so we use stats and fetch operations.
    
    Returns:
        Dictionary mapping vector IDs to their data
    """
    vectors = {}
    
    try:
        # Get index stats to understand what we're working with
        stats = index.describe_index_stats()
        total_vectors = stats.get('total_vector_count', 0)
        
        if total_vectors == 0:
            return vectors
        
        # Since we know the vector IDs follow a pattern (meeting-{filename}),
        # we can try to fetch them. However, for a more robust solution,
        # we'll need to maintain a list of expected IDs from source files.
        # For now, we'll use the source files to determine expected IDs.
        
    except Exception as e:
        print(f"Error getting index stats: {e}")
    
    return vectors


def fetch_vectors_by_ids(vector_ids: List[str]) -> Dict[str, Any]:
    """
    Fetch specific vectors by their IDs.
    
    Args:
        vector_ids: List of vector IDs to fetch
        
    Returns:
        Dictionary mapping vector IDs to their data
    """
    vectors = {}
    
    if not vector_ids:
        return vectors
    
    try:
        # Fetch vectors (Pinecone allows fetching up to 1000 at a time)
        batch_size = 100
        for i in range(0, len(vector_ids), batch_size):
            batch_ids = vector_ids[i:i + batch_size]
            response = index.fetch(ids=batch_ids)
            
            for vector_id, vector_data in response.vectors.items():
                vectors[vector_id] = vector_data
                
    except Exception as e:
        print(f"Error fetching vectors: {e}")
    
    return vectors


def validate_index_stats(result: ValidationResult) -> Dict[str, Any]:
    """Validate index statistics and configuration."""
    print("\n📊 Checking index statistics...")
    
    try:
        stats = index.describe_index_stats()
        result.stats['Total Vectors'] = stats.get('total_vector_count', 0)
        result.stats['Index Dimension'] = stats.get('dimension', 'Unknown')
        result.stats['Index Fullness'] = stats.get('index_fullness', 0)
        
        # Validate dimension
        if result.stats['Index Dimension'] == DIMENSION:
            result.add_pass(f"Index dimension matches expected: {DIMENSION}")
        else:
            result.add_fail(
                f"Index dimension mismatch: expected {DIMENSION}, "
                f"got {result.stats['Index Dimension']}"
            )
        
        return stats
        
    except Exception as e:
        result.add_fail(f"Failed to get index stats: {e}")
        return {}


def validate_file_coverage(
    source_files: Dict[str, str],
    db_vectors: Dict[str, Any],
    result: ValidationResult
) -> None:
    """Validate that all source files are present in the database."""
    print("\n📁 Checking file coverage...")
    
    # Expected vector IDs based on source files
    expected_ids = {f"meeting-{filename.lower()}": filename for filename in source_files.keys()}
    
    # Check for missing files
    missing_files = []
    for vector_id, filename in expected_ids.items():
        if vector_id not in db_vectors:
            missing_files.append(filename)
            result.add_fail(f"File '{filename}' not found in database (expected ID: {vector_id})")
        else:
            result.add_pass(f"File '{filename}' found in database (ID: {vector_id})")
    
    # Check for unexpected vectors
    expected_vector_ids = set(expected_ids.keys())
    actual_vector_ids = set(db_vectors.keys())
    unexpected_ids = actual_vector_ids - expected_vector_ids
    
    if unexpected_ids:
        for vector_id in unexpected_ids:
            result.add_warning(f"Unexpected vector found in database: {vector_id}")
    
    result.stats['Expected Files'] = len(source_files)
    result.stats['Files in DB'] = len([v for v in db_vectors.keys() if v.startswith('meeting-')])
    result.stats['Missing Files'] = len(missing_files)
    result.stats['Unexpected Vectors'] = len(unexpected_ids)


def validate_text_content(
    source_files: Dict[str, str],
    db_vectors: Dict[str, Any],
    result: ValidationResult
) -> None:
    """Validate that text content in database matches source files."""
    print("\n📝 Checking text content integrity...")
    
    text_mismatches = 0
    
    for vector_id, vector_data in db_vectors.items():
        if not vector_id.startswith('meeting-'):
            continue
        
        # Extract filename from vector ID
        filename = vector_id.replace('meeting-', '').upper()
        # Handle case variations
        matching_filename = None
        for source_filename in source_files.keys():
            if source_filename.upper() == filename:
                matching_filename = source_filename
                break
        
        if not matching_filename:
            result.add_warning(f"Could not find source file for vector {vector_id}")
            continue
        
        # Get text from metadata (Vector object has metadata as attribute)
        metadata = vector_data.metadata or {}
        db_text = metadata.get('text', '').strip()
        source_text = source_files[matching_filename].strip()
        
        # Compare texts
        if db_text == source_text:
            result.add_pass(f"Text content matches for {matching_filename}")
        else:
            text_mismatches += 1
            # Show differences
            db_len = len(db_text)
            source_len = len(source_text)
            
            if db_len != source_len:
                result.add_fail(
                    f"Text length mismatch for {matching_filename}: "
                    f"DB has {db_len} chars, source has {source_len} chars"
                )
            else:
                # Find first difference
                for i, (db_char, src_char) in enumerate(zip(db_text, source_text)):
                    if db_char != src_char:
                        result.add_fail(
                            f"Text content mismatch for {matching_filename} "
                            f"at position {i}: DB='{db_char}', Source='{src_char}'"
                        )
                        break
    
    result.stats['Text Mismatches'] = text_mismatches


def validate_metadata(
    source_files: Dict[str, str],
    db_vectors: Dict[str, Any],
    result: ValidationResult
) -> None:
    """Validate metadata structure and content."""
    print("\n🏷️  Checking metadata...")
    
    required_metadata_fields = ['text', 'filename', 'source']
    
    for vector_id, vector_data in db_vectors.items():
        if not vector_id.startswith('meeting-'):
            continue
        
        metadata = vector_data.metadata or {}
        
        # Check required fields
        for field in required_metadata_fields:
            if metadata and field in metadata:
                result.add_pass(f"Metadata field '{field}' present for {vector_id}")
            else:
                result.add_fail(f"Missing required metadata field '{field}' for {vector_id}")
        
        # Validate filename matches
        if metadata and 'filename' in metadata:
            expected_filename = vector_id.replace('meeting-', '')
            actual_filename = metadata['filename'].lower()
            if actual_filename == expected_filename:
                result.add_pass(f"Metadata filename matches for {vector_id}")
            else:
                result.add_fail(
                    f"Filename mismatch for {vector_id}: "
                    f"expected '{expected_filename}', got '{actual_filename}'"
                )
        
        # Validate source
        if metadata and 'source' in metadata:
            if metadata['source'] == 'meeting_notes':
                result.add_pass(f"Source metadata correct for {vector_id}")
            else:
                result.add_warning(
                    f"Unexpected source value for {vector_id}: {metadata['source']}"
                )


def validate_embeddings(
    source_files: Dict[str, str],
    db_vectors: Dict[str, Any],
    result: ValidationResult
) -> None:
    """Validate embedding vectors."""
    print("\n🔢 Checking embeddings...")
    
    embedding_issues = 0
    
    for vector_id, vector_data in db_vectors.items():
        if not vector_id.startswith('meeting-'):
            continue
        
        values = vector_data.values or []
        
        # Check dimension
        if len(values) == DIMENSION:
            result.add_pass(f"Embedding dimension correct for {vector_id} ({DIMENSION})")
        else:
            embedding_issues += 1
            result.add_fail(
                f"Embedding dimension mismatch for {vector_id}: "
                f"expected {DIMENSION}, got {len(values)}"
            )
        
        # Check if embedding is all zeros (unlikely but possible error)
        if values and all(v == 0.0 for v in values):
            embedding_issues += 1
            result.add_fail(f"Embedding is all zeros for {vector_id}")
        
        # Validate embedding matches regenerated embedding
        metadata = vector_data.metadata or {}
        db_text = metadata.get('text', '') if metadata else ''
        
        if db_text:
            try:
                # Regenerate embedding from stored text
                regenerated_embedding = get_openai_embedding(db_text)
                
                # Compare dimensions
                if len(regenerated_embedding) != len(values):
                    result.add_warning(
                        f"Embedding dimension changed for {vector_id} "
                        f"(model may have been updated)"
                    )
                else:
                    # Check if embeddings are similar (they should be identical)
                    # Use cosine similarity check
                    db_vec = np.array(values)
                    regen_vec = np.array(regenerated_embedding)
                    
                    # Normalize vectors
                    db_norm = db_vec / (np.linalg.norm(db_vec) + 1e-10)
                    regen_norm = regen_vec / (np.linalg.norm(regen_vec) + 1e-10)
                    
                    similarity = np.dot(db_norm, regen_norm)
                    
                    if similarity > 0.99:  # Very high similarity threshold
                        result.add_pass(
                            f"Embedding validation passed for {vector_id} "
                            f"(similarity: {similarity:.4f})"
                        )
                    else:
                        result.add_warning(
                            f"Embedding similarity check for {vector_id}: {similarity:.4f} "
                            f"(may indicate model change or data corruption)"
                        )
            except Exception as e:
                result.add_warning(f"Could not validate embedding for {vector_id}: {e}")
    
    result.stats['Embedding Issues'] = embedding_issues


def validate_vector_ids(
    source_files: Dict[str, str],
    db_vectors: Dict[str, Any],
    result: ValidationResult
) -> None:
    """Validate vector ID format and consistency."""
    print("\n🆔 Checking vector IDs...")
    
    expected_pattern = "meeting-{filename}"
    
    for filename in source_files.keys():
        expected_id = f"meeting-{filename.lower()}"
        
        if expected_id in db_vectors:
            result.add_pass(f"Vector ID format correct for {filename}: {expected_id}")
        else:
            # Try to find it with different case
            found = False
            for vector_id in db_vectors.keys():
                if vector_id.lower() == expected_id.lower():
                    result.add_warning(
                        f"Vector ID case mismatch for {filename}: "
                        f"expected {expected_id}, found {vector_id}"
                    )
                    found = True
                    break
            
            if not found:
                result.add_fail(f"Vector ID not found for {filename}: {expected_id}")


def run_full_validation() -> ValidationResult:
    """Run complete database validation."""
    print("\n" + "="*70)
    print("STARTING DATABASE VALIDATION")
    print("="*70)
    
    result = ValidationResult()
    
    # Step 1: Read source files
    print("\n📂 Reading source files...")
    source_files = read_meeting_notes(DATA_DIR)
    
    if not source_files:
        result.add_fail("No source files found in data directory!")
        return result
    
    result.stats['Source Files Found'] = len(source_files)
    print(f"✓ Found {len(source_files)} source files")
    
    # Step 2: Get index statistics
    index_stats = validate_index_stats(result)
    
    # Step 3: Fetch vectors from database
    print("\n🔍 Fetching vectors from database...")
    expected_vector_ids = [f"meeting-{filename.lower()}" for filename in source_files.keys()]
    db_vectors = fetch_vectors_by_ids(expected_vector_ids)
    
    if not db_vectors:
        result.add_fail("No vectors found in database! Database may be empty.")
        return result
    
    result.stats['Vectors Fetched'] = len(db_vectors)
    print(f"✓ Fetched {len(db_vectors)} vectors from database")
    
    # Step 4: Run all validation checks
    validate_file_coverage(source_files, db_vectors, result)
    validate_vector_ids(source_files, db_vectors, result)
    validate_text_content(source_files, db_vectors, result)
    validate_metadata(source_files, db_vectors, result)
    validate_embeddings(source_files, db_vectors, result)
    
    return result


if __name__ == "__main__":
    result = run_full_validation()
    result.print_summary()

