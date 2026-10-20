"""JSON 읽기·쓰기 도우미 (scraper 스크립트 공용)

write_json: 같은 폴더의 임시 파일에 다 쓴 뒤 os.replace 로 바꿔치기 → 쓰다가 끊겨도 기존 파일이 깨지지 않음
"""
import json
import os
import tempfile


def load_json(path, default):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def write_json(path, data, **dump_kw):
    """원자적 저장. dump_kw 는 json.dump 옵션 (ensure_ascii=False 기본)"""
    dump_kw.setdefault("ensure_ascii", False)
    d = os.path.dirname(path) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", suffix=".json", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, **dump_kw)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def write_text(path, text):
    """원자적 텍스트 저장 (보고서 등)"""
    d = os.path.dirname(path) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", suffix=".txt", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise
