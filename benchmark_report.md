# Benchmark Raporu: Baseline vs Agentic (Detaylı Analiz)

**Rapor Tarihi:** 2026-01-02 17:08:40

## 1. Genel Özet (Model ve Mode Bazında)

| Model            | Mode     |   Success Rate (%) |   Avg Attempts |   Avg Tool Calls |   Avg Total Tokens |   Avg Duration (s) |   Avg Agent Steps |   Run Count |
|:-----------------|:---------|-------------------:|---------------:|-----------------:|-------------------:|-------------------:|------------------:|------------:|
| gemini-2.0-flash | agentic  |               50.0 |            2.2 |              8.1 |            40415.5 |               28.7 |              24.8 |          12 |
| gemini-2.0-flash | baseline |               66.7 |            1.8 |              3.7 |             4358.2 |                5.4 |               5.5 |          12 |
| gemini-2.5-flash | agentic  |               83.3 |            1.5 |              5.1 |            50057.1 |               86.6 |              16.6 |          12 |
| gemini-2.5-flash | baseline |               83.3 |            1.4 |              2.8 |             7698.6 |               23.9 |               4.2 |          12 |
| gemini-2.5-pro   | agentic  |               91.7 |            1.4 |              6.6 |            51888.9 |              162.9 |              19.2 |          12 |
| gemini-2.5-pro   | baseline |               83.3 |            1.3 |              2.5 |             6107.0 |               31.3 |               3.8 |          12 |

## 2. Task Bazlı Başarı Analizi

| Task                            |   ('gemini-2.0-flash', 'agentic') |   ('gemini-2.0-flash', 'baseline') |   ('gemini-2.5-flash', 'agentic') |   ('gemini-2.5-flash', 'baseline') |   ('gemini-2.5-pro', 'agentic') |   ('gemini-2.5-pro', 'baseline') |
|:--------------------------------|----------------------------------:|-----------------------------------:|----------------------------------:|-----------------------------------:|--------------------------------:|---------------------------------:|
| async_race_condition            |                                 0 |                                100 |                               100 |                                100 |                             100 |                              100 |
| boundary_threshold              |                               100 |                                100 |                               100 |                                100 |                             100 |                              100 |
| bugsinpy_black_async_for_13     |                                 0 |                                100 |                               100 |                                100 |                             100 |                              100 |
| bugsinpy_pysnooper_unicode_1    |                                 0 |                                  0 |                                 0 |                                100 |                             100 |                              100 |
| bugsinpy_thefuck_fish_version_3 |                               100 |                                100 |                               100 |                                100 |                             100 |                              100 |
| bugsinpy_thefuck_fix_file_28    |                               100 |                                  0 |                               100 |                                100 |                             100 |                              100 |
| bugsinpy_tqdm_enumerate_start_1 |                               100 |                                100 |                               100 |                                100 |                             100 |                              100 |
| cache_invalidation              |                               100 |                                100 |                               100 |                                100 |                             100 |                              100 |
| null_handling_profile           |                                 0 |                                  0 |                               100 |                                  0 |                             100 |                                0 |
| off_by_one_loop                 |                               100 |                                100 |                               100 |                                100 |                             100 |                              100 |
| swallowed_exception             |                                 0 |                                  0 |                                 0 |                                  0 |                               0 |                                0 |
| type_coercion_price             |                                 0 |                                100 |                               100 |                                100 |                             100 |                              100 |

## 3. Task Bazlı Ortalama Attempt Sayısı

| Task                            |   ('gemini-2.0-flash', 'agentic') |   ('gemini-2.0-flash', 'baseline') |   ('gemini-2.5-flash', 'agentic') |   ('gemini-2.5-flash', 'baseline') |   ('gemini-2.5-pro', 'agentic') |   ('gemini-2.5-pro', 'baseline') |
|:--------------------------------|----------------------------------:|-----------------------------------:|----------------------------------:|-----------------------------------:|--------------------------------:|---------------------------------:|
| async_race_condition            |                               3.0 |                                1.0 |                               1.0 |                                1.0 |                             1.0 |                              1.0 |
| boundary_threshold              |                               1.0 |                                2.0 |                               1.0 |                                1.0 |                             1.0 |                              1.0 |
| bugsinpy_black_async_for_13     |                               3.0 |                                2.0 |                               1.0 |                                1.0 |                             1.0 |                              1.0 |
| bugsinpy_pysnooper_unicode_1    |                               3.0 |                                3.0 |                               3.0 |                                2.0 |                             3.0 |                              1.0 |
| bugsinpy_thefuck_fish_version_3 |                               2.0 |                                1.0 |                               1.0 |                                1.0 |                             1.0 |                              1.0 |
| bugsinpy_thefuck_fix_file_28    |                               2.0 |                                3.0 |                               1.0 |                                1.0 |                             1.0 |                              1.0 |
| bugsinpy_tqdm_enumerate_start_1 |                               1.0 |                                1.0 |                               1.0 |                                1.0 |                             1.0 |                              1.0 |
| cache_invalidation              |                               1.0 |                                1.0 |                               1.0 |                                1.0 |                             1.0 |                              1.0 |
| null_handling_profile           |                               3.0 |                                3.0 |                               2.0 |                                3.0 |                             2.0 |                              3.0 |
| off_by_one_loop                 |                               1.0 |                                1.0 |                               1.0 |                                1.0 |                             1.0 |                              1.0 |
| swallowed_exception             |                               3.0 |                                3.0 |                               3.0 |                                3.0 |                             3.0 |                              3.0 |
| type_coercion_price             |                               3.0 |                                1.0 |                               2.0 |                                1.0 |                             1.0 |                              1.0 |

## 4. Task Bazlı Ortalama Token Kullanımı

| Task                            |   ('gemini-2.0-flash', 'agentic') |   ('gemini-2.0-flash', 'baseline') |   ('gemini-2.5-flash', 'agentic') |   ('gemini-2.5-flash', 'baseline') |   ('gemini-2.5-pro', 'agentic') |   ('gemini-2.5-pro', 'baseline') |
|:--------------------------------|----------------------------------:|-----------------------------------:|----------------------------------:|-----------------------------------:|--------------------------------:|---------------------------------:|
| async_race_condition            |                             67975 |                               2089 |                             35847 |                               3675 |                           23517 |                             3545 |
| boundary_threshold              |                             27919 |                               5043 |                             25337 |                               3376 |                           46004 |                             3565 |
| bugsinpy_black_async_for_13     |                             50082 |                               4677 |                             27710 |                               5335 |                           36985 |                             6389 |
| bugsinpy_pysnooper_unicode_1    |                             71865 |                               7716 |                            159564 |                              17981 |                          136299 |                             6567 |
| bugsinpy_thefuck_fish_version_3 |                             29388 |                               2098 |                             38313 |                               4427 |                           37968 |                             3550 |
| bugsinpy_thefuck_fix_file_28    |                             61365 |                               8467 |                             32219 |                               7419 |                           54584 |                             6141 |
| bugsinpy_tqdm_enumerate_start_1 |                             12010 |                               2125 |                             26389 |                               3027 |                           39425 |                             3912 |
| cache_invalidation              |                             18375 |                               2569 |                             24150 |                               3290 |                           43189 |                             3889 |
| null_handling_profile           |                             45576 |                               6447 |                             48217 |                              13601 |                           62761 |                            16266 |
| off_by_one_loop                 |                             16736 |                               2031 |                             36267 |                               2919 |                           23581 |                             3391 |
| swallowed_exception             |                             44665 |                               6970 |                             78949 |                              21814 |                           77213 |                            12246 |
| type_coercion_price             |                             39030 |                               2066 |                             67723 |                               5519 |                           41141 |                             3823 |

## 5. Task Bazlı Ortalama Süre (saniye)

| Task                            |   ('gemini-2.0-flash', 'agentic') |   ('gemini-2.0-flash', 'baseline') |   ('gemini-2.5-flash', 'agentic') |   ('gemini-2.5-flash', 'baseline') |   ('gemini-2.5-pro', 'agentic') |   ('gemini-2.5-pro', 'baseline') |
|:--------------------------------|----------------------------------:|-----------------------------------:|----------------------------------:|-----------------------------------:|--------------------------------:|---------------------------------:|
| async_race_condition            |                              46.0 |                                2.8 |                              52.0 |                                9.9 |                            77.2 |                             16.0 |
| boundary_threshold              |                              15.0 |                                6.6 |                              40.8 |                                6.8 |                           143.9 |                             12.9 |
| bugsinpy_black_async_for_13     |                              37.9 |                                6.0 |                              61.1 |                               16.0 |                           115.9 |                             36.8 |
| bugsinpy_pysnooper_unicode_1    |                              48.4 |                                9.2 |                             288.5 |                               67.4 |                           425.4 |                             37.0 |
| bugsinpy_thefuck_fish_version_3 |                              24.5 |                                2.6 |                              48.6 |                               12.2 |                           107.2 |                             15.2 |
| bugsinpy_thefuck_fix_file_28    |                              32.4 |                               11.1 |                              60.7 |                               24.2 |                           171.5 |                             34.5 |
| bugsinpy_tqdm_enumerate_start_1 |                              10.9 |                                2.7 |                              55.4 |                                6.9 |                           109.8 |                             17.6 |
| cache_invalidation              |                              13.2 |                                3.1 |                              34.6 |                                5.7 |                           112.8 |                             13.9 |
| null_handling_profile           |                              37.6 |                                7.6 |                              99.3 |                               38.6 |                           202.4 |                             95.2 |
| off_by_one_loop                 |                              12.1 |                                2.4 |                              44.1 |                                6.3 |                            85.7 |                             14.2 |
| swallowed_exception             |                              34.7 |                                7.9 |                             127.2 |                               75.0 |                           274.4 |                             58.6 |
| type_coercion_price             |                              31.3 |                                2.8 |                             127.2 |                               17.9 |                           128.8 |                             23.8 |

## 6. Başarısız Runlar (Detay)

| Task                         | Model            | Mode     |   Attempts |   Total Tokens |   Duration (s) | Run ID                   |
|:-----------------------------|:-----------------|:---------|-----------:|---------------:|---------------:|:-------------------------|
| bugsinpy_thefuck_fix_file_28 | gemini-2.0-flash | baseline |          3 |           8467 |           11.1 | baseline_20260102_142445 |
| null_handling_profile        | gemini-2.5-pro   | baseline |          3 |          16266 |           95.2 | baseline_20260102_164144 |
| null_handling_profile        | gemini-2.0-flash | agentic  |          3 |          45576 |           37.6 | agentic_20260102_142052  |
| null_handling_profile        | gemini-2.5-flash | baseline |          3 |          13601 |           38.6 | baseline_20260102_144835 |
| null_handling_profile        | gemini-2.0-flash | baseline |          3 |           6447 |            7.6 | baseline_20260102_142523 |
| bugsinpy_black_async_for_13  | gemini-2.0-flash | agentic  |          3 |          50082 |           37.9 | agentic_20260102_141701  |
| async_race_condition         | gemini-2.0-flash | agentic  |          3 |          67975 |           46.0 | agentic_20260102_141527  |
| type_coercion_price          | gemini-2.0-flash | agentic  |          3 |          39030 |           31.3 | agentic_20260102_142252  |
| swallowed_exception          | gemini-2.5-flash | agentic  |          3 |          78949 |          127.2 | agentic_20260102_144041  |
| swallowed_exception          | gemini-2.5-pro   | baseline |          3 |          12246 |           58.6 | baseline_20260102_165017 |
| swallowed_exception          | gemini-2.0-flash | agentic  |          3 |          44665 |           34.7 | agentic_20260102_142204  |
| swallowed_exception          | gemini-2.0-flash | baseline |          3 |           6970 |            7.9 | baseline_20260102_142548 |
| swallowed_exception          | gemini-2.5-flash | baseline |          3 |          21814 |           75.0 | baseline_20260102_144938 |
| swallowed_exception          | gemini-2.5-pro   | agentic  |          3 |          77213 |          274.4 | agentic_20260102_164524  |
| bugsinpy_pysnooper_unicode_1 | gemini-2.0-flash | agentic  |          3 |          71865 |           48.4 | agentic_20260102_141752  |
| bugsinpy_pysnooper_unicode_1 | gemini-2.5-flash | agentic  |          3 |         159564 |          288.5 | agentic_20260102_142911  |
| bugsinpy_pysnooper_unicode_1 | gemini-2.0-flash | baseline |          3 |           7716 |            9.2 | baseline_20260102_142417 |

## 7. Maliyet Analizi (Tahmini)

**Not:** Maliyet hesaplamaları Gemini pricing'e göre yaklaşık değerlerdir.

| Model            | Mode     |   Avg Prompt Tokens |   Avg Completion Tokens |   Cost per Run ($) |   Run Count |   Total Cost ($) |
|:-----------------|:---------|--------------------:|------------------------:|-------------------:|------------:|-----------------:|
| gemini-2.0-flash | agentic  |          37243.7500 |               3171.7500 |             0.0150 |          12 |           0.1798 |
| gemini-2.0-flash | baseline |           3504.7500 |                853.4167 |             0.0021 |          12 |           0.0249 |
| gemini-2.5-flash | agentic  |          33196.7500 |               3866.0000 |             0.0146 |          12 |           0.1752 |
| gemini-2.5-flash | baseline |           2634.0833 |               1192.0000 |             0.0022 |          12 |           0.0266 |
| gemini-2.5-pro   | agentic  |          34160.3333 |               3086.5833 |             0.1520 |          12 |           1.8236 |
| gemini-2.5-pro   | baseline |           2443.7500 |                831.3333 |             0.0173 |          12 |           0.2074 |

