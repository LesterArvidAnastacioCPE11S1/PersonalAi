import re

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class KnowledgeStatement:

    subject: str

    predicate: str

    value: str

    source_text: str = ""


@dataclass
class WorldEntity:

    name: str

    entity_type: str = "unknown"

    attributes: Dict = field(
        default_factory=dict
    )

    relationships: Dict = field(
        default_factory=dict
    )

    facts: List[str] = field(
        default_factory=list
    )


@dataclass
class CharacterRecord(WorldEntity):

    entity_type: str = "character"


class KnowledgeBase:

    def __init__(self):

        self.entities: Dict[
            str,
            WorldEntity
        ] = {}

        self.statements: List[
            KnowledgeStatement
        ] = []

    # =========================================================
    # ENTITY MANAGEMENT
    # =========================================================

    def get_or_create_entity(
        self,
        name: str,
        entity_type: str = "unknown"
    ):

        key = name.lower()

        if key not in self.entities:

            self.entities[key] = WorldEntity(
                name=name,
                entity_type=entity_type
            )

        return self.entities[key]

    def get_or_create_character(
        self,
        name: str
    ):

        key = name.lower()

        if key not in self.entities:

            self.entities[key] = CharacterRecord(
                name=name
            )

        return self.entities[key]

    # =========================================================
    # STATEMENTS
    # =========================================================

    def add_statement(
        self,
        subject: str,
        predicate: str,
        value: str,
        source_text: str = ""
    ):

        statement = KnowledgeStatement(
            subject=subject,
            predicate=predicate,
            value=value,
            source_text=source_text
        )

        self.statements.append(
            statement
        )

        return statement

    def get_statements_for(
        self,
        subject: str
    ):

        return [
            statement
            for statement in self.statements
            if statement.subject.lower()
            == subject.lower()
        ]

    def get_statements_by_predicate(
        self,
        predicate: str
    ):

        return [
            statement
            for statement in self.statements
            if statement.predicate.lower()
            == predicate.lower()
        ]

    def get_all_statements(self):

        return self.statements

    # =========================================================
    # SEMANTIC QUERY RETRIEVAL
    # =========================================================

    def find_relevant_statements(
        self,
        subject=None,
        predicate=None,
        object=None,
        limit=5
    ):
        """
        Find stored statements that are relevant
        to a structured semantic query.

        None means that field acts as a wildcard.
        """

        results = []

        for statement in self.statements:

            score = 0

            # -------------------------------------------------
            # SUBJECT
            # -------------------------------------------------

            if subject is not None:

                if (
                    statement.subject.lower()
                    == subject.lower()
                ):

                    score += 3

                else:

                    continue

            # -------------------------------------------------
            # PREDICATE
            # -------------------------------------------------

            if predicate is not None:

                if (
                    statement.predicate.lower()
                    == predicate.lower()
                ):

                    score += 2

            # -------------------------------------------------
            # OBJECT
            # -------------------------------------------------

            if object is not None:

                if statement.value is not None:

                    if (
                        statement.value.lower()
                        == object.lower()
                    ):

                        score += 3

                    else:

                        continue

            # -------------------------------------------------
            # ADD MATCH
            # -------------------------------------------------

            if score > 0:

                results.append(
                    (
                        score,
                        statement
                    )
                )

        # Highest relevance first.
        results.sort(
            key=lambda item: item[0],
            reverse=True
        )

        return [
            statement
            for score, statement
            in results[:limit]
        ]

    # =========================================================
    # ATTRIBUTES
    # =========================================================

    def add_attribute(
        self,
        entity_name: str,
        attribute: str,
        value: str
    ):

        entity = (
            self.get_or_create_entity(
                entity_name
            )
        )

        entity.attributes[
            attribute
        ] = value

    # =========================================================
    # RELATIONSHIPS
    # =========================================================

    def add_relationship(
        self,
        subject: str,
        relationship: str,
        target: str
    ):

        entity = (
            self.get_or_create_entity(
                subject
            )
        )

        if relationship not in entity.relationships:

            entity.relationships[
                relationship
            ] = []

        entity.relationships[
            relationship
        ].append(target)

    # =========================================================
    # FACTS
    # =========================================================

    def add_fact(
        self,
        entity_name: str,
        fact: str
    ):

        entity = (
            self.get_or_create_entity(
                entity_name
            )
        )

        entity.facts.append(
            fact
        )

    # =========================================================
    # ENTITY LOOKUP
    # =========================================================

    def get_entity(
        self,
        name: str
    ):

        return self.entities.get(
            name.lower()
        )

    def get_character(
        self,
        name: str
    ):

        entity = self.entities.get(
            name.lower()
        )

        if isinstance(
            entity,
            CharacterRecord
        ):

            return entity

        return None

    def get_all_entities(self):

        return list(
            self.entities.values()
        )

    def get_all_characters(self):

        return [
            entity
            for entity in self.entities.values()
            if isinstance(
                entity,
                CharacterRecord
            )
        ]

    # =========================================================
    # CLEAR
    # =========================================================

    def clear(self):

        self.entities.clear()

        self.statements.clear()


# =============================================================
# LEGACY CHARACTER EXTRACTOR
# =============================================================

class KnowledgeExtractor:

    def __init__(self):

        self.character_intro_patterns = [
            re.compile(
                r"(?P<name>[A-Z][a-zA-Z0-9_-]*) "
                r"is a (?P<role>.+)",
                re.IGNORECASE
            )
        ]

        self.occupation_pattern = re.compile(
            r"(?P<name>[A-Z][a-zA-Z0-9_-]*) "
            r"is (?:a|an) "
            r"(?P<occupation>.+)",
            re.IGNORECASE
        )

        self.owns_pattern = re.compile(
            r"(?P<name>[A-Z][a-zA-Z0-9_-]*) "
            r"owns "
            r"(?P<object>.+)",
            re.IGNORECASE
        )

        self.has_pattern = re.compile(
            r"(?P<name>[A-Z][a-zA-Z0-9_-]*) "
            r"has "
            r"(?P<object>.+)",
            re.IGNORECASE
        )

    def extract(
        self,
        text: str,
        knowledge_base: KnowledgeBase
    ):

        results = []

        for match in (
            self.character_intro_patterns
        ):

            result = match.search(text)

            if result:

                name = result.group(
                    "name"
                )

                role = result.group(
                    "role"
                )

                character = (
                    knowledge_base
                    .get_or_create_character(
                        name
                    )
                )

                character.attributes[
                    "role"
                ] = role

                results.append(
                    (
                        name,
                        "role",
                        role
                    )
                )

        match = (
            self.occupation_pattern.search(
                text
            )
        )

        if match:

            name = match.group(
                "name"
            )

            occupation = match.group(
                "occupation"
            )

            character = (
                knowledge_base
                .get_or_create_character(
                    name
                )
            )

            character.attributes[
                "occupation"
            ] = occupation

            results.append(
                (
                    name,
                    "occupation",
                    occupation
                )
            )

        match = (
            self.owns_pattern.search(
                text
            )
        )

        if match:

            name = match.group(
                "name"
            )

            owned_object = match.group(
                "object"
            )

            character = (
                knowledge_base
                .get_or_create_character(
                    name
                )
            )

            character.relationships.setdefault(
                "owns",
                []
            ).append(
                owned_object
            )

            results.append(
                (
                    name,
                    "owns",
                    owned_object
                )
            )

        match = (
            self.has_pattern.search(
                text
            )
        )

        if match:

            name = match.group(
                "name"
            )

            value = match.group(
                "object"
            )

            character = (
                knowledge_base
                .get_or_create_character(
                    name
                )
            )

            character.facts.append(
                value
            )

            results.append(
                (
                    name,
                    "has",
                    value
                )
            )

        return results