# The Blue Red AI Quote Assistant

FastAPI + PostgreSQL tabanlı kaynaklı teklif asistanı. React web admin ve Expo mobil istemci aynı `quote_id` için aynı kalıcı veritabanı durumunu okur.

## Kapsam

- Backend: FastAPI, SQLAlchemy, PostgreSQL, SSE streaming chat.
- Veritabanı: ürünler, bilgi kayıtları, müşteriler, teklifler, teklif kalemleri, fiyat kuralları, tool logları, chat session/message ve idempotency tablosu.
- Tool sözleşmeleri: `search_products`, `get_knowledge_entries`, `get_quote`, `add_to_quote`, `update_quote_item`, `replace_with_alternative`.
- Fallback: `OPENAI_API_KEY` boşsa güvenli Türkçe kaynaklı cevap üretir ve emin olunmayan mutasyon yapmaz.
- Web: quote state, chat, SSE tool event görünümü.
- Mobil: Expo chat ve quote ekranı.

## Docker ile çalıştırma

```bash
cp .env.example .env
docker compose up --build
```

- Backend: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`
- Web: `http://127.0.0.1:5173`

Seed işlemi backend startup sırasında `the_blue_red_candidate_case_dataset/*.json` dosyalarından otomatik yapılır. Manuel reset:

```bash
curl -X POST http://127.0.0.1:8000/seed/reset
```

## Lokal backend testi

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt
.venv/bin/pytest backend/tests
```

Testler SQLite üzerinde aynı SQLAlchemy modellerini ve JSON seed loader’ı kullanır. Uygulama Docker’da PostgreSQL’e bağlanır.

## API uçları

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

## Tool davranışı

`add_to_quote` aynı ürün için ikinci aktif satır açmaz, mevcut aktif satırın miktarını artırır. Aynı `idempotency_key` tekrar geldiğinde sonuç replay edilir ve miktar ikinci kez artmaz.

`update_quote_item` için `quantity = 0` silme yapmaz; kalemi `inactive` durumuna alır. Böylece web/mobil geçmiş satırı görürken toplamlar yalnızca aktif kalemlerden hesaplanır.

`replace_with_alternative` eski kalemi `replaced` yapar, yeni ürünü aktif satır olarak ekler veya mevcut aktif hedef satır varsa miktarı artırır. Eski miktar korunur.

Fiyat üst limiti otomatik ürün ekleme/değiştirmede kesin filtredir. Stok miktarı `0` olan ürün, kullanıcı açıkça beklemeyi kabul etmeden ve müşteri `allow_backorder=true` olmadan eklenmez.

## Bilinen sınırlamalar

- PDF metni lokal ortamda `pdftotext`/PDF Python kütüphanesi olmadığı için otomatik çıkarılamadı; implementasyon `tool_contracts.json`, `golden_test_scenarios.json` ve dataset dosyaları esas alınarak yapıldı.
- Router deterministic/hybrid yapıdadır; LLM entegrasyonu yalnızca ileride cevap metni zenginleştirme katmanı olarak eklenebilir.
- Test kapsamı kritik tool/idempotency/fallback senaryolarını kapsar; 22 golden senaryonun tamamı için ayrı assertion matrisi genişletilebilir.
- Mobil SSE okuması Expo ortam uyumluluğu için response text parse eder; web gerçek stream reader kullanır.

