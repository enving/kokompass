#!/usr/bin/env python3
"""Offline-Dateitranskription mit Kodiktat (Deutsch/Englisch auf CPU).

Aufruf mit kodiktat/.venv/bin/python. Keine Downloads und keine Cloud-Fallbacks.
Zeitmarken sind Grenzen tatsächlich dekodierter Audioblöcke, keine Wortzeiten.
"""
from konfiguration import felder, pfad
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import wave


def model_metadata(language="auto"):
    configured = felder().get('stt_api_pfad')
    if not configured:
        raise ValueError('stt_api_pfad in kontextquellen.md fehlt')
    scripts = pfad(configured)
    sys.path.insert(0, str(scripts))
    from kodiktat_api import metadata
    return metadata(language)


def transcribe(source, output, language="auto"):
    import numpy as np
    info = model_metadata(language)
    from kodiktat_api import recognizer
    rec = recognizer(num_threads=2, language=language)
    with tempfile.TemporaryDirectory(prefix='wiki-audio-') as temporary:
        wav = Path(temporary) / 'audio.wav'
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', str(source), '-vn', '-ar', '16000', '-ac', '1', '-c:a', 'pcm_s16le', str(wav)], check=True, timeout=600, capture_output=True)
        segments = []
        with wave.open(str(wav), 'rb') as audio:
            total, rate = audio.getnframes(), audio.getframerate()
            if total <= 0:
                raise ValueError('Audio enthält keine dekodierbaren Samples')
            start = 0
            while start < total:
                samples = np.frombuffer(audio.readframes(rate * 30), dtype=np.int16)
                if not len(samples):
                    raise RuntimeError('Audiodekodierung endet vorzeitig')
                text = rec.transcribe(samples)
                end = start + len(samples)
                segments.append({'start': start / rate, 'end': end / rate, 'text': text,
                                 'pruefen': not bool(text.strip())})
                start = end
        result = {**info,
                  'offline': True, 'duration': total / rate, 'decoded_until': start / rate,
                  'timestamp_kind': 'audio_block_boundaries', 'segments': segments,
                  'text': ' '.join(s['text'] for s in segments),
                  'quality': 'Spracherkennung ungeprüft; Blockgrenzen können Wörter teilen. Leere Blöcke prüfen.'}
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps({'dauer': result['duration'], 'dekodiert_bis': result['decoded_until'],
                          'woerter': len(result['text'].split()), 'leere_bloecke': sum(s['pruefen'] for s in segments)}, ensure_ascii=False))
        return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, nargs='?')
    parser.add_argument('output', type=Path, nargs='?')
    parser.add_argument('--sprache', choices=('auto', 'de', 'en'), default='auto')
    parser.add_argument('--modellinfo', action='store_true')
    args = parser.parse_args()
    if args.modellinfo:
        print(json.dumps(model_metadata(args.sprache)))
    elif args.source is None or args.output is None:
        parser.error('source und output erforderlich')
    else:
        transcribe(args.source, args.output, args.sprache)
