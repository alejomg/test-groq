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
	Reply with very short answers, maximum 2 sentences. 
	
	Add a small reference at the end of each one of your responses.
	
	The theme of the small reference must be related to one of these options:
	
	    - Star Wars
	    - Star Trek
	    - Pirates of the Caribean
	    - Vikings
	
	Keep the initial selection for the rest of the conversation.
	Also it is very important that your answers are short, this is crucial.
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
