"""Progress tracking for analysis pipeline stages."""

import logging
from typing import Dict, Optional
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class ProgressTracker:
    """Tracks progress of analysis pipeline stages."""
    
    def __init__(self):
        self._progress_store: Dict[str, Dict] = {}
    
    def create_progress(self, request_id: Optional[str] = None) -> str:
        """Create new progress tracking entry."""
        if not request_id:
            request_id = str(uuid.uuid4())
        
        self._progress_store[request_id] = {
            "request_id": request_id,
            "created_at": datetime.now().isoformat(),
            "fetching": "pending",
            "parsing": "pending", 
            "chunking": "pending",
            "review": "pending",
            "error": None,
            "completed": False
        }
        
        logger.info(f"Created progress tracker for request {request_id}")
        return request_id
    
    def update_progress(self, request_id: str, stage: str, status: str, error: Optional[str] = None):
        """Update progress for a specific stage."""
        if request_id not in self._progress_store:
            logger.warning(f"Progress tracker not found for request {request_id}")
            return
        
        progress = self._progress_store[request_id]
        progress[stage] = status
        
        if error:
            progress["error"] = error
            logger.error(f"Stage {stage} error for request {request_id}: {error}")
        else:
            logger.info(f"Stage {stage} {status} for request {request_id}")
    
    def get_progress(self, request_id: str) -> Optional[Dict]:
        """Get progress for a specific request."""
        return self._progress_store.get(request_id)
    
    def complete_progress(self, request_id: str):
        """Mark progress as completed and clean up."""
        if request_id in self._progress_store:
            self._progress_store[request_id]["completed"] = True
            # Clean up after reasonable time (could be extended for history)
            logger.info(f"Completed progress tracking for request {request_id}")
    
    def cleanup_expired(self, max_age_seconds: int = 3600):
        """Remove expired progress entries."""
        current_time = datetime.now()
        expired = []
        
        for request_id, progress in self._progress_store.items():
            created_at = datetime.fromisoformat(progress["created_at"])
            if (current_time - created_at).seconds > max_age_seconds:
                expired.append(request_id)
        
        for request_id in expired:
            del self._progress_store[request_id]
        
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired progress entries")

# Global progress tracker instance
progress_tracker = ProgressTracker()