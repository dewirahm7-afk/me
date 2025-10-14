# backend/core/session_manager.py
import json
import time
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import uuid

@dataclass
class Session:
    id: str
    workdir: Path
    video_path: Optional[Path] = None
    srt_path: Optional[Path] = None
    wav_16k: Optional[Path] = None
    segjson: Optional[Path] = None
    spkjson: Optional[Path] = None
    srt_id: Optional[Path] = None
    status: str = 'created'
    progress: int = 0
    current_step: str = ''
    created_at: float = 0
    updated_at: float = 0
    error: Optional[str] = None

class SessionManager:
    def __init__(self, workdir_base: Path):
        self.workdir_base = workdir_base
        self.workdir_base.mkdir(parents=True, exist_ok=True)
        self.sessions: Dict[str, Session] = {}
        self.session_file = workdir_base / "sessions.json"
        self._load_sessions()
    
    def _load_sessions(self):
        """Load sessions from disk"""
        if self.session_file.exists():
            try:
                data = self._read_json_safe(self.session_file, {})
                for session_id, session_data in data.items():
                    # Convert path strings back to Path objects
                    for key, value in session_data.items():
                        if isinstance(value, str) and ('path' in key or key == 'workdir'):
                            session_data[key] = Path(value)
                    
                    self.sessions[session_id] = Session(**session_data)
            except Exception as e:
                print(f"Error loading sessions: {e}")
    
    def _save_sessions(self):
        """Save sessions to disk"""
        try:
            sessions_data = {}
            for session_id, session in self.sessions.items():
                session_data = asdict(session)
                # Convert Path objects to strings for JSON serialization
                for key, value in session_data.items():
                    if isinstance(value, Path):
                        session_data[key] = str(value)
                sessions_data[session_id] = session_data
            
            self._write_json_safe(self.session_file, sessions_data)
        except Exception as e:
            print(f"Error saving sessions: {e}")
    
    def create_session(self, video_name: str, srt_name: str) -> Session:
        """Create new session"""
        session_id = str(uuid.uuid4())
        workdir = self.workdir_base / session_id
        workdir.mkdir(parents=True, exist_ok=True)
        
        session = Session(
            id=session_id,
            workdir=workdir,
            status='created',
            created_at=time.time(),
            updated_at=time.time()
        )
        
        self.sessions[session_id] = session
        self._save_sessions()
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        return self.sessions.get(session_id)
    
    def update_session(self, session_id: str, **kwargs):
        """Update session attributes"""
        session = self.get_session(session_id)
        if session:
            for key, value in kwargs.items():
                if hasattr(session, key):
                    setattr(session, key, value)
            session.updated_at = time.time()
            self._save_sessions()
    
    def delete_session(self, session_id: str):
        """Delete session and its files"""
        session = self.get_session(session_id)
        if session:
            # Remove workdir
            try:
                shutil.rmtree(session.workdir)
            except Exception as e:
                print(f"Error deleting workdir: {e}")
            
            # Remove from sessions
            del self.sessions[session_id]
            self._save_sessions()
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all sessions"""
        sessions_list = []
        for session in self.sessions.values():
            session_data = asdict(session)
            # Convert Path objects to strings
            for key, value in session_data.items():
                if isinstance(value, Path):
                    session_data[key] = str(value)
            sessions_list.append(session_data)
        
        return sorted(sessions_list, key=lambda x: x['created_at'], reverse=True)
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """Clean up old sessions"""
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        sessions_to_delete = []
        for session_id, session in self.sessions.items():
            if current_time - session.created_at > max_age_seconds:
                sessions_to_delete.append(session_id)
        
        for session_id in sessions_to_delete:
            self.delete_session(session_id)
    
    def _read_json_safe(self, path: Path, default=None):
        """Safely read JSON file"""
        try:
            if path.exists():
                return json.loads(path.read_text(encoding='utf-8'))
            return default
        except Exception as e:
            print(f"JSON read error {path}: {e}")
            return default
    
    def _write_json_safe(self, path: Path, data: Any):
        """Safely write JSON file"""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            return True
        except Exception as e:
            print(f"JSON write error {path}: {e}")
            return False

# Create global instance
session_manager = SessionManager(Path("workspaces"))