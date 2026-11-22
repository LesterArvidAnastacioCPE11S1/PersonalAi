def pending_approvals(approvals):

    return [
        item for item in (approvals or [])
        if item.get("status") == "pending"
    ]


def tool_exchange_active(activity, messages):

    run_ids = [
        item.get("message_id")
        for item in (activity or [])
        if item.get("message_id")
    ]

    if not run_ids:

        return False

    user_ids = [
        item["id"]
        for item in (messages or [])
        if item.get("role") == "user" and item.get("id")
    ]

    if not user_ids:

        return False

    return max(run_ids) >= min(user_ids[-2:])


def is_affirmation(understanding):

    return (
        understanding is not None
        and understanding.label == "affirmation"
        and understanding.confidence >= 0.30
    )


def activity_note(activity, pending):

    lines = []

    for item in pending[-3:]:

        lines.append(
            f"- pending approval: {item.get('tool')} "
            f"{item.get('args')}: {item.get('summary')}"
        )

    for item in (activity or [])[-5:]:

        output = " ".join(
            str(item.get("output") or "").split()
        )[:200]

        lines.append(
            f"- {item.get('tool')} {item.get('args')} -> "
            f"{item.get('status')}: {output}"
        )

    if not lines:

        return ""

    return (
        "ROUTING NOTE\n"
        "Recent tool activity from earlier turns, for reference only:\n"
        + "\n".join(lines)
        + "\nUse it to resolve references like 'it', 'that', or 'go ahead'. "
        "Do not claim anything from it happened in this turn. If an approval "
        "is already pending, do not propose it again and do not say it ran; "
        "tell the user to press Approve on the card."
    )


def approval_wait_note(pending):

    lines = [
        f"- {item.get('tool')} {item.get('args')}: {item.get('summary')}"
        for item in (pending or [])[-3:]
    ]

    return (
        "ROUTING NOTE\n"
        "An approval card is already waiting for the user:\n"
        + "\n".join(lines)
        + "\nThe user just agreed with it. Tell them to press Approve on the "
        "card in one short sentence. Do not claim it ran and do not propose "
        "another action."
    )
