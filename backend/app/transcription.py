import os
from functools import lru_cache
from typing import Any, Dict, List, Optional

from app.diarization import (
    describe_model_load_error,
    get_diarization_config,
    get_speaker_constraints,
    is_diarization_enabled,
)
from app.env import load_app_env

load_app_env()


def parse_bool_env(name: str, default: bool = False) -> bool:
    value = os.environ.get(name, "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def get_whisperx_device() -> str:
    configured = os.environ.get("WHISPERX_DEVICE", "auto").strip().lower()
    if configured and configured != "auto":
        return configured

    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


def get_whisperx_compute_type(device: str) -> str:
    configured = os.environ.get("WHISPERX_COMPUTE_TYPE", "").strip()
    if configured:
        return configured
    return "float16" if device == "cuda" else "int8"


def get_whisperx_language() -> Optional[str]:
    configured = os.environ.get("WHISPERX_LANGUAGE", "").strip().lower()
    return configured or None


def get_whisperx_model_name(device: str) -> str:
    configured_dir = os.environ.get("WHISPERX_MODEL_DIR", "").strip()
    if configured_dir:
        return configured_dir

    configured = os.environ.get("WHISPERX_MODEL", "").strip()
    if configured:
        return configured
    return "large-v2" if device == "cuda" else "small"


def get_whisperx_batch_size(device: str) -> int:
    configured = os.environ.get("WHISPERX_BATCH_SIZE", "").strip()
    if configured:
        try:
            return max(1, int(configured))
        except ValueError:
            pass
    return 16 if device == "cuda" else 4


def get_whisperx_threads() -> int:
    configured = os.environ.get("WHISPERX_THREADS", "").strip()
    if configured:
        try:
            return max(1, int(configured))
        except ValueError:
            pass

    cpu_count = os.cpu_count() or 4
    return max(2, min(cpu_count, 8))


def get_whisperx_vad_method(device: str) -> str:
    configured = os.environ.get("WHISPERX_VAD_METHOD", "").strip().lower()
    if configured:
        return configured
    return "silero" if device == "cpu" else "pyannote"


def get_whisperx_download_root() -> Optional[str]:
    configured = os.environ.get("WHISPERX_DOWNLOAD_ROOT", "").strip()
    return configured or None


def is_whisperx_local_files_only() -> bool:
    return parse_bool_env("WHISPERX_LOCAL_FILES_ONLY", False)


def get_whisperx_align_model_name() -> Optional[str]:
    configured = os.environ.get("WHISPERX_ALIGN_MODEL", "").strip()
    return configured or None


def get_whisperx_align_model_dir() -> Optional[str]:
    configured = os.environ.get("WHISPERX_ALIGN_MODEL_DIR", "").strip()
    return configured or get_whisperx_download_root()


def is_whisperx_align_local_files_only() -> bool:
    return parse_bool_env(
        "WHISPERX_ALIGN_LOCAL_FILES_ONLY", is_whisperx_local_files_only()
    )


def describe_whisperx_load_error(exc: Exception, target: str) -> str:
    message = str(exc)
    lowered = message.lower()

    if any(
        token in lowered
        for token in (
            "maxretryerror",
            "ssl",
            "unexpected_eof_while_reading",
            "ssleoferror",
            "httpsconnectionpool",
        )
    ):
        return (
            f"Unable to download the WhisperX {target} from Hugging Face because the SSL/network "
            "connection failed. Retry on a more stable network, or pre-download the model and set "
            "`WHISPERX_DOWNLOAD_ROOT` / `WHISPERX_LOCAL_FILES_ONLY=1`."
        )

    if any(token in lowered for token in ("401", "403", "unauthorized", "access denied")):
        return (
            f"Access to the WhisperX {target} was denied. Check whether the model requires authentication "
            "and verify any Hugging Face token configuration."
        )

    if "local_files_only" in lowered or "cannot find the requested files in the disk cache" in lowered:
        return (
            f"The WhisperX {target} was not found in the local cache. Download it once online first, "
            "or disable local-only mode."
        )

    return f"Failed to load the WhisperX {target}: {message}"


def load_audio_for_whisperx(audio_path: str):
    try:
        import whisperx

        return whisperx.load_audio(audio_path)
    except FileNotFoundError:
        try:
            import numpy as np
            import soundfile as sf
            import torch
            import torchaudio
        except ImportError as exc:
            raise RuntimeError(
                "Audio decoding requires ffmpeg or the soundfile/torchaudio fallback dependencies."
            ) from exc

        try:
            waveform, sample_rate = sf.read(audio_path, always_2d=True)
        except Exception as exc:
            raise RuntimeError(
                "WhisperX could not decode the uploaded audio. Install ffmpeg or convert the file to WAV."
            ) from exc

        mono = waveform.mean(axis=1, dtype=np.float32)
        audio_tensor = torch.from_numpy(mono).unsqueeze(0)

        if sample_rate != 16000:
            audio_tensor = torchaudio.functional.resample(audio_tensor, sample_rate, 16000)

        return audio_tensor.squeeze(0).numpy().astype(np.float32, copy=False)


@lru_cache(maxsize=4)
def get_whisperx_model(model_name: str, device: str, compute_type: str):
    try:
        import whisperx
    except ImportError as exc:
        raise RuntimeError(
            "WhisperX is not installed. Install dependencies from requirements.txt."
        ) from exc

    try:
        return whisperx.load_model(
            model_name,
            device,
            compute_type=compute_type,
            language=get_whisperx_language(),
            vad_method=get_whisperx_vad_method(device),
            download_root=get_whisperx_download_root(),
            local_files_only=is_whisperx_local_files_only(),
            threads=get_whisperx_threads(),
        )
    except Exception as exc:
        raise RuntimeError(describe_whisperx_load_error(exc, "ASR model")) from exc


@lru_cache(maxsize=8)
def get_alignment_model(language_code: str, device: str):
    import whisperx

    try:
        return whisperx.load_align_model(
            language_code=language_code,
            device=device,
            model_name=get_whisperx_align_model_name(),
            model_dir=get_whisperx_align_model_dir(),
            model_cache_only=is_whisperx_align_local_files_only(),
        )
    except Exception as exc:
        raise RuntimeError(describe_whisperx_load_error(exc, "alignment model")) from exc


@lru_cache(maxsize=2)
def get_whisperx_diarization_pipeline(token: str, device: str):
    try:
        from whisperx.diarize import DiarizationPipeline
    except ImportError as exc:
        raise RuntimeError(
            "WhisperX diarization components are not installed. Install dependencies from requirements.txt."
        ) from exc

    try:
        return DiarizationPipeline(token=token, device=device)
    except Exception as exc:
        config = get_diarization_config()
        raise RuntimeError(describe_model_load_error(exc, config)) from exc


def normalize_word_entries(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    words = []
    for segment in segments:
        for word in segment.get("words", []) or []:
            start = word.get("start")
            end = word.get("end", start)
            token = word.get("word") or word.get("text") or ""
            if start is None or end is None or not str(token).strip():
                continue
            entry = {
                "text": str(token).strip(),
                "start": float(start),
                "end": float(end),
            }
            if word.get("speaker"):
                entry["speaker"] = str(word["speaker"])
            words.append(entry)
    return words


def normalize_transcript_segments(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized = []
    for segment in segments or []:
        text = str(segment.get("text", "")).strip()
        start = segment.get("start")
        end = segment.get("end")
        if not text or start is None or end is None:
            continue

        row = {
            "text": text,
            "start": float(start),
            "end": float(end),
        }
        if segment.get("speaker"):
            row["speaker"] = str(segment["speaker"])
        normalized.append(row)
    return normalized


def normalize_diarization_segments(diarize_segments: Any) -> List[Dict[str, Any]]:
    if diarize_segments is None:
        return []

    if hasattr(diarize_segments, "to_dict"):
        rows = diarize_segments.to_dict("records")
    else:
        rows = list(diarize_segments)

    normalized = []
    for row in rows:
        start = row.get("start")
        end = row.get("end")
        speaker = row.get("speaker") or row.get("label")
        if start is None or end is None or speaker is None:
            continue
        normalized.append(
            {
                "speaker": str(speaker),
                "start": float(start),
                "end": float(end),
            }
        )
    return normalized


def format_speaker_label(raw_speaker: str, speaker_map: Dict[str, str]) -> str:
    if raw_speaker not in speaker_map:
        speaker_map[raw_speaker] = f"Speaker {len(speaker_map) + 1}"
    return speaker_map[raw_speaker]


def merge_speaker_segments(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not segments:
        return []

    merged = []
    current = dict(segments[0])

    for segment in segments[1:]:
        same_speaker = segment.get("speaker") == current.get("speaker")
        short_gap = float(segment["start"]) - float(current["end"]) <= 1.2

        if same_speaker and short_gap:
            current["text"] = f"{current['text']} {segment['text']}".strip()
            current["end"] = segment["end"]
        else:
            merged.append(current)
            current = dict(segment)

    merged.append(current)
    return merged


def enrich_speaker_segments(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    speaker_map: Dict[str, str] = {}
    enriched = []
    for segment in segments:
        raw_speaker = str(segment.get("speaker", "Unknown"))
        enriched.append(
            {
                **segment,
                "speaker": raw_speaker,
                "speaker_label": format_speaker_label(raw_speaker, speaker_map),
            }
        )
    return enriched


def build_speaker_aware_transcript(speaker_segments: List[Dict[str, Any]]) -> str:
    lines = []
    for segment in speaker_segments:
        label = segment.get("speaker_label") or segment.get("speaker", "Speaker")
        lines.append(f"{label}: {segment['text']}")
    return "\n\n".join(lines)


def build_plain_transcript(segments: List[Dict[str, Any]]) -> str:
    return " ".join(segment["text"] for segment in segments).strip()


def cleanup_torch_memory(device: str) -> None:
    if device != "cuda":
        return

    try:
        import gc
        import torch

        gc.collect()
        torch.cuda.empty_cache()
    except Exception:
        pass


def process_audio_with_whisperx(audio_path: str) -> Dict[str, Any]:
    try:
        import whisperx
    except ImportError as exc:
        raise RuntimeError(
            "WhisperX is not installed. Install dependencies from requirements.txt."
        ) from exc

    device = get_whisperx_device()
    compute_type = get_whisperx_compute_type(device)
    model_name = get_whisperx_model_name(device)
    batch_size = get_whisperx_batch_size(device)

    audio = load_audio_for_whisperx(audio_path)
    model = get_whisperx_model(model_name, device, compute_type)
    result = model.transcribe(audio, batch_size=batch_size)

    aligned_result = result
    align_error = ""
    language_code = result.get("language")
    if language_code:
        try:
            model_a, metadata = get_alignment_model(language_code, device)
            aligned_result = whisperx.align(
                result["segments"],
                model_a,
                metadata,
                audio,
                device,
                return_char_alignments=False,
            )
            if "language" not in aligned_result:
                aligned_result["language"] = language_code
        except Exception as exc:
            align_error = str(exc)

    diarization_config = get_diarization_config()
    diarization_status = "disabled"
    diarization_backend = "disabled"
    diarization_segments: List[Dict[str, Any]] = []
    diarization_error = ""
    whisperx_result = aligned_result

    if is_diarization_enabled():
        diarization_backend = diarization_config["backend"]
        if not diarization_config["enabled"]:
            diarization_status = "unconfigured"
        elif diarization_config["backend"] != "community-1":
            diarization_status = "error"
            diarization_error = (
                "WhisperX integration currently supports only community-1 diarization "
                "with a Hugging Face token."
            )
        else:
            diarization_status = "completed"
            try:
                diarize_model = get_whisperx_diarization_pipeline(
                    diarization_config["token"], device
                )
                diarize_kwargs = {
                    key: value
                    for key, value in get_speaker_constraints().items()
                    if value is not None
                }
                diarize_output = (
                    diarize_model(audio, **diarize_kwargs)
                    if diarize_kwargs
                    else diarize_model(audio)
                )
                diarization_segments = normalize_diarization_segments(diarize_output)
                whisperx_result = whisperx.assign_word_speakers(
                    diarize_output, whisperx_result
                )
            except Exception as exc:
                diarization_status = "error"
                diarization_error = str(exc)

    transcript_segments = normalize_transcript_segments(
        whisperx_result.get("segments", []) or aligned_result.get("segments", [])
    )
    transcript_text = whisperx_result.get("text") or build_plain_transcript(transcript_segments)

    speaker_segments: List[Dict[str, Any]] = []
    if diarization_status == "completed":
        speaker_ready_segments = [
            segment for segment in transcript_segments if segment.get("speaker")
        ]
        speaker_segments = enrich_speaker_segments(
            merge_speaker_segments(speaker_ready_segments)
        )

    cleanup_torch_memory(device)

    if align_error and not diarization_error:
        diarization_error = f"Alignment warning: {align_error}"
    elif align_error and diarization_error:
        diarization_error = f"{diarization_error} | Alignment warning: {align_error}"

    return {
        "transcript": transcript_text,
        "speaker_aware_transcript": build_speaker_aware_transcript(speaker_segments),
        "speaker_segments": speaker_segments,
        "diarization_segments": diarization_segments,
        "diarization_status": diarization_status,
        "diarization_backend": diarization_backend,
        "diarization_error": diarization_error,
        "transcript_segments": transcript_segments,
        "word_segments": normalize_word_entries(
            whisperx_result.get("segments", []) or aligned_result.get("segments", [])
        ),
        "transcription_engine": "whisperx",
        "transcription_model": model_name,
        "language": whisperx_result.get("language") or language_code or "",
    }
