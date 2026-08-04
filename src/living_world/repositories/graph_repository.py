class GraphRepository:
    """Repository abstraction. SQLite implementation arrives in a later release."""

    def save(self,state)->None:
        raise NotImplementedError

    def load(self):
        raise NotImplementedError
