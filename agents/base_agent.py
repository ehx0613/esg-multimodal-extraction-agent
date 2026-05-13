from abc import ABC, abstractmethod

class BaseAgent(ABC):
    def __init__(self, name):
        self.name = name
    def log(self, msg):
        print(f"[{self.name}] {msg}")
    @abstractmethod
    def run(self, state):
        pass
