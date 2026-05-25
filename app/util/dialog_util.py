from app.models.dialog import DMessage, Dialog
from app.schemas.dialog_response import DialogSimpleMessage


def get_raw_message_from_dmessage(dialog_message: DMessage) -> dict[str, str]:
    return {
        "text": dialog_message.text,
        "type": dialog_message.type
    }


def get_list_of_raw_messages(dialog: Dialog) -> list[dict[str, str]]:

    """
    Converts a list of DMessage from a Dialog to a list of dictionaries
    :param dialog:
    :return:
    """
    if not dialog or not dialog.messages:
        return []

    return [
        get_raw_message_from_dmessage(message)
        for message in dialog.messages
    ]


def get_dialog_messages_from_raw_messages(raw_messages: list[dict[str, str]]) -> list[DialogSimpleMessage]:
    """
    Converts a list of dictionaries to a list of DialogSingleMessage Pydantic model
    :param raw_messages:
    :return:
    """
    return [DialogSimpleMessage(**raw_message) for raw_message in raw_messages]


def get_system_prompt_message() -> str:
    return """
Reply with extremely short answers, maximum 2 sentences total.

At the end of every response, append a very small and subtle reference.

The reference must be inspired by ONE randomly chosen universe from this list:
- Star Wars
- Star Trek
- Pirates of the Caribbean
- Vikings
- Lord of the Rings
- Marvel
- Some Klingon joke
- Advice in Elvish language
- Cowboy & Western slang 

Important rules:
- Randomly choose ONE universe at the beginning of the conversation.
- Do NOT always pick the first item in the list.
- Keep the same universe for the entire conversation.
- Never mention the name of the universe, franchise.
- The reference could feel like a tiny stylistic flavor, joke or explicit fandom reference.

Examples of GOOD references:
- [May the force be with you]
- [Beam me up]
- [Ahoy matey]
- [Odin watches]

Examples of BAD references:
- [Star Wars: May the force be with you]

Keep every answer concise. Brevity is extremely important.
    """


def init_history_turn() -> list[dict[str, str]]:
    # Set the system prompt
    system_prompt = {
        "role": "system",
        "content": get_system_prompt_message()
    }
        
    return [system_prompt]


def get_turn_from_dmessage(dialog_message: DMessage) -> dict[str, str]:
    return {
        "role": dialog_message.type.lower(),
        "content": dialog_message.text
    }


def get_history_turn_from_dialog(dialog: Dialog) -> list[dict[str, str]]:

    """
    Returns the history turn of a dialog
    :param dialog:
    :return:
    """
    if not dialog or not dialog.messages:
        return []

    return [
        get_turn_from_dmessage(message)
        for message in dialog.messages
    ]
