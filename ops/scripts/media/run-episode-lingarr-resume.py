#!/usr/bin/env python3
import json
import re
import sys
import time
import shutil
from pathlib import Path
from urllib import request

API = 'http://127.0.0.1:9876/api/translate/content'
SEASON_DIR = Path.home() / 'Media/Series/King the Land/Season 1'
SEC_DIR = Path.home() / 'arr/security'
BATCH_SIZE = 20


def log(msg):
    print(msg, flush=True)


def parse_srt(path: Path):
    txt = path.read_text(encoding='utf-8', errors='ignore').replace('\r\n', '\n')
    blocks = []
    for b in re.split(r'\n\s*\n', txt.strip()):
        lines = b.split('\n')
        if len(lines) >= 3 and lines[0].strip().isdigit() and '-->' in lines[1]:
            blocks.append({
                'idx': int(lines[0].strip()),
                'ts': lines[1].strip(),
                'text': '\n'.join(lines[2:]).strip(),
            })
    return blocks


def is_bad(src: str, tr: str) -> bool:
    s = (src or '').strip()
    t = (tr or '').strip()
    if not t:
        return True
    if 'Subtitle translation by' in s:
        return True
    if len(s) < 45 and len(t) > 180:
        return True
    if len(t) > max(320, 5 * max(1, len(s))):
        return True
    if t.count('"') >= 6 and len(t) > 140:
        return True
    return False


def call_lingarr(lines_payload, timeout=140):
    payload = {
        'arrMediaId': 1,
        'title': 'King the Land',
        'sourceLanguage': 'en',
        'targetLanguage': 'pt-BR',
        'mediaType': 'Episode',
        'lines': lines_payload,
    }
    body = json.dumps(payload).encode('utf-8')
    req = request.Request(API, data=body, headers={'Content-Type': 'application/json'})
    with request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8', errors='ignore'))


def translate_single_line(src: str):
    arr = call_lingarr([{'position': 0, 'line': src}], timeout=45)
    if isinstance(arr, list) and arr and isinstance(arr[0], dict):
        return str(arr[0].get('line', '')).strip()
    return ''


def write_srt(path: Path, blocks, texts, upto=None):
    n = len(blocks) if upto is None else upto
    parts = []
    for i in range(n):
        b = blocks[i]
        txt = texts[i] if texts[i] is not None else b['text']
        parts.append(f"{b['idx']}\n{b['ts']}\n{txt}\n")
    path.write_text('\n'.join(parts), encoding='utf-8')


def main():
    if len(sys.argv) < 2:
        raise SystemExit('usage: run-episode-lingarr-resume.py S01E06')

    token = sys.argv[1].strip().upper()
    if not re.match(r'^S\d{2}E\d{2}$', token):
        raise SystemExit('episode token must be SxxExx')

    en_candidates = sorted(SEASON_DIR.glob(f'*{token}*.en.srt'))
    if not en_candidates:
        raise SystemExit(f'no EN srt found for {token}')

    en = en_candidates[0]
    pt = Path(str(en).replace('.en.srt', '.pt-BR.srt'))
    partial = Path(str(pt).replace('.pt-BR.srt', '.pt-BR.partial.srt'))
    ckpt = SEC_DIR / f'lingarr-{token}.checkpoint.json'
    SEC_DIR.mkdir(parents=True, exist_ok=True)

    en_blocks = parse_srt(en)
    total = len(en_blocks)
    if total == 0:
        raise SystemExit('EN srt parsed as empty')

    texts = [None] * total
    done = 0
    batch_errors = 0
    single_retry = 0
    fallback = 0

    # load prior partial state if any
    if partial.exists():
        p_blocks = parse_srt(partial)
        if p_blocks:
            by_idx = {b['idx']: b['text'] for b in p_blocks}
            for i, b in enumerate(en_blocks):
                if b['idx'] in by_idx:
                    texts[i] = by_idx[b['idx']]
                else:
                    break
            while done < total and texts[done] is not None:
                done += 1

    if ckpt.exists():
        try:
            c = json.loads(ckpt.read_text(encoding='utf-8'))
            done = max(done, int(c.get('done', done)))
            batch_errors = int(c.get('batch_errors', 0))
            single_retry = int(c.get('single_retry', 0))
            fallback = int(c.get('fallback', 0))
        except Exception:
            pass

    if pt.exists() and done == 0:
        ts = time.strftime('%Y%m%d-%H%M%S')
        bkp = Path(str(pt).replace('.srt', f'.pre-resume-{ts}.srt'))
        shutil.copy2(pt, bkp)
        log(f'BACKUP={bkp.name}')
    elif not pt.exists():
        log('BACKUP=none (new pt-BR file will be created)')

    log(f'RESUME_FROM={done}/{total}')

    i = done
    while i < total:
        end = min(i + BATCH_SIZE, total)
        batch = en_blocks[i:end]
        payload = [{'position': j, 'line': b['text']} for j, b in enumerate(batch)]

        result = None
        for attempt in (1, 2, 3):
            try:
                result = call_lingarr(payload, timeout=160)
                break
            except Exception:
                if attempt < 3:
                    time.sleep(1.5 * attempt)
                else:
                    batch_errors += 1

        rmap = {}
        if isinstance(result, list):
            for item in result:
                if isinstance(item, dict) and 'position' in item and 'line' in item:
                    try:
                        rmap[int(item['position'])] = str(item['line'])
                    except Exception:
                        pass

        for j, b in enumerate(batch):
            src = b['text']
            tr = (rmap.get(j) or '').strip()

            if is_bad(src, tr):
                try:
                    cand = translate_single_line(src)
                    if not is_bad(src, cand):
                        tr = cand
                        single_retry += 1
                    else:
                        tr = src
                        fallback += 1
                except Exception:
                    tr = src
                    fallback += 1

            texts[i + j] = tr

        i = end
        write_srt(partial, en_blocks, texts, upto=i)
        ckpt.write_text(json.dumps({
            'episode': token,
            'done': i,
            'total': total,
            'batch_errors': batch_errors,
            'single_retry': single_retry,
            'fallback': fallback,
            'updated_at': int(time.time())
        }, ensure_ascii=False, indent=2), encoding='utf-8')

        log(f'PROGRESS {i}/{total} batch_errors={batch_errors} single_retry={single_retry} fallback={fallback}')

    write_srt(pt, en_blocks, texts, upto=None)
    ckpt.write_text(json.dumps({
        'episode': token,
        'done': total,
        'total': total,
        'batch_errors': batch_errors,
        'single_retry': single_retry,
        'fallback': fallback,
        'updated_at': int(time.time()),
        'status': 'done'
    }, ensure_ascii=False, indent=2), encoding='utf-8')

    log(f'DONE file={pt.name} total={total} batch_errors={batch_errors} single_retry={single_retry} fallback={fallback}')


if __name__ == '__main__':
    main()
