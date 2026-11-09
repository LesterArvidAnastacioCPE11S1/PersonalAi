import json
import random
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from datetime import datetime
from pathlib import Path

from features.attachments import AttachmentError


POLL_SECONDS = 2
START_SECONDS = 180
SCENE_MIN_CHARS = 120


class ImageError(Exception):
    pass


class ImageService:

    def __init__(self, config, store, attachments):

        self.settings = config.image
        self.model_settings = config.model
        self.store = store
        self.attachments = attachments
        self.error = ""
        self._lock = threading.Lock()
        self._process = None

    def status(self):

        if not self.settings.enabled:

            return {"enabled": False, "online": False, "error": "disabled"}

        online = self._online()

        return {
            "enabled": True,
            "online": online,
            "error": "" if online else (self.error or "not running")
        }

    def generate(self, conversation_id, message_id=None, prompt=None):

        if not self.settings.enabled:

            raise ImageError("Image generation is turned off in config.json.")

        scene = self._scene(conversation_id, message_id)
        text = (prompt or "").strip() or scene

        if not text:

            raise ImageError("There is no scene to paint yet.")

        full = self._compose(text)

        with self._lock:

            self._unload_chat()
            self._ensure_online()

            try:

                data = self._render(full)

            finally:

                self._stop()

        return self._store_image(conversation_id, message_id, data), full

    def _ollama_root(self):

        parsed = urllib.parse.urlparse(self.model_settings.base_url)

        if not parsed.scheme or not parsed.netloc:

            return ""

        return f"{parsed.scheme}://{parsed.netloc}"

    def _running_models(self, root):

        try:

            with urllib.request.urlopen(root + "/api/ps", timeout=5) as response:

                payload = json.load(response)

        except Exception:

            return []

        return payload.get("models") or []

    def _unload_chat(self):

        root = self._ollama_root()

        if not root:

            return

        for item in self._running_models(root):

            name = item.get("name") or item.get("model")

            if not name:

                continue

            body = json.dumps(
                {"model": name, "keep_alive": 0}
            ).encode("utf-8")
            request = urllib.request.Request(
                root + "/api/generate",
                data=body,
                headers={"Content-Type": "application/json"}
            )

            try:

                with urllib.request.urlopen(request, timeout=30):

                    pass

            except Exception:

                pass

        deadline = time.time() + 10

        while time.time() < deadline:

            if not self._running_models(root):

                return

            time.sleep(0.5)

    def _scene(self, conversation_id, message_id):

        messages = self.store.get_messages(conversation_id)
        end = len(messages) - 1

        if message_id is not None:

            for index, row in enumerate(messages):

                if row["id"] == message_id:

                    end = index
                    break

        window = messages[:end + 1]

        for row in reversed(window):

            content = (row["content"] or "").strip()

            if row["role"] == "assistant" and len(content) >= SCENE_MIN_CHARS:

                return content

        for row in reversed(window):

            content = (row["content"] or "").strip()

            if row["role"] == "user" and content:

                return content

        return ""

    def _compose(self, text):

        clean = " ".join((text or "").split())
        limit = max(120, int(self.settings.prompt_chars))

        if len(clean) > limit:

            cut = clean[-limit:]
            space = cut.find(" ")

            if 0 <= space < 40:

                cut = cut[space + 1:]

            clean = cut

        style = (self.settings.style or "").strip()

        if style:

            clean = f"{clean}, {style}"

        return clean[:600]

    def _store_image(self, conversation_id, message_id, data):

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

        try:

            row, _ = self.attachments.save(
                conversation_id,
                f"scene-{stamp}.png",
                data
            )

        except AttachmentError as error:

            raise ImageError(str(error)) from error

        if message_id is not None:

            self.store.link_attachments([row["id"]], message_id)
            row = self.store.get_attachment(row["id"]) or row

        return self.attachments.public(row)

    def _base(self):

        return self.settings.comfy_url.rstrip("/")

    def _online(self, timeout=2):

        try:

            with urllib.request.urlopen(
                self._base() + "/system_stats",
                timeout=timeout
            ) as response:

                return response.status == 200

        except Exception:

            return False

    def _ensure_online(self):

        if self._online():

            self.error = ""

            return

        if not self.settings.auto_start:

            raise ImageError("ComfyUI is not running at " + self._base() + ".")

        folder = Path(self.settings.comfy_dir)
        python = folder / ".venv" / "Scripts" / "python.exe"
        main = folder / "main.py"

        if not python.exists() or not main.exists():

            raise ImageError(
                "ComfyUI was not found at " + str(folder) + ". "
                "Set image.comfy_dir in config.json."
            )

        port = urllib.parse.urlparse(self._base()).port or 8188
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        command = [
            str(python),
            str(main),
            "--listen",
            "127.0.0.1",
            "--port",
            str(port)
        ] + [str(item) for item in (self.settings.start_args or [])]

        self._process = subprocess.Popen(
            command,
            cwd=str(folder),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags
        )

        deadline = time.time() + START_SECONDS

        while time.time() < deadline:

            if self._online():

                self.error = ""

                return

            if self._process.poll() is not None:

                self.error = "ComfyUI exited during startup."

                raise ImageError(
                    "ComfyUI failed to start. Check the image settings in "
                    "config.json."
                )

            time.sleep(1)

        self.error = "ComfyUI did not start in time."

        raise ImageError(self.error)

    def _render(self, prompt):

        workflow = self._workflow(prompt)
        body = json.dumps({"prompt": workflow}).encode("utf-8")
        request = urllib.request.Request(
            self._base() + "/prompt",
            data=body,
            headers={"Content-Type": "application/json"}
        )

        try:

            with urllib.request.urlopen(request, timeout=60) as response:

                queued = json.load(response)

        except urllib.error.HTTPError as error:

            detail = error.read().decode("utf-8", "replace")

            raise ImageError(
                "ComfyUI rejected the request: " + detail[:300]
            ) from error

        except Exception as error:

            raise ImageError(f"Could not reach ComfyUI: {error}") from error

        prompt_id = queued.get("prompt_id")

        if not prompt_id:

            raise ImageError(
                "ComfyUI did not queue the image: " + str(queued)[:300]
            )

        deadline = time.time() + max(30, int(self.settings.timeout))

        while time.time() < deadline:

            entry = self._history(prompt_id)

            if entry is not None:

                return self._fetch(entry)

            time.sleep(POLL_SECONDS)

        raise ImageError(
            "The image took too long. Try again with a smaller size."
        )

    def _history(self, prompt_id):

        try:

            with urllib.request.urlopen(
                self._base() + "/history/" + prompt_id,
                timeout=15
            ) as response:

                history = json.load(response)

        except Exception:

            return None

        return history.get(prompt_id)

    def _stop(self):

        process = self._process

        if process is None:

            return

        self._release()
        self._process = None

        try:

            process.terminate()
            process.wait(timeout=15)

        except Exception:

            try:

                process.kill()

            except Exception:

                pass

    def _release(self):
        request = urllib.request.Request(
            self._base() + "/free",
            data=json.dumps(
                {"unload_models": True, "free_memory": True}
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        try:

            with urllib.request.urlopen(request, timeout=10):

                pass

        except Exception:

            pass

    def _fetch(self, entry):
        status = entry.get("status") or {}

        if status.get("status_str") == "error":

            raise ImageError(
                "ComfyUI could not build the image. Check its console output."
            )

        image = None

        for output in (entry.get("outputs") or {}).values():

            images = output.get("images") or []

            if images:

                image = images[0]

                break

        if image is None:

            raise ImageError("ComfyUI finished without an image.")

        query = urllib.parse.urlencode(
            {
                "filename": image["filename"],
                "subfolder": image.get("subfolder", ""),
                "type": image.get("type", "output")
            }
        )

        with urllib.request.urlopen(
            self._base() + "/view?" + query,
            timeout=60
        ) as response:

            return response.read()

    def _workflow(self, prompt):

        settings = self.settings
        seed = random.randint(1, 2_147_483_647)
        checkpoint = settings.checkpoint
        lora = (settings.lora or "").strip()

        nodes = {
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": checkpoint}
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": prompt, "clip": ["4", 1]}
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": settings.negative, "clip": ["4", 1]}
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": int(settings.width),
                    "height": int(settings.height),
                    "batch_size": 1
                }
            },
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": seed,
                    "steps": int(settings.steps),
                    "cfg": float(settings.cfg),
                    "sampler_name": settings.sampler,
                    "scheduler": settings.scheduler,
                    "denoise": 1.0,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0]
                }
            },
            "8": {
                "class_type": "VAEDecodeTiled",
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2],
                    "tile_size": 256,
                    "overlap": 64,
                    "temporal_size": 64,
                    "temporal_overlap": 8
                }
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": "personalai_scene",
                    "images": ["8", 0]
                }
            }
        }

        if lora:

            nodes["10"] = {
                "class_type": "LoraLoader",
                "inputs": {
                    "model": ["4", 0],
                    "clip": ["4", 1],
                    "lora_name": lora,
                    "strength_model": 1.0,
                    "strength_clip": 1.0
                }
            }
            nodes["3"]["inputs"]["model"] = ["10", 0]
            nodes["6"]["inputs"]["clip"] = ["10", 1]
            nodes["7"]["inputs"]["clip"] = ["10", 1]

        return nodes
