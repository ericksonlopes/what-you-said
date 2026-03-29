from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid


@dataclass
class User:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    email: str = ""
    full_name: Optional[str] = None
    picture_url: Optional[str] = None
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    def __post_init__(self):
        if not self.email:
            raise ValueError("User email is required")
