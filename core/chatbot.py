from core.conversation import ConversationManager
from core.context import ContextAnalyzer, ContextProcessor
from core.router import AIRouter
from models.base import LanguageModel
from core.generation_context import GenerationContextBuilder


class Chatbot:

    def __init__(
        self,
        model: LanguageModel,
        context_analyzer: ContextAnalyzer
    ):

        self.name = "PersonalAI"

        self.conversation = ConversationManager()

        self.model = model

        self.context_analyzer = context_analyzer

        self.context_processor = ContextProcessor()
        self.generation_context_builder = GenerationContextBuilder()
        self.knowledge_base = (
            self.context_processor.knowledge_base
        )

        self.router = AIRouter()

        self.last_context = None
        self.last_route = None

    def respond(self, message):

        # Get the conversation BEFORE adding the current message.
        previous_history = self.conversation.get_history()

        # Analyze the current message using previous conversation.
        context = self.context_analyzer.analyze(
            message,
            previous_history
        )

        # Process the context.
        context = self.context_processor.process(context)

        # Add the user's message to the conversation.
        self.conversation.add_message(
            "user",
            message
        )

        # Determine which system should handle the request.
        route = self.router.route(context)

        self.last_context = context
        self.last_route = route

        # Generate the response.
        history = self.conversation.get_history()

        generation_context = self.generation_context_builder.build(
            context,
            history
        )
        
        response = self.model.generate(
            history,
            generation_context
        )

        # Store the assistant response.
        self.conversation.add_message(
            "assistant",
            response
        )

        return response

    def get_conversation(self):
        return self.conversation.get_history()

    def clear_conversation(self):
        self.conversation.clear()

    def get_last_context(self):
        return self.last_context

    def get_last_route(self):
        return self.last_route