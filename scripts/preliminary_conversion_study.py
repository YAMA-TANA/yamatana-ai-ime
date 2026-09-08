"""Run a practical conversion-pattern study against the packaged ONNX model."""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ranker.onnx_ranker import OnnxRuriReranker


@dataclass(frozen=True)
class Case:
    label: str
    category: str
    reading: str
    prefix: str
    suffix: str
    expected: str
    candidates: tuple[str, ...]


def case(
    label: str,
    category: str,
    reading: str,
    prefix: str,
    suffix: str,
    expected: str,
    *candidates: str,
) -> Case:
    if expected not in candidates:
        raise ValueError(f"{label}: expected candidate is missing")
    if candidates[0] == expected:
        raise ValueError(f"{label}: challenge order must not start with expected")
    return Case(label, category, reading, prefix, suffix, expected, candidates)


CASES = (
    # Numeric expressions and counters.
    case("順位・第5位", "数字・表記", "だいごい", "大会の最終順位は", "だった。", "第5位", "第魚凍", "第五位", "第5位", "醍醐井"),
    case("順位・1位", "数字・表記", "いちい", "売上ランキングで", "を獲得した。", "1位", "位置位", "一位", "1位", "一意"),
    case("人数・3人", "数字・表記", "さんにん", "会議には", "が参加した。", "3人", "月桃", "三人", "3人", "サンニン"),
    case("回数・第2回", "数字・表記", "だいにかい", "次の会議は", "です。", "第2回", "第二回", "第2回", "台にかい"),
    case("個数・12個", "数字・表記", "じゅうにこ", "部品を", "発注した。", "12個", "十二湖", "十二個", "12個"),
    case("年・2026年", "数字・表記", "にせんにじゅうろくねん", "契約は", "に更新する。", "2026年", "二千二十六年", "2026年"),
    case("割合・5%", "数字・表記", "ごぱーせんと", "売上が前年比", "増加した。", "5%", "五パーセント", "5%", "誤パーセント"),
    case("章・第5章", "数字・表記", "だいごしょう", "詳細は", "を参照する。", "第5章", "醍醐賞", "第五章", "第5章"),
    case("時刻・3時", "数字・表記", "さんじ", "会議は午後", "から始まる。", "3時", "惨事", "三時", "3時"),
    case("日付・15日", "数字・表記", "じゅうごにち", "提出期限は", "です。", "15日", "十五地", "十五日", "15日"),
    # Numeric-looking lexicalized expressions that must remain in kanji.
    case("慣用句・一石二鳥", "数字・漢字維持", "いっせきにちょう", "この方法ならまさに", "だ。", "一石二鳥", "1石2鳥", "一石二鳥", "一石二兆"),
    case("慣用句・一期一会", "数字・漢字維持", "いちごいちえ", "出会いを", "の精神で大切にする。", "一期一会", "1期1会", "一期一会", "苺一会"),
    case("図形・三角形", "数字・漢字維持", "さんかくけい", "三つの辺を持つ図形は", "である。", "三角形", "3角形", "三角形", "参画系"),
    case("感覚・五感", "数字・漢字維持", "ごかん", "視覚や聴覚などの", "を研ぎ澄ます。", "五感", "5感", "五感", "互換"),
    case("法律・第三者", "数字・漢字維持", "だいさんしゃ", "契約に関係のない", "へ開示しない。", "第三者", "第3者", "第三者", "代参者"),
    case("個別・一人一人", "数字・漢字維持", "ひとりひとり", "参加者", "に説明した。", "一人一人", "1人1人", "一人一人", "ひとりひとり"),
    case("ことわざ・百聞は一見にしかず", "数字・漢字維持", "ひゃくぶんはいっけんにしかず", "ことわざの", "を実感した。", "百聞は一見にしかず", "100聞は1見にしかず", "百聞は一見にしかず", "百聞は一件にしかず"),
    case("化学・二酸化炭素", "数字・漢字維持", "にさんかたんそ", "温室効果ガスの", "を削減する。", "二酸化炭素", "2酸化炭素", "二酸化炭素", "二参加炭素"),
    # Everyday homophones.
    case("顔の鼻", "一般同音語", "はな", "彼の顔の", "は大きい。", "鼻", "花", "鼻", "はな", "華"),
    case("庭の花", "一般同音語", "はな", "庭には美しい", "が咲いた。", "花", "鼻", "花", "はな", "華"),
    case("天気の雨", "一般同音語", "あめ", "午後から", "が降る。", "雨", "飴", "雨", "あめ"),
    case("菓子の飴", "一般同音語", "あめ", "子どもに甘い", "を渡す。", "飴", "雨", "飴", "あめ"),
    case("印刷用紙", "一般同音語", "かみ", "プリンターに", "を補充する。", "紙", "神", "髪", "紙", "上"),
    case("美容院の髪", "一般同音語", "かみ", "美容院で", "を切る。", "髪", "紙", "神", "髪", "上"),
    case("川の橋", "一般同音語", "はし", "川に新しい", "を架ける。", "橋", "端", "箸", "橋"),
    case("食事の箸", "一般同音語", "はし", "食事に使う", "を並べる。", "箸", "橋", "端", "箸"),
    case("工場の機械", "一般同音語", "きかい", "工場の大型", "を点検する。", "機械", "機会", "器械", "機械"),
    case("好機の機会", "一般同音語", "きかい", "海外進出の", "を逃さない。", "機会", "機械", "器械", "機会"),
    # Inflected verbs and adjectives.
    case("事故に遭う", "異字同訓", "あう", "交通事故に", "可能性がある。", "遭う", "会う", "合う", "遭う"),
    case("友人に会う", "異字同訓", "あう", "駅で友人に", "約束をした。", "会う", "合う", "遭う", "会う"),
    case("条件に合う", "異字同訓", "あう", "要件に", "製品を選ぶ。", "合う", "会う", "遭う", "合う"),
    case("病気を治す", "異字同訓", "なおす", "医師が病気を", "ために治療する。", "治す", "直す", "治す", "なおす"),
    case("機械を直す", "異字同訓", "なおす", "故障した機械を", "作業を始める。", "直す", "治す", "直す", "なおす"),
    case("距離を測る", "異字同訓", "はかる", "レーザーで距離を", "。", "測る", "計る", "量る", "図る", "測る"),
    case("時間を計る", "異字同訓", "はかる", "ストップウォッチで時間を", "。", "計る", "測る", "量る", "図る", "計る"),
    case("暑い夏", "異字同訓", "あつい", "今年の夏は", "日が続く。", "暑い", "熱い", "厚い", "暑い"),
    case("熱いスープ", "異字同訓", "あつい", "鍋のスープは", "ので注意する。", "熱い", "暑い", "厚い", "熱い"),
    case("厚い資料", "異字同訓", "あつい", "ページ数の多い", "資料を読む。", "厚い", "暑い", "熱い", "厚い"),
    # Practical domain vocabulary.
    case("代金決済", "実務・専門", "けっさい", "請求代金をオンラインで", "する。", "決済", "決裁", "決済", "血祭"),
    case("稟議決裁", "実務・専門", "けっさい", "部長が稟議書を", "した。", "決裁", "決済", "決裁", "血祭"),
    case("法律施行", "実務・専門", "しこう", "改正法を来月から", "する。", "施行", "思考", "試行", "指向", "施行"),
    case("実験試行", "実務・専門", "しこう", "新方式を実験環境で", "する。", "試行", "施行", "思考", "指向", "試行"),
    case("アンテナ指向", "実務・専門", "しこう", "アンテナの", "性を測定する。", "指向", "思考", "志向", "試行", "指向"),
    case("調査回答", "実務・専門", "かいとう", "アンケートに", "する。", "回答", "解凍", "怪盗", "回答"),
    case("冷凍品解凍", "実務・専門", "かいとう", "冷凍食品を", "する。", "解凍", "回答", "怪盗", "解凍"),
    case("ソフト更新", "実務・専門", "こうしん", "ソフトウェアを最新版へ", "する。", "更新", "交信", "後進", "更新"),
    case("機能実装", "実務・専門", "じっそう", "新しい検索機能を", "する。", "実装", "実相", "実装", "じっそう"),
    case("システム障害", "実務・専門", "しょうがい", "本番システムで", "が発生した。", "障害", "生涯", "渉外", "障害"),
    case("悪性腫瘍", "実務・専門", "しゅよう", "検査で悪性の", "が見つかった。", "腫瘍", "主要", "収容", "腫瘍"),
    case("ウイルス感染", "実務・専門", "かんせん", "新型ウイルスに", "した。", "感染", "幹線", "観戦", "感染"),
    # Targets containing particles or auxiliaries, plus collapsed compounds.
    case("花を・助詞込み", "助詞・分節", "はなを", "庭で美しい", "眺める。", "花を", "鼻を", "花を", "はなを"),
    case("花が・助詞込み", "助詞・分節", "はなが", "庭の桜の", "咲いた。", "花が", "鼻が", "花が", "はなが"),
    case("鼻の・助詞込み", "助詞・分節", "はなの", "彼の顔にある", "形を見る。", "鼻の", "花の", "鼻の", "はなの"),
    case("機械を・助詞込み", "助詞・分節", "きかいを", "工場で大型", "点検する。", "機械を", "機会を", "器械を", "機械を"),
    case("決済を・助詞込み", "助詞・分節", "けっさいを", "請求書のオンライン", "完了した。", "決済を", "決裁を", "決済を", "血祭を"),
    case("第5位に・助詞込み", "助詞・分節", "だいごいに", "大会では", "入賞した。", "第5位に", "第魚凍", "第五位に", "第5位に", "醍醐井"),
    case("3人で・助詞込み", "助詞・分節", "さんにんで", "担当者", "対応する。", "3人で", "三人で", "3人で", "月桃で"),
    case("施行する・補助語込み", "助詞・分節", "しこうする", "改正された制度を", "予定だ。", "施行する", "思考する", "試行する", "施行する"),
    case("非行少年・複合語", "助詞・分節", "ひこうしょうねん", "警察が", "を補導した。", "非行少年", "飛行少年", "非行少年", "飛行小年"),
    case("週刊誌・複合語", "助詞・分節", "しゅうかんし", "毎週発売される", "を読む。", "週刊誌", "週間誌", "週刊誌", "習慣誌"),
)


CONTEXT_MODES = {
    "both": lambda item: (item.prefix, item.suffix),
    "prefix_only": lambda item: (item.prefix, ""),
    "suffix_only": lambda item: ("", item.suffix),
    "short_prefix": lambda item: (item.prefix[-2:], ""),
    "no_context": lambda _item: ("", ""),
    "previous_sentence": lambda item: (
        f"昨日の会議は予定どおり終了した　{item.prefix}", item.suffix
    ),
}


def ordered_candidates(item: Case, order: str) -> list[str]:
    if order == "challenge":
        return list(item.candidates)
    return [item.expected] + [word for word in item.candidates if word != item.expected]


def aggregate(rows: Iterable[dict], key: str) -> dict[str, dict[str, int | float]]:
    totals: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for row in rows:
        group = str(row[key])
        totals[group][1] += 1
        totals[group][0] += int(row["end_to_end_correct"])
    return {
        group: {
            "correct": values[0],
            "total": values[1],
            "accuracy": round(values[0] / values[1], 4),
        }
        for group, values in sorted(totals.items())
    }


def run_study(compute_mode: str, model_path: Path | None) -> dict:
    ranker = OnnxRuriReranker(
        settings={
            "compute_mode": compute_mode,
            "context_enabled": True,
            "context_chars": 128,
            "document_domain": "general",
            "custom_instruction": "",
            "lexical_grounding": True,
        },
        model_path=model_path,
    )
    rows = []
    for item in CASES:
        for context_mode, context_factory in CONTEXT_MODES.items():
            prefix, suffix = context_factory(item)
            for order in ("challenge", "control"):
                words = ordered_candidates(item, order)
                request = {
                    "request_id": f"{item.label}:{context_mode}:{order}",
                    "preceding_text": prefix,
                    "following_text": suffix,
                    "read": item.reading,
                    "candidates": [
                        {"id": f"c{index}", "text": word, "rank": index}
                        for index, word in enumerate(words, start=1)
                    ],
                }
                response = ranker.rank(request)
                by_id = {candidate["id"]: candidate["text"] for candidate in request["candidates"]}
                ranker_top = by_id[response["candidates"][0]["id"]]

                # Mirrors AiRewriter's current single-segment sentence-start
                # gate.  Short readings never reach the ranker without document
                # context, even if they are multiword phrases such as だいごい.
                ai_called = bool(prefix or suffix) or len(item.reading) >= 6
                end_to_end_top = ranker_top if ai_called else words[0]
                rows.append(
                    {
                        "label": item.label,
                        "category": item.category,
                        "reading": item.reading,
                        "context_mode": context_mode,
                        "order": order,
                        "original_prefix": prefix,
                        "original_suffix": suffix,
                        "used_prefix": ranker.last_explanation["context"]["preceding_text"],
                        "used_suffix": ranker.last_explanation["context"]["following_text"],
                        "candidates": words,
                        "expected": item.expected,
                        "ai_called": ai_called,
                        "ranker_top": ranker_top,
                        "end_to_end_top": end_to_end_top,
                        "ranker_correct": ranker_top == item.expected,
                        "end_to_end_correct": end_to_end_top == item.expected,
                        "latency_ms": ranker.last_latency_ms,
                        "explanation": ranker.last_explanation,
                    }
                )
    correct = sum(int(row["end_to_end_correct"]) for row in rows)
    return {
        "compute_mode": compute_mode,
        "model_path": str(ranker.model_path),
        "case_count": len(CASES),
        "decision_count": len(rows),
        "correct": correct,
        "accuracy": round(correct / len(rows), 4),
        "by_category": aggregate(rows, "category"),
        "by_context_mode": aggregate(rows, "context_mode"),
        "by_order": aggregate(rows, "order"),
        "rows": rows,
    }


def markdown_report(result: dict) -> str:
    lines = [
        "# 実用変換パターン予備調査",
        "",
        f"- モデル: `{result['model_path']}`",
        f"- 基本ケース: {result['case_count']}",
        f"- 総判定: {result['decision_count']}",
        f"- エンドツーエンド正答: {result['correct']}/{result['decision_count']} ({result['accuracy']:.1%})",
        "",
        "## 文脈条件別",
        "",
        "| 条件 | 正答 | 正答率 |",
        "|---|---:|---:|",
    ]
    for name, values in result["by_context_mode"].items():
        lines.append(
            f"| {name} | {values['correct']}/{values['total']} | {values['accuracy']:.1%} |"
        )
    lines.extend(("", "## カテゴリ別", "", "| カテゴリ | 正答 | 正答率 |", "|---|---:|---:|"))
    for name, values in result["by_category"].items():
        lines.append(
            f"| {name} | {values['correct']}/{values['total']} | {values['accuracy']:.1%} |"
        )
    failures = [
        row for row in result["rows"]
        if not row["end_to_end_correct"] and row["order"] == "challenge"
    ]
    lines.extend((
        "",
        "## Challenge順での失敗",
        "",
        "| ケース | 文脈条件 | 読み | 期待 | 実結果 | AI呼出 |",
        "|---|---|---|---|---|---:|",
    ))
    for row in failures:
        lines.append(
            f"| {row['label']} | {row['context_mode']} | {row['reading']} | "
            f"{row['expected']} | {row['end_to_end_top']} | {row['ai_called']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compute-mode", choices=("cpu", "gpu"), default="cpu")
    parser.add_argument("--model", type=Path, default=None)
    parser.add_argument(
        "--output", type=Path, default=ROOT / "build" / "preliminary_conversion_study.json"
    )
    args = parser.parse_args()
    result = run_study(args.compute_mode, args.model)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    report_path = args.output.with_suffix(".md")
    report_path.write_text(markdown_report(result), encoding="utf-8")
    print(
        f"{result['correct']}/{result['decision_count']} "
        f"({result['accuracy']:.1%}) -> {report_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
