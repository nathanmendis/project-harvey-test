# core/action_result.py

from pydantic import BaseModel

class ActionResult(BaseModel):
    success: bool = True
    message: str = ""
