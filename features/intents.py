import re

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
    "coding",
    "question",
    "chat",
    "continue_story",
    "ooc",
    "rewrite",
    "expand",
    "time_skip",
    "image_generation"
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
            "The user is correcting canon. This is out of character. "
            "Acknowledge the correction in one short line, apply it from now "
            "on, and do not narrate the correction as a scene event or put it "
            "in a character's mouth."
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
    "question": {
        "setup": (
            "The user asked you a question, not a foundation answer. Your "
            "first sentence must answer it directly and truthfully, in one "
            "to three sentences, before you ask anything. Do not reply with "
            "questions only. Then return to the setup interview with one or "
            "two focused questions. Do not treat the answer as story canon."
        )
    },
    "coding": {
        "chat": (
            "The user is asking about code or a software project. Use the "
            "coding mode for this turn. If they requested a change, inspect "
            "the relevant existing source and provide the concrete change "
            "instead of a generic example."
        )
    },
    "chat": {
        "setup": (
            "The user is making conversation instead of answering the "
            "interview. Reply to them briefly and naturally first, then "
            "return to the setup interview with one or two focused questions."
        )
    },
    "ooc": {
        "setup": (
            "The user stepped outside the setup interview. Address what they "
            "said directly in one or two sentences, then return to the setup "
            "questions."
        ),
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
    },
    "image_generation": {
        "setup": (
            "The user wants a picture. The app paints the latest scene; do "
            "not write prose. Reply in one short sentence."
        ),
        "chat": (
            "The user wants a picture made. The app paints the latest scene; "
            "do not write new prose. Reply in one short sentence."
        ),
        "story": (
            "The user wants the current scene painted as an image. The app "
            "handles it; do not narrate further or describe the picture. Reply "
            "in one short sentence."
        )
    }
}


def normalize(message):

    return " ".join((message or "").split())


CODING_LANGUAGE_CUES = re.compile(
    r"\b(?:luau?|python|javascript|typescript|java|c\+\+|c#|rust|"
    r"golang|php|ruby|sql|html|css|powershell|bash|programming|"
    r"source code|codebase|stack trace|traceback|compiler|compile|"
    r"syntax error|exception|pathfinding(?:service)?|datastoreservice|"
    r"remoteevent|remotefunction|humanoid|tweenservice|vector3|"
    r"replicatedstorage|serverscriptservice|localscript|modulescript|"
    r"roblox studio)\b",
    re.IGNORECASE
)
CODING_SUBJECT_CUES = re.compile(
    r"\b(?:code|codes|script|scripts|program|programs|bug|bugs|"
    r"debug|function|functions|module|modules|api|algorithm|"
    r"source|syntax|error|errors|pathfinding|npc|npcs|mechanic|"
    r"mechanics|system|systems|feature|features|movement|behavior|"
    r"behaviour)\b",
    re.IGNORECASE
)
CODING_ACTION_CUES = re.compile(
    r"\b(?:add|analy[sz]e|build|change|check|create|debug|edit|"
    r"explain|extend|fix|help|implement|improve|inspect|make|modify|"
    r"optimi[sz]e|refactor|repair|review|rewrite|update|write|"
    r"what is|what does|how do|how can|why does|why is|tell me about)\b",
    re.IGNORECASE
)
STRONG_CODING_ACTION_CUES = re.compile(
    r"\b(?:add|build|change|create|debug|edit|fix|implement|modify|"
    r"optimi[sz]e|refactor|repair|rewrite|update|write)\b",
    re.IGNORECASE
)
CODING_FOLLOW_UP_CUES = re.compile(
    r"\b(?:go ahead|do that|do it|yes|sure|please do|apply it|"
    r"make those changes|make that change|use that|do what you "
    r"recommended|do what you suggested)\b",
    re.IGNORECASE
)
STORY_REQUEST_CUES = re.compile(
    r"\b(?:story|stories|roleplay|scene|narrative|chapter|fiction|"
    r"character|protagonist)\b",
    re.IGNORECASE
)
STORY_CREATION_CUES = re.compile(
    r"\b(?:tell|write|create|invent|make|continue|expand|rewrite)\b"
    r".{0,40}\b(?:story|stories|roleplay|scene|narrative|chapter|"
    r"fiction)\b",
    re.IGNORECASE
)
STORY_INTENTS = {
    "begin_story",
    "continue_story",
    "creative_writing",
    "roleplay",
    "storytelling"
}


def understand(message):

    return get_intent_model().classify(normalize(message))


def is_coding_request(
    message,
    understanding=None,
    phase="chat",
    history=None,
    project_active=False
):

    text = normalize(message)

    if not text:

        return False

    has_language = bool(CODING_LANGUAGE_CUES.search(text))
    has_subject = bool(CODING_SUBJECT_CUES.search(text))
    has_action = bool(CODING_ACTION_CUES.search(text))
    story_confident = bool(
        understanding
        and understanding.label in STORY_INTENTS
        and understanding.confidence >= 0.40
    )

    if story_confident:

        if (
            STORY_REQUEST_CUES.search(text)
            and (
                STORY_CREATION_CUES.search(text)
                or not (
                    has_subject
                    and STRONG_CODING_ACTION_CUES.search(text)
                )
            )
        ):

            return False

        if not (
            (has_language or has_subject)
            and has_action
            or (
                project_active
                and has_subject
                and STRONG_CODING_ACTION_CUES.search(text)
            )
        ):

            return False

    if has_language:

        return True

    if has_subject and has_action:

        return True

    if (
        understanding
        and understanding.label == "coding"
        and understanding.confidence >= 0.22
    ):

        return True

    context = " ".join(
        str(item.get("content") or "")
        for item in (history or [])[-6:]
        if item.get("role") in {"user", "assistant"}
    )
    has_code_context = bool(
        CODING_LANGUAGE_CUES.search(context)
        or (
            CODING_SUBJECT_CUES.search(context)
            and CODING_ACTION_CUES.search(context)
        )
    )

    return bool(
        has_code_context
        and (
            CODING_FOLLOW_UP_CUES.search(text)
            or (
                project_active
                and has_action
                and len(text.split()) <= 12
            )
        )
    )


def assistant_mode_for(
    message,
    understanding=None,
    phase="chat",
    history=None,
    project_active=False
):

    if is_coding_request(
        message,
        understanding,
        phase,
        history,
        project_active
    ):

        return "coding"

    if phase in {"setup", "story"}:

        return "story"

    return "assistant"


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
