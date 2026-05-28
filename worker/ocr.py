from vllm import start_vllm_server, VLLM_BASE_URL

_document_converter = None


def get_document_converter():
    global _document_converter
    if _document_converter is None:
        start_vllm_server("ibm-granite/granite-docling-258M", [
            "--served-model-name", "ibm-granite/granite-docling-258M",
            "--max-num-seqs", "512",
            "--max-num-batched-tokens", "8192",
            "--enable-chunked-prefill",
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
    converter = get_document_converter()
    print(f"Performing OCR on document: {file_path}")
    result = converter.convert(file_path)
    md_path = file_path + ".md"
    with open(md_path, "w") as f:
        f.write(result.document.export_to_markdown())
    print(f"OCR complete: {md_path}")
    return md_path
