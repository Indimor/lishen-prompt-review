#!/usr/bin/env python3
"""Validate scene review markdown files.

Checks that each card contains non-empty source text and GLM V1 prompt text.
Later V2 files can use the same headings plus `### 洄光导演修订版 V2`
and `### 修改记录`.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENE_PATTERN = re.compile(r"SC\d{2}\.md$")
CARD_PATTERN = re.compile(r"(?m)^## (SC\d{2}-C\d{2})\s*$")


@dataclass
class Finding:
    level: str
    file: str
    card_id: str
    message: str


def section_text(card_block: str, heading: str) -> str | None:
    pattern = re.compile(
        rf"(?ms)^### {re.escape(heading)}\s*\n(.*?)(?=^### |^## |^---\s*$|\Z)"
    )
    match = pattern.search(card_block)
    if not match:
        return None
    return match.group(1).strip()


def split_cards(text: str) -> list[tuple[str, str]]:
    matches = list(CARD_PATTERN.finditer(text))
    cards: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        cards.append((match.group(1), text[match.start():end]))
    return cards


def validate_scene(path: Path) -> tuple[int, list[Finding]]:
    text = path.read_text(encoding="utf-8")
    cards = split_cards(text)
    findings: list[Finding] = []

    if not cards:
        findings.append(Finding("ERROR", path.name, "-", "未找到任何卡片标题"))
        return 0, findings

    seen: set[str] = set()
    for card_id, block in cards:
        if card_id in seen:
            findings.append(Finding("ERROR", path.name, card_id, "卡号重复"))
        seen.add(card_id)

        source = section_text(block, "对应卡片原文")
        v1 = section_text(block, "视频提示词 V1")

        if source is None:
            findings.append(Finding("ERROR", path.name, card_id, "缺少‘对应卡片原文’标题"))
        elif not source:
            findings.append(Finding("ERROR", path.name, card_id, "对应卡片原文为空"))

        if v1 is None:
            findings.append(Finding("ERROR", path.name, card_id, "缺少‘视频提示词 V1’标题"))
        elif not v1:
            findings.append(Finding("ERROR", path.name, card_id, "视频提示词 V1 正文为空"))

    return len(cards), findings


def main() -> int:
    scene_files = sorted(
        path for path in ROOT.iterdir() if path.is_file() and SCENE_PATTERN.fullmatch(path.name)
    )
    all_findings: list[Finding] = []
    total_cards = 0

    if not scene_files:
        all_findings.append(Finding("ERROR", ".", "-", "仓库根目录未找到 SCxx.md"))

    for path in scene_files:
        card_count, findings = validate_scene(path)
        total_cards += card_count
        all_findings.extend(findings)

    report = {
        "scene_count": len(scene_files),
        "card_count": total_cards,
        "error_count": sum(item.level == "ERROR" for item in all_findings),
        "findings": [asdict(item) for item in all_findings],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))

    if all_findings:
        print("\nFAIL：审阅源文件不完整。", file=sys.stderr)
        return 1

    print("\nPASS：所有场次的原文与 V1 均非空。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
