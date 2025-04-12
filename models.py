from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any



class DocumentContent(BaseModel):
    """Structure for the document to be retyped"""
    text: str = Field(description="Raw text of the document")
    source: Optional[str] = Field(None, description="Source of the document")

class RetypedDocument(BaseModel):
    """Structure for the retyped document"""
    content: str = Field(description="The exact content of the document, retaining original formatting")
