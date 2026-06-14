class MessageDeduplicator:
    def __init__(self, max_size=5000):
        self.max_size = max_size
        self.seen = set()
        self.history = []

    def is_duplicate(self, channel_id: int, message_id: int) -> bool:
        key = (channel_id, message_id)
        if key in self.seen:
            return True
        
        self.seen.add(key)
        self.history.append(key)
        
        # Evict oldest if limit reached
        if len(self.history) > self.max_size:
            old_key = self.history.pop(0)
            self.seen.discard(old_key)
            
        return False

deduplicator = MessageDeduplicator()
