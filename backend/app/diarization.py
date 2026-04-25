import os
from functools import lru_cache
from typing import Any, Dict, List, Optional

from app.env import load_app_env

load_app_env()

DEFAULT_LOCAL_MODEL = "pyannote/speaker-diarization-community-1"
DEFAULT_CLOUD_MODEL = "pyannote/speaker-diarization-precision-2"
PLACEHOLDER_VALUES = {
    "",
    "your_huggingface_token_here",
    "your_pyannoteai_key",
    "your_pyannoteai_api_key_here",
}


def is_diarization_enabled() -> bool:
    value = os.environ.get("DIARIZATION_ENABLED", "1").strip().lower()
    return value not in {"0", "false", "no", "off"}


def get_diarization_config() -> Dict[str, Any]:
    huggingface_token = os.environ.get("HUGGINGFACE_TOKEN", "").strip()
    pyannoteai_api_key = os.environ.get("PYANNOTEAI_API_KEY", "").strip()
    configured_backend = os.environ.get("DIARIZATION_BACKEND", "").strip().lower()

    if huggingface_token in PLACEHOLDER_VALUES:
        huggingface_token = ""

    if pyannoteai_api_key in PLACEHOLDER_VALUES:
        pyannoteai_api_key = ""

    if configured_backend == "precision-2":
        return {
            "enabled": bool(pyannoteai_api_key),
            "backend": "precision-2",
            "model": os.environ.get("DIARIZATION_MODEL", DEFAULT_CLOUD_MODEL),
            "token": pyannoteai_api_key,
            "device": "cloud",
        }

    if configured_backend == "community-1":
        return {
            "enabled": bool(huggingface_token),
            "backend": "community-1",
            "model": os.environ.get("DIARIZATION_MODEL", DEFAULT_LOCAL_MODEL),
            "token": huggingface_token,
            "device": os.environ.get("DIARIZATION_DEVICE", "auto"),
        }

    if pyannoteai_api_key:
        return {
            "enabled": True,
            "backend": "precision-2",
            "model": os.environ.get("DIARIZATION_MODEL", DEFAULT_CLOUD_MODEL),
            "token": pyannoteai_api_key,
            "device": "cloud",
        }

    if huggingface_token:
        return {
            "enabled": True,
            "backend": "community-1",
            "model": os.environ.get("DIARIZATION_MODEL", DEFAULT_LOCAL_MODEL),
            "token": huggingface_token,
            "device": os.environ.get("DIARIZATION_DEVICE", "auto"),
        }

    return {
        "enabled": False,
        "backend": "unconfigured",
        "model": None,
        "token": None,
        "device": None,
    }


def get_speaker_constraints() -> Dict[str, Optional[int]]:
    def parse_int(name: str) -> Optional[int]:
        raw_value = os.environ.get(name, "").strip()
        if not raw_value:
            return None
        try:
            return int(raw_value)
        except ValueError:
            return None

    return {
        "num_speakers": parse_int("DIARIZATION_NUM_SPEAKERS"),
        "min_speakers": parse_int("DIARIZATION_MIN_SPEAKERS"),
        "max_speakers": parse_int("DIARIZATION_MAX_SPEAKERS"),
    }


def describe_model_load_error(exc: Exception, config: Dict[str, Any]) -> str:
    message = str(exc)
    lowered = message.lower()
    model = config.get("model") or "the configured diarization model"

    if "cannot find the requested files in the local cache" in lowered:
        return (
            f"Unable to download {model} from Hugging Face. Check network access to "
            "huggingface.co, accept the model terms, and verify HUGGINGFACE_TOKEN."
        )

    if any(
        token in lowered
        for token in (
            "winerror 10061",
            "actively refused",
            "actively refused it",
            "cannot send a request, as the client has been closed",
            "connection refused",
            "connecterror",
        )
    ):
        return (
            f"Unable to connect to Hugging Face while loading {model}. "
            "Check whether this machine can reach https://huggingface.co "
            "(VPN/proxy/firewall), then retry."
        )

    if any(
        token in lowered
        for token in ("401", "403", "gated repo", "access to model", "unauthorized")
    ):
        return (
            f"Access to {model} was denied. Verify that HUGGINGFACE_TOKEN is valid and "
            "that the account accepted the pyannote model terms on Hugging Face."
        )

    if "repository not found" in lowered or "revision not found" in lowered:
        return (
            f"The diarization model '{model}' could not be found on Hugging Face. "
            "Check DIARIZATION_MODEL and DIARIZATION_BACKEND."
        )

    return f"Failed to load diarization model '{model}': {message}"


@lru_cache(maxsize=1)
def get_diarization_pipeline():
    config = get_diarization_config()
    if not config["enabled"]:
        raise RuntimeError("Speaker diarization is not configured.")

    try:
        from pyannote.audio import Pipeline
    except ImportError as exc:
        raise RuntimeError(
            "pyannote.audio is not installed. Install dependencies from requirements.txt."
        ) from exc

    try:
        pipeline = Pipeline.from_pretrained(config["model"], token=config["token"])
    except Exception as exc:
        raise RuntimeError(describe_model_load_error(exc, config)) from exc

    if config["backend"] != "precision-2" and config["device"] != "cloud":
        try:
            import torch

            device_name = config["device"]
            if device_name == "auto":
                if torch.cuda.is_available():
                    pipeline.to(torch.device("cuda"))
            else:
                pipeline.to(torch.device(device_name))
        except Exception:
            # CPU fallback is acceptable when GPU is unavailable or torch is not configured for CUDA.
            pass

    return pipeline


def normalize_turn(turn: Any) -> Dict[str, float]:
    return {
        "start": float(getattr(turn, "start", 0.0)),
        "end": float(getattr(turn, "end", 0.0)),
    }


def load_audio_for_diarization(audio_path: str) -> Dict[str, Any]:
    try:
        import soundfile as sf
        import torch
    except ImportError as exc:
        raise RuntimeError(
            "soundfile is required for in-memory audio loading. Install dependencies from requirements.txt."
        ) from exc

    try:
        waveform, sample_rate = sf.read(audio_path, always_2d=True)
    except Exception as exc:
        raise RuntimeError(
            "Failed to decode audio via soundfile. Install a compatible libsndfile build or convert the audio to WAV."
        ) from exc

    return {
        "waveform": torch.from_numpy(waveform.T).float(),
        "sample_rate": int(sample_rate),
    }


def diarize_audio(audio_path: str) -> Dict[str, Any]:
    if not is_diarization_enabled():
        return {
            "status": "disabled",
            "backend": "disabled",
            "segments": [],
            "exclusive_segments": [],
        }

    config = get_diarization_config()
    if not config["enabled"]:
        return {
            "status": "unconfigured",
            "backend": config["backend"],
            "segments": [],
            "exclusive_segments": [],
        }

    pipeline = get_diarization_pipeline()
    constraints = {k: v for k, v in get_speaker_constraints().items() if v is not None}
    audio_input = load_audio_for_diarization(audio_path)
    output = pipeline(audio_input, **constraints) if constraints else pipeline(audio_input)

    speaker_diarization = getattr(output, "speaker_diarization", output)
    exclusive_diarization = getattr(output, "exclusive_speaker_diarization", None)

    def to_segments(annotation: Any) -> List[Dict[str, Any]]:
        if annotation is None:
            return []

        if hasattr(annotation, "itertracks"):
            rows = []
            for turn, _, speaker in annotation.itertracks(yield_label=True):
                normalized_turn = normalize_turn(turn)
                rows.append(
                    {
                        "speaker": str(speaker),
                        "start": normalized_turn["start"],
                        "end": normalized_turn["end"],
                    }
                )
            return rows

        rows = []
        for item in annotation:
            if len(item) >= 2:
                turn, speaker = item[0], item[1]
                normalized_turn = normalize_turn(turn)
                rows.append(
                    {
                        "speaker": str(speaker),
                        "start": normalized_turn["start"],
                        "end": normalized_turn["end"],
                    }
                )
        return rows

    exclusive_segments = to_segments(exclusive_diarization)
    segments = to_segments(speaker_diarization)

    return {
        "status": "completed",
        "backend": config["backend"],
        "model": config["model"],
        "segments": segments,
        "exclusive_segments": exclusive_segments,
    }
