"""Digi-API 실제 응답 형식 점검용 (Actions 로그에 출력)"""
import json

import requests

S = requests.Session()
S.headers.update({"User-Agent": "Mozilla/5.0"})
BASE = "https://digi-api.com/api/v1"


def get(path):
    return S.get(f"{BASE}/{path}", timeout=30).json()


def names(path, key="name"):
    data = get(path)
    items = data.get("content", {})
    if isinstance(items, dict):
        items = items.get("fields", [])
    return [i.get(key) for i in items]


print("=== LEVELS ===")
print(json.dumps(names("level?pageSize=100"), ensure_ascii=False))
print("=== TYPES ===")
print(json.dumps(names("type?pageSize=500"), ensure_ascii=False))
print("=== ATTRIBUTES ===")
print(json.dumps(names("attribute?pageSize=50"), ensure_ascii=False))

for n in ["Omegamon", "Paildramon", "Greymon", "Agumon", "Koromon", "Imperialdramon(Paladin Mode)"]:
    d = get(f"digimon/{n}")
    print(f"=== {n} ===")
    print("levels:", [x["level"] for x in d.get("levels", [])], "types:", [x["type"] for x in d.get("types", [])])
    for side in ["priorEvolutions", "nextEvolutions"]:
        evs = d.get(side, [])
        print(f"  {side} ({len(evs)}):")
        for e in evs[:25]:
            print(f"    {e.get('id')} | {e.get('digimon')} | {e.get('condition')!r}")
