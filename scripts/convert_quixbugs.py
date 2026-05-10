#!/usr/bin/env python3
"""Convert QuixBugs Python programs to bugtest tasks_v2 format.

Usage:
    python scripts/convert_quixbugs.py --task bitcount
    python scripts/convert_quixbugs.py --all
    python scripts/convert_quixbugs.py --list
    python scripts/convert_quixbugs.py --task bitcount --dry
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "evaluation" / "quixbugs_raw"
TASKS_DIR = REPO_ROOT / "evaluation" / "tasks_v2"

SKIP = {
    "node",
    "breadth_first_search",
    "depth_first_search",
    "detect_cycle",
    "minimum_spanning_tree",
    "reverse_linked_list",
    "shortest_path_length",
    "shortest_path_lengths",
    "shortest_paths",
    "topological_ordering",
}


# Per-algorithm curated metadata. Keys MUST match python_programs/*.py stems.
# difficulty: easy | medium | hard (test-generation güçlüğüne göre — algoritma değil)
# bug_type: kategorize edilmiş defect sınıfı (post-hoc stratifikasyon için)
# bug_description: bug'ı tarif eder, fix'i sızdırmaz; LLM'e prompt'ta gider
# test_hint: test üretimi için somut bir input önerisi; LLM'e prompt'ta gider
# expected_failure_signal: testin buggy üzerinde nasıl fail edeceğinin imzası; rapor + sanity için
TASK_CATALOG: dict[str, dict[str, str]] = {
    "bitcount": {
        "difficulty": "easy",
        "bug_type": "bitwise_operator",
        "bug_description": "Buggy versiyonda `n` her iterasyonda XOR ile güncelleniyor; bu, en düşük 1-biti temizlemiyor ve sonsuz döngüye yol açıyor.",
        "test_hint": "bitcount(127) gibi birden fazla 1-bit içeren bir girdi kullan; doğru sayıyı assert et.",
        "expected_failure_signal": "Test ya timeout olur (>5s) ya da yanlış sayı döner.",
    },
    "bucketsort": {
        "difficulty": "medium",
        "bug_type": "wrong_variable_reference",
        "bug_description": "İçteki döngü `arr` üzerinde iteration yapıyor ama doğrusu sayım dizisi (`counts`) üzerinde olmalı; bu yüzden çıktı yanlış sıralı/eksik elemanlı oluyor.",
        "test_hint": "Tekrar eden değerler içeren küçük bir liste (örn. [3, 1, 2, 1]) ve yeterince büyük bucket sayısı (k=4) ile çağır; sonucun sıralı eşit listeye eşit olduğunu assert et.",
        "expected_failure_signal": "Çıktı sıralı liste değil veya eleman sayısı/değeri girdiyle uyuşmuyor.",
    },
    "find_first_in_sorted": {
        "difficulty": "easy",
        "bug_type": "loop_boundary",
        "bug_description": "Binary search döngü koşulu `lo <= hi`; bu bazı eşit-değer durumlarda sonsuz döngüye yol açıyor (`mid` değişmediğinde).",
        "test_hint": "Tekrar eden hedef değerler içeren sıralı bir dizide ilk konumu ara (örn. [3, 4, 5, 5, 5, 6], hedef 5 → 2).",
        "expected_failure_signal": "Test timeout olur veya yanlış index döner.",
    },
    "find_in_sorted": {
        "difficulty": "easy",
        "bug_type": "off_by_one_recursion",
        "bug_description": "Yukarı yarıya recurse ederken `mid` ile başlanıyor; doğrusu `mid + 1`. Bu, hedef yukarı yarıdayken sonsuz recursion'a yol açıyor.",
        "test_hint": "find_in_sorted([3, 4, 5, 6, 7], 7) gibi hedefin son eleman olduğu bir aramayı dene.",
        "expected_failure_signal": "Test timeout olur veya RecursionError üretir.",
    },
    "flatten": {
        "difficulty": "easy",
        "bug_type": "yield_wrong_value",
        "bug_description": "Non-list dalında `yield flatten(x)` (generator yield ediyor) yapılmış; doğrusu `yield x`. Sonuç bir liste yerine generator nesneleri içerir.",
        "test_hint": "İç içe basit liste (örn. [1, [2, 3], [[4]]]) ile çağırıp `list(flatten(...))` çıktısını [1, 2, 3, 4]'e eşit assert et.",
        "expected_failure_signal": "Çıktı listesi içinde generator object'leri (skaler değil) bulunur.",
    },
    "gcd": {
        "difficulty": "easy",
        "bug_type": "argument_order",
        "bug_description": "Recursive çağrıda argümanlar `(a % b, b)` sırasında; doğrusu `(b, a % b)`. `a % b < b` olduğundan yeniden aynı argümanla çağrılır → sonsuz recursion.",
        "test_hint": "gcd(35, 21) gibi bir çağrıda timeout/recursion error gözle ya da sonucu 7'ye eşit assert et.",
        "expected_failure_signal": "Test RecursionError veya timeout üretir.",
    },
    "get_factors": {
        "difficulty": "medium",
        "bug_type": "wrong_base_case",
        "bug_description": "Asal sayı için boş liste `[]` dönülüyor; doğrusu `[n]`. Sonuçta asal girdiler eksik dönüyor.",
        "test_hint": "Asal bir sayı (örn. get_factors(7)) için sonucun [7] olduğunu assert et.",
        "expected_failure_signal": "Asal girdi için fonksiyon [] döner.",
    },
    "hanoi": {
        "difficulty": "medium",
        "bug_type": "wrong_target_variable",
        "bug_description": "Tek-disk durumunda adım `(start, helper)` olarak append ediliyor; doğrusu `(start, end)`. Üretilen hareketler problem semantiğine uymuyor.",
        "test_hint": "hanoi(2, start=1, end=3) çıktısının tam olarak [(1,2),(1,3),(2,3)] olduğunu assert et.",
        "expected_failure_signal": "Hareket listesi yanlış hedeflere işaret eder; doğrudan eşitlik kontrolü fail eder.",
    },
    "is_valid_parenthesization": {
        "difficulty": "medium",
        "bug_type": "missing_final_check",
        "bug_description": "Fonksiyon karakterleri tarayınca `True` dönüyor; ama açık kalan parantezi kontrol etmiyor. Doğrusu sonda `depth == 0` kontrolü.",
        "test_hint": "is_valid_parenthesization('((') gibi açık fazlası girdi için False beklenir.",
        "expected_failure_signal": "Açık parantez fazla olan girdi için True döner.",
    },
    "kheapsort": {
        "difficulty": "medium",
        "bug_type": "wrong_slice_start",
        "bug_description": "Heap'e eklendikten sonra döngü tüm `arr` üzerinde değil, `arr[k:]` üzerinde yapılmalı; aksi halde ilk k eleman iki kere işleniyor.",
        "test_hint": "Küçük bir liste (örn. [3, 2, 1, 5, 4], k=2) ile çağır; sonuç sıralı listeye eşit olmalı.",
        "expected_failure_signal": "Çıktı eleman sayısı girdiyi aşıyor veya sıralama hatalı.",
    },
    "knapsack": {
        "difficulty": "hard",
        "bug_type": "off_by_one_comparison",
        "bug_description": "Ağırlık karşılaştırması `weight < j`; doğrusu `weight <= j`. Bu yüzden tam kapasiteyi dolduran item'lar değerlendirmeye dahil edilmiyor.",
        "test_hint": "Tam kapasite eşleşmesi gerektiren bir durum üret (örn. capacity=3, items=[(3, 10), (1, 5)]) ve optimum değeri assert et.",
        "expected_failure_signal": "Tam kapasiteyi dolduran item'lar paketlenmediğinden değer eksik döner.",
    },
    "kth": {
        "difficulty": "hard",
        "bug_type": "missing_decrement",
        "bug_description": "Üst yarıya recurse ederken `k` aynen geçiyor; doğrusu `k - num_lessoreq`. Bu yüzden indeks anlamı bozulup yanlış eleman dönüyor.",
        "test_hint": "kth([3, 1, 2, 5, 4], 3) çağrısında doğru k-th order statistic'in (örn. 4) döndüğünü assert et.",
        "expected_failure_signal": "Yanlış order statistic döner (özellikle k pivot'tan büyükken).",
    },
    "lcs_length": {
        "difficulty": "hard",
        "bug_type": "dp_index_error",
        "bug_description": "Match durumunda DP güncellemesi `dp[i-1, j] + 1` yerine `dp[i-1, j-1] + 1` olmalı; aksi halde aynı j sütununu zincirler ve LCS uzunluğunu şişirir.",
        "test_hint": "lcs_length('ABCBDAB', 'BDCAB') gibi bir çiftte bilinen sonucu (4) assert et.",
        "expected_failure_signal": "Gerçek LCS uzunluğundan farklı (genellikle daha büyük) bir değer döner.",
    },
    "levenshtein": {
        "difficulty": "hard",
        "bug_type": "extra_increment",
        "bug_description": "İlk karakterler eşitken sonuca `1 +` ekleniyor; eşit karakter mesafeyi artırmamalı. Doğrusu sadece `levenshtein(source[1:], target[1:])`.",
        "test_hint": "İlk karakterleri eşit iki kelime için sonuç (örn. levenshtein('abc', 'abd') == 1) assert et.",
        "expected_failure_signal": "Beklenen düzenleme mesafesinden büyük değer döner.",
    },
    "lis": {
        "difficulty": "hard",
        "bug_type": "missing_max",
        "bug_description": "Uzunluk güncellemesi `longest = length + 1`; doğrusu `longest = max(longest, length + 1)`. Aksi hâlde ulaşılan en uzun yerine en son zincir tutulur.",
        "test_hint": "lis([4, 1, 5, 2, 3]) gibi bir girdide doğru LIS uzunluğunu (3) assert et.",
        "expected_failure_signal": "LIS uzunluğu olası değerin altında döner.",
    },
    "longest_common_subsequence": {
        "difficulty": "hard",
        "bug_type": "missing_recursion_advance",
        "bug_description": "Eşleşme dalında `b` aynı kalıyor (`a[1:], b`); doğrusu `b[1:]` ile ilerlemeli. Eşleşmeden sonra aynı `b` karakterini tekrar tüketebilir.",
        "test_hint": "longest_common_subsequence('AGCAT', 'GAC') gibi bir girdi için sonucun olası bir LCS olduğunu kontrol et.",
        "expected_failure_signal": "LCS'in uzunluğu beklenenden büyük veya tekrar eden karakterli yanlış altdizi döner.",
    },
    "max_sublist_sum": {
        "difficulty": "easy",
        "bug_type": "missing_zero_floor",
        "bug_description": "Kadane güncellemesi `max_ending_here + x`; doğrusu `max(0, max_ending_here + x)`. Negatif birikim sıfırlanmadığı için sonuç bozulur.",
        "test_hint": "Negatif değer içeren bir liste için (örn. [4, -5, 2, 1, -1, 3]) doğru max-subarray toplamını (5) assert et.",
        "expected_failure_signal": "Kümülatif negatif düşüşü taşıdığı için sonuç gerçekten alınabilecek max'tan küçük.",
    },
    "mergesort": {
        "difficulty": "medium",
        "bug_type": "wrong_base_case",
        "bug_description": "Recursion taban koşulu `len(arr) == 0`; doğrusu `len(arr) <= 1`. Tek elemanlı listeler split edilmeye çalışıldığı için sonsuz recursion oluşur.",
        "test_hint": "Tek elemanlı bir listeyle (mergesort([1])) ya da küçük listeyle çağırıp recursion error/timeout gözle.",
        "expected_failure_signal": "RecursionError veya timeout.",
    },
    "next_palindrome": {
        "difficulty": "hard",
        "bug_type": "missing_return",
        "bug_description": "Tüm-9 durumu için bir return üretiliyor ama palindrom basit zam durumunda hiçbir return yok; fonksiyon None döner.",
        "test_hint": "next_palindrome([1, 4, 3, 4, 1]) gibi normal bir girdide sonucun bir liste olduğunu (None değil) assert et.",
        "expected_failure_signal": "Sonuç None döner; karşılaştırma TypeError veya assertion fail eder.",
    },
    "next_permutation": {
        "difficulty": "medium",
        "bug_type": "reversed_comparison",
        "bug_description": "Pivot bulma karşılaştırması `perm[j] < perm[i]`; doğrusu `perm[i] < perm[j]`. Lexicographic next yerine yanlış swap ediyor.",
        "test_hint": "next_permutation([3, 2, 4, 1]) için bilinen lex-next ([3, 4, 1, 2]) çıktısını assert et.",
        "expected_failure_signal": "Çıktı doğru lex-next değil; verilen örnekte yanlış permütasyon döner.",
    },
    "pascal": {
        "difficulty": "medium",
        "bug_type": "off_by_one_range",
        "bug_description": "İç döngü `range(0, r)`; doğrusu `range(0, r + 1)`. Her satırın son elemanı (1) eksik kalır.",
        "test_hint": "pascal(3) çağrısında satır uzunluklarının [1, 2, 3] olduğunu assert et.",
        "expected_failure_signal": "Satır uzunluğu beklenenden bir eksik (örn. son satır 2 elemanlı).",
    },
    "possible_change": {
        "difficulty": "medium",
        "bug_type": "missing_base_case",
        "bug_description": "`coins` boşalınca taban durumu yok; sadece `total < 0` kontrolü var. Boş paralarla pozitif total ulaşıldığında IndexError fırlar.",
        "test_hint": "possible_change([], 5) çağrısında IndexError yerine 0 sayısının döndüğünü assert et.",
        "expected_failure_signal": "Test IndexError yakalar veya yanlış değer alır.",
    },
    "powerset": {
        "difficulty": "medium",
        "bug_type": "missing_subset_concat",
        "bug_description": "Recursive sonuç sadece `first` içeren altkümeleri döndürüyor; içermeyenler (rest_subsets) eklenmemiş. Doğrusu `rest_subsets + [[first] + s for s in rest_subsets]`.",
        "test_hint": "powerset([1, 2]) çağrısının uzunluğunun 4 (boş küme dahil) olduğunu assert et.",
        "expected_failure_signal": "Powerset boyutu 2^n yerine 2^(n-1) ya da daha az.",
    },
    "quicksort": {
        "difficulty": "medium",
        "bug_type": "strict_comparison",
        "bug_description": "Greater bölmesi `x > pivot` ile filtreleniyor; eşit pivot değerleri tamamen düşüyor. Doğrusu `x >= pivot` (ilk elemanı pivot olarak çıkardıktan sonra).",
        "test_hint": "Tekrar eden değerler içeren liste (örn. [3, 1, 3, 2]) için sıralı çıktıyı assert et; uzunluk korunmalı.",
        "expected_failure_signal": "Çıktı uzunluğu girdiden küçük; tekrar eden eleman düşmüş.",
    },
    "rpn_eval": {
        "difficulty": "hard",
        "bug_type": "swapped_operands",
        "bug_description": "Operatör çağrısı `op(token, a, b)`; doğrusu `op(token, b, a)`. Çıkarma/bölme gibi non-commutative ops yanlış sıralı uygulanır.",
        "test_hint": "Çıkarma ya da bölme içeren bir RPN ifadesi (örn. ['5', '1', '-'] sonucu 4) ile test et.",
        "expected_failure_signal": "Çıkarma/bölme sonucu işaret veya değer olarak ters çıkar.",
    },
    "shunting_yard": {
        "difficulty": "hard",
        "bug_type": "missing_push",
        "bug_description": "Operator durumunda `opstack.append(token)` satırı eksik; çıkış token'ları yalnızca operand'lardan oluşur.",
        "test_hint": "shunting_yard(['1', '+', '2']) çağrısının ['1', '2', '+'] üretmesini assert et.",
        "expected_failure_signal": "Çıktıda operatör hiç yok (sadece operand'lar).",
    },
    "sieve": {
        "difficulty": "easy",
        "bug_type": "wrong_quantifier",
        "bug_description": "Asallık testi `any(n % p > 0)`; doğrusu `all(n % p > 0)`. `any` neredeyse her sayıya True döner → asal olmayanlar da listelenir.",
        "test_hint": "sieve(7) çağrısının sadece [2, 3, 5, 7] döndüğünü assert et.",
        "expected_failure_signal": "Çıktı [2, 3, 4, 5, 6, 7] gibi composite'leri içerir.",
    },
    "sqrt": {
        "difficulty": "medium",
        "bug_type": "wrong_convergence_check",
        "bug_description": "Konverjans koşulu `abs(x - approx)`; Newton-Raphson için `abs(x - approx ** 2)` olmalı. Gerçek kare köke yaklaşmayan bir döngü.",
        "test_hint": "sqrt(2, 0.01) çıktısının yaklaşık 1.41 olduğunu (epsilon ile) assert et.",
        "expected_failure_signal": "Sonuç gerçek karekökten çok uzak veya algoritma çok erken döner.",
    },
    "subsequences": {
        "difficulty": "medium",
        "bug_type": "wrong_base_case",
        "bug_description": "k=0 için boş liste `[]` dönülüyor; doğrusu `[[]]` (bir tane boş alt-dizi). Yokluğu kombinatoryel sayıyı sıfırlar.",
        "test_hint": "subsequences(a=1, b=5, k=2) çağrısının uzunluğunun C(4,2)=6 olduğunu assert et.",
        "expected_failure_signal": "Çıktı boş liste; uzunluk kontrolü 0 verir.",
    },
    "to_base": {
        "difficulty": "hard",
        "bug_type": "wrong_concat_order",
        "bug_description": "Sonuç birikimi `result + alphabet[i]`; doğrusu `alphabet[i] + result`. Çıktı tabanın ters sırasında oluşur.",
        "test_hint": "to_base(31, 16) çıktısının '1F' olduğunu assert et.",
        "expected_failure_signal": "Beklenen string'in tersini döner (örn. 'F1').",
    },
    "wrap": {
        "difficulty": "hard",
        "bug_type": "missing_final_append",
        "bug_description": "Döngü sonunda kalan `text` lines listesine eklenmiyor; sondaki kelime grubu çıktıdan kayboluyor.",
        "test_hint": "wrap('aaa bbb ccc', 4) çağrısının ['aaa', 'bbb', 'ccc'] olduğunu assert et.",
        "expected_failure_signal": "Çıktı listesinin uzunluğu beklenenden bir eksik; son satır eksik.",
    },
}


def list_available_tasks() -> list[str]:
    buggy_dir = RAW_DIR / "python_programs"
    fixed_dir = RAW_DIR / "correct_python_programs"
    if not (buggy_dir.exists() and fixed_dir.exists()):
        raise SystemExit(f"QuixBugs raw bulunamadi. Beklenen yol: {RAW_DIR}")

    buggy = {p.stem for p in buggy_dir.glob("*.py") if not p.stem.endswith("_test")}
    fixed = {p.stem for p in fixed_dir.glob("*.py") if not p.stem.endswith("_test")}
    return sorted((buggy & fixed) - SKIP)


def convert_task(name: str, *, dry: bool) -> Path | None:
    buggy_src = RAW_DIR / "python_programs" / f"{name}.py"
    fixed_src = RAW_DIR / "correct_python_programs" / f"{name}.py"

    if not buggy_src.exists() or not fixed_src.exists():
        print(f"  [SKIP] {name}: kaynak dosya eksik")
        return None

    if name not in TASK_CATALOG:
        print(f"  [WARN] {name}: TASK_CATALOG'da yok, generic metadata yazilacak")

    catalog = TASK_CATALOG.get(name, {})
    task_id = f"quixbugs_{name}"
    target = TASKS_DIR / task_id

    metadata = {
        "task_id": task_id,
        "task_name": name,
        "difficulty": catalog.get("difficulty", ""),
        "bug_type": catalog.get("bug_type", ""),
        "bug_description": catalog.get(
            "bug_description",
            f"QuixBugs '{name}' algoritmasinda tek satirlik defect var.",
        ),
        "test_hint": catalog.get("test_hint", ""),
        "expected_failure_signal": catalog.get("expected_failure_signal", ""),
        "source": "QuixBugs",
        "source_url": "https://github.com/jkoppel/QuixBugs",
        "tags": ["quixbugs", "algorithmic", catalog.get("difficulty", "")],
    }

    if dry:
        print(f"  [DRY] {name} -> {target}")
        print(f"        difficulty: {metadata['difficulty']}, bug_type: {metadata['bug_type']}")
        return target

    (target / "buggy").mkdir(parents=True, exist_ok=True)
    (target / "fixed").mkdir(parents=True, exist_ok=True)

    # Byte-level copy preserves original line endings (e.g. wrap.py uses CRLF)
    # so the converted task is bit-identical to the upstream QuixBugs source.
    (target / "buggy" / "source.py").write_bytes(buggy_src.read_bytes())
    (target / "fixed" / "source.py").write_bytes(fixed_src.read_bytes())
    (target / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"  [OK]  {task_id}  ({metadata['difficulty']}, {metadata['bug_type']})")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(
        description="QuixBugs Python programlarini tasks_v2 formatina donusturur"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--task", help="Tek bir QuixBugs algoritmasi adi (orn: bitcount)")
    group.add_argument("--all", action="store_true", help="Tum uygun algoritmalari donustur")
    group.add_argument("--list", action="store_true", help="Donusturulebilir algoritmalari listele")
    parser.add_argument("--dry", action="store_true", help="Sadece goster, dosya yazma")
    args = parser.parse_args()

    available = list_available_tasks()

    if args.list:
        print(f"Donusturulebilir {len(available)} algoritma:")
        for name in available:
            cat = TASK_CATALOG.get(name, {})
            tag = f"[{cat.get('difficulty', '?')}/{cat.get('bug_type', '?')}]"
            print(f"  - {name:30s} {tag}")
        missing = [n for n in available if n not in TASK_CATALOG]
        if missing:
            print(f"\nUYARI: {len(missing)} algoritma TASK_CATALOG'da eksik: {missing}")
        return

    if args.task:
        if args.task not in available:
            if args.task in SKIP:
                raise SystemExit(
                    f"'{args.task}' helper bagimliligi nedeniyle MVP'de atlaniyor."
                )
            raise SystemExit(
                f"'{args.task}' QuixBugs'ta bulunamadi. --list ile listeyi gorun."
            )
        convert_task(args.task, dry=args.dry)
    elif args.all:
        print(
            f"Donusturuluyor: {len(available)} algoritma"
            + (" (DRY RUN)" if args.dry else "")
        )
        for name in available:
            convert_task(name, dry=args.dry)


if __name__ == "__main__":
    main()
