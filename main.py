import threading
import webbrowser

import uvicorn

from config import load_config, save_config
from features.mobile_access import generate_token, lan_addresses


def main():

    config = load_config()

    url = f"http://127.0.0.1:{config.app.port}"

    if (
        config.app.mobile_access
        and not config.app.access_token
    ):

        config.app.access_token = generate_token()
        save_config(config)

    print()
    print("==============================")
    print("PersonalAI")
    print("==============================")
    print(f"UI         : {url}")
    print(f"Model      : {config.model.model or 'auto (first model the server reports)'}")
    print(f"Endpoint   : {config.model.base_url}")
    print(f"Database   : {config.app.db_path}")
    print(f"Temperature: {config.model.temperature}")
    print(f"Max tokens : {config.model.max_tokens}")
    print(f"Streaming  : {config.model.stream}")
    print(f"Vision     : {'on' if config.model.vision else 'off'}")
    print("Attachments: 6 files max, text/PDF/DOCX/images")
    print(
        "Freedom    : "
        + (
            "no refusals on"
            if config.behavior.no_refusals
            else "model defaults"
        )
    )
    print(
        "Memory     : "
        + (
            f"auto every {config.memory.extract_every} messages"
            if config.memory.auto_extract
            else "manual only"
        )
    )

    if config.app.mobile_access:

        code = config.app.access_token

        if len(code) == 10:

            code = f"{code[:5]}-{code[5:]}"

        print("Phone      : on")
        print(f"Access code: {code}")

        addresses = lan_addresses()

        if addresses:

            for address in addresses:

                print(
                    f"Phone URL  : http://{address}:{config.app.port}"
                )

        else:

            print("Phone URL  : no LAN address found")

        print(
            "Firewall   : allow Python on private networks "
            "or the phone cannot connect"
        )

    else:

        print("Phone      : off (enable in Settings)")

    print("==============================")
    print()

    if config.app.open_browser:

        threading.Timer(
            1.0,
            lambda: webbrowser.open(url)
        ).start()

    uvicorn.run(
        "server:app",
        host=(
            "0.0.0.0"
            if config.app.mobile_access
            else config.app.host
        ),
        port=config.app.port,
        log_level="info"
    )


if __name__ == "__main__":

    main()
