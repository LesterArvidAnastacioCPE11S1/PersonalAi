from features.intent_model import get_intent_model


MIN_CONFIDENCE = 0.30


INTENT_ORDER = (
    "begin_story",
    "affirmation",
    "deny",
    "pause",
    "request_summary",
    "skip_interview",
    "ai_decides",
    "revise",
    "start_over",
    "mode_chat",
    "continue_story",
    "ooc",
    "rewrite",
    "expand",
    "time_skip"
)


INTENT_GUIDANCE = {
    "begin_story": {
        "setup": (
            "The user asked to begin, but the setup gate has not opened. Do "
            "not write prose. Ask them to confirm the Story Brief and press "
            "Begin story, or say \"begin the story\"."
        ),
        "story": (
            "The user has confirmed the start. Open the story now from the "
            "established foundation."
        )
    },
    "affirmation": {
        "setup": (
            "The user agreed with your last question. Use it as an answer and "
            "continue the interview. Do not start the story unless they say so."
        ),
        "story": (
            "The user agreed with your last prompt. Act on that agreement."
        )
    },
    "deny": {
        "setup": (
            "The user declined or is not ready. Do not start the story. "
            "Acknowledge briefly and wait."
        ),
        "story": (
            "The user declined. Do not advance the scene. Acknowledge and wait."
        )
    },
    "pause": {
        "setup": (
            "The user wants to pause. Stop asking new questions, acknowledge, "
            "and wait."
        ),
        "story": (
            "The user wants to pause. Stop the scene where it is. Do not skip "
            "time or add new events."
        )
    },
    "request_summary": {
        "setup": (
            "The user asked for the foundation summary. Present the Story Brief "
            "now using what you have, mark unknown areas as gaps, and ask for "
            "corrections."
        ),
        "story": (
            "The user asked for a recap. Give a short continuity recap, then "
            "continue from the current moment."
        )
    },
    "skip_interview": {
        "setup": (
            "The user wants fewer questions. Stop broad interviewing. Use what "
            "you have, present the Story Brief with gaps marked, and ask for "
            "confirmation."
        ),
        "story": ""
    },
    "ai_decides": {
        "setup": (
            "The user delegates the choices. Fill gaps with two or three "
            "clearly marked suggestions, present the brief, and ask for "
            "confirmation."
        ),
        "story": (
            "The user delegates the next choice. Make it for them and keep the "
            "story moving."
        )
    },
    "revise": {
        "setup": (
            "The user is correcting the foundation. Update only the affected "
            "parts and show the revised brief or changed lines."
        ),
        "story": (
            "The user is correcting canon. Apply the correction and keep the "
            "story consistent with it."
        )
    },
    "start_over": {
        "setup": (
            "The user wants a fresh foundation. Rebuild from their new premise "
            "and do not reuse discarded details unless they ask."
        ),
        "story": (
            "The user wants a fresh start. Ask whether to restart the current "
            "scene or rebuild the foundation, then do not continue the old "
            "thread."
        )
    },
    "mode_chat": {
        "chat": (
            "The user wants an ordinary conversation. Stay in chat mode. Do "
            "not start a story or a setup interview."
        ),
        "setup": (
            "The user is leaving the story setup. Do not ask any more setup "
            "questions and do not present the brief. Confirm the switch in one "
            "sentence, then respond to what they said as a general assistant."
        ),
        "story": (
            "The user is leaving the story. Do not narrate or continue the "
            "scene. Confirm the switch in one brief sentence, then respond as "
            "a general assistant."
        )
    },
    "continue_story": {
        "setup": (
            "The user wants to proceed. Ask the next focused interview "
            "questions. Do not start the story."
        ),
        "story": (
            "The user wants the story to continue. Continue from the current "
            "moment without recapping."
        )
    },
    "ooc": {
        "setup": "",
        "story": (
            "The user is speaking out of character. Answer as the assistant, "
            "not in scene. Do not write narration or dialogue for this reply."
        )
    },
    "rewrite": {
        "setup": (
            "The user wants a different version. Rewrite the last reply or "
            "brief rather than continuing forward."
        ),
        "story": (
            "The user wants the last response rewritten. Rewrite it and do not "
            "continue past it."
        )
    },
    "expand": {
        "setup": (
            "The user wants more detail. Expand the current answer or brief "
            "with concrete specifics."
        ),
        "story": (
            "The user wants more detail. Expand the current moment. Do not skip "
            "time or rush to the next event."
        )
    },
    "time_skip": {
        "setup": "",
        "story": (
            "The user wants to skip ahead. Move the story forward to the "
            "requested point and cover what changed in scene."
        )
    }
}


def normalize(message):

    return " ".join((message or "").split())


def understand(message):

    return get_intent_model().classify(normalize(message))


def intents_from(turn):

    if turn is None or turn.confidence < MIN_CONFIDENCE:

        return set()

    if turn.label not in INTENT_GUIDANCE:

        return set()

    return {turn.label}


def detect(message):

    return intents_from(understand(message))


def intent_block(intents, phase):

    if not intents:

        return ""

    lines = []

    for name in INTENT_ORDER:

        if name not in intents:

            continue

        guidance = INTENT_GUIDANCE.get(
            name,
            {}
        ).get(phase, "")

        if guidance:

            lines.append(f"- {guidance}")

    if not lines:

        return ""

    return (
        "USER INTENT THIS TURN\n"
        + "\n".join(lines)
    )
