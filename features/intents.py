import re


EXAMPLES = {
    "begin_story": (
        "start the story",
        "begin the story",
        "write the opening scene",
        "let's start",
        "let's get started",
        "I'm ready to begin",
        "start now",
        "can you start the story?",
        "begin",
        "just start"
    ),
    "affirmation": (
        "yes",
        "yeah",
        "yep",
        "sure",
        "okay",
        "go ahead",
        "I'm ready",
        "let's go",
        "do it",
        "sounds good",
        "that works",
        "yes please"
    ),
    "deny": (
        "no",
        "nope",
        "not yet",
        "not now",
        "no thanks",
        "don't",
        "stop",
        "hold on"
    ),
    "pause": (
        "wait",
        "hold on",
        "one moment",
        "give me a second",
        "let me think",
        "not yet",
        "pause",
        "be right back",
        "hold that thought"
    ),
    "request_summary": (
        "show me the brief",
        "give me a summary",
        "summarize what we have",
        "recap",
        "what do we have so far",
        "where are we",
        "catch me up",
        "list the foundation",
        "overview of the world"
    ),
    "skip_interview": (
        "skip the questions",
        "skip the interview",
        "no more questions",
        "stop asking questions",
        "enough questions",
        "get to the story",
        "cut to the story",
        "I don't want to answer questions"
    ),
    "ai_decides": (
        "you decide",
        "you choose",
        "your call",
        "surprise me",
        "whatever you think",
        "I don't care",
        "fill in the blanks",
        "make something up",
        "invent it",
        "up to you"
    ),
    "revise": (
        "change the tone",
        "make the setting darker",
        "remove that faction",
        "add a rival character",
        "rename the city",
        "actually, the world is colder",
        "instead, make it a desert",
        "on second thought, change the era",
        "I'd rather have a different premise"
    ),
    "start_over": (
        "start over",
        "start again",
        "start from scratch",
        "reset the foundation",
        "scrap this",
        "scrap the setup",
        "rebuild the world",
        "new idea",
        "forget the setup",
        "wipe it"
    ),
    "continue_story": (
        "continue",
        "go on",
        "keep going",
        "carry on",
        "resume",
        "proceed",
        "next",
        "what happens next"
    ),
    "ooc": (
        "OOC: are you there?",
        "(OOC) change the pacing",
        "[OOC] let's talk about the plot",
        "out of character: I need a break",
        "// ooc: quick question"
    ),
    "rewrite": (
        "rewrite that",
        "rewrite the last response",
        "try again",
        "redo that",
        "regenerate",
        "that's not what I meant",
        "undo that",
        "different take"
    ),
    "expand": (
        "more detail",
        "in more detail",
        "expand on that",
        "elaborate",
        "flesh that out",
        "go deeper",
        "slow down",
        "take your time",
        "describe it more"
    ),
    "time_skip": (
        "skip ahead",
        "time skip",
        "jump forward",
        "jump to the next morning",
        "fast forward",
        "three days later",
        "next morning",
        "next day"
    )
}


BEGIN_PATTERNS = (
    re.compile(
        r"\b(?:start|begin|write)\s+(?:the|our|this|my|a|an)\s+"
        r"(?:story|scene|opening|tale|first scene)\b",
        re.IGNORECASE
    ),
    re.compile(
        r"\b(?:start|begin)\s+writing\b",
        re.IGNORECASE
    ),
    re.compile(
        r"\b(?:let'?s|let us)\s+(?:start|begin|get started)\b"
        r"(?!\s+(?:over|again|back)\b)",
        re.IGNORECASE
    ),
    re.compile(
        r"\b(?:let'?s|let us)\s+go\b(?:\s+now\b)?[.!]?$",
        re.IGNORECASE
    ),
    re.compile(
        r"\b(?:i(?:'m| am)\s+ready\s+to\s+(?:begin|start|get started))\b"
        r"(?!\s+(?:over|again)\b)",
        re.IGNORECASE
    ),
    re.compile(
        r"\b(?:start|begin|write|go)\s+(?:now|it|already)\b",
        re.IGNORECASE
    ),
    re.compile(
        r"^(?:ok(?:ay)?[,.!\s]+)?(?:and|but|so|then)?[,.!\s]*"
        r"(?:please\s+)?(?:start|begin)[.!]?$",
        re.IGNORECASE
    ),
    re.compile(
        r"\b(?:i\s+want\s+to|i(?:'d| would)\s+like\s+to|i\s+wanna)\s+"
        r"(?:start|begin)\b(?!\s+(?:with|over|again)\b)",
        re.IGNORECASE
    ),
    re.compile(
        r"\b(?:can|could|shall|should)\s+we\s+(?:start|begin)\b"
        r"(?!\s+(?:with|over|again)\b)",
        re.IGNORECASE
    ),
    re.compile(
        r"\b(?:can|could|would|will)\s+you\s+(?:start|begin|write)\s+"
        r"(?:the|our|this|my|a|an)\s+(?:story|scene|opening)\b",
        re.IGNORECASE
    ),
    re.compile(
        r"\bjust\s+(?:start|begin)(?:\s+(?:now|the story|it))?[.!]?$",
        re.IGNORECASE
    ),
    re.compile(
        r"^(?:yes|yeah|yep|sure|ok(?:ay)?)[,.!\s]+"
        r"(?:start|begin)(?:\s+(?:now|the story))?[.!]?$",
        re.IGNORECASE
    )
)

NEGATED_BEGIN = re.compile(
    r"\b(?:don'?t|do not|doesn'?t|not|never|no)\b"
    r"[^.?!,;]{0,30}\b(?:start|begin|write|go)\b",
    re.IGNORECASE
)

AFFIRMATION = re.compile(
    r"^(?:ok(?:ay)?[,.!\s]+)?"
    r"(?:yes|yeah|yep|yup|sure|alright|ok(?:ay)?|go ahead|"
    r"i(?:'m| am) ready|ready|let'?s go|do it|go|"
    r"sounds good|looks good|perfect|great|that works|"
    r"absolutely|definitely|please do|correct|right)"
    r"(?:\s+please)?[.!]?$",
    re.IGNORECASE
)

DENY = re.compile(
    r"(?:^(?:no|nope|nah|not yet|not now|later|"
    r"no thanks|no thank you|don'?t|do not|stop|"
    r"hold on|wait)\b)|"
    r"(?:\b(?:i(?:'m| am)\s+)?not\s+ready\b)",
    re.IGNORECASE
)

READY_CUE = re.compile(
    r"\b(?:ready to (?:begin|start|get started)|"
    r"shall we (?:begin|start|get started)|"
    r"(?:begin|start) the story|ready when you are|"
    r"begin whenever|start whenever|whenever you(?:'re| are) ready|"
    r"say the word|just say (?:begin|start|go)|"
    r"if you(?:'re| are) ready to (?:begin|start))\b",
    re.IGNORECASE
)

PAUSE = re.compile(
    r"\b(?:wait|hold on|one moment|give me a (?:second|minute|moment)|"
    r"let me think|not yet|not now|pause|brb|be right back|"
    r"i'?ll be back|hold that thought)\b",
    re.IGNORECASE
)

OTHER_INTENTS = {
    "request_summary": (
        re.compile(
            r"\b(?:story brief|brief|summary|summarize|recap|rundown|"
            r"foundation so far|what (?:do we|we) have(?: so far)?|"
            r"where are we|catch me up|"
            r"list (?:what we have|the foundation)|"
            r"overview of (?:the )?(?:world|foundation|story))\b",
            re.IGNORECASE
        ),
    ),
    "skip_interview": (
        re.compile(
            r"\b(?:skip (?:the )?(?:questions|interview|setup)|"
            r"no more questions|stop asking(?: questions)?|"
            r"enough questions|stop with the questions|"
            r"get to the story|cut to the story|"
            r"i don'?t want to answer(?: more)? questions|"
            r"let'?s skip(?: this)?|skip the rest)\b",
            re.IGNORECASE
        ),
    ),
    "ai_decides": (
        re.compile(
            r"\b(?:you (?:decide|choose|pick)|your (?:call|choice)|"
            r"surprise me|dealer'?s choice|"
            r"whatever you (?:think|want|prefer)|"
            r"i don'?t (?:care|mind)|fill in the blanks|"
            r"make something up|invent it|"
            r"use your (?:judgment|imagination)|up to you)\b",
            re.IGNORECASE
        ),
    ),
    "revise": (
        re.compile(
            r"\b(?:change|revise|edit|update|remove|delete|drop|add|"
            r"rename|replace|swap|tweak|adjust|make)\b[^.?!\n]{0,80}\b"
            r"(?:setting|world|lore|character|characters|faction|"
            r"factions|rule|rules|tone|style|timeline|history|conflict|"
            r"premise|role|location|locations|city|cities|town|"
            r"kingdom|realm|nation|empire|arc|arcs)\b",
            re.IGNORECASE
        ),
        re.compile(
            r"\b(?:actually|instead|on second thought|scratch that|"
            r"i(?:'d| would) rather)\b",
            re.IGNORECASE
        ),
    ),
    "start_over": (
        re.compile(
            r"\b(?:start over|start again|start from scratch|from scratch|"
            r"reset (?:the )?(?:foundation|setup|story|world)|"
            r"scrap (?:this|it)|scrap the (?:setup|foundation|world)|"
            r"rebuild (?:the )?(?:foundation|setup|world)|new idea|"
            r"forget (?:the|this) (?:setup|world)|wipe (?:it|this))\b",
            re.IGNORECASE
        ),
    ),
    "continue_story": (
        re.compile(
            r"^(?:continue|go on|keep going|carry on|resume|proceed|"
            r"next|and then\??|what happens next\??|go)[.!]?$",
            re.IGNORECASE
        ),
        re.compile(
            r"\b(?:what happens next|and then what|"
            r"(?:continue|resume) (?:the )?(?:story|scene))\b",
            re.IGNORECASE
        ),
    ),
    "ooc": (
        re.compile(
            r"^(?:ooc\b|\(ooc\b|\[ooc\b|out of character\b|"
            r"//\s*ooc\b)",
            re.IGNORECASE
        ),
    ),
    "rewrite": (
        re.compile(
            r"\b(?:rewrite (?:that|this|the last(?: response| reply)?|it)|"
            r"try again|redo (?:that|this|it)|regenerate|"
            r"that'?s not what i meant|not what i meant|"
            r"undo (?:that|this)|different take)\b",
            re.IGNORECASE
        ),
    ),
    "expand": (
        re.compile(
            r"\b(?:more detail|in more detail|expand (?:on )?(?:that|this|it)|"
            r"elaborate|flesh (?:that|this|it) out|go deeper|"
            r"slow (?:down|it down)|take your time|"
            r"describe (?:that|it) more)\b",
            re.IGNORECASE
        ),
    ),
    "time_skip": (
        re.compile(
            r"\b(?:skip ahead|time ?skip|jump (?:ahead|forward|to)|"
            r"fast forward|days later|weeks later|months later|"
            r"next morning|next day)\b",
            re.IGNORECASE
        ),
    )
}


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


def asks_to_begin(message):

    return bool(
        READY_CUE.search(message or "")
    )


def _begin_candidates(text):

    clauses = re.split(
        r"(?<=[.!?,;])\s+",
        text
    )

    return [
        clause
        for clause in clauses
        if clause.strip() and not NEGATED_BEGIN.search(clause)
    ]


def detect(message):

    text = normalize(message)

    if not text:

        return set()

    found = set()

    for clause in _begin_candidates(text):

        if any(
            pattern.search(clause)
            for pattern in BEGIN_PATTERNS
        ):

            found.add("begin_story")
            break

    if AFFIRMATION.match(text):

        found.add("affirmation")

    if DENY.match(text):

        found.add("deny")

    if PAUSE.search(text):

        found.add("pause")

    for name, patterns in OTHER_INTENTS.items():

        if any(
            pattern.search(text)
            for pattern in patterns
        ):

            found.add(name)

    if "begin_story" in found:

        found.discard("deny")
        found.discard("pause")

    if "start_over" in found:

        found.discard("revise")

    return found


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
