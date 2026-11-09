import threading
import time
import urllib.request

import uvicorn

from config import load_config, save_config
from features.browser_open import open_ui
from features.mobile_access import generate_token, lan_addresses


def open_when_ready(url):

    for _ in range(240):

        try:

            urllib.request.urlopen(
                url + "/api/ping",
                timeout=2
            ).close()
            open_ui(url)
            return

        except Exception:

            time.sleep(0.5)


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
    print(
        "Vision     : "
        + (
            f"on ({config.model.vision_model})"
            if config.model.vision and config.model.vision_model
            else (
                "on (main model)"
                if config.model.vision
                else "off"
            )
        )
    )
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

        threading.Thread(
            target=open_when_ready,
            args=(url,),
            daemon=True
        ).start()

    import server as server_module

    server_config = uvicorn.Config(
        server_module.app,
        host=(
            "0.0.0.0"
            if config.app.mobile_access
            else config.app.host
        ),
        port=config.app.port,
        log_level="info"
    )
    server = uvicorn.Server(server_config)

    def shutdown():

        time.sleep(0.4)
        server.should_exit = True

    server_module.app.state.shutdown = shutdown
    server.run()


if __name__ == "__main__":

    main()
