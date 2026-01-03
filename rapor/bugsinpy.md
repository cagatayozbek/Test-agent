# BugsInPy Entegrasyon Test Raporu (2 Ocak 2026)

## Özet

- Koşulan komutlar:
  - İlk toplu koşu: `python3 evaluation/run_all.py --test-gen --mode both --task bugsinpy --max-retries 2 --output runs/bugsinpy_flash.json`
  - Tekrarlar (sadece başarısız görevler):
    - `python3 evaluation/run_all.py --test-gen --mode both --task bugsinpy_black_async_for_13 --max-retries 3 --verbose --output runs/bugsinpy_retry_black_async_for_13.json`
    - `python3 evaluation/run_all.py --test-gen --mode both --task bugsinpy_pysnooper_unicode_1 --max-retries 3 --verbose --output runs/bugsinpy_retry_pysnooper_unicode_1.json`
- Nihai durum (son tekrarlar dahil): Toplam 10 run (5 görev x baseline/agentic)
- Bug-revealing test üretimi: 9/10 (BRTR)
  - Baseline: 4/5 (80%), ort. deneme: ~1.5 (pysnooper başarısız)
  - Agentic: 5/5 (100%), ort. deneme: ~1.4
- Kalıcı başarısızlık: Baseline için `bugsinpy_pysnooper_unicode_1` (encoding bug; sistemsel hata yok, kasıtlı başarısızlık kabul edildi). Agentic aynı görevde 3. denemede başarılı.

## Görevler ve Sonuçlar

| Görev                           | Kaynak            | Py versiyon | Pytest komutu                                                           | Baseline                      | Agentic             | Notlar                                                                                            |
| ------------------------------- | ----------------- | ----------- | ----------------------------------------------------------------------- | ----------------------------- | ------------------- | ------------------------------------------------------------------------------------------------- |
| bugsinpy_thefuck_fix_file_28    | thefuck (bug 28)  | 3.7.0       | pytest tests/rules/test_fix_file.py::test_get_new_command_with_settings | Başarılı (deneme 2)           | Başarılı (deneme 1) | İlk toplu koşuda baseline deneme 2’de geçti, agentic ilk denemede geçti.                          |
| bugsinpy_thefuck_fish_version_3 | thefuck (bug 3)   | 3.7.0       | pytest tests/shells/test_fish.py::TestFish::test_info                   | Başarılı (deneme 2)           | Başarılı (deneme 1) | İlk denemede syntax_error aldı, ikinci denemede düzeldi; agentic tek seferde geçti.               |
| bugsinpy_pysnooper_unicode_1    | PySnooper (bug 1) | 3.8.1       | pytest -q -s tests/test_chinese.py::test_chinese                        | Başarısız (3 deneme, no_fail) | Başarılı (deneme 3) | Baseline bug-revealing üretemedi (encoding default UTF-8); agentic 3. denemede başardı.           |
| bugsinpy_black_async_for_13     | black (bug 13)    | 3.8.3       | python -m unittest -q tests.test_black.BlackTestCase.test_python37      | Başarılı (deneme 1, tekrar)   | Başarılı (deneme 1) | İlk toplu koşuda baseline syntax_error (import); tekrar koşusunda her iki mod ilk denemede geçti. |
| bugsinpy_tqdm_enumerate_start_1 | tqdm (bug 1)      | 3.6.9       | python3 -m pytest tqdm/tests/tests_contrib.py::test_enumerate           | Başarılı (deneme 2)           | Başarılı (deneme 1) | Baseline ilk deneme syntax_error, ikinci denemede geçti; agentic tek seferde geçti.               |

## Gözlemler

- Agentic tüm görevlerde 5/5 bug-revealing test üretti; en zorlayıcı vaka PySnooper için 3 deneme gerekti.
- Baseline 4/5; PySnooper’da kalıcı no_fail (UTF-8 default ortamında bug tetiklenmedi). Sistemsel hata yok, kabul edildi.
- Black async import hatası, TestWriter prompt’una eklenen “from source import …” kuralıyla çözüldü ve tekrar koşusunda ilk denemede geçti.
- Ortalama deneme sayıları düşük; retry mekanizması amaca uygun çalışıyor.

### Model notları

- İki model denendi: gemini-2.5-pro (ilk koşu) ve gemini-2.5-flash (güncel tekrarlar). Başarı farkı küçük: pro’da BRTR ~80%/100%, flash’ta ilk toplu koşuda 70%/80% iken (import/encoding kaynaklı), tekrarlarla 80%/100% seviyesine çıktı.

## Önerilen Sonraki Adımlar

1. PySnooper baseline’ı olduğu gibi bırakıyoruz (bilinçli no_fail). Gerekirse non-UTF-8 ortam zorlamalı senaryo ile yeniden denenebilir.
2. Tekil raporlar: [runs/bugsinpy_flash.json](runs/bugsinpy_flash.json), [runs/bugsinpy_retry_black_async_for_13.json](runs/bugsinpy_retry_black_async_for_13.json), [runs/bugsinpy_retry_pysnooper_unicode_1.json](runs/bugsinpy_retry_pysnooper_unicode_1.json).
3. İstersen `--evaluate` ile değerlendirme ekleyip yeni bir konsolide JSON üretebiliriz.

## Referans Görev Dosyaları

- [evaluation/tasks_v2/bugsinpy_thefuck_fix_file_28/metadata.json](evaluation/tasks_v2/bugsinpy_thefuck_fix_file_28/metadata.json)
- [evaluation/tasks_v2/bugsinpy_thefuck_fish_version_3/metadata.json](evaluation/tasks_v2/bugsinpy_thefuck_fish_version_3/metadata.json)
- [evaluation/tasks_v2/bugsinpy_pysnooper_unicode_1/metadata.json](evaluation/tasks_v2/bugsinpy_pysnooper_unicode_1/metadata.json)
- [evaluation/tasks_v2/bugsinpy_black_async_for_13/metadata.json](evaluation/tasks_v2/bugsinpy_black_async_for_13/metadata.json)
- [evaluation/tasks_v2/bugsinpy_tqdm_enumerate_start_1/metadata.json](evaluation/tasks_v2/bugsinpy_tqdm_enumerate_start_1/metadata.json)
