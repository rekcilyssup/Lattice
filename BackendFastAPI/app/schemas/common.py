from typing import Literal, Optional
from pydantic import BaseModel


class Citation(BaseModel):
    citation_id: str
    document_name: str
    page_number: int
    exact_quote: str
    context_snippet: str


class Message(BaseModel):
    id: str
    role: Literal['user', 'assistant']
    content: str
    citations: list[Citation] = []


class Document(BaseModel):
    id: str
    name: str
    status: Literal['ingesting', 'indexed', 'failed']
    progress: Optional[int] = None


class Workspace(BaseModel):
    id: str
    name: str
    documents: list[Document]
    messages: list[Message]
