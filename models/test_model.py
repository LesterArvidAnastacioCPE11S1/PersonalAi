from models.base import LanguageModel


class TestModel(LanguageModel):

    def generate(self, messages):
        last_message = messages[-1]["content"]

        return f"[Test Model] I received: {last_message}"