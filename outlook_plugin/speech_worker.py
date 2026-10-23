"""Isolated, local-only ASR/diarization worker. No application secrets are needed."""
import hashlib
import json
import os
from pathlib import Path
import ssl
import sys
import tarfile
import urllib.request

SEG_URL = 'https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-segmentation-models/sherpa-onnx-pyannote-segmentation-3-0.tar.bz2'
EMB_URL = 'https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/wespeaker_en_voxceleb_resnet34.onnx'
SEG_SHA = '24615ee884c897d9d2ba09bb4d30da6bb1b15e685065962db5b02e76e4996488'
EMB_SHA = '5ef208a9da1453335308a6b6f4e6dfbd7e183a38b604de0a57664f45d257fe94'
MODEL_REVISION = '536b0662742c02347bc0e980a01041f333bce120'


def atomic(path, data):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False)); temp.chmod(0o600); temp.replace(path)


def download(url, target, checksum):
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == checksum:
        return
    import certifi
    temporary = target.with_suffix('.download')
    digest = hashlib.sha256()
    with urllib.request.urlopen(url, timeout=60, context=ssl.create_default_context(cafile=certifi.where())) as response, temporary.open('wb') as output:
        total = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk: break
            total += len(chunk)
            if total > 100_000_000: raise ValueError('Speech model download exceeded its expected size.')
            digest.update(chunk); output.write(chunk)
    if digest.hexdigest() != checksum:
        temporary.unlink(missing_ok=True)
        raise ValueError('Speech model verification failed. Retry the download.')
    temporary.replace(target)


def assign_speakers(words, turns):
    """Match each timed word by overlap; do not guess across silence or overlapping voices."""
    rows = []; cursor = 0
    for word in words:
        start, end = float(word['start']), float(word['end'])
        while cursor < len(turns) and turns[cursor]['end'] <= start: cursor += 1
        scores = {}
        for index in range(cursor,len(turns)):
            turn=turns[index]
            if turn['start'] >= end: break
            overlap = max(0, min(end, turn['end']) - max(start, turn['start']))
            scores[turn['speaker']] = scores.get(turn['speaker'], 0) + overlap
        ranked = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
        speaker = ranked[0][0] if ranked and ranked[0][1] >= (end-start)*0.4 else 'Unknown speaker'
        if len(ranked) > 1 and ranked[1][1] >= ranked[0][1]*0.6: speaker = 'Overlapping speakers'
        if rows and rows[-1]['speaker'] == speaker and start-rows[-1]['end'] < 1.5 and len(rows[-1]['text']) < 600:
            rows[-1]['text'] += word['text']; rows[-1]['end'] = end
        else: rows.append({'start': start, 'end': end, 'speaker': speaker, 'text': word['text']})
    for row in rows: row['text'] = row['text'].strip()
    return [row for row in rows if row['text']]


def run(source, cache, output, progress):
    import numpy as np
    import av
    from faster_whisper import WhisperModel
    from huggingface_hub import snapshot_download
    import sherpa_onnx
    cache.mkdir(parents=True, exist_ok=True)
    def stage(message, percent=0): atomic(progress, {'message':message, 'percent':percent})
    stage('Preparing local speech models…')
    download(SEG_URL, cache/'segmentation.tar.bz2', SEG_SHA)
    download(EMB_URL, cache/'embedding.onnx', EMB_SHA)
    segmentation = cache/'segmentation.onnx'
    if not segmentation.exists():
        with tarfile.open(cache/'segmentation.tar.bz2') as archive:
            member = next(m for m in archive.getmembers() if m.name == 'sherpa-onnx-pyannote-segmentation-3-0/model.onnx' and m.isfile())
            with archive.extractfile(member) as src: segmentation.write_bytes(src.read())
    model_path = snapshot_download('Systran/faster-whisper-small', revision=MODEL_REVISION, cache_dir=str(cache/'whisper'), allow_patterns=['config.json','model.bin','tokenizer.json','vocabulary.*'], token=False)
    stage('Reading audio…')
    # Decode in bounded chunks. PyAV handles the recorded M4A/MP4 without ffmpeg installation.
    parts = []; count = 0
    with av.open(str(source)) as container:
        if not container.streams.audio: raise ValueError('This recording has no audio track.')
        resampler = av.AudioResampler(format='flt', layout='mono', rate=16000)
        for frame in container.decode(audio=0):
            for converted in resampler.resample(frame):
                part = converted.to_ndarray().reshape(-1); count += len(part)
                if count > 16000*10800: raise ValueError('Transcription supports recordings up to three hours. Split this file into shorter recordings.')
                parts.append(part)
        for converted in resampler.resample(None): parts.append(converted.to_ndarray().reshape(-1))
    if not parts: raise ValueError('No audio was found in this recording.')
    audio = np.concatenate(parts); del parts
    stage('Separating speakers…')
    config = sherpa_onnx.OfflineSpeakerDiarizationConfig(
        segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(model=str(segmentation)), num_threads=2),
        embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(cache/'embedding.onnx'), num_threads=2),
        clustering=sherpa_onnx.FastClusteringConfig(num_clusters=-1, threshold=0.5), min_duration_on=0.3, min_duration_off=0.5)
    if not config.validate(): raise ValueError('Local speaker models could not be loaded.')
    diarizer = sherpa_onnx.OfflineSpeakerDiarization(config)
    def callback(done, total):
        if done % 10 == 0: stage('Separating speakers…', round(35*done/max(1,total)))
        return 0
    turns = [{'start':float(t.start),'end':float(t.end),'speaker':str(t.speaker)} for t in diarizer.process(audio, callback=callback).sort_by_start_time()]
    names = {}; ordered = []
    for turn in turns:
        if turn['speaker'] not in names: names[turn['speaker']] = 'Speaker '+str(len(names)+1)
        ordered.append(dict(turn, speaker=names[turn['speaker']]))
    del diarizer
    stage('Transcribing…', 35)
    model = WhisperModel(model_path, device='cpu', compute_type='int8', cpu_threads=2, num_workers=1)
    segments, info = model.transcribe(audio, beam_size=5, word_timestamps=True, vad_filter=True, condition_on_previous_text=False)
    words = []
    for segment in segments:
        for word in segment.words or []: words.append({'start':word.start,'end':word.end,'text':word.word})
        stage('Transcribing…', min(95,35+round(60*segment.end/max(1,len(audio)/16000))))
    rows = assign_speakers(words, ordered)
    atomic(output, {'segments':rows,'language':info.language,'duration':len(audio)/16000,'engine':'faster-whisper small / sherpa-onnx','speaker_names':{}})
    stage('Transcript saved',100)


if __name__ == '__main__':
    import threading,time
    parent=os.getppid()
    def watch_parent():
        while True:
            time.sleep(2)
            if os.getppid()!=parent:os._exit(2)
    threading.Thread(target=watch_parent,daemon=True).start()
    try:os.nice(10)
    except OSError:pass
    try: run(*[Path(arg) for arg in sys.argv[1:5]])
    except Exception as exc:
        atomic(Path(sys.argv[4]), {'message':'Transcription failed: '+str(exc)[:500], 'error':True})
        sys.exit(1)
