class AIRouter:

    def route(self, context):

        routes = {
            "chat": "chat",
            "question": "question",
            "coding": "coding",
            "instruction": "instruction",

            "storytelling": "storytelling",
            "roleplay": "roleplay",
            "continue_story": "storytelling",
            "creative_writing": "creative_writing",

            "memory_save": "memory",
            "memory_recall": "memory",

            "summarization": "summarization",

            "unknown": "unknown"
        }

        return routes.get(context.intent, "unknown")