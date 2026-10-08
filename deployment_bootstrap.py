from llm_client import InternChatClient


def provided_client():
    return InternChatClient(timeout=240, retry=3)