 STORY_STYLES = [
    {
        "key": "grok",
        "name": "Grok-inspired",
        "description": (
            "Expressive, immersive, spontaneous prose with bold turns, "
            "sharp voices, and high momentum."
        ),
        "instructions": (
            "Write with high energy, irreverence, and spontaneity. Favor "
            "vivid, expressive prose and sharp, unguarded character voices. "
            "Let scenes take bold turns and introduce unexpected developments "
            "that grow logically from what is already established. Keep the "
            "momentum high, avoid formulaic pacing, and do not sand down "
            "rough edges or surprising ideas."
        )
    },
    {
        "key": "chatgpt",
        "name": "ChatGPT-inspired",
        "description": (
            "Structured, coherent storytelling with balanced description, "
            "natural dialogue, and strong continuity."
        ),
        "instructions": (
            "Write structured, coherent scenes with clear cause and effect. "
            "Balance action, dialogue, and description evenly. Keep character "
            "motivations legible and dialogue natural. Track continuity "
            "carefully, resolve beats cleanly, and end each scene with a "
            "clear step forward."
        )
    },
    {
        "key": "modern",
        "name": "Modern",
        "description": (
            "Contemporary style with natural dialogue, dynamic pacing, and "
            "character-driven cinematic scenes."
        ),
        "instructions": (
            "Write in a contemporary voice with natural, lived-in dialogue "
            "and dynamic pacing. Build character-driven scenes with cinematic "
            "but restrained description: specific sensory details, confident "
            "cuts, and consequences that land. Avoid ornate prose and "
            "old-fashioned narration."
        )
    },
    {
        "key": "classic",
        "name": "Classic",
        "description": (
            "Traditional literary narration with richer prose, atmosphere, "
            "and a deliberate pace."
        ),
        "instructions": (
            "Write traditional literary narration with richer, carefully "
            "built prose. Favor atmosphere, measured pacing, and evocative "
            "description. Use longer, well-formed sentences where they serve "
            "the rhythm, but stay readable. Let tension accumulate slowly "
            "instead of rushing to the next beat."
        )
    },
    {
        "key": "novel",
        "name": "Novel",
        "description": (
            "Deep literary narration focused on character interiority, "
            "development, world-building, and descriptive passages."
        ),
        "instructions": (
            "Write like a literary novel. Give weight to interior thought, "
            "character development, and subtext. Develop the world through "
            "specific detail and lived texture rather than exposition. Use "
            "descriptive passages that reveal character and place, and let "
            "scenes breathe. Prioritize depth over speed."
        )
    },
    {
        "key": "cinematic",
        "name": "Cinematic",
        "description": (
            "Visual, dramatic storytelling built from composed scenes, "
            "blocking, atmosphere, and impactful beats."
        ),
        "instructions": (
            "Write as if composing shots. Establish scene geography and "
            "character blocking clearly. Mix sharp dialogue, physical action, "
            "and atmosphere. Use visual, sensory detail and dramatic timing: "
            "cut between moments, hold on impactful beats, and end scenes on "
            "a strong image. Keep exposition visual rather than explained."
        )
    },
    {
        "key": "minimalist",
        "name": "Minimalist",
        "description": (
            "Lean, concise narration with straightforward dialogue and "
            "description limited to what matters."
        ),
        "instructions": (
            "Write lean and direct. Use short sentences, plain vocabulary, "
            "and dialogue-forward scenes. Include only the description that "
            "carries meaning. Cut filler, adverbs, and repeated beats. Let "
            "gaps and implications do the work, and keep every paragraph "
            "purposeful."
        )
    }
]

STYLE_MAP = {
    item["key"]: item
    for item in STORY_STYLES
}

DEFAULT_STYLE = {
    "key": "",
    "name": "Default",
    "description": (
        "No preset voice. The scenario's own style and tone guide the prose."
    )
}


def style_options():

    return [DEFAULT_STYLE] + [
        {
            "key": item["key"],
            "name": item["name"],
            "description": item["description"]
        }
        for item in STORY_STYLES
    ]


def is_style_key(value):

    key = (value or "").strip().lower()

    return key == "" or key in STYLE_MAP


def normalize_style(value):

    key = (value or "").strip().lower()

    return key if key in STYLE_MAP else ""


def style_name(value):

    key = normalize_style(value)

    if not key:

        return DEFAULT_STYLE["name"]

    return STYLE_MAP[key]["name"]


def style_block(value):

    item = STYLE_MAP.get(normalize_style(value))

    if item is None:

        return ""

    return (
        f"NARRATIVE STYLE: {item['name']}\n"
        f"{item['instructions']}\n"
        "- Apply this style to new narration only.\n"
        "- Never rewrite, summarize, or retell earlier scenes to match it.\n"
        "- Never change established facts, characters, lore, or continuity "
        "to fit the style."
    )
