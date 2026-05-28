_whisperx_model = None


def get_whisperx_model():
    global _whisperx_model
    if _whisperx_model is None:
        import whisperx
        _whisperx_model = whisperx.load_model(
            "medium", "cuda", compute_type="float16"
        )
    return _whisperx_model


def transcribe_audio(file_path):
    model = get_whisperx_model()
    print(f"Transcribing audio file: {file_path}")
    # You can remove the task parameter here to prevent translation to english
    result = model.transcribe(file_path, batch_size=8, task="translate")
    result_text = ("\n".join(seg["text"] for seg in result["segments"]))
    txt_path = file_path + ".txt"
    with open(txt_path, "w") as f:
        f.write(result_text)
    print(f"Transcription complete: {txt_path}")
    return txt_path
