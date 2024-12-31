import math
import pydub
from io import BytesIO


def get_seg_from_file_data(data):
    seg = pydub.AudioSegment.from_file(data)

    return seg


def export_seg_to_bytes(seg):
    data = BytesIO()
    seg.export(data, format="mp3")
    return data.getvalue()


def get_bytes_count_to_mb(bytes_count):
    return bytes_count / 1024 / 1024


def get_seg_credit_val(seg):
    return math.ceil(seg.duration_seconds / 60)
