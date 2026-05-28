from worker.vllm import start_vllm_server, VLLM_BASE_URL
import ocrmypdf
from ocrmypdf import OcrOptions
import subprocess

_document_converter = None


def get_document_converter():
    # Lazy-loads an AI-powered OCR model (Granite Docling) via a local vLLM server.
    # Only starts the server on first call; reuses it for subsequent documents.
    global _document_converter
    if _document_converter is None:
        start_vllm_server("ibm-granite/granite-docling-258M", [
            "--served-model-name", "ibm-granite/granite-docling-258M",
            "--max-num-seqs", "512",
            "--max-num-batched-tokens", "16384",
            "--enable-chunked-prefill",
            "--enable-prefix-caching",
            "--gpu-memory-utilization", "0.9",
        ])
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import VlmConvertOptions, VlmPipelineOptions
        from docling.datamodel.vlm_engine_options import ApiVlmEngineOptions, VlmEngineType
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.pipeline.vlm_pipeline import VlmPipeline

        vlm_options = VlmConvertOptions.from_preset(
            "granite_docling",
            engine_options=ApiVlmEngineOptions(
                runtime_type=VlmEngineType.API,
                url=f"{VLLM_BASE_URL}/v1/chat/completions",
                params={
                    "model": "ibm-granite/granite-docling-258M",
                    "temperature": 0.0,
                    "max_tokens": 4096,
                    "skip_special_tokens": False,
                },
                timeout=90,
                concurrency=16,
            ),
        )
        pipeline_options = VlmPipelineOptions(
            vlm_options=vlm_options, enable_remote_services=True
        )
        _document_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options, pipeline_cls=VlmPipeline
                )
            }
        )
    return _document_converter


def ocr_document(file_path):
    # Uses the AI document converter to extract text from a PDF (higher quality, slower).
    converter = get_document_converter()
    print(f"Performing OCR on document: {file_path}")
    result = converter.convert(file_path)
    txt_path = file_path + ".txt"
    with open(txt_path, "w") as f:
        f.write(result.document.export_to_text())
    print(f"OCR complete: {txt_path}")
    return txt_path


def ocr_document_ocrmypdf(file_path):
    # Uses traditional OCR (Tesseract via ocrmypdf), then extracts text with pdftotext.
    # Faster and lighter than the AI approach; skip_text avoids re-OCRing already-digital pages.
    options = OcrOptions(
        input_file=file_path,
        output_file=f'{file_path}.pdf',
        deskew=True,
        languages=['eng'],
        skip_text=True
    )
    print("Running ocr with ocrmypdf")
    ocrmypdf.ocr(options)
    print("finished ocrmypdf, converting to text")
    # use pdftotext to extract text file, return text file
    text_output_path = file_path + ".txt"
    subprocess.run(["pdftotext", options.output_file, text_output_path, "-layout"], check=True)
    print(f"OCR complete: {text_output_path}")
    return text_output_path