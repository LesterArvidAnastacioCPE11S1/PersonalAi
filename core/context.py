from dataclasses import dataclass, field
from typing import List, Dict

from core.context_extractors import (
    MemoryExtractor,
    ReferenceExtractor,
    ReferenceResolver,
    EntityExtractor
)

from models.entity_model import EntityRecognizer
from core.semantic import QwenSemanticInterpreter
from core.knowledge import KnowledgeBase


@dataclass
class Entity:

    name: str
    ner_label: str
    confidence: float
    start: int
    end: int


@dataclass
class Context:

    intent: str

    confidence: float

    entities: List[Entity] = field(
        default_factory=list
    )

    semantic_statements: list = field(
        default_factory=list
    )

    relevant_knowledge: list = field(
        default_factory=list
    )

    references: List[str] = field(
        default_factory=list
    )

    relevant_history: list = field(
        default_factory=list
    )

    mode: str = "normal"

    memory_requests: list = field(
        default_factory=list
    )

    additional_data: Dict = field(
        default_factory=dict
    )


class ContextAnalyzer:

    def analyze(
        self,
        message: str,
        conversation_history: list
    ) -> Context:

        raise NotImplementedError


class ContextProcessor:

    def __init__(self):

        self.memory_extractor = (
            MemoryExtractor()
        )

        self.reference_extractor = (
            ReferenceExtractor()
        )

        self.reference_resolver = (
            ReferenceResolver()
        )

        self.entity_recognizer = (
            EntityRecognizer()
        )

        self.semantic_interpreter = (
            QwenSemanticInterpreter()
        )

        self.knowledge_base = (
            KnowledgeBase()
        )

        self.legacy_entity_extractor = (
            EntityExtractor()
        )

    def process(
        self,
        context: Context
    ) -> Context:

        message = (
            context.additional_data.get(
                "message",
                ""
            )
        )

        history = (
            context.additional_data.get(
                "history",
                []
            )
        )

        # ---------------------------------------------------------
        # ENTITY RECOGNITION
        # ---------------------------------------------------------

        detected_entities = (
            self.entity_recognizer.recognize(
                message
            )
        )

        context.entities = []

        for entity in detected_entities:

            context.entities.append(
                Entity(
                    name=entity["text"],
                    ner_label=entity["label"],
                    confidence=entity["confidence"],
                    start=entity["start"],
                    end=entity["end"]
                )
            )

        # ---------------------------------------------------------
        # SEMANTIC INTERPRETATION
        # ---------------------------------------------------------

        semantic_statements = (
            self.semantic_interpreter.interpret(
                message,
                detected_entities,
                history
            )
        )

        context.semantic_statements = (
            semantic_statements
        )

        # ---------------------------------------------------------
        # STORE FACTUAL KNOWLEDGE
        # ---------------------------------------------------------

        for statement in semantic_statements:

            if statement.type != "statement":

                continue

            if statement.object is None:

                continue

            self.knowledge_base.add_statement(
                subject=statement.subject,
                predicate=statement.predicate,
                value=statement.object,
                source_text=message
            )

        # ---------------------------------------------------------
        # KNOWLEDGE RETRIEVAL
        # ---------------------------------------------------------

        context.relevant_knowledge = []

        for statement in semantic_statements:

            if statement.type != "question":

                continue

            relevant = (
                self.knowledge_base
                .find_relevant_statements(
                    subject=statement.subject,
                    predicate=statement.predicate,
                    object=statement.object
                )
            )

            for result in relevant:

                if result not in (
                    context.relevant_knowledge
                ):

                    context.relevant_knowledge.append(
                        result
                    )

        # ---------------------------------------------------------
        # MEMORY EXTRACTION
        # ---------------------------------------------------------

        if context.intent == "memory_save":

            context.memory_requests = (
                self.memory_extractor.extract(
                    message
                )
            )

        # ---------------------------------------------------------
        # REFERENCE EXTRACTION
        # ---------------------------------------------------------

        context.references = (
            self.reference_extractor.extract(
                message
            )
        )

        # ---------------------------------------------------------
        # REFERENCE RESOLUTION
        # ---------------------------------------------------------

        if (
            context.references
            or context.entities
            or context.intent == "memory_recall"
        ):

            context.relevant_history = (
                self.reference_resolver.resolve(
                    message,
                    history,
                    context.entities
                )
            )

        # ---------------------------------------------------------
        # MODE
        # ---------------------------------------------------------

        if context.intent in [
            "roleplay",
            "storytelling",
            "continue_story",
            "creative_writing"
        ]:

            context.mode = "creative"

        elif context.intent in [
            "memory_save",
            "memory_recall"
        ]:

            context.mode = "memory"

        else:

            context.mode = "normal"

        return context