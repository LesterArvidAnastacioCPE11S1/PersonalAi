from features.intents import understand


class RequestRouter:

    def classify(self, message, understanding=None):

        turn = understanding or understand(message)

        return turn.label, turn.scores

    def decide(self, message, understanding=None):

        text = (message or "").strip()

        if not text:

            return "general", "unknown"

        turn = understanding or understand(text)

        ranked = sorted(
            turn.scores.items(),
            key=lambda pair: pair[1],
            reverse=True
        )

        runner_up = ranked[1][1] if len(ranked) > 1 else 0.0

        if turn.confidence < 0.18:

            return "general", turn.label

        if (
            turn.confidence < 0.30
            and turn.confidence < runner_up * 1.5
        ):

            return "general", turn.label

        if turn.label == "continue_story":

            return "continue", turn.label

        if turn.label in {"storytelling", "roleplay", "begin_story"}:

            return "story", turn.label

        return "general", turn.label
