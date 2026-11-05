from dataclasses import dataclass

@dataclass
class SemanticStatement:

    subject: str
    predicate: str
    object: str | None
    confidence: float = 0.0
    type: str = "statement"