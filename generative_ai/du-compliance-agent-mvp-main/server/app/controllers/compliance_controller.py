import os
import sys
import time
import asyncio
import json
import hashlib
import uuid
import re
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from typing import List, Optional, Dict
from app.utils.stream_emitter import StreamEmitter
from app.utils.file_converter import file_to_markdown
from app.utils.document_gatekeeper import validate_document_relevance
from app.utils.llm_compliance_evaluator import (
    read_markdown_files,
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_USER_PROMPT,
    FIXED_SYSTEM_PREFIX
)
from app.utils.regulation_names import get_regulation_display_name
from app.utils.json_schema import get_default_columns, validate_column_name, validate_description
from app.services.compliance_service import ComplianceService

router = APIRouter()
service = ComplianceService()

# Ensure /tmp directory exists
TMP_DIR = "/tmp"
os.makedirs(TMP_DIR, exist_ok=True)

# Get confidence threshold from environment variable, default to 70
def get_confidence_threshold() -> int:
    """Get gatekeeper confidence threshold from environment variable."""
    try:
        threshold_str = os.environ.get("GATEKEEPER_CONFIDENCE_THRESHOLD", "70")
        threshold = int(threshold_str)
        # Validate range (0-100)
        if threshold < 0 or threshold > 100:
            print("Warning: GATEKEEPER_CONFIDENCE_THRESHOLD out of range (0-100), using default 70", file=sys.stderr)
            return 70
        return threshold
    except (ValueError, TypeError):
        print("Warning: Invalid GATEKEEPER_CONFIDENCE_THRESHOLD value, using default 70", file=sys.stderr)
        return 70

CONFIDENCE_THRESHOLD = get_confidence_threshold()
print(f"Info: Gatekeeper confidence threshold set to {CONFIDENCE_THRESHOLD}", file=sys.stderr)

# Maximum file size for Excel files (10MB)
MAX_EXCEL_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes
EXCEL_EXTENSIONS = {'.csv', '.xlsx', '.xls', '.xlsm'}

# Store user-uploaded policy files temporarily (session_id -> {original_filename -> file_path})
# This ensures each upload session has isolated file storage
# In production, this could be replaced with a proper session storage or database
user_policy_files: Dict[str, Dict[str, str]] = {}

# Store mapping from custom names to original filenames (session_id -> {custom_name -> original_filename})
# This allows lookup by custom name while using original filename as the unique key
policy_custom_name_map: Dict[str, Dict[str, str]] = {}


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal attacks.
    
    Args:
        filename: Original filename from user upload
        
    Returns:
        Sanitized filename safe for use in file paths
        
    Security measures:
        - Uses os.path.basename() to remove any directory components
        - Removes/replaces dangerous characters (path separators, null bytes, etc.)
        - Replaces spaces with underscores for consistency
    """
    if not filename:
        return "unnamed_file"
    
    # Extract only the filename component (removes any directory path)
    # This prevents path traversal attacks like "../../../etc/passwd"
    basename = os.path.basename(filename)
    
    # Remove null bytes and other control characters
    # Replace path separators and other dangerous characters
    sanitized = basename.replace("\x00", "")  # Remove null bytes
    sanitized = sanitized.replace("/", "_")    # Replace forward slashes
    sanitized = sanitized.replace("\\", "_")  # Replace backslashes
    sanitized = sanitized.replace(" ", "_")   # Replace spaces
    
    # Remove any remaining dangerous characters (colons on Windows, etc.)
    # Keep only alphanumeric, dots, hyphens, and underscores
    sanitized = re.sub(r'[^\w\.\-]', '_', sanitized)
    
    # Ensure the filename is not empty after sanitization
    if not sanitized or sanitized.strip() == "":
        sanitized = "unnamed_file"
    
    # Limit filename length to prevent filesystem issues
    max_length = 255
    if len(sanitized) > max_length:
        # Keep extension if present
        name, ext = os.path.splitext(sanitized)
        max_name_length = max_length - len(ext)
        sanitized = name[:max_name_length] + ext
    
    return sanitized


def validate_path_within_tmp_dir(file_path: str) -> str:
    """
    Validate that a file path is within TMP_DIR to prevent path traversal attacks.
    
    Args:
        file_path: The file path to validate
        
    Returns:
        The normalized absolute path if valid
        
    Raises:
        ValueError: If the path is outside TMP_DIR
    """
    # Get absolute paths for comparison
    abs_tmp_dir = os.path.abspath(TMP_DIR)
    abs_file_path = os.path.abspath(file_path)
    
    # Ensure the file path is within TMP_DIR
    if not abs_file_path.startswith(abs_tmp_dir):
        raise ValueError(f"Path traversal detected: {file_path} is outside {TMP_DIR}")
    
    return abs_file_path


@router.get("/api/compliance/regulations")
async def get_regulations():
    """
    Get list of available regulations with their display names.
    Returns a list of regulations with filename and display name.
    """
    knowledge_base_dir = service.knowledge_base_dir
    regulations = read_markdown_files(knowledge_base_dir)
    
    result = []
    for regulation_name, _ in regulations:
        display_name = get_regulation_display_name(regulation_name)
        result.append({
            "filename": regulation_name,
            "displayName": display_name
        })
    
    return {"regulations": result}


@router.get("/api/compliance/default-columns")
async def get_default_columns_endpoint():
    """
    Get list of default columns for the compliance report.
    Returns the column definitions from the default schema.
    """
    columns = get_default_columns()
    return {"columns": columns}


@router.get("/api/compliance/default-prompts")
async def get_default_prompts_endpoint():
    """
    Get default system and user prompts for the compliance evaluation.
    Returns the editable portions of the prompts (excluding the fixed prefix).
    
    The fixed system prompt prefix is: "You are a meticulous compliance analyst working at du (ETIC)."
    This prefix is always prepended to the system prompt and cannot be modified.
    
    Note: The actual prompts sent to the LLM will also include:
    - Output format definition (column keys and descriptions)
    - Criticality instructions (if a criticality column is present)
    - Clause text instructions (if a clause text column is present)
    These are automatically appended based on the column definitions.
    """
    # Import the default prompts from the evaluator module
    # These are the editable portions (without the fixed prefix)
    return {
        "systemPrompt": DEFAULT_SYSTEM_PROMPT,
        "userPrompt": DEFAULT_USER_PROMPT,
        "fixedPrefix": FIXED_SYSTEM_PREFIX
    }


@router.post("/api/compliance/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    selected_regulations: Optional[str] = Form(None),
    policy_files: Optional[List[UploadFile]] = File(None),
    policy_custom_names: Optional[str] = Form(None),
    custom_columns: Optional[str] = Form(None),
    custom_system_prompt: Optional[str] = Form(None),
    custom_user_prompt: Optional[str] = Form(None)
):
    """
    Upload and process PDF files for compliance verification.
    Returns a streaming response with status updates.
    
    Args:
        files: List of uploaded files
        selected_regulations: Optional JSON string of selected regulation filenames
        policy_files: Optional list of user-uploaded policy files
        policy_custom_names: Optional JSON string mapping original filenames to custom names
        custom_columns: Optional JSON string of custom column definitions
        custom_system_prompt: Optional custom system prompt (editable portion)
        custom_user_prompt: Optional custom user prompt
    """
    emitter = StreamEmitter()
    
    # Parse selected regulations if provided
    # If selected_regulations is provided (even as empty string), parse it
    # This allows us to distinguish between "no selection provided" (None) and "empty selection" ([])
    selected_regulations_list = None
    if selected_regulations is not None:
        try:
            parsed = json.loads(selected_regulations)
            if isinstance(parsed, list):
                # Always use the list, even if empty (empty list means user deselected all)
                selected_regulations_list = parsed
            else:
                # Invalid format, treat as None (backward compatible)
                selected_regulations_list = None
        except (json.JSONDecodeError, TypeError):
            # Invalid JSON, treat as None (backward compatible)
            selected_regulations_list = None
    
    # Parse custom names mapping if provided
    policy_custom_names_dict: Dict[str, str] = {}
    if policy_custom_names is not None:
        try:
            parsed = json.loads(policy_custom_names)
            if isinstance(parsed, dict):
                policy_custom_names_dict = parsed
        except (json.JSONDecodeError, TypeError):
            # Invalid JSON, treat as empty dict (backward compatible)
            policy_custom_names_dict = {}
    
    # Parse and validate custom columns if provided
    custom_columns_list: Optional[List[Dict]] = None
    if custom_columns is not None:
        try:
            parsed = json.loads(custom_columns)
            if isinstance(parsed, list):
                # Validate each column
                validated_columns = []
                for col in parsed:
                    if not isinstance(col, dict):
                        continue
                    
                    name = col.get("name", "")
                    description = col.get("description", "")
                    
                    # Validate name
                    is_valid, error = validate_column_name(name)
                    if not is_valid:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid column name '{name}': {error}"
                        )
                    
                    # Validate description
                    is_valid, error = validate_description(description)
                    if not is_valid:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid description for column '{name}': {error}"
                        )
                    
                    validated_columns.append({
                        "name": name,
                        "description": description,
                        "type": col.get("type", "string"),
                        "enum": col.get("enum")
                    })
                
                custom_columns_list = validated_columns if validated_columns else None
        except json.JSONDecodeError:
            # Invalid JSON, treat as None (backward compatible)
            custom_columns_list = None
        except HTTPException:
            # Re-raise HTTP exceptions for validation errors
            raise
    
    # Validate and sanitize custom prompts if provided
    # Custom prompts are plain strings, not JSON, so just validate length and content
    validated_system_prompt: Optional[str] = None
    if custom_system_prompt is not None and custom_system_prompt.strip():
        # Basic validation: ensure it's not too long (max 6000 characters)
        if len(custom_system_prompt) > 6000:
            raise HTTPException(
                status_code=400,
                detail="Custom system prompt must be at most 6000 characters"
            )
        validated_system_prompt = custom_system_prompt.strip()
    
    validated_user_prompt: Optional[str] = None
    if custom_user_prompt is not None and custom_user_prompt.strip():
        # Basic validation: ensure it's not too long (max 2000 characters)
        if len(custom_user_prompt) > 2000:
            raise HTTPException(
                status_code=400,
                detail="Custom user prompt must be at most 2000 characters"
            )
        validated_user_prompt = custom_user_prompt.strip()
    
    async def process():
        all_issues = []
        valid_files = []  # Store valid files with their content and metadata
        user_uploaded_regulations = []  # Store user-uploaded policy files as (filename, markdown_content) tuples
        policy_file_paths = []  # Store paths to policy files for cleanup
        
        # Generate a unique session ID for this upload request
        # This ensures file isolation between different users/requests
        session_id = str(uuid.uuid4())
        
        # Initialize session storage for this request
        user_policy_files[session_id] = {}
        policy_custom_name_map[session_id] = {}
        
        # PHASE 0: Process user-uploaded policy files
        if policy_files:
            for policy_file in policy_files:
                timestamp = int(time.time() * 1000)
                # Sanitize filename to prevent path traversal attacks
                safe_filename = sanitize_filename(policy_file.filename)
                # Create a unique ID for the file based on filename and timestamp
                file_id = hashlib.md5(f"{policy_file.filename}_{timestamp}".encode()).hexdigest()
                policy_file_path = os.path.join(TMP_DIR, f"policy_upload_{file_id}_{safe_filename}")
                # Validate path is within TMP_DIR to prevent path traversal attacks
                policy_file_path = validate_path_within_tmp_dir(policy_file_path)
                policy_file_paths.append(policy_file_path)
                
                # Get custom name if available, otherwise use original filename
                policy_name = policy_custom_names_dict.get(policy_file.filename, policy_file.filename)
                original_filename = policy_file.filename
                
                try:
                    # Read and save policy file
                    file_bytes = await policy_file.read()
                    with open(policy_file_path, "wb") as f:
                        f.write(file_bytes)
                    
                    # Store file path using original filename as key (ensures uniqueness)
                    # Store in session-specific dictionary to prevent cross-user access
                    user_policy_files[session_id][original_filename] = policy_file_path
                    
                    # Store mapping from custom name to original filename
                    # This allows lookup by custom name when generating URLs
                    policy_custom_name_map[session_id][policy_name] = original_filename
                    
                    # Convert to markdown
                    try:
                        loop = asyncio.get_event_loop()
                        markdown_content = await loop.run_in_executor(
                            None,
                            file_to_markdown,
                            policy_file_path
                        )
                        # Store as (custom_name, markdown_content) tuple
                        user_uploaded_regulations.append((policy_name, markdown_content))
                    except Exception as e:
                        print(f"Error converting policy file {policy_file.filename} to markdown: {e}")
                        # Continue with other policy files even if one fails
                        if session_id in user_policy_files and original_filename in user_policy_files[session_id]:
                            del user_policy_files[session_id][original_filename]
                        if session_id in policy_custom_name_map and policy_name in policy_custom_name_map[session_id]:
                            del policy_custom_name_map[session_id][policy_name]
                        if os.path.exists(policy_file_path):
                            try:
                                os.remove(policy_file_path)
                            except Exception as e2:
                                print(f"Error removing policy file {policy_file_path}: {e2}")
                except Exception as e:
                    print(f"Error processing policy file {policy_file.filename}: {e}")
                    # Clean up on error
                    if session_id in user_policy_files and original_filename in user_policy_files[session_id]:
                        del user_policy_files[session_id][original_filename]
                    if session_id in policy_custom_name_map and policy_name in policy_custom_name_map[session_id]:
                        del policy_custom_name_map[session_id][policy_name]
                    if os.path.exists(policy_file_path):
                        try:
                            os.remove(policy_file_path)
                        except Exception as e2:
                            print(f"Error removing policy file {policy_file_path}: {e2}")
        
        # PHASE 1: Validate all files first
        for file in files:
            # Create unique filename for /tmp storage
            timestamp = int(time.time() * 1000)
            # Sanitize filename to prevent path traversal attacks
            safe_filename = sanitize_filename(file.filename)
            file_path = os.path.join(TMP_DIR, f"compliance_upload_{timestamp}_{safe_filename}")
            # Validate path is within TMP_DIR to prevent path traversal attacks
            file_path = validate_path_within_tmp_dir(file_path)
            
            # Read and save file with progress tracking
            chunk_size = 8192  # 8KB chunks
            total_size = 0
            
            try:
                # Read file content
                file_bytes = await file.read()
                total_size = len(file_bytes)
                
                # Check file size limit for Excel files
                file_ext = os.path.splitext(file.filename)[1].lower() if file.filename else ''
                if file_ext in EXCEL_EXTENSIONS and total_size > MAX_EXCEL_FILE_SIZE:
                    # File size exceeds limit for Excel files
                    size_mb = total_size / (1024 * 1024)
                    await emitter.emit({
                        "type": "document_invalid",
                        "data": {
                            "filename": file.filename,
                            "reason": f"File size ({size_mb:.1f}MB) exceeds the 10MB limit for Excel files. Please upload a smaller file."
                        }
                    })
                    continue  # Skip to next file
                
                # Save to /tmp with progress emission
                with open(file_path, "wb") as f:
                    bytes_written = 0
                    for i in range(0, len(file_bytes), chunk_size):
                        chunk = file_bytes[i:i + chunk_size]
                        f.write(chunk)
                        bytes_written += len(chunk)
                        
                        # Calculate and emit progress
                        progress = int((bytes_written / total_size) * 100) if total_size > 0 else 100
                        await emitter.emit({
                            "type": "uploading",
                            "data": {
                                "filename": file.filename,
                                "progress": progress
                            }
                        })
                
                # Emit parsing status
                await emitter.emit({
                    "type": "parsing",
                    "data": {"filename": file.filename}
                })
                
                # Convert file to markdown format
                try:
                    file_content = file_to_markdown(file_path)
                    
                    # Check if content is empty or contains only a title (no actual data)
                    if file_ext in EXCEL_EXTENSIONS:
                        # For Excel files, check if content is meaningful
                        content_lines = [line.strip() for line in file_content.split('\n') if line.strip()]
                        # A valid Excel markdown should have at least a title and a table header
                        if len(content_lines) < 3:
                            raise ValueError("Excel file contains no readable data")
                            
                except ValueError as e:
                    # ValueError indicates empty file or corrupted data
                    error_msg = str(e)
                    print(f"Error converting file to markdown (ValueError): {e}")
                    await emitter.emit({
                        "type": "document_invalid",
                        "data": {
                            "filename": file.filename,
                            "reason": f"Unable to process file: {error_msg}"
                        }
                    })
                    # Clean up and continue to next file
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                        except Exception as e2:
                            print(f"Error removing file {file_path}: {e2}")
                    continue  # Skip to next file
                    
                except RuntimeError as e:
                    # RuntimeError indicates missing dependencies or read errors
                    error_msg = str(e)
                    print(f"Error converting file to markdown (RuntimeError): {e}")
                    await emitter.emit({
                        "type": "document_invalid",
                        "data": {
                            "filename": file.filename,
                            "reason": f"Unable to process file: {error_msg}"
                        }
                    })
                    # Clean up and continue to next file
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                        except Exception as e2:
                            print(f"Error removing file {file_path}: {e2}")
                    continue  # Skip to next file
                    
                except Exception as e:
                    # General conversion error
                    error_msg = str(e)
                    print(f"Error converting file to markdown: {e}")
                    
                    # For Excel files, emit document_invalid instead of sending error text to gatekeeper
                    if file_ext in EXCEL_EXTENSIONS:
                        await emitter.emit({
                            "type": "document_invalid",
                            "data": {
                                "filename": file.filename,
                                "reason": f"Error processing Excel file: {error_msg}"
                            }
                        })
                        # Clean up and continue to next file
                        if os.path.exists(file_path):
                            try:
                                os.remove(file_path)
                            except Exception as e2:
                                print(f"Error removing file {file_path}: {e2}")
                        continue  # Skip to next file
                    else:
                        # For non-Excel files, keep original behavior
                        file_content = f"Error converting file: {error_msg}"
                
                # Emit validating status
                await emitter.emit({
                    "type": "validating",
                    "data": {"filename": file.filename}
                })
                
                # Validate document relevance using gatekeeper
                try:
                    # Run in executor to avoid blocking async loop
                    loop = asyncio.get_event_loop()
                    validation_result = await loop.run_in_executor(
                        None,
                        validate_document_relevance,
                        file_content
                    )
                    status = validation_result.get("status", "INVALID")
                    confidence = validation_result.get("confidence", 0)
                    
                    # Check if document is valid and confidence is above threshold
                    if status != "VALID" or confidence < CONFIDENCE_THRESHOLD:
                        # Document is not relevant, emit document_invalid event
                        reason = validation_result.get("reason", "Document is not relevant to telecom/domain compliance")
                        await emitter.emit({
                            "type": "document_invalid",
                            "data": {
                                "filename": file.filename,
                                "reason": reason
                            }
                        })
                        # Clean up and continue to next file
                        if os.path.exists(file_path):
                            try:
                                os.remove(file_path)
                            except Exception as e:
                                print(f"Error removing file {file_path}: {e}")
                        continue  # Skip to next file
                    
                except Exception as e:
                    # Gatekeeper validation failed, emit error and skip this file
                    error_msg = f"Document validation error: {str(e)}"
                    print(f"Gatekeeper validation error: {e}")
                    await emitter.emit({
                        "type": "error",
                        "data": {"message": error_msg}
                    })
                    # Clean up and continue to next file
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                        except Exception as e:
                            print(f"Error removing file {file_path}: {e}")
                    continue  # Skip to next file
                
                # File passed validation, emit file_validated event and store for processing
                await emitter.emit({
                    "type": "file_validated",
                    "data": {
                        "filename": file.filename
                    }
                })
                
                # Store valid file for processing in phase 2
                valid_files.append({
                    "filename": file.filename,
                    "content": file_content,
                    "file_path": file_path
                })
                
            except Exception as e:
                # Handle any other errors during upload/parsing
                error_msg = f"Error processing file {file.filename}: {str(e)}"
                print(f"Error processing file: {e}")
                await emitter.emit({
                    "type": "error",
                    "data": {"message": error_msg}
                })
                # Clean up on error
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"Error removing file {file_path}: {e}")
        
        # PHASE 2: Process all valid files
        for valid_file in valid_files:
            try:
                # Define callback for verification progress (when regulation starts)
                async def on_verification_progress(regulation_name: str, regulation_index: int, total_regulations: int):
                    # Just log regular info without using sys.stderr to avoid mixing with error logs
                    print(f"Info: {regulation_index}/{total_regulations} - Verifying against {regulation_name}")
                    await emitter.emit({
                        "type": "verifying",
                        "data": {
                            "regulation_name": regulation_name,
                            "regulation_index": regulation_index,
                            "total_regulations": total_regulations
                        }
                    })
                
                # Define callback for issues found
                async def on_issues_delta(issues: list):
                    await emitter.emit({
                        "type": "issues_delta",
                        "data": {"issues": [issue.to_dict() for issue in issues]}
                    })
                
                # Define callback for regulation completion (when regulation finishes)
                async def on_regulation_complete(regulation_name: str, regulation_index: int, total_regulations: int):
                    print(f"Info: {regulation_index}/{total_regulations} - Completed {regulation_name}")
                    await emitter.emit({
                        "type": "regulation_complete",
                        "data": {
                            "regulation_name": regulation_name,
                            "regulation_index": regulation_index,
                            "total_regulations": total_regulations
                        }
                    })
                
                # Process file content and get compliance issues with real-time progress
                issues = await service.verify_against_regulations(
                    valid_file["content"],
                    on_progress=on_verification_progress,
                    on_issues_delta=on_issues_delta,
                    on_regulation_complete=on_regulation_complete,
                    selected_regulations=selected_regulations_list,
                    user_uploaded_regulations=user_uploaded_regulations if user_uploaded_regulations else None,
                    session_id=session_id,
                    custom_columns=custom_columns_list,
                    custom_system_prompt=validated_system_prompt,
                    custom_user_prompt=validated_user_prompt,
                    input_file_name=valid_file["filename"]
                )
                all_issues.extend([issue.to_dict() for issue in issues])
                
            finally:
                # Clean up uploaded file
                if os.path.exists(valid_file["file_path"]):
                    try:
                        os.remove(valid_file["file_path"])
                    except Exception as e:
                        print(f"Error removing file {valid_file['file_path']}: {e}")
        
        # Emit completion with all issues for confirmation
        await emitter.emit({
            "type": "complete",
            "data": {"issues": all_issues}
        })
        
        # Schedule cleanup of policy files after a delay to allow frontend to access them
        # Files are kept for 1 hour to allow users to access policy files via URLs in compliance issues
        # After that, they're cleaned up automatically
        async def cleanup_session_files():
            await asyncio.sleep(3600)  # Wait 1 hour
            if session_id in user_policy_files:
                for original_filename, policy_path in list(user_policy_files[session_id].items()):
                    if os.path.exists(policy_path):
                        try:
                            os.remove(policy_path)
                        except Exception as e:
                            print(f"Error removing policy file {policy_path}: {e}")
                del user_policy_files[session_id]
            if session_id in policy_custom_name_map:
                del policy_custom_name_map[session_id]
        
        # Start cleanup task in background (fire and forget)
        asyncio.create_task(cleanup_session_files())
    
    return emitter.stream_response(process(), keep_alive=True)


@router.get("/api/compliance/user_policy/{session_id}/{filename}")
async def get_user_policy_file(session_id: str, filename: str) -> FileResponse:
    """
    Serve a user-uploaded policy file.
    Files are stored temporarily and cleaned up after processing.
    Requires session_id to ensure users can only access their own files.
    """
    from urllib.parse import unquote
    
    # Decode filename if URL-encoded
    filename = unquote(filename)
    
    # Security check for filename
    if ".." in filename or filename.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    # Security check for session_id (prevent path traversal)
    if ".." in session_id or "/" in session_id:
        raise HTTPException(status_code=400, detail="Invalid session ID")
    
    # Look up file path in session-specific storage
    if session_id not in user_policy_files:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # First, try to map custom name to original filename
    original_filename = filename
    if session_id in policy_custom_name_map and filename in policy_custom_name_map[session_id]:
        original_filename = policy_custom_name_map[session_id][filename]
    
    # Look up file using original filename (which is the unique key)
    if original_filename not in user_policy_files[session_id]:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_path = user_policy_files[session_id][original_filename]
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        # Clean up stale reference
        if original_filename in user_policy_files[session_id]:
            del user_policy_files[session_id][original_filename]
        if session_id in policy_custom_name_map and filename in policy_custom_name_map[session_id]:
            del policy_custom_name_map[session_id][filename]
        raise HTTPException(status_code=404, detail="File not found")
    
    # Determine media type based on extension
    # Extract extension from file_path (actual file) not filename (custom name lookup key)
    # This ensures we get the correct extension even when custom names don't include extensions
    ext = os.path.splitext(file_path)[1].lower()
    media_types = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".csv": "text/csv",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls": "application/vnd.ms-excel",
        ".xlsm": "application/vnd.ms-excel.sheet.macroEnabled.12"
    }
    media_type = media_types.get(ext, "application/octet-stream")
    
    return FileResponse(
        file_path,
        media_type=media_type,
        headers={"Content-Disposition": f"inline; filename=\"{filename}\""}
    )
