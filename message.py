# I made this its own file so my main one stayed cleaner


class Message:
    """little class to hold one prompt I want to grade"""

    def __init__(self, role, content, timestamp=""):
        # role is like "user" or "ai", didnt end up using ai but left it in case
        self.role = role
        self.content = content
        self.timestamp = timestamp

    def word_count(self):
        # just splits on whitespace
        return len(self.content.split())

    def summary(self, max_length=80):
        """chops the message down so I can show a preview in the history screen"""
        text = self.content.replace("\n", " ").strip()
        if len(text) <= max_length:
            return text
        # -3 to leave room for the ...
        return text[:max_length - 3] + "..."

    def __str__(self):
        return "[" + self.role + "] " + self.summary()
