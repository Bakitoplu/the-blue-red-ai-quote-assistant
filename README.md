# The Blue Red AI Quote Assistant

The Blue Red; barkod okuyucu, el terminali, yazıcı, yazılım lisansı ve kurulum hizmetleri satan B2B bir satış platformu için hazırlanmış kaynaklı teklif asistanıdır.

Kullanıcı web veya mobil sohbet ekranından ürün, stok, fiyat, politika, uyumluluk ve teklif ile ilgili Türkçe sorular sorabilir. Sistem ilgili ürün ve bilgi kayıtlarını bulur, cevabı kaynaklarıyla birlikte üretir ve gerektiğinde aynı kalıcı teklif taslağı üzerinde gerçek değişiklik yapar.

Bu projede hedef, yalnızca chat cevabı üretmek değil; kaynaklı cevap, güvenli tool-call akışı, gerçek quote mutation, web/mobil ortak state ve test edilebilir log katmanını birlikte göstermektir.

## İçindekiler

- [Tech Stack](#tech-stack)
- [Mimari](#mimari)
- [Kurulum](#kurulum)
- [Docker Compose](#docker-compose)
- [Backend Endpointleri](#backend-endpointleri)
- [Web Kullanımı](#web-kullanımı)
- [Mobil Kullanımı](#mobil-kullanımı)
- [Retrieval Yaklaşımı](#retrieval-yaklaşımı)
- [Tool Orchestration](#tool-orchestration)
- [Fallback Mode](#fallback-mode)
- [Müşteri ve Teklif Kapsamı](#müşteri-ve-teklif-kapsamı)
- [Teklif Mutasyon Modeli](#teklif-mutasyon-modeli)
- [Fiyatlandırma Kuralları](#fiyatlandırma-kuralları)
- [Streaming Eventleri](#streaming-eventleri)
- [Testler](#testler)
- [Demo Akışı](#demo-akışı)
- [Güvenlik](#güvenlik)
- [Trade-off ve Bilinen Sınırlamalar](#trade-off-ve-bilinen-sınırlamalar)

## Tech Stack

- Backend: FastAPI, SQLAlchemy, PostgreSQL
- Web: React + Vite
- Mobile: React Native / Expo
- Runtime: Docker Compose
- Tests: pytest
- Streaming: Server-Sent Events

## Mimari

Backend tek doğruluk kaynağıdır. Web ve mobil aynı backend API’sini kullanır. Teklif durumu frontend içinde ayrı ayrı tutulmaz; her iki istemci de `GET /quotes/{quote_id}` endpointinden aynı PostgreSQL state’ini okur.

Chat istekleri `POST /chat/stream` endpointine gönderilir. Backend mesajı işler, gerekli tool fonksiyonlarını deterministic olarak çağırır, kaynakları toplar, gerekirse pending action oluşturur ve SSE eventleriyle cevabı stream eder.

```text
React Web ─┐
           ├── FastAPI ── PostgreSQL
Expo App ──┘      │
                  ├── deterministic intent router
                  ├── quote/product/knowledge tools
                  ├── pending action + idempotency
                  └── SSE + tool-call logging
```

Temel karar: fiyat, stok, kaynak, mutasyon ve idempotency kararları LLM’ye bırakılmaz. Bu kararlar backend tool fonksiyonları ve safety kontrolleriyle uygulanır.

## Kurulum

```bash
cp .env.example .env
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
```

Örnek env değerleri:

```bash
DATABASE_URL=postgresql+psycopg://tbr:tbr@localhost:5432/tbr
DATASET_DIR=the_blue_red_candidate_case_dataset
AUTO_SEED=true
LLM_ENABLED=false
LLM_MODEL=gpt-4.1-mini
OPENAI_API_KEY=
VITE_API_URL=http://127.0.0.1:8000
EXPO_PUBLIC_API_URL=http://127.0.0.1:8000
```

`.env` repoya eklenmez. Production ortamında veritabanı parolası ve API anahtarları secret manager veya deployment-level environment variables ile verilmelidir.

## Docker Compose

Projeyi tek komutla ayağa kaldırmak için:

```bash
docker compose up --build
```

Servisler:

- Backend: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`
- Web: `http://127.0.0.1:5173`
- PostgreSQL: Docker network içinde backend tarafından kullanılır

Health kontrolü:

```bash
curl http://127.0.0.1:8000/health
```

Beklenen cevap:

```json
{"status":"ok"}
```

Seed verisini sıfırlamak için:

```bash
curl -X POST http://127.0.0.1:8000/seed/reset
```

Backend startup sırasında dataset JSON dosyalarını yükler.

## Backend Endpointleri

Ana endpointler:

- `GET /health`
- `GET /products`
- `POST /products`
- `PUT /products/{product_id}`
- `GET /knowledge`
- `POST /knowledge`
- `PUT /knowledge/{knowledge_id}`
- `GET /customers`
- `GET /customers/{customer_id}`
- `POST /customers`
- `GET /customers/{customer_id}/quotes`
- `POST /quotes`
- `GET /quotes/{quote_id}`
- `POST /quotes/{quote_id}/items/{product_id}/quantity`
- `GET /tool-call-logs`
- `GET /sessions/{session_id}/tool-calls`
- `POST /chat/stream`
- `GET /chat/stream`
- `POST /seed/reset`

## Web Kullanımı

```bash
cd web
npm install
npm run dev
```

Web uygulaması gerçek backend API’ye bağlıdır.

İlk ekranda müşteri girişi vardır:

```text
Müşteri ID
Giriş yap
```

Müşteri ID’si olmayan kullanıcı ayrı “Yeni müşteri kaydı” ekranına geçebilir. Kayıt ekranında kullanıcı customer ID yazmaz. Backend yeni müşteri için `CUST-NEW-###` formatında çakışmayan ID üretir ve kullanıcıya gösterir.

Girişten sonra webde sadece oturumdaki müşterinin teklifleri listelenir. Seçili müşteri için yeni draft teklif oluşturulabilir. Yeni teklif ID’si backend tarafından `Q-NEW-###` formatında üretilir ve otomatik seçilir.

Web menüsü:

- Sohbet: streaming chat, müşteri-dostu cevaplar ve sade kaynak listesi
- Teklifler: aktif teklif kalemleri, satır toplamları ve `[-] [quantity] [+]` kontrolleri
- Ürünler: demo/admin amaçlı ürün listeleme, ekleme ve düzenleme
- Bilgi: demo/admin amaçlı knowledge listeleme, ekleme ve düzenleme

Müşteri arayüzünde Loglar sekmesi yoktur. Raw tool eventleri, JSON payloadları ve debug bilgileri müşteri sohbetine veya teklif ekranına karışmaz.

Tool-call logları yine de backend tarafında korunur:

```bash
curl -s http://127.0.0.1:8000/tool-call-logs
curl -s http://127.0.0.1:8000/sessions/WEB-Q-1002/tool-calls
```

## Mobil Kullanımı

```bash
cd mobile
npm install
EXPO_PUBLIC_API_URL=http://BILGISAYARIN_LAN_IP_ADRESI:8000 npm run start
```

Fiziksel telefonda Expo Go kullanırken `127.0.0.1` telefonun kendisini gösterir. Bu yüzden `EXPO_PUBLIC_API_URL`, bilgisayarın aynı Wi-Fi ağındaki LAN IP adresi olmalıdır.

Mobil akış:

1. İlk ekranda müşteri ID ile giriş yapılır.
2. Müşteri ID’si olmayan kullanıcı “Yeni müşteri kaydı” ekranından kayıt oluşturabilir.
3. Kayıtta kullanıcı customer ID yazmaz; backend ID üretir ve mobilde gösterir.
4. Giriş sonrası sohbet ekranı açılır.
5. Sağ üstteki ikon ile Teklifler ekranına geçilir.
6. Teklifler ekranında sadece oturumdaki müşterinin teklifleri görünür.
7. Yeni teklif oluşturulabilir; backend quote ID üretir ve yeni teklif otomatik seçilir.
8. Mobildeki `[-] [quantity] [+]` kontrolleri web ile aynı backend quantity endpointini kullanır.

Web ve mobil aynı `customer_id` + `quote_id` ile aynı kalıcı quote state’ini okur.

## Retrieval Yaklaşımı

Bu teslimde embedding, vector index veya genel amaçlı semantik arama yerine deterministic SQL/JSON retrieval tercih edildi.

Nedenleri:

- Dataset küçük ve yapılandırılmıştır.
- Ürünlerde fiyat, stok, kategori ve tag gibi kesin filtreler gerekir.
- Politika cevaplarında kaynak gösterimi zorunludur.
- Golden senaryolarda tekrarlanabilir sonuç beklenir.
- Fiyat/stok gibi konularda LLM tahmini yerine veri tabanı kayıtları kullanılmalıdır.

Ürün araması şu alanları dikkate alır:

- `name_tr`
- Türkçe aliaslar
- tags
- category
- brand
- notes
- price/stock filtreleri

Knowledge retrieval şu alanları kullanır:

- `topic`
- `title`
- `body`
- `source`
- `applies_to`

Politika cevaplarında kaynak olarak en az bir `knowledge_id` döner. Ürün cevaplarında ilgili `product_id` kaynak olarak gösterilir.

## Tool Orchestration

Router Türkçe kullanıcı mesajını deterministic olarak sınıflandırır, gerekli tool fonksiyonlarını çalıştırır ve her tool çağrısını loglar.

Zorunlu tool fonksiyonları:

- `search_products`
- `get_knowledge_entries`
- `get_quote`
- `add_to_quote`
- `update_quote_item`
- `replace_with_alternative`

Normal user-facing mode:

- `require_confirmation=true`
- Ürün soruları mutasyon yapmaz.
- Ürün önerileri doğrudan teklif değiştirmez; önce onay ister.
- `ekle`, `sepete at`, `dahil et`, `alalım`, `teklifime yaz` gibi ifadeler de önce onay ister.
- `evet`, `tamam`, `onaylıyorum`, `ekle`, `olur`, `okey` gibi kısa onaylar pending action varsa uygular.
- Ürün/fiyat/özellik içeren “ekle” mesajları yeni add intent sayılır; kör şekilde pending confirmation sayılmaz.
- `kaldır`, `sil`, `çıkar`, `istemiyorum` gibi ifadeler remove intent olarak ele alınır.
- `3 adet yap`, `miktarı 4 yap`, `bir tane daha`, `azalt` gibi ifadeler quantity update intent olarak ele alınır.
- `daha ucuz alternatif`, `bu pahalı`, `muadili var mı`, `bunun yerine` gibi ifadeler replace intent olarak ele alınır.
- Belirsiz mesajlarda netleştirme sorusu sorulur.

Fiyat parsing örnekleri:

- `1000 TL`
- `1.000 TL`
- `9 bin TL`
- `9k`
- `9000 altı`
- `9000’e kadar`
- `bütçe 9000`

Yaygın typo/normalization örnekleri:

- `barkot okucu`
- `scaner`
- `yazici`
- `sarj`
- `kilif`
- `adaptor`
- `degistir`
- `kaldir`
- `cikar`

Contract/golden mode:

- `require_confirmation=false`
- Golden senaryolarda beklenen doğrudan tool-call ve mutation davranışları korunur.

## Fallback Mode

`LLM_ENABLED=false`, `OPENAI_API_KEY` yok veya LLM çağrısı başarısızsa sistem deterministic router ile çalışmaya devam eder.

Garanti edilen davranışlar:

- fiyat/stok/kaynak uydurulmaz
- politika cevabı kaynak olmadan verilmez
- ürün cevabı ürün verisi olmadan verilmez
- normal user-facing mode’da onaysız teklif mutasyonu yapılmaz
- belirsiz isteklerde netleştirme sorulur
- güvenli olmayan aksiyonlarda controlled error veya güvenli fallback cevabı döner
- tool-call logları yazılmaya devam eder

## Müşteri ve Teklif Kapsamı

- Kullanıcı önce müşteri ID ile giriş yapar.
- Web ve mobil sadece giriş yapılan müşterinin tekliflerini listeler.
- Yeni müşteri kaydı oluşturulabilir; backend `CUST-NEW-###` formatında otomatik ID üretir.
- Yeni müşteri oluşturulunca ID kullanıcıya gösterilir.
- Giriş yapılan müşteri için yeni draft teklif oluşturulabilir; backend `Q-NEW-###` formatında otomatik ID üretir.
- Chat ve quantity mutation istekleri `customer_id` + `quote_id` ile gider.
- Backend, quote ile customer eşleşmezse chat ve quantity mutation işlemlerini engeller.
- Müşteri değişince eski `quote_id` temizlenir.
- Web ve mobil aynı customer/quote akışını ve aynı backend state’ini kullanır.
- Müşteri teklif ekranlarında `inactive`, `removed` veya `replaced` kalemler aktif ürün gibi gösterilmez.

## Teklif Mutasyon Modeli

Teklif taslağı üzerinde mutasyon, chat cevabı üretmekten farklıdır. Mutasyon yapıldığında PostgreSQL’deki quote state gerçekten değişir.

- `add_to_quote`: Ürünü aktif teklif kalemi olarak ekler. Aynı ürün zaten aktifse ikinci satır açmaz, miktarı artırır.
- `update_quote_item`: Miktarı günceller. `quantity=0` için satırı fiziksel olarak silmez, `inactive` yapar.
- `replace_with_alternative`: Eski satırı `replaced` yapar, yeni ürünü aktif satır olarak ekler veya mevcut hedef satırın miktarını artırır.

Idempotency davranışı:

- Aynı `idempotency_key` replay edilir.
- Miktar ikinci kez artmaz.
- Add key’i `{message_id}:add:{product_id}` formatındadır.
- Replace key’i `{message_id}:replace:{from_product_id}:{to_product_id}` formatındadır.
- Retry aynı key ile gelirse kayıtlı sonuç döner ve `replayed=true` olarak işaretlenir.

Toplamlar ve indirimler `get_quote` sırasında güncel aktif satırlar üzerinden hesaplanır.

## Fiyatlandırma Kuralları

`price_rules.json` kuralları uygulanır:

- `RUL-PARTNER-3`: partner müşteri + aynı kategori miktarı >= 3 için %7 indirim
- `RUL-ACC-5`: aksesuar miktarı >= 5 için %5 indirim
- `RUL-BUNDLE-NO-STACK`: bundle ek indirim almaz
- `RUL-SVC-URGENT`: acil servis indirim almaz
- `RUL-SW-BUNDLE`: `PRD-SW-520` ve `PRD-SW-530` birlikteyse %8 indirim
- `RUL-PLUS-QTY`: PLUS SKU ve ürün miktarı >= 4 ise %6 indirim

Fiyat limiti otomatik öneri, ekleme ve değiştirme akışlarında kesin filtredir. Limitin üzerindeki ürün önerilmez ve teklife eklenmez.

Stok `0` ürünler varsayılan olarak önerilmez veya eklenmez. Yalnızca kullanıcı açıkça beklemeyi kabul ederse ve müşteri için stok bekleme izni varsa beklemeli kalem olarak ele alınabilir.

## Streaming Eventleri

SSE eventleri:

- `message_start`: `session_id`, `message_id`
- `tool_call_start`: tool adı, input, `sequence_no`
- `tool_call_result`: success/error, replay bilgisi, `quote_delta`
- `source`: `product_id` veya `knowledge_id`, müşteri-dostu `label`
- `text_delta`: Türkçe cevap parçaları
- `done` veya `controlled_error`

Retry durumunda aynı `message_id` aynı idempotency key’i üretir. Mutation ikinci kez uygulanmaz.

## Testler

Backend testleri:

```bash
python3 -m py_compile backend/app/*.py
.venv/bin/pytest backend/tests --basetemp=.pytest_tmp -p no:cacheprovider
```

Son doğrulama çıktısı:

```text
57 passed
```

Test kapsamı:

- golden senaryoların tool-call, source ve DB quote assertion kontrolü
- customer create/read, scoped quote listesi ve yeni draft quote API akışı
- quote/customer mismatch chat guard ve quantity mutation guard
- tool-call log DB/endpoints görünürlüğü
- Product Q&A mutasyonsuz cevapları
- Policy Q&A kaynaklı cevapları
- geniş chat intent parsing
- fiyat formatları ve typo toleransı
- belirsiz kısa mesaj ve confirmation/add ayrımı
- confirmation/pending action akışı
- fiyat limiti safety check
- stok dışı/backorder kuralları
- add/update/replace mutasyonları
- duplicate ve idempotency
- pricing rule hesapları
- fallback davranışı

## Demo Akışı

1. Sistemi başlat:

```bash
docker compose up --build
```

2. Web’i aç:

```text
http://127.0.0.1:5173
```

3. Müşteri girişi yap:

```text
CUST-ANK-002
```

4. `Q-1002` teklifini seç.

5. Ürün bilgisi sor:

```text
BlueScan Air fiyatı ne kadar ve stokta var mı?
```

Beklenen: fiyat, stok, garanti ve teslimat bilgisi; ürün eklenmez.

6. Politika sorusu sor:

```text
Aktive edilmiş yazılım lisansını iade edebilir miyiz?
```

Beklenen: kaynaklı politika cevabı; teklif değişmez.

7. Ürün önerisi iste:

```text
9 bin TL QR okuyucu
```

Beklenen: uygun ürün önerilir ve onay sorulur.

8. Onay ver:

```text
evet
```

Beklenen: ürün teklif taslağına gerçekten eklenir.

9. Fiyat limiti güvenliğini test et:

```text
1.000 TL altında stokta kablosuz QR okuyucu ekle
```

Beklenen: uygun ürün bulunamadığı söylenir ve teklif değişmez.

10. Webde yapılan değişiklik mobilde aynı quote seçildiğinde görünür.

## Güvenlik

`.env` commit edilmez. Repoda yalnızca `.env.example` bulunur. Demo PostgreSQL kullanıcı/parolası local development içindir; production secret olarak kullanılmaz.

Gizli değer kontrolü için:

```bash
git grep -n "sk-\|OPENAI_API_KEY=.*[A-Za-z0-9]\|private_key\|api_key\|secret\|token\|password"
git log --all -S "sk-" --source --all
git log --all -S "OPENAI_API_KEY" --source --all
```

## Trade-off ve Bilinen Sınırlamalar

Bu teslimde bilinçli olarak aşağıdaki trade-off’lar yapıldı:

- Embedding/vector index yerine deterministic SQL/JSON retrieval kullanıldı.
- Production auth/role management eklenmedi; müşteri ID tabanlı demo scope uygulandı.
- Admin/customer ayrımı production policy seviyesinde değil, demo UI seviyesinde tutuldu.
- Büyük ölçekli concurrency isolation testleri kapsam dışı bırakıldı.
- Genel amaçlı serbest asistan davranışı yerine case kapsamındaki ürün, politika ve teklif akışları önceliklendirildi.
- Gelişmiş semantik/fuzzy ranking yerine alias, tag, normalization ve deterministic filtreler kullanıldı.

Daha detaylı açıklamalar için bkz. [KNOWN_LIMITATIONS.md](./KNOWN_LIMITATIONS.md).
