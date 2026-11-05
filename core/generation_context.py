class GenerationContextBuilder:

    def build(
        self,
        context,
        conversation_history
    ):

        generation_context = {
            "intent": context.intent,
            "mode": context.mode,
            "confidence": context.confidence,
            "entities": [],
            "semantic_statements": [],
            "semantic_questions": [],
            "relevant_knowledge": [],
            "relevant_history": context.relevant_history
        }

        # ---------------------------------------------------------
        # ENTITIES
        # ---------------------------------------------------------

        for entity in context.entities:

            generation_context[
                "entities"
            ].append(
                {
                    "name": entity.name,
                    "label": entity.ner_label,
                    "confidence": entity.confidence
                }
            )

        # ---------------------------------------------------------
        # SEMANTIC STATEMENTS
        # ---------------------------------------------------------

        for statement in context.semantic_statements:

            if statement.type != "statement":

                continue

            generation_context[
                "semantic_statements"
            ].append(
                {
                    "subject": statement.subject,
                    "predicate": statement.predicate,
                    "object": statement.object,
                    "confidence": statement.confidence
                }
            )

        # ---------------------------------------------------------
        # SEMANTIC QUESTIONS
        # ---------------------------------------------------------

        for statement in context.semantic_statements:

            if statement.type != "question":

                continue

            generation_context[
                "semantic_questions"
            ].append(
                {
                    "subject": statement.subject,
                    "predicate": statement.predicate,
                    "object": statement.object,
                    "confidence": statement.confidence
                }
            )

        # ---------------------------------------------------------
        # RELEVANT KNOWLEDGE
        # ---------------------------------------------------------

        for statement in context.relevant_knowledge:

            generation_context[
                "relevant_knowledge"
            ].append(
                {
                    "subject": statement.subject,
                    "predicate": statement.predicate,
                    "object": statement.value,
                    "source_text": statement.source_text
                }
            )

        return generation_context