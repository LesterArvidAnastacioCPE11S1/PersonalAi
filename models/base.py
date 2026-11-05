from abc import ABC, abstractmethod

class LanguageModel(ABC):

    @abstractmethod
    def generate(self, messages, context=None):
        pass