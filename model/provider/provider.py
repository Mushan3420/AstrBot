import abc

class Provider:
    def __init__(self, cfg):
        pass
    
    @abc.abstractmethod
    def text_chat(self, prompt, session_id, image_url: None, function_call: None):
        pass

    @abc.abstractmethod
    def forget(self, session_id = None) -> bool:
        pass