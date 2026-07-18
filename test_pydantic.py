from pydantic import BaseModel
from typing import Optional

class CompileRequest(BaseModel):
    source_type: str
    content: str
    title: Optional[str] = ""

req = CompileRequest(source_type="test", content="test", approved_observations=[{"a": 1}])
print(hasattr(req, "approved_observations"))
