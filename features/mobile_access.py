import html
import ipaddress
import secrets
import socket


TOKEN_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
TOKEN_LENGTH = 10
COOKIE_NAME = "pai_token"
HEADER_NAME = "X-PAI-Token"


def generate_token():

    raw = "".join(
        secrets.choice(TOKEN_ALPHABET)
        for _ in range(TOKEN_LENGTH)
    )

    return f"{raw[:5]}-{raw[5:]}"


def normalize_token(value):

    if not value:

        return ""

    return "".join(
        character
        for character in str(value).upper()
        if character.isalnum()
    )


def token_valid(expected, provided):

    expected_token = normalize_token(expected)
    provided_token = normalize_token(provided)

    if not expected_token or not provided_token:

        return False

    return secrets.compare_digest(
        expected_token,
        provided_token
    )


def is_loopback(host):

    if not host:

        return False

    try:

        return ipaddress.ip_address(host).is_loopback

    except ValueError:

        return host == "localhost"


def lan_addresses():

    found = set()

    try:

        with socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM
        ) as probe:

            probe.connect(("10.255.255.255", 1))
            found.add(probe.getsockname()[0])

    except OSError:

        pass

    try:

        for info in socket.getaddrinfo(
            socket.gethostname(),
            None,
            socket.AF_INET
        ):

            found.add(info[4][0])

    except OSError:

        pass

    usable = []

    for address in found:

        try:

            parsed = ipaddress.ip_address(address)

        except ValueError:

            continue

        if (
            parsed.is_loopback
            or parsed.is_link_local
            or parsed.is_unspecified
        ):

            continue

        usable.append(address)

    return sorted(usable)


def login_page(error=""):

    message = (
        f"<p class='error'>{html.escape(error)}</p>"
        if error
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PersonalAI access</title>
<style>
:root {{ color-scheme: dark; }}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background: #0b0b0b;
  color: #f2f2f2;
  font-family: -apple-system, "Segoe UI", system-ui, sans-serif;
}}
.card {{
  width: 100%;
  max-width: 360px;
  padding: 24px;
  border: 1px solid #232323;
  border-radius: 16px;
  background: #111;
}}
h1 {{
  margin: 0 0 6px;
  font-size: 20px;
  font-weight: 650;
}}
p {{
  margin: 0 0 18px;
  font-size: 13px;
  line-height: 1.5;
  color: #9a9a9a;
}}
.error {{ color: #ff8f8f; }}
label {{
  display: block;
  margin-bottom: 8px;
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #8a8a8a;
}}
input {{
  width: 100%;
  padding: 12px;
  border: 1px solid #2c2c2c;
  border-radius: 10px;
  background: #0d0d0d;
  color: #f4f4f4;
  font-size: 17px;
  letter-spacing: 0.14em;
  text-align: center;
  text-transform: uppercase;
}}
input:focus {{ outline: none; border-color: #5b5b5b; }}
button {{
  width: 100%;
  margin-top: 12px;
  padding: 12px;
  border: 0;
  border-radius: 10px;
  background: #f2f2f2;
  color: #101010;
  font-size: 14px;
  font-weight: 650;
  cursor: pointer;
}}
</style>
</head>
<body>
<form class="card" method="get" action="/pair">
  <h1>PersonalAI</h1>
  <p>Enter the access code shown in the app window on the PC. Your phone must be on the same network.</p>
  {message}
  <label for="code">Access code</label>
  <input id="code" name="token" autocomplete="off" autocapitalize="characters" spellcheck="false" placeholder="ABCDE-FGHIJ" required>
  <button type="submit">Open chat</button>
</form>
</body>
</html>"""
