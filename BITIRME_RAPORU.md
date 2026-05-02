# LLM Tabanlı Çok Ajanlı Hata Tespit ve Test Üretimi: Deneysel Bir Çalışma

## 1. Giriş

### 1.1 Problem Tanımı

Yazılım testleri, hata tespitinin en temel aracıdır. Ancak etkili test yazmak
uzmanlık, zaman ve kodun derinlemesine anlaşılmasını gerektirir. Büyük Dil
Modelleri (LLM), kod anlama ve üretme konusunda önemli yetenekler göstermektedir.

Bu çalışma şu soruyu araştırmaktadır:

> **Yapılandırılmış bir kod analizi adımı eklemek, LLM'in hata ortaya çıkaran
> test üretme başarısını artırır mı?**

### 1.2 Motivasyon

LLM'ler test yazarken çeşitli zorluklarla karşılaşır:

- **Test framework bilgisi**: Model, pytest gibi araçları bilse bile dolambaçlı
  davranabilir. Elinde somut veri olmalı ve test dilinin kurallarını bilmelidir.
- **Hata yapma eğilimi**: LLM kesinlikle hata yapabilir ve hatalarını kendi
  başına çözemeyebilir. İnsan desteği ve denetimi şarttır.
- **Planlama eksikliği**: Önceden test case planı çıkarılmalı, ardından test
  yazdırılmalıdır. Plansız test üretimi düşük kaliteli sonuçlar doğurur.
- **Bütünsel bakış açısı**: Model, dosyalar, kod parçacıkları ve fonksiyonlar
  arasında bağlantı kurabilmelidir. Büyük resmi görmeden yazılan testler
  yüzeysel kalır.

Bu çalışma, bu zorlukları aşmak için "önce analiz et, sonra test yaz" stratejisinin
etkinliğini ölçmektedir.

### 1.3 Araştırma Soruları

1. Kod analizi adımı eklemek test kalitesini artırır mı?
2. Bu etki model büyüklüğüne göre değişir mi?
3. Analizi her zaman mı yoksa sadece ihtiyaç duyulduğunda mı yapmak daha iyidir?

## 2. Yöntem

### 2.1 Deney Tasarımı

Üç farklı pipeline modu karşılaştırılmıştır:

```
Baseline:   Görev → TestWriter → Doğrulama (tekrar x3)
Agentic:    Görev → Analyzer → TestWriter → Doğrulama (tekrar x3)
Adaptive:   Görev → TestWriter → Doğrulama
              |                       |
              |      Başarısızsa:     |
              +--- Analyzer → TestWriter → Doğrulama (tekrar x2)
```

**Baseline:** Doğrudan test üretimi, analiz yok. Model sadece kaynak kodu ve
hata açıklamasını görür.

**Agentic (Her Zaman Analiz):** Model önce kodu analiz eder, yapılandırılmış bir
hipotez üretir. Bu hipotez test yazıcıya bağlam olarak verilir.

**Adaptive (İhtiyaç Halinde Analiz):** İlk deneme analiz olmadan yapılır. Başarısız
olursa, analiz eklenerek tekrar denenir. Bu strateji, güçlü modellerin gereksiz
analizden kaçınmasını sağlar.

### 2.2 Adil Karşılaştırma Garantileri

Deneysel geçerlilik için şu önlemler alınmıştır:

- **Aynı TestWriter prompt'u**: Her üç modda da test yazıcı aynı sistem talimatını alır
- **Aynı tekrar bütçesi**: Maksimum 3 deneme hakkı (tüm modlar için eşit)
- **Deterministik doğrulama**: pytest çıkış kodu ile değerlendirme (LLM yargısı yok)
- **Serpiştirilmiş çalıştırma sırası**: Her task için baseline→agentic→adaptive sırasıyla
  çalıştırılarak zamansal yanlılık kontrol altına alınmıştır

### 2.3 Doğrulama Kriteri

Bir test **hata ortaya çıkaran (bug-revealing)** olarak kabul edilir ancak ve ancak:
- Hatalı kodda **BAŞARISIZ** olursa (hatayı tespit eder)
- Düzeltilmiş kodda **BAŞARILI** olursa (düzeltmeyi doğrular)

Bu ikili kriter, testin hem hassasiyetini hem de özgüllüğünü garanti eder.

### 2.4 Test Edilen Modeller

Altı farklı LLM, üç farklı model ailesi ve geniş bir parametre aralığında test edilmiştir:

| # | Model | Parametre | Mimari | Aile |
|---|---|---|---|---|
| 1 | Meta Llama 3.1 8B | 8B | Dense | Meta |
| 2 | Meta Llama 4 Maverick | 17B (MoE) | MoE | Meta |
| 3 | Meta Llama 3.3 70B | 70B | Dense | Meta |
| 4 | OpenAI GPT-OSS | 120B | Dense | OpenAI |
| 5 | Mistral Medium 3.5 | 128B | Dense | Mistral |
| 6 | Anthropic Claude Sonnet 4.5 | ~175B* | Dense | Anthropic |

*Claude Sonnet parametre sayısı kamuya açıklanmamıştır; sektör tahminidir.

### 2.5 Değerlendirme Görevleri

12 görev, farklı hata kategorilerini kapsayacak şekilde tasarlanmıştır:

| Kategori | Görevler | Zorluk |
|---|---|---|
| Sınır Değer Hataları | boundary_threshold, off_by_one_loop | Kolay |
| Eşzamanlılık | async_race_condition | Zor |
| Durum Yönetimi | cache_invalidation | Orta |
| Hata Yakalama | swallowed_exception | Orta |
| Tip Güvenliği | type_coercion_price, null_handling_profile | Orta |
| Gerçek Dünya (BugsInPy) | black, pysnooper, thefuck (x2), tqdm | Orta-Zor |

Görevlerin 5'i bu çalışma için özel olarak tasarlanmış, 7'si BugsInPy veri
setinden alınmıştır. Her görev, hatalı ve düzeltilmiş olmak üzere iki versiyon
içerir.

### 2.6 Metrikler

- **BRTR** (Bug-Revealing Test Rate): Hata ortaya çıkaran test üretme başarı oranı
- **Delta**: Agentic/Adaptive BRTR eksi Baseline BRTR (+: analiz faydalı, -: analiz zararlı)
- **Deneme Sayısı**: Başarıya ulaşmak için gereken ortalama tekrar sayısı
- **%95 Güven Aralığı**: Wilson skoru ile hesaplanan binom oranı güven aralığı

## 3. Sonuçlar

### 3.1 Genel BRTR Karşılaştırması

| Model | Boyut | Baseline | Agentic | Adaptive | En İyi Mod |
|---|---|---|---|---|---|
| Claude Sonnet | ~175B | **97.2%** | JSON hata* | **97.2%** | Baseline = Adaptive |
| GPT-OSS | 120B | **86.1%** | 80.0% | **86.1%** | Baseline = Adaptive |
| Mistral 3.5 | 128B | **58.3%** | 51.4% | **58.3%** | Baseline = Adaptive |
| Llama 3.3 | 70B | 47.2% | **50.0%** | 41.7% | Agentic |
| Llama 4 Maverick | 17B | 38.9% | 44.4% | **50.0%** | **Adaptive** |
| Llama 3.1 | 8B | **30.6%** | 28.6%** | N/A | Baseline |

*Claude CLI düz metin döndürdüğü için Analyzer JSON ayrıştırma hatası verdi.
**8B modelde agentic run'ların %81'i JSON hatası ile başarısız oldu.

### 3.2 Delta Analizi (Baseline'a Göre Fark)

| Model | Agentic Delta | Adaptive Delta | Yorum |
|---|---|---|---|
| Claude Sonnet | N/A (JSON hata) | **0.0%** | Zaten çok güçlü, analiz gereksiz |
| GPT-OSS 120B | **-6.1%** | **0.0%** | Analiz zarar veriyor; adaptive telafi ediyor |
| Mistral 128B | **-6.9%** | **0.0%** | Analiz zarar veriyor; adaptive telafi ediyor |
| Llama 70B | **+2.8%** | -5.5% | Agentic hafif fayda sağlıyor |
| Llama 4 17B | **+5.5%** | **+11.1%** | Adaptive en güçlü faydayı sağlıyor |
| Llama 8B | -2.0% | N/A | Pipeline kullanılamaz durumda |

### 3.3 Görev Bazlı Karşılaştırma

| Görev | Claude | GPT-OSS | Mistral | Llama 70B | Llama 4 | Llama 8B |
|---|---|---|---|---|---|---|
| boundary_threshold | **100** | **100** | **100** | **100** | **100** | 33 |
| off_by_one_loop | **100** | **100** | **100** | **100** | **100** | **100** |
| bugsinpy_tqdm | **100** | **100** | **100** | **100** | **100** | 33 |
| bugsinpy_thefuck_fish | **100** | **100** | **100** | **100** | **100** | 33 |
| bugsinpy_black | **100** | **100** | **100** | **100** | **100** | 67 |
| type_coercion_price | **100** | **100** | **100** | 67 | 33 | 33 |
| swallowed_exception | **100** | **100** | **100** | 67 | 33 | 33 |
| bugsinpy_pysnooper | **100** | **100** | 0 | 0 | 0 | 33 |
| cache_invalidation | **100** | **100** | 0 | 0 | 0 | 0 |
| null_handling_profile | **100** | 67 | 0 | 0 | 0 | 0 |
| async_race_condition | **100** | 33 | 0 | 0 | 0 | 0 |
| bugsinpy_thefuck_fix | 67 | 33 | 0 | 0 | 0 | 0 |

*Baseline BRTR değerleri gösterilmiştir. Kalın = %100 başarı.*

### 3.4 Görev Zorluk Katmanları

**Katman 1 — Kolay (5 görev):** `boundary_threshold`, `off_by_one_loop`,
`bugsinpy_tqdm`, `bugsinpy_thefuck_fish`, `bugsinpy_black`

Tüm yetkin modeller (17B+) bu görevleri çözmektedir. Hatalar basit ve
lokalizedir (yanlış operatör, eksik argüman). Analiz adımı fayda sağlamamaktadır.

**Katman 2 — Orta (3 görev):** `type_coercion_price`, `swallowed_exception`,
`bugsinpy_pysnooper`

Model kapasitesine göre değişen sonuçlar. `swallowed_exception` görevinde analiz
tüm modellerde zarar vermektedir. Analiz adımının en değişken etki gösterdiği
katmandır.

**Katman 3 — Zor (4 görev):** `cache_invalidation`, `null_handling_profile`,
`async_race_condition`, `bugsinpy_thefuck_fix`

Yalnızca Claude Sonnet ve GPT-OSS bu görevleri çözebilmektedir. Eşzamanlılık,
durum yönetimi ve karmaşık gerçek dünya hatalarını içerir.

## 4. Analiz ve Bulgular

### 4.1 Bulgu 1: Model Kapasitesi Baskın Faktördür

```
Baseline BRTR (model boyutuna göre):

  Claude Sonnet ~175B:  ████████████████████████████████████████████████  97.2%
  GPT-OSS 120B:        ████████████████████████████████████████████      86.1%
  Mistral 128B:        █████████████████████████████                     58.3%
  Llama 70B:           ███████████████████████                           47.2%
  Llama 4 17B:         ███████████████████                               38.9%
  Llama 8B:            ███████████████                                   30.6%
```

Modeller arasındaki fark (%30→%97) pipeline mimarisinin etkisinden (%12'den az)
çok daha büyüktür. **Daha iyi model seçmek, pipeline karmaşıklığı eklemekten
çok daha etkilidir.**

Bu bulgu, mentörümüzün "LLM'in elinde veri olmalı, test dilini bilmeli"
önerisini doğrulamaktadır — güçlü modeller bu bilgiyi zaten içselleştirmiştir.

### 4.2 Bulgu 2: Analiz Faydası Ters-U Eğrisi İzler

| Model Gücü | Agentic Etkisi | Adaptive Etkisi | Yorum |
|---|---|---|---|
| Çok güçlü (Claude, GPT-OSS) | Zarar / Nötr | Nötr | Analiz gereksiz |
| Güçlü (Mistral 128B) | Zarar (-6.9%) | Nötr | Analiz gereksiz |
| Orta (Llama 70B) | Hafif fayda (+2.8%) | Hafif zarar | Karışık |
| Orta-alt (Llama 4 17B) | Fayda (+5.5%) | **En iyi (+11.1%)** | Analiz faydalı |
| Zayıf (Llama 8B) | Kullanılamaz | N/A | Pipeline kırık |

**Yorum:** Analiz adımı, güçlü modellere zarar verir (zaten cevabı biliyorlar),
orta güçteki modellere fayda sağlar (yönlendirmeye ihtiyaçları var), ve zayıf
modellerde çalışmaz (yapılandırılmış çıktı üretemezler).

Bu bulgu, mentörümüzün "önceden test case planı çıkmalı, sonra test yazdırılmalı"
önerisini kısmen doğrulamaktadır — ancak bu strateji yalnızca belirli model
kapasitelerinde etkilidir.

### 4.3 Bulgu 3: Adaptive Mod En Optimal Stratejidir

Llama 4 Maverick (17B) sonuçları:
- Baseline: %38.9
- Agentic (her zaman analiz): %44.4 (+5.5%)
- **Adaptive (ihtiyaç halinde analiz): %50.0 (+11.1%)**

Adaptive mod, "önce dene, başarısız olursan analiz et" stratejisiyle:
- Güçlü modellerde gereksiz analizi atlar (baseline ile eşit)
- Orta modellerde en yüksek faydayı sağlar
- Token maliyetini optimize eder

### 4.4 Bulgu 4: Analiz Onay Yanlılığı Yaratabilir

`swallowed_exception` görevi tüm modellerde tutarlı bir anti-kalıp gösterir:

| Model | Baseline | Agentic | Delta |
|---|---|---|---|
| Claude Sonnet | 100% | 100% | 0% |
| GPT-OSS 120B | 100% | 100% | 0% |
| Mistral 128B | **100%** | **0%** | **-100%** |
| Llama 70B | **67%** | **0%** | **-67%** |
| Llama 4 17B | **33%** | **0%** | **-33%** |

Analyzer, "bare except NameError'ı yutuyor" diye doğru bir hipotez üretir.
Ancak bu hipotez, TestWriter'ı `pytest.raises(NameError)` yazmaya yönlendirir
— exception zaten yutulduğu için bu test her zaman başarısız olur.

**Ders:** Doğru analiz her zaman faydalı test stratejisine dönüşmez.
Analiz, modeli tek bir yaklaşıma kilitleyerek keşif alanını daraltabilir.

Bu bulgu, mentörümüzün "büyük resmi görmesi lazım, dosyalar ve fonksiyonlar
arasında bağlantı kurması gerek" önerisini desteklemektedir — tek bir hipoteze
odaklanmak büyük resmi kaçırmaya yol açabilir.

### 4.5 Bulgu 5: Yapılandırılmış Çıktı Bir Kapasite Eşiğidir

| Model | Agentic Tamamlanan Run | Oran |
|---|---|---|
| GPT-OSS 120B | 35/36 | %97 |
| Mistral 128B | 35/36 | %97 |
| Llama 70B | 34/36 | %94 |
| Llama 4 17B | 36/36 | %100 |
| Llama 8B | **7/36** | **%19** |

8B model, CodeAnalysis JSON çıktısını %81 oranında üretememektedir. Çok ajanlı
pipeline'lar, yapılandırılmış agent-arası iletişim gerektirdiğinde, modelin
minimum bir yetenek eşiğini aşması zorunludur.

### 4.6 Bulgu 6: Görev Zorluğu Sonuçları Belirler

Görevler, model veya pipeline modundan bağımsız olarak üç katmana ayrılır:

- **Her zaman çözülen** (%42): Basit, lokalize hatalar
- **Bazen çözülen** (%17): Model kapasitesine bağlı
- **Nadiren çözülen** (%42): Yalnızca en güçlü modeller başarılı

Pipeline mimarisi yalnızca "bazen çözülen" kategorisinde fark yaratmaktadır.

## 5. Test Yazarken Dikkat Edilmesi Gerekenler

Bu deneylerden çıkarılan ve LLM ile test yazarken dikkat edilmesi gereken
pratik öneriler:

### 5.1 LLM'in Güçlü ve Zayıf Yönleri

**LLM'in iyi yaptığı:**
- Basit, lokalize hataları tespit etme (yanlış operatör, eksik argüman)
- Sınır değer testleri yazma (boundary conditions)
- Bilinen kalıplardaki hataları yakalama

**LLM'in zorlandığı:**
- Eşzamanlılık (concurrency) hataları
- Durum yönetimi (state management) hataları
- Dolaylı nedensellik (hata bir yerde, semptom başka yerde)
- Yutulmuş istisnalar (swallowed exceptions) — doğru teşhis, yanlış test

### 5.2 Best Practice Öneriler

1. **Önce model seçimini doğru yapın**: Model kapasitesi, pipeline mimarisinden
   çok daha etkilidir. Zayıf modelle karmaşık pipeline yerine güçlü modelle
   basit pipeline tercih edin.

2. **Analizi koşullu uygulayın (Adaptive strateji)**: Her zaman analiz yapmak
   yerine, ilk deneme başarısız olursa analiz ekleyin. Bu strateji hem güçlü
   hem orta güçteki modellerde optimal sonuç verir.

3. **Test planı çıkarın**: Mentörümüzün önerdiği gibi, önceden test case planı
   çıkarılmalıdır. Ancak bu plan, modeli tek bir hipoteze kilitlememeli, birden
   fazla olası hata senaryosunu içermelidir.

4. **İnsan denetimi şarttır**: LLM kesinlikle hata yapabilir ve kendi hatalarını
   her zaman düzeltemez. Üretilen testler mutlaka insan tarafından gözden
   geçirilmelidir.

5. **Bağlam sağlayın**: Model, dosyalar ve fonksiyonlar arasında bağlantı
   kurabilmesi için yeterli bağlam almalıdır. Sadece kaynak kodu değil, hata
   açıklaması, ilgili dosyalar ve test stratejisi de verilmelidir.

6. **Tekrar mekanizması ekleyin**: İlk denemede başarısız olan testler, pytest
   çıktısından öğrenerek iyileştirilebilir. 3 deneme hakkı ile başarı oranı
   önemli ölçüde artmaktadır.

### 5.3 Bad Practice Durumlar

1. **Her zaman analiz yapmak**: Güçlü modellerde gereksiz analiz, performansı
   düşürür ve onay yanlılığı yaratır.

2. **Tek hipoteze bağlanmak**: Analyzer'ın tek bir hipotezi, test yazıcıyı
   yanlış yöne kilitleyebilir. Birden fazla alternatif strateji sunulmalıdır.

3. **LLM yargısına güvenmek**: Test doğrulaması deterministik olmalıdır
   (pytest çıkış kodu). LLM'in "bu test iyi" demesi güvenilir değildir.

4. **Küçük modelle karmaşık pipeline**: 8B model, yapılandırılmış JSON çıktısı
   üretmekte %81 oranında başarısız olmaktadır. Modelin kapasitesine uygun
   pipeline tasarlanmalıdır.

5. **Plansız test üretimi**: Doğrudan "test yaz" demek yerine, önce hatanın
   nerede olduğunu, hangi girdilerin tetiklediğini ve beklenen davranışın ne
   olduğunu belirtmek test kalitesini artırır.

## 6. Token Maliyet Analizi

| Model | Baseline Token/Run | Agentic Token/Run | Adaptive Token/Run | Agentic Ek Maliyet |
|---|---|---|---|---|
| GPT-OSS 120B | 2,617 | 4,152 | 3,227 | +%59 |
| Mistral 128B | 1,602 | 2,788 | 2,136 | +%74 |
| Llama 70B | 1,719 | 2,399 | 2,136 | +%40 |
| Llama 4 17B | 2,001 | 2,710 | 2,317 | +%35 |
| Llama 8B | 2,300 | 3,298 | N/A | +%43 |

Agentic mod, %35-74 oranında ek token maliyeti getirmektedir. Adaptive mod,
analiz maliyetini yalnızca gerektiğinde ödeyerek bu maliyeti optimize eder.

## 7. Mimari Tasarım Kararları

### 7.1 Neden 2 Agent (6 Değil)?

Başlangıçta 5 ajanlı pipeline tasarlanmıştı:
```
Planner → Analysis → Critic → Reflection → Executor
```

Ancak deneyler, tek bir analiz adımının bile güçlü modellerde zarar verdiğini
göstermiştir. Daha fazla agent eklemek:
- Doğrusal olarak daha fazla yapılandırılmış çıktı gerektirir
- Onay yanlılığını katlar (her agent bir öncekinin hipotezini pekiştirir)
- Token maliyetini orantısız artırır

Bu nedenle pipeline, Analyzer + TestWriter olarak sadeleştirilmiştir.

### 7.2 Neden Deterministik Doğrulama?

LLM tabanlı değerlendirme (LLM-as-judge) yerine pytest çıkış kodları
kullanılmaktadır. Nedenleri:
- LLM yargısı tutarsızdır ve yanlış sınıflandırma yapabilir
- Ek API çağrısı maliyeti getirir
- Modlar arasında adaletsiz token bütçesi oluşturur
- Boolean mantık (başarısız VE başarılı = hata ortaya çıkaran) yeterli ve güvenilirdir

### 7.3 Neden Adaptive Mod?

Deneyler üç temel gözlem ortaya koymuştur:
1. Güçlü modeller analiz olmadan çözer → analiz gereksiz
2. Orta modeller analiz ile iyileşir → analiz faydalı
3. Zayıf modeller analiz üretemez → analiz imkansız

Adaptive mod, "önce dene, başarısız olursan analiz et" stratejisiyle bu üç
durumu tek bir pipeline'da optimize eder.

## 8. Geçerlilik Tehditleri

1. **Küçük örneklem**: Görev başına 3 tekrar, istatistiksel gücü sınırlamaktadır.
   Güven aralıkları geniştir ve modlar arasında örtüşmektedir.

2. **Model ailesi çeşitliliği**: 6 modelden 3'ü Llama ailesidir. Daha farklı
   mimarilerin test edilmesi genellenebilirliği güçlendirecektir.

3. **Altyapı karıştırıcıları**: Python 3.9 tip işareti uyumsuzluğu ve eksik
   pytest-asyncio eklentisi bazı görevlerde altyapı kaynaklı başarısızlıklara
   neden olmuştur.

4. **JSON ayrıştırma kırılganlığı**: Agentic pipeline, Analyzer'dan geçerli
   JSON çıktısı gerektirmekte ve bu durum küçük modeller için tek bir hata
   noktası oluşturmaktadır.

5. **Prompt hassasiyeti**: Farklı prompt formülasyonları farklı sonuçlar
   üretebilir. Prompt ablation çalışması yapılmamıştır.

## 9. Sonuç ve Öneriler

### 9.1 Ana Sonuçlar

1. **Model kapasitesi baskın faktördür.** Modeller arası %67'lik BRTR farkı
   (%30→%97), pipeline mimarisinin %12'den az olan etkisini gölgede bırakmaktadır.

2. **Analiz faydası ters-U eğrisi izler.** Güçlü modellere zarar verir, orta
   güçteki modellere fayda sağlar, zayıf modellerde çalışmaz.

3. **Adaptive mod en optimal stratejidir.** Güçlü modellerde baseline ile eşit,
   orta modellerde en yüksek fayda (+%11.1), ve gereksiz maliyetten kaçınır.

4. **Ön-analiz onay yanlılığı yaratabilir.** swallowed_exception görevi, doğru
   analizin yanlış test stratejisine yol açabileceğini göstermektedir.

5. **Çok ajanlı pipeline'lar minimum kapasite eşiği gerektirir.** 8B model,
   yapılandırılmış çıktı üretmekte %81 oranında başarısız olmaktadır.

6. **LLM hata yapabilir, insan denetimi şarttır.** En güçlü model bile
   (Claude Sonnet, %97.2) %100 başarı sağlayamamaktadır. Üretilen testler
   mutlaka insan tarafından gözden geçirilmelidir.

### 9.2 Gelecek Çalışmalar

- Tekrar sayısını 10+'a çıkararak istatistiksel güç artırma
- Çoklu hipotez stratejisi ile onay yanlılığını azaltma
- Farklı model aileleri (Gemma, Qwen) ile genellenebilirlik testi
- Python 3.10+ ortamında altyapı sorunlarını giderme
- Daha büyük ve karmaşık gerçek dünya projelerinde test etme

## 10. Ham Veri

Tüm deney verileri `results/` dizininde mevcuttur:

```
results/
  analysis_vs_direct_<timestamp>/
    summary.json              # Toplu istatistikler
    config.yaml               # Konfigürasyon kopyası
    runs/<görev_id>/           # Tekil run kayıtları
      baseline_run_01.json
      agentic_run_01.json
      adaptive_run_01.json
```

Her run kaydı: üretilen test kodu, doğrulama çıktısı (hatalı ve düzeltilmiş
sürümlerin pytest çıktıları), token kullanımı, süre ve analiz (agentic/adaptive
modda) bilgilerini içermektedir.

### Test Edilen Modeller ve Deney Zaman Damgaları

| Model | Provider | Deney Tarihi |
|---|---|---|
| Llama 3.3 70B | NVIDIA Build | 2026-04-30 |
| Llama 3.1 8B | NVIDIA Build | 2026-04-30 |
| Mistral Medium 3.5 | NVIDIA Build | 2026-04-30 |
| Llama 4 Maverick | NVIDIA Build | 2026-04-30 |
| GPT-OSS 120B | NVIDIA Build | 2026-04-30 |
| Claude Sonnet 4.5 | Claude Code CLI | 2026-05-01/02 |
