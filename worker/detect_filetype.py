
import magic

import mimetypes

def detect_file_type(file_path):
    """Return one of: audio_video, PDF, image, text, or other."""
    mime_type = None

    try:
        mime_type = magic.from_file(file_path, mime=True)
        mime_type = mime_type.lower() if mime_type else None
    except (OSError, magic.MagicException):
        mime_type = None

    if not mime_type:
        guessed_type, _ = mimetypes.guess_type(file_path)
        mime_type = guessed_type.lower() if guessed_type else ""

    if mime_type.startswith("audio/") or mime_type.startswith("video/"):
        return "audio_video"

    if mime_type == "application/pdf":
        return "PDF"

    if mime_type.startswith("image/"):
        return "image"

    if mime_type.startswith("text/"):
        return "text"

    return "other"