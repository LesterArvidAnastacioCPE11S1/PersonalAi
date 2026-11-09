import json
import os

from dataclasses import asdict, dataclass, field, fields
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = ROOT / "config.json"


@dataclass
class ModelConfig:
    base_url: str = "http://127.0.0.1:1234/v1"
    model: str = ""
    api_key: str = "lm-studio"
    temperature: float = 0.9
    top_p: float = 0.95
    max_tokens: int = 900
    timeout: int = 300
    stream: bool = True
    vision: bool = False
    vision_model: str = ""


@dataclass
class ContextConfig:
    max_messages: int = 24
    max_chars: int = 16000


@dataclass
class AppConfig:
    host: str = "127.0.0.1"
    port: int = 8000
    db_path: str = "data/personal_ai.db"
    open_browser: bool = True
    mobile_access: bool = False
    access_token: str = ""


@dataclass
class BehaviorConfig:
    no_refusals: bool = True
    custom_instructions: str = ""


@dataclass
class MemoryConfig:
    auto_extract: bool = True
    extract_every: int = 3
    max_lore_chars: int = 4000
    max_summary_chars: int = 1400


@dataclass
class ImageConfig:
    enabled: bool = True
    comfy_url: str = "http://127.0.0.1:8188"
    comfy_dir: str = "comfyui"
    start_args: list = field(default_factory=lambda: ["--directml"])
    checkpoint: str = "v1-5-pruned-emaonly-fp16.safetensors"
    lora: str = "lcm-sd15.safetensors"
    steps: int = 8
    cfg: float = 1.5
    sampler: str = "lcm"
    scheduler: str = "sgm_uniform"
    width: int = 512
    height: int = 768
    negative: str = (
        "lowres, blurry, watermark, text, signature, deformed, "
        "extra limbs, bad anatomy"
    )
    style: str = "digital painting, cinematic lighting, detailed"
    prompt_chars: int = 320
    timeout: int = 300
    auto_start: bool = True


@dataclass
class Config:
    model: ModelConfig = field(default_factory=ModelConfig)
    context: ContextConfig = field(default_factory=ContextConfig)
    app: AppConfig = field(default_factory=AppConfig)
    behavior: BehaviorConfig = field(default_factory=BehaviorConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    image: ImageConfig = field(default_factory=ImageConfig)


def _build(section_type, values):
    if not isinstance(values, dict):
        return section_type()

    allowed = {item.name for item in fields(section_type)}

    return section_type(
        **{
            key: value
            for key, value in values.items()
            if key in allowed
        }
    )


def _resolve_path(value):
    path = Path(value)

    if path.is_absolute():
        return path

    return ROOT / path


def load_config(path=None):
    source = Path(
        path or os.environ.get("PAI_CONFIG", DEFAULT_CONFIG_PATH)
    )

    data = {}

    if source.exists():
        with source.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

    config = Config(
        model=_build(ModelConfig, data.get("model", {})),
        context=_build(ContextConfig, data.get("context", {})),
        app=_build(AppConfig, data.get("app", {})),
        behavior=_build(BehaviorConfig, data.get("behavior", {})),
        memory=_build(MemoryConfig, data.get("memory", {})),
        image=_build(ImageConfig, data.get("image", {}))
    )

    config.model.base_url = os.environ.get(
        "PAI_BASE_URL",
        config.model.base_url
    )

    config.model.model = os.environ.get(
        "PAI_MODEL",
        config.model.model
    )

    config.model.api_key = os.environ.get(
        "PAI_API_KEY",
        config.model.api_key
    )

    config.app.port = int(
        os.environ.get("PAI_PORT", config.app.port)
    )

    config.app.open_browser = (
        os.environ.get(
            "PAI_OPEN_BROWSER",
            "1" if config.app.open_browser else "0"
        )
        == "1"
    )

    config.app.db_path = _resolve_path(
        os.environ.get(
            "PAI_DB_PATH",
            config.app.db_path
        )
    )

    config.image.comfy_dir = _resolve_path(config.image.comfy_dir)

    return config


def _display_path(value):

    path = Path(value).resolve()

    try:

        return path.relative_to(ROOT).as_posix()

    except ValueError:

        return str(path)


def save_config(config, path=None):

    target = Path(
        path or os.environ.get("PAI_CONFIG", DEFAULT_CONFIG_PATH)
    )

    data = {
        "model": asdict(config.model),
        "context": asdict(config.context),
        "app": {
            **asdict(config.app),
            "db_path": _display_path(config.app.db_path)
        },
        "behavior": asdict(config.behavior),
        "memory": asdict(config.memory),
        "image": {
            **asdict(config.image),
            "comfy_dir": _display_path(config.image.comfy_dir)
        }
    }

    handle_path = target.with_suffix(".tmp")

    with handle_path.open("w", encoding="utf-8") as handle:

        json.dump(data, handle, indent=2)
        handle.write("\n")

    handle_path.replace(target)
