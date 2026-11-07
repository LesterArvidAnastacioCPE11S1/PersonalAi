from features.intents import normalize, understand


ACTIONS = {
    "ui_new_chat": ("new_chat", "a new chat"),
    "ui_settings": ("open_settings", "Settings"),
    "ui_memory": ("open_memory", "Story memory"),
    "ui_scenario": ("open_scenario", "Scenario"),
    "ui_styles": ("open_styles", "Storytelling style"),
    "ui_sidebar": ("open_sidebar", "Chat list")
}

MIN_CONFIDENCE = 0.45
MAX_COMMAND_LENGTH = 140


def match_action(message, understanding=None):

    text = normalize(message)

    if not text or len(text) > MAX_COMMAND_LENGTH:

        return None

    turn = understanding or understand(text)

    if turn.label not in ACTIONS:

        return None

    if turn.confidence < MIN_CONFIDENCE:

        return None

    name, label = ACTIONS[turn.label]

    return {
        "name": name,
        "label": label
    }
