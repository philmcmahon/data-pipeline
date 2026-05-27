import os

SUPPORTED_DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".odt",
    ".rtf",
    ".txt",
    ".md",
}

SUPPORTED_AUDIO_VIDEO_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".m4a",
    ".aac",
    ".flac",
    ".ogg",
    ".wma",
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".webm",
    ".m4v",
}

SUPPORTED_EXTENSIONS = SUPPORTED_DOCUMENT_EXTENSIONS | SUPPORTED_AUDIO_VIDEO_EXTENSIONS

# Check file extension so that any files we aren't interested in are discarded
def is_supported_key(key):
    if key.endswith("/"):
        return False

    extension = os.path.splitext(key)[1].lower()
    return extension in SUPPORTED_EXTENSIONS