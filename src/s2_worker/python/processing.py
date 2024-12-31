from transcription_utils import process
import sys

if __name__ == "__main__":
    process(sys.argv[1], sys.argv[2], device="cpu", model="small")
