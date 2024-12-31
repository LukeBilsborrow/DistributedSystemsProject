import srt
import datetime
from faster_whisper import WhisperModel
import torch
from demucs.separate import main as separate
from pathlib import Path
from pydub import AudioSegment


# preprocessing
def demucs_process(
    input_path, output_path="/content/demucs", model_name="htdemucs", shifts=0
):
    input_path = Path(input_path)
    base_params = ["-o", output_path, "-n", model_name]

    if type(shifts) == int:
        base_params.append("--shifts")
        base_params.append(str(shifts))

    separate(base_params + [str(input_path)])
    output_root = (
        Path("/content")
        / "demucs"
        / model_name
        / input_path.name.split(".")[0]
        / "vocals.wav"
    )
    return str(output_root)


def shorthand_silero(audio_path, silero_opts=None):
    if silero_opts is None:
        silero_opts = {}

    silero_model, silero_utils = load_silero(onnx=silero_opts.get("onnx", False))
    (get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks) = (
        silero_utils
    )

    silerio_segments = get_silero_segments(
        audio_path, silero_model, read_audio, get_speech_timestamps
    )

    return silerio_segments


def load_silero(onnx=False):
    model, utils = torch.hub.load(
        repo_or_dir="snakers4/silero-vad",
        model="silero_vad",
        force_reload=True,
        onnx=onnx,
    )

    return model, utils


def get_silero_segments(
    audio_path,
    model,
    read_audio,
    get_speech_timestamps,
    sampling_rate=16000,
    return_seconds=True,
    threshold=0.82,
):
    wav = read_audio(audio_path, sampling_rate=sampling_rate)
    # get speech timestamps from full audio file
    speech_timestamps = get_speech_timestamps(
        wav,
        model,
        sampling_rate=sampling_rate,
        return_seconds=return_seconds,
        threshold=threshold,
    )
    return list(speech_timestamps)


# whisper
def process_faster_whisper(
    audio_path,
    device=None,
    compute_type="int8",
    cpu_threads=8,
    task="translate",
    model="medium",
    model_opts=None,
):

    if model_opts is None:
        model_opts = {}
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    model = WhisperModel(
        model, device=device, compute_type=compute_type, cpu_threads=cpu_threads
    )
    segments, info = model.transcribe(
        audio_path, beam_size=model_opts.get("beam_size", 5), task=task
    )

    return list(segments)


# utils
def extract_audio(file_path, output_audio_path):
    audio = AudioSegment.from_file(file_path)
    audio.export(output_audio_path, format="wav")

    return output_audio_path


def get_confirmed_segments(silerio_segments, whisper_segments):
    whisper_segment_idx = 0
    silerio_segment_idx = 0
    # we want to crop all the whisper segments so that they are within the silerio segments
    # both lists are sorted by start_time and and are non-overlapping
    # but it is possible that a whisper segment appears between two silerio segments in which case it should be removed
    # each segment has a start_time and end_time

    new_segments = []

    while silerio_segment_idx < len(silerio_segments) and whisper_segment_idx < len(
        whisper_segments
    ):
        silerio_segment = silerio_segments[silerio_segment_idx]
        whisper_segment = whisper_segments[whisper_segment_idx]

        if whisper_segment["end"] > silerio_segment["start"]:
            # these segments may overlap
            if whisper_segment["start"] < silerio_segment["end"]:
                # the whisper segment is within the silerio segment
                new_time = {
                    "start": max(whisper_segment["start"], silerio_segment["start"]),
                    "end": min(whisper_segment["end"], silerio_segment["end"]),
                    "content": whisper_segment["content"],
                }
                new_segments.append(new_time)
                whisper_segment_idx += 1

            else:
                # the whisper segment is after the silerio segment
                silerio_segment_idx += 1

        else:
            # the whisper segment is before the silerio segment
            whisper_segment_idx += 1

    return new_segments


# neutral segment has a start and end, and a content
def whisper_segment_to_neutral(segment):
    return {
        "start": segment.start,
        "end": segment.end,
        "content": segment.text,
    }


def segments_to_srt(segments, output_path):
    new_segments = []
    for count, segment in enumerate(segments):
        new_item = srt.Subtitle(
            index=count,
            start=datetime.timedelta(seconds=segment["start"]),
            end=datetime.timedelta(seconds=segment["end"]),
            content=segment["content"],
        )
        new_segments.append(new_item)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(srt.compose(new_segments))


def process(
    input_path,
    output_path,
    device="cuda",
    model="large-v2",
    use_demucs=True,
    use_vad=True,
):
    target_path = input_path + ".wav"
    extract_audio(input_path, target_path)

    if use_demucs:
        target_path = demucs_process(input_path=target_path)

    whisper_segments = process_faster_whisper(target_path, device=device, model=model)

    if use_vad:
        silero_segments = shorthand_silero(target_path)

    whisper_segments = [
        whisper_segment_to_neutral(segment) for segment in whisper_segments
    ]

    if use_vad:
        whisper_segments = get_confirmed_segments(silero_segments, whisper_segments)

    segments_to_srt(whisper_segments, output_path)
