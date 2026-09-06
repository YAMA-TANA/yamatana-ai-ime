import json
from pathlib import Path

data = json.load(open("build/holdout_120_evaluation.json", encoding="utf-8"))

print("=" * 80)
print("120-QUESTION STRICT HOLDOUT BENCHMARK (AFTER ADDITIONAL TRAINING)")
print("=" * 80)

for mode_key in ["gpu", "cpu"]:
    m = data[mode_key]
    mode_label = m["mode_label"]
    print(f"\n--- MODE: {mode_label} ---")
    print(f"Mozc Simple Conversion Acc : {m['mozc_accuracy']}%")
    print(f"Teacher Model (310M) Acc   : {m['teacher_accuracy']}%")
    print(f"Student Model (70M) Acc    : {m['student_accuracy']}%")
    print(f"Agreement Rate             : {m['agreement_rate']}%")
    print(f"Avg Teacher Latency        : {m['avg_teacher_latency_ms']} ms")
    print(f"Avg Student Latency        : {m['avg_student_latency_ms']} ms")
    print("\n[Category Breakdown]")
    print(f"{'Category':<15} | {'Total':<6} | {'Mozc':<10} | {'Teacher (310M)':<16} | {'Student (70M)':<16}")
    print("-" * 75)
    for cat, stats in m["category_breakdown"].items():
        tot = stats["total"]
        mozc_str = f"{stats['mozc']}/{tot} ({stats['mozc']/tot*100:.1f}%)"
        t_str = f"{stats['teacher']}/{tot} ({stats['teacher']/tot*100:.1f}%)"
        s_str = f"{stats['student']}/{tot} ({stats['student']/tot*100:.1f}%)"
        print(f"{cat:<15} | {tot:<6} | {mozc_str:<10} | {t_str:<16} | {s_str:<16}")

# Inspect specific questions: q081 (じっそう -> 実装), and 異字同訓 verbs
print("\n" + "=" * 80)
print("KEY SAMPLES FROM HOLDOUT TEST:")
print("=" * 80)
for item in data["gpu"]["details"]:
    if item["id"] in ["q081", "q085", "q086", "q001", "q002", "q003", "q035", "q036", "q038"]:
        print(f"[{item['id']}] Category: {item['category']} | Reading: {item['reading']}")
        print(f"    Context: {item['context']}")
        print(f"    Expected: {item['expected']} | Mozc: {item['mozc_pick']} (OK={item['mozc_ok']})")
        print(f"    Teacher : {item['teacher_pick']} (OK={item['teacher_ok']})")
        print(f"    Student : {item['student_pick']} (OK={item['student_ok']})")
