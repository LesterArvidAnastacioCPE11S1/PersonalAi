class ConversationManager:
    def __init__(self, max_messages=20):
        self.max_messages = max_messages
        self.messages = []
        
    def add_message(self, role, content):
        self.messages.append({"role": role, "content": content})
        
        self._limit_history()
        
    def get_history(self):
        return self.messages.copy()
    
    def clear(self):
        self.messages.clear()
        
    def _limit_history(self):
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]