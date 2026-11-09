import sys

from features.browser_open import open_ui


def main():

    if len(sys.argv) < 2:

        return 1

    open_ui(sys.argv[1])

    return 0


if __name__ == "__main__":

    sys.exit(main())
