# The Blue Red AI Quote Assistant

The Blue Red için kaynaklı, streaming çalışan teklif asistanı. Kullanıcı Türkçe chat üzerinden ürün, politika, stok, fiyat, uyumluluk ve teklif soruları sorar; backend gerekli tool fonksiyonlarını deterministic olarak çalıştırır ve aynı kalıcı teklif taslağını web ile mobilde gösterir.

## Tech Stack

- Backend: FastAPI, SQLAlchemy, PostgreSQL
- Web: React + Vite
- Mobile: React Native / Expo
- Runtime: Docker Compose
- Tests: pytest
- Streaming: SSE

## Architecture

Backend tek doğruluk kaynağıdır. Web ve mobil `GET /quotes/{quote_id}` endpointinden aynı DB state’ini okur. Chat istekleri `POST /chat/stream` ile SSE olarak akar; her tool çağrısı `tool_call_logs` tablosuna yazılır. Normal web/mobil chat deneyiminde teklif mutasyonları önce onay ister; golden/contract test modunda `require_confirmation=false` ile doğrudan tool contract davranışı doğrulanır.

```text
React Web ─┐
           ├── FastAPI ── PostgreSQL
Expo App ──┘      │
                  └── deterministic router + quote tools + SSE
```

Ana sistem güvenli deterministic fallback ile çalışır. `LLM_ENABLED=false` varsayılandır. `LLM_ENABLED=true` ve `OPENAI_API_KEY` verildiğinde LLM doğal Türkçe response writer/intent helper olarak kullanılabilir; ürün, fiyat, stok, kaynak ve mutasyon kararları backend safety layer’dan geçer.

## Setup

```bash
cp .env.example .env
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
```

Temel env değerleri:

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

## Docker Compose

```bash
docker compose up --build
```

- Backend: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`
- Web: `http://127.0.0.1:5173`

Compose servisleri: `postgres`, `backend`, `web`. Backend startup sırasında JSON seed dosyalarını yükler.

Seed’i manuel sıfırlamak için:

```bash
curl -X POST http://127.0.0.1:8000/seed/reset
```

## Backend Endpoints

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
- `GET /tool-call-logs`
- `GET /sessions/{session_id}/tool-calls`
- `POST /chat/stream`
- `GET /chat/stream`
- `POST /seed/reset`
- `POST /quotes/{quote_id}/items/{product_id}/quantity`

## Web

```bash
cd web
npm install
npm run dev
```

Web uygulaması gerçek backend API’ye bağlıdır. İlk ekranda yalnızca müşteri girişi vardır; “Yeni müşteri kaydı” ayrı kayıt ekranını açar. Kayıtta kullanıcı ID yazmaz, backend `CUST-NEW-###` formatında çakışmayan müşteri ID üretir ve oluşturulan ID kullanıcıya gösterilir. Girişten sonra teklif dropdown’u sadece oturumdaki müşteriye ait teklifleri gösterir; seçili müşteri için backend tarafından `Q-NEW-###` formatında yeni draft teklif oluşturulabilir. Sol menü:

- Sohbet: ChatGPT benzeri kullanıcı/asistan balonları, streaming cevap, sade kaynak listesi
- Teklifler: kalıcı draft state, yalnızca aktif teklif kalemleri, satır toplamları ve `[-] [quantity] [+]` kontrolleri
- Ürün listeleme, ekleme ve düzenleme
- Knowledge listeleme, ekleme ve düzenleme

Müşteri arayüzünde Loglar sekmesi yoktur. Raw tool event ve JSON debug bilgileri müşteri sohbetine karışmaz; `tool_call_logs` tablosu ile `/tool-call-logs` ve `/sessions/{session_id}/tool-calls` endpointleri backend/debug kullanımı için korunur.

## Mobile

```bash
cd mobile
npm install
EXPO_PUBLIC_API_URL=http://BILGISAYARIN_LAN_IP_ADRESI:8000 npm run start
```

Expo Go fiziksel telefonda çalışırken `127.0.0.1` telefonun kendisini gösterir; bu yüzden `EXPO_PUBLIC_API_URL` bilgisayarın aynı Wi-Fi ağındaki LAN IP adresi olmalıdır. Expo uygulaması backend’e bağlanır. İlk ekranda müşteri ID ile giriş yapılır veya ayrı “Yeni müşteri kaydı” ekranından kayıt oluşturulur; kullanıcı customer ID yazmaz, backend ID üretir ve mobil bunu gösterir. Girişten sonra sadece oturumdaki müşterinin teklifleri seçilebilir. Seçili müşteri için yeni draft teklif oluşturulabilir; kullanıcı quote ID yazmaz, backend ID üretir. Chat mesajı seçili `customer_id` + `quote_id` ile gönderilir, stream cevabı chat balonunda birikir, sade kaynaklar gösterilir ve aynı quote state’i okunur. Mobil teklif ekranında web ile aynı quantity endpoint’i üzerinden `[-] [quantity] [+]` kontrolleri çalışır.

## Retrieval

İlk teslim için embedding yerine SQL/JSON alanları üzerinde deterministic retrieval kullanıldı. Ürün araması şu alanları dikkate alır:

- `name_tr`
- Türkçe aliaslar
- tags
- category
- brand
- notes
- price/stock filtreleri

Knowledge retrieval `topic`, `title`, `body`, `source` ve `applies_to` alanlarını kullanır. Politika cevaplarında en az bir `knowledge_id` kaynak olarak döner.

## Tool Orchestration

Router LLM tool-calling’e bağımlı değildir. Türkçe niyetleri deterministic olarak sınıflandırır, gerekli tool sırasını çalıştırır ve her çağrıyı loglar. Product Q&A mesajları mutasyonsuz cevaplanır; fiyat, stok, QR desteği, garanti ve teslimat soruları `products.json` ve gerekirse `knowledge_entries.json` kaynaklarından yanıtlanır.

Zorunlu tool fonksiyonları:

- `search_products`
- `get_knowledge_entries`
- `get_quote`
- `add_to_quote`
- `update_quote_item`
- `replace_with_alternative`

Fiyat limiti otomatik ekleme/değiştirmede kesin filtredir. Stok `0` ürünler kullanıcı açıkça beklemeyi kabul etmeden ve müşteri `allow_backorder=true` olmadan eklenmez.

Normal user-facing mode:

- `require_confirmation=true`
- Ürün önerisi veya “ekle” talebi önce ürün özeti ve onay sorusu üretir.
- Onay kelimeleri: `evet`, `tamam`, `onaylıyorum`, `ekle`, `uygula`, `olur`.
- İptal kelimeleri: `hayır`, `iptal`, `vazgeç`, `ekleme`, `istemiyorum`.
- Pending action DB’de `pending_actions` tablosunda tutulur.

Contract/golden mode:

- `require_confirmation=false`
- Golden senaryolardaki doğrudan tool-call/mutation beklentileri korunur.

## Customer And Quote Scope

- Kullanıcı önce müşteri olarak giriş yapar.
- Web ve mobil sadece giriş yapılan müşterinin tekliflerini listeler.
- Yeni müşteri kaydı oluşturulabilir; backend `CUST-NEW-###` formatında otomatik ID üretir, oluşturulan müşteriyle otomatik giriş yapılır ve ID kullanıcıya gösterilir.
- Giriş yapılan müşteri için yeni draft teklif oluşturulabilir; backend `Q-NEW-###` formatında otomatik ID üretir ve yeni teklif otomatik seçilir.
- Chat ve quantity mutation istekleri `customer_id` + `quote_id` ile gider.
- Backend, quote ile customer eşleşmezse chat ve quantity mutation işlemlerini controlled error/403 ile engeller.
- Müşteri değişince eski `quote_id` temizlenir.
- Web ve mobil aynı customer/quote akışını ve aynı backend state’ini kullanır.
- Müşteri teklif ekranlarında `inactive`, `removed` veya `replaced` kalemler aktif ürün gibi gösterilmez; audit/status bilgisi backend state ve loglarda korunur.

## Quote Mutation Model

- `add_to_quote`: Aynı ürün aktifse ikinci satır açmaz, miktarı artırır.
- `update_quote_item`: `quantity=0` için satırı silmez, `inactive` yapar.
- `replace_with_alternative`: Eski satırı `replaced` yapar, yeni ürünü aktif satır olarak ekler veya mevcut hedef satırın miktarını artırır.
- Idempotency: Aynı `idempotency_key` replay edilir; miktar ikinci kez artmaz.

Toplamlar ve indirimler `get_quote` sırasında güncel aktif satırlar üzerinden hesaplanır.

## Pricing

`price_rules.json` kuralları uygulanır:

- `RUL-PARTNER-3`: partner müşteri + kategori miktarı >= 3 için %7
- `RUL-ACC-5`: aksesuar miktarı >= 5 için %5
- `RUL-BUNDLE-NO-STACK`: bundle ek indirim almaz
- `RUL-SVC-URGENT`: acil servis indirim almaz
- `RUL-SW-BUNDLE`: `PRD-SW-520` ve `PRD-SW-530` birlikteyse %8
- `RUL-PLUS-QTY`: PLUS SKU ve ürün miktarı >= 4 ise %6

## Streaming Events

SSE eventleri:

- `message_start`: `session_id`, `message_id`
- `tool_call_start`: tool adı, input, `sequence_no`
- `tool_call_result`: success/error, replay bilgisi, `quote_delta`
- `source`: `product_id` veya `knowledge_id` ve müşteri-dostu `label`
- `text_delta`: Türkçe cevap parçaları
- `done` veya `controlled_error`

Retry durumunda aynı `message_id` aynı idempotency key’i üretir; mutation ikinci kez uygulanmaz.

## Tests

```bash
.venv/bin/pytest backend/tests --basetemp=/Users/bakitoplu/Desktop/case/.pytest_tmp -p no:cacheprovider
```

Son test çıktısı:

```text
collected 49 items
backend/tests/test_customer_quote_api.py ...
backend/tests/test_golden_scenarios_full.py ......................
backend/tests/test_orchestrator.py ....
backend/tests/test_pricing_rules.py ......
backend/tests/test_tools.py .....
backend/tests/test_user_facing_chat.py .........
49 passed
```

Test kapsamı:

- 22 golden senaryonun tool call, source ve DB quote assertion kontrolü
- Customer create/list/read, scoped quote listesi ve yeni draft quote API akışı
- Quote/customer mismatch chat guard ve quantity mutation guard
- Tool-call log DB/endpoints görünürlüğünün korunması
- Product Q&A mutasyonsuz cevapları
- Confirmation/pending action akışı
- Fiyat limiti safety check
- Backorder kuralları
- Retrieval ve grounding
- Add/update/replace mutasyonları
- Duplicate ve idempotency
- Fiyat/stok kuralları
- Fallback kaynaklı cevap
- Pricing rule hesapları

## Demo Flow

1. `docker compose up --build`
2. Web’i aç: `http://127.0.0.1:5173`
3. `Q-1002` seç.
4. Chat’e şu mesajı gönder:

```text
9.000 TL altında, stokta olan kablosuz QR barkod okuyucu ekler misin?
```

5. Normal user mode’da asistan uygun ürünü önerir ve onay ister.
6. “Evet ekle” mesajından sonra `PRD-BC-110` aktif satır olarak eklenir.
7. Mobilde aynı `quote_id` açıldığında aynı kalıcı teklif durumu okunur.

## Security

`.env` commit edilmez. Sadece `.env.example` repoda bulunur. Demo PostgreSQL kullanıcı/parolası local development içindir; production için secret manager veya deployment-level env kullanılmalıdır.

## Known Limitations

Bkz. [KNOWN_LIMITATIONS.md](./KNOWN_LIMITATIONS.md).
