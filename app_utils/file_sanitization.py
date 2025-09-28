import os
import re
import mimetypes
import hashlib
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

# Import the general sanitization utilities
from app_utils.sanitization import sanitize_string

# Safe file extensions and MIME types
SAFE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp',  # Images
    '.pdf', '.txt', '.csv', '.xlsx', '.docx',  # Documents
    '.mp4', '.webm', '.mp3', '.wav',  # Media
    '.json', '.xml'  # Data
}

SAFE_MIME_TYPES = {
    'image/jpeg', 'image/png', 'image/gif', 'image/svg+xml', 'image/webp',
    'application/pdf', 'text/plain', 'text/csv', 
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'video/mp4', 'video/webm', 'audio/mpeg', 'audio/wav',
    'application/json', 'application/xml'
}

# Maximum file size (10MB by default)
MAX_FILE_SIZE = 10 * 1024 * 1024

def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal and command injection.
    
    Args:
        filename: The original filename
        
    Returns:
        A sanitized filename
    """
    # Remove any directory components
    filename = os.path.basename(filename)
    
    # Remove any potentially dangerous characters
    filename = re.sub(r'[^\w\.-]', '_', filename)
    
    # Ensure the filename doesn't start with a dot (hidden file)
    if filename.startswith('.'):
        filename = 'f' + filename
        
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        name = name[:245]  # Leave room for extension
        filename = name + ext
        
    return filename

def validate_file_content(file_path: str, expected_mime_type: Optional[str] = None) -> Tuple[bool, str]:
    """
    Validate file content by checking its actual MIME type.
    
    Args:
        file_path: Path to the file
        expected_mime_type: Expected MIME type (optional)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Use mimetypes to guess the MIME type based on file extension
        detected_mime, _ = mimetypes.guess_type(file_path)
        
        if not detected_mime:
            return False, "Could not determine file type"

        # Check if the detected MIME type is in our safe list
        if detected_mime not in SAFE_MIME_TYPES:
            return False, f"Unsafe file type detected: {detected_mime}"
        
        # If an expected MIME type was provided, verify it matches
        if expected_mime_type and detected_mime != expected_mime_type:
            return False, f"File type mismatch: expected {expected_mime_type}, got {detected_mime}"
            
        return True, ""
    except Exception as e:
        return False, f"Error validating file content: {str(e)}"

def compute_file_hash(file_path: str) -> str:
    """
    Compute SHA-256 hash of a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        SHA-256 hash as a hexadecimal string
    """
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def sanitize_file_upload(file_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize and validate a file upload.
    
    Args:
        file_data: Dictionary containing file information
            - filename: Original filename
            - content_type: Declared content type
            - file_path: Path to the temporary file
            - size: File size in bytes
            
    Returns:
        Dictionary with validation results
        - is_valid: Boolean indicating if the file is safe
        - sanitized_filename: Sanitized version of the filename
        - error: Error message if validation failed
        - file_hash: SHA-256 hash of the file (if valid)
    """
    result = {
        "is_valid": False,
        "sanitized_filename": "",
        "error": "",
        "file_hash": ""
    }
    
    # Check if required fields are present
    required_fields = ["filename", "content_type", "file_path", "size"]
    for field in required_fields:
        if field not in file_data:
            result["error"] = f"Missing required field: {field}"
            return result
    
    # Sanitize filename
    original_filename = file_data["filename"]
    sanitized_filename = sanitize_filename(original_filename)
    result["sanitized_filename"] = sanitized_filename
    
    # Check file size
    if file_data["size"] > MAX_FILE_SIZE:
        result["error"] = f"File too large: {file_data['size']} bytes (max {MAX_FILE_SIZE} bytes)"
        return result
    
    # Check file extension
    file_ext = os.path.splitext(sanitized_filename)[1].lower()
    if file_ext not in SAFE_EXTENSIONS:
        result["error"] = f"Unsafe file extension: {file_ext}"
        return result
    
    # Validate file content
    is_valid, error = validate_file_content(file_data["file_path"], file_data["content_type"])
    if not is_valid:
        result["error"] = error
        return result
    
    # Compute file hash for integrity verification
    result["file_hash"] = compute_file_hash(file_data["file_path"])
    result["is_valid"] = True
    
    return result

def get_safe_upload_path(base_dir: str, filename: str, user_id: Optional[str] = None) -> str:
    """
    Generate a safe path for storing an uploaded file.
    
    Args:
        base_dir: Base directory for uploads
        filename: Sanitized filename
        user_id: Optional user ID for user-specific directories
        
    Returns:
        A safe absolute path for the file
    """
    # Create a directory structure that prevents path traversal
    if user_id:
        # Sanitize user_id to prevent directory traversal
        safe_user_id = re.sub(r'[^\w-]', '_', str(user_id))
        upload_dir = os.path.join(base_dir, safe_user_id)
    else:
        upload_dir = os.path.join(base_dir, 'public')
    
    # Ensure the directory exists
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate a unique filename to prevent overwriting
    name, ext = os.path.splitext(filename)
    timestamp = hashlib.md5(str(os.urandom(32)).encode()).hexdigest()[:8]
    unique_filename = f"{name}_{timestamp}{ext}"
    
    # Return the full path
    return os.path.join(upload_dir, unique_filename)