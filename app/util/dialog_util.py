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
