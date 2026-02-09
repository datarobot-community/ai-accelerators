import asyncio
import sys
from pathlib import Path
from typing import List, Callable, Awaitable, Optional, Tuple, Dict
from urllib.parse import quote
from app.models.compliance import ComplianceIssue
from app.utils.llm_client import create_llm_client
from app.utils.llm_compliance_evaluator import read_markdown_files, build_compliance_prompt, evaluate_compliance
from app.utils.json_schema import get_compliance_json_schema
from app.utils.regulation_names import get_regulation_display_name


class ComplianceService:
    """Service for LLM-based compliance verification."""
    
    def __init__(self):
        # Path to knowledge base directory
        self.knowledge_base_dir = Path(__file__).parent.parent / "knowledge-base"
    
    async def _verify_single_regulation(
        self, 
        file_content: str, 
        regulation_name: str,
        regulation_content: str,
        is_user_uploaded: bool = False,
        session_id: Optional[str] = None,
        custom_columns: Optional[List[Dict]] = None,
        custom_system_prompt: Optional[str] = None,
        custom_user_prompt: Optional[str] = None,
        input_file_name: Optional[str] = None
    ) -> List[ComplianceIssue]:
        """
        Verify file content against a single regulation using LLM.
        Returns a list of compliance issues found for this regulation.
        
        Args:
            file_content: Content of the file to verify
            regulation_name: Name of the regulation
            regulation_content: Content of the regulation (markdown)
            is_user_uploaded: Whether this is a user-uploaded policy file
            session_id: Session ID for user-uploaded file URL generation
            custom_columns: Optional list of custom column definitions for the report
            custom_system_prompt: Optional custom system prompt (editable portion)
            custom_user_prompt: Optional custom user prompt
            input_file_name: Optional name of the input file being verified
        """
        # Create LLM client
        client, model = create_llm_client()
        
        # Build prompt for this regulation (with custom columns and prompts)
        messages = build_compliance_prompt(
            regulation_name, 
            regulation_content, 
            file_content, 
            custom_columns,
            custom_system_prompt,
            custom_user_prompt
        )
        
        # Get JSON schema (with custom columns if provided)
        json_schema = get_compliance_json_schema(custom_columns)
        
        # Run in executor to avoid blocking async loop
        loop = asyncio.get_event_loop()
        issues_data = await loop.run_in_executor(
            None,
            evaluate_compliance,
            client,
            model,
            messages,
            json_schema
        )
        
        # Convert to ComplianceIssue objects and add regulation_file_url
        issues = []
        
        if is_user_uploaded:
            # For user-uploaded policies, create a URL to serve the file
            display_name = Path(regulation_name).stem.replace("_", " ").replace("-", " ").title()
            # Create URL to serve the user-uploaded policy file with session_id for security
            encoded_filename = quote(regulation_name)
            if session_id:
                base_path = f"./api/compliance/user_policy/{session_id}/{encoded_filename}"
            else:
                # Fallback for backward compatibility (should not happen in normal flow)
                base_path = f"./api/compliance/user_policy/{encoded_filename}"
        else:
            # Build a URL for the corresponding PDF in regulations_pdf
            # regulation_name is the markdown filename returned by read_markdown_files
            pdf_filename = Path(regulation_name).with_suffix(".pdf").name
            encoded_filename = quote(pdf_filename)
            # Using a relative path for the PDF file
            base_path = f"./api/regulations_pdf/{encoded_filename}"
            # Use the same human-readable name as in the progress event
            display_name = get_regulation_display_name(regulation_name)

        for issue_dict in issues_data:
            issue_dict["regulation_file_url"] = base_path
            issue_dict["regulation_file_name"] = display_name
            # Add input file name if provided
            if input_file_name:
                issue_dict["input_file_name"] = input_file_name
            issues.append(ComplianceIssue(**issue_dict))
        
        return issues
    
    async def verify_against_regulations(
        self, 
        file_content: str,
        on_progress: Callable[[str, int, int], Awaitable[None]] = None,
        on_issues_delta: Callable[[List[ComplianceIssue]], Awaitable[None]] = None,
        on_regulation_complete: Callable[[str, int, int], Awaitable[None]] = None,
        selected_regulations: Optional[List[str]] = None,
        user_uploaded_regulations: Optional[List[Tuple[str, str]]] = None,
        session_id: Optional[str] = None,
        custom_columns: Optional[List[Dict]] = None,
        custom_system_prompt: Optional[str] = None,
        custom_user_prompt: Optional[str] = None,
        input_file_name: Optional[str] = None
    ) -> List[ComplianceIssue]:
        """
        Verify file content against regulations in knowledge base.
        Calls on_progress callback for each regulation being verified.
        Calls on_issues_delta callback with issues after each regulation.
        Calls on_regulation_complete callback when each regulation finishes.
        Returns list of all compliance issues found.
        
        Args:
            file_content: Content of the file to verify
            on_progress: Optional callback for progress updates (when regulation starts)
            on_issues_delta: Optional callback for incremental issues
            on_regulation_complete: Optional callback when regulation completes (regulation_name, index, total)
            selected_regulations: Optional list of regulation filenames to verify against.
                                 If None or empty, verifies against all regulations.
            user_uploaded_regulations: Optional list of (filename, markdown_content) tuples
                                       for user-uploaded policy files.
            session_id: Session ID for user-uploaded file URL generation
            custom_columns: Optional list of custom column definitions for the report
            custom_system_prompt: Optional custom system prompt (editable portion)
            custom_user_prompt: Optional custom user prompt
            input_file_name: Optional name of the input file being verified
        """
        all_issues = []
        
        # Read all regulations from knowledge base
        all_regulations = read_markdown_files(self.knowledge_base_dir)
        
        # Filter regulations based on selection
        # selected_regulations can be:
        # - None: no selection provided (backward compatible - use all preloaded)
        # - Empty list []: user explicitly deselected all preloaded (use none)
        # - Non-empty list: user selected specific preloaded regulations (use only those)
        if selected_regulations is not None:
            # A selection was provided (could be empty list)
            if len(selected_regulations) > 0:
                # User selected specific preloaded regulations
                selected_set = set(selected_regulations)
                regulations = [(name, content) for name, content in all_regulations if name in selected_set]
            else:
                # Empty list means user deselected all preloaded regulations
                regulations = []
        else:
            # None means no selection provided (backward compatible - use all preloaded)
            regulations = all_regulations
        
        # Track which regulations are user-uploaded BEFORE merging
        # Create a set of user-uploaded regulation names for efficient lookup
        user_uploaded_names = set()
        if user_uploaded_regulations:
            user_uploaded_names = {name for name, _ in user_uploaded_regulations}
        
        # Track the starting index of user-uploaded regulations
        # This allows us to distinguish KB regulations from user-uploaded ones
        # even when they have the same name
        kb_regulations_count = len(regulations)
        
        # Add user-uploaded regulations to the list
        # Note: user_uploaded_regulations already contains only the selected ones
        # (frontend filters before sending only selected user-uploaded policy files)
        if user_uploaded_regulations:
            regulations.extend(user_uploaded_regulations)
        
        total_regulations = len(regulations)
        
        # Process regulations in parallel to reduce total processing time
        # This prevents gateway timeouts when processing multiple regulations
        async def process_regulation_with_callbacks(
            regulation_index: int,
            regulation_name: str,
            regulation_content: str
        ) -> List[ComplianceIssue]:
            """Process a single regulation with progress and issues callbacks."""
            # Check if this is a user-uploaded regulation
            # We check both: 1) if the name is in user_uploaded_names, AND
            # 2) if we're past the KB regulations (to handle name collisions)
            is_user_uploaded = (
                user_uploaded_regulations is not None and
                regulation_name in user_uploaded_names and
                regulation_index >= kb_regulations_count
            )
            
            # Get display name for this regulation
            if is_user_uploaded:
                display_name = Path(regulation_name).stem.replace("_", " ").replace("-", " ").title()
            else:
                display_name = get_regulation_display_name(regulation_name)
            
            # Notify progress via callback when regulation starts
            if on_progress:
                await on_progress(display_name, regulation_index + 1, total_regulations)
            
            # Verify against this regulation
            # Wrap in try-except to handle individual regulation failures gracefully
            try:
                regulation_issues = await self._verify_single_regulation(
                    file_content, 
                    regulation_name, 
                    regulation_content,
                    is_user_uploaded=is_user_uploaded,
                    session_id=session_id,
                    custom_columns=custom_columns,
                    custom_system_prompt=custom_system_prompt,
                    custom_user_prompt=custom_user_prompt,
                    input_file_name=input_file_name
                )
                
                # Emit issues delta immediately after verification
                if on_issues_delta and regulation_issues:
                    await on_issues_delta(regulation_issues)
                
                # Notify completion callback when regulation finishes
                if on_regulation_complete:
                    await on_regulation_complete(display_name, regulation_index + 1, total_regulations)
                
                return regulation_issues
            except Exception as e:
                # Log error but don't fail the entire request
                print(f"Error processing regulation {regulation_name}: {e}", file=sys.stderr)
                # Still notify completion even on error, so frontend can track it
                if on_regulation_complete:
                    await on_regulation_complete(display_name, regulation_index + 1, total_regulations)
                # Return empty list so processing continues
                return []
        
        # Process all regulations in parallel using asyncio.gather
        # This significantly reduces total processing time compared to sequential processing
        tasks = [
            process_regulation_with_callbacks(
                regulation_index,
                regulation_name,
                regulation_content
            )
            for regulation_index, (regulation_name, regulation_content) in enumerate(regulations)
        ]
        
        # Wait for all regulations to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect all issues from all regulations
        for result in results:
            if isinstance(result, Exception):
                # Log exception but continue
                print(f"Error in parallel regulation processing: {result}", file=sys.stderr)
            elif isinstance(result, list):
                all_issues.extend(result)
        
        return all_issues
