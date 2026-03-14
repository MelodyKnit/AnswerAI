from pydantic import BaseModel


class KnowledgePointTreeNode(BaseModel):
    id: int
    name: str
    path: str
    level: int
    children: list["KnowledgePointTreeNode"] = []


KnowledgePointTreeNode.model_rebuild()
