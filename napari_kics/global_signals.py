class signals:
    def __new__(cls):
        if not hasattr(cls, "instance"):
            cls.instance = super().__new__(cls)
            cls.instance.sampleLoaded = Signal()

        return cls.instance


class Signal:
    def __init__(self):
        self.listeners = list()

    def connect(self, action):
        self.listeners.append(action)

    def emit(self, *args, **kwargs):
        for listener in self.listeners:
            listener(*args, **kwargs)
