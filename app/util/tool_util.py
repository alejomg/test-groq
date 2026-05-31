from datetime import datetime

def get_current_datetime(date_format="%Y-%m-%d %H:%M:%S"):
    if not date_format:
        raise ValueError("date_format cannot be empty")
    return datetime.now().strftime(date_format)


get_current_datetime_tool = {
        "type": "function",
        "function": {
            "name": "get_current_datetime",
            "description": "Returns the current date and time formatted according to the specified format.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date_format": {
                        "type": "string",
                        "description": "A string specifying the format of the returned datetime. Uses Python's strftime format codes.",
                        "default": "%Y-%m-%d %H:%M:%S"
                    },
                },
                "required": ["date_format"],
            },
        },
    }

tools = [get_current_datetime_tool]
