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

Backend tek doğruluk kaynağıdır. Web ve mobil `GET /quotes/{quote_id}` endpointinden aynı DB state’ini okur. Chat istekleri `POST /chat/stream` ile SSE olarak akar; her tool çağrısı `tool_call_logs` tablosuna yazılır.

```text
React Web ─┐
           ├── FastAPI ── PostgreSQL
Expo App ──┘      │
                  └── deterministic router + quote tools + SSE
```

Ana sistem LLM’siz deterministic çalışır. `LLM_ENABLED=false` varsayılandır. LLM ileride yalnızca cevap metnini zenginleştiren opsiyonel bir response writer olarak eklenebilir; fiyat, stok, idempotency ve mutasyon kararları backend kurallarıyla verilir.

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
- `GET /quotes/{quote_id}`
- `GET /tool-call-logs`
- `GET /sessions/{session_id}/tool-calls`
- `POST /chat/stream`
- `GET /chat/stream`
- `POST /seed/reset`

## Web

```bash
cd web
npm install
npm run dev
```

Web admin paneli gerçek backend API’ye bağlıdır:

- Ürün listeleme, ekleme ve düzenleme
- Knowledge listeleme, ekleme ve düzenleme
- Teklif görüntüleme
- Chat test ekranı
- SSE event görünümü
- Kalıcı tool-call log viewer

## Mobile

```bash
cd mobile
npm install
npm run start
```

Expo uygulaması backend’e bağlanır, chat mesajı gönderir, stream cevabını ve kaynakları gösterir, aynı quote state’ini okur.

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

Router LLM tool-calling’e bağımlı değildir. Türkçe niyetleri deterministic olarak sınıflandırır, gerekli tool sırasını çalıştırır ve her çağrıyı loglar.

Zorunlu tool fonksiyonları:

- `search_products`
- `get_knowledge_entries`
- `get_quote`
- `add_to_quote`
- `update_quote_item`
- `replace_with_alternative`

Fiyat limiti otomatik ekleme/değiştirmede kesin filtredir. Stok `0` ürünler kullanıcı açıkça beklemeyi kabul etmeden ve müşteri `allow_backorder=true` olmadan eklenmez.

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
- `source`: `product_id` veya `knowledge_id`
- `text_delta`: Türkçe cevap parçaları
- `done` veya `controlled_error`

Retry durumunda aynı `message_id` aynı idempotency key’i üretir; mutation ikinci kez uygulanmaz.

## Tests

```bash
.venv/bin/pytest backend/tests
```

Son test çıktısı:

```text
collected 37 items
backend/tests/test_golden_scenarios_full.py ......................
backend/tests/test_orchestrator.py ....
backend/tests/test_pricing_rules.py ......
backend/tests/test_tools.py .....
37 passed
```

Test kapsamı:

- 22 golden senaryonun tool call, source ve DB quote assertion kontrolü
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

5. `PRD-BC-110` aktif satır olarak eklenir, SSE tool eventleri akar ve tool-call logları web panelde görünür.
6. Mobilde aynı `quote_id` açıldığında aynı kalıcı teklif durumu okunur.

## Security

`.env` commit edilmez. Sadece `.env.example` repoda bulunur. Demo PostgreSQL kullanıcı/parolası local development içindir; production için secret manager veya deployment-level env kullanılmalıdır.

## Known Limitations

Bkz. [KNOWN_LIMITATIONS.md](./KNOWN_LIMITATIONS.md).
