import sys

from features.browser_open import open_ui


def main():

    if len(sys.argv) < 2:

        return 1

    result = open_ui(sys.argv[1])

    if result == "window":

        print("[ui] PersonalAI window opened.")

    elif result == "browser":

        print("[ui] Opened PersonalAI in your default browser.")

    else:

        print(
            f"[ui] Could not open the window. Open {sys.argv[1]} in your browser."
        )
        return 1

    return 0


if __name__ == "__main__":

    sys.exit(main())
