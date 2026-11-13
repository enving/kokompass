#!/usr/bin/env python3
"""Direkter Offline-Aufruf der vorhandenen Docling-Installation ohne HTTP-Server.

Keine Bildbeschreibungen, keine generativen Sprachmodelle, kein Cloud-Fallback.
OCR/Layout-Modelle können lokal benötigt werden; fehlende Modelle melden Fehler.
"""
import os
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
import argparse
from pathlib import Path


def convert(source, destination):
    from docling.document_converter import DocumentConverter, PdfFormatOption, ImageFormatOption
    from docling.datamodel.base_models import InputFormat, ConversionStatus
    from docling.datamodel.pipeline_options import PdfPipelineOptions, OcrMacOptions
    def converter(ocr):
        options = PdfPipelineOptions()
        options.enable_remote_services = False
        options.do_picture_description = False
        options.do_picture_classification = False
        options.do_ocr = ocr
        options.ocr_options = OcrMacOptions(lang=['de-DE', 'en-US'])
        return DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options), InputFormat.IMAGE: ImageFormatOption(pipeline_options=options)})
    image = source.suffix.lower() in {'.png', '.jpg', '.jpeg', '.webp'}
    result = converter(image).convert(source)
    text = result.document.export_to_markdown()
    if source.suffix.lower() == '.pdf' and len(text.strip()) < 50:
        result = converter(True).convert(source)
        text = result.document.export_to_markdown()
    if result.status != ConversionStatus.SUCCESS or not text.strip():
        raise RuntimeError('Docling-Konvertierung unvollständig oder leer')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text + '\n')
    print(f'Docling lokal: {len(text)} Zeichen; Abbildungen nicht inhaltlich ausgewertet')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    convert(args.source, args.destination)
