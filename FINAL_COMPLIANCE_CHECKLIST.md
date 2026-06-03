# Final Compliance Checklist

## Core Delivery

- OK: FastAPI backend mevcut.
- OK: PostgreSQL Docker Compose servisi ve SQLAlchemy veri modeli mevcut.
- OK: React web panel gerçek backend API’ye bağlı.
- OK: React Native / Expo mobil uygulama gerçek backend API’ye bağlı.
- OK: Docker Compose `postgres`, `backend`, `web` servislerini tanımlar.
- OK: `.env.example` mevcut; `.env` gitignore’da.
- OK: JSON seed startup sırasında otomatik yüklenir; `/seed/reset` endpointi vardır.
- OK: SSE chat stream endpointi vardır.
- OK: Quote read endpointi vardır.
- OK: Product CRUD/list endpointleri vardır.
- OK: Knowledge CRUD/list endpointleri vardır.
- OK: Tool-call logları DB’de tutulur ve endpoint/web log viewer ile görülebilir.
- OK: LLM kapalıyken kaynaklı cevap ve deterministic tool orchestration çalışır.
- OK: Web ve mobil aynı quote endpointini kullanır.
- OK: Mutasyon tool’ları gerçek DB state’ini değiştirir.
- OK: Backend testleri gerçek davranışı doğrular.
- OK: README, AI_USAGE ve KNOWN_LIMITATIONS mevcut.
- OK: Gizli değer commit edilmedi.

## Tool Contracts

- OK: `search_products` query/locale/filter/limit yapısını destekler; alias/tag/category/price/stock filtrelerini uygular ve match evidence döner.
- OK: `get_knowledge_entries` topic/locale/query/limit ile kaynak döner; politika cevapları `knowledge_id` kaynaklıdır.
- OK: `get_quote` ortak kalıcı teklif state’ini, satır toplamlarını, durumları, indirimleri ve genel toplamı döner.
- OK: `add_to_quote` DB mutasyonu yapar, aktif satırı birleştirir, idempotency replay’i korur ve stok/backorder kuralını uygular.
- OK: `update_quote_item` miktar günceller; `quantity=0` için `inactive` durumunu kullanır.
- OK: `replace_with_alternative` eski satırı `replaced` yapar, yeni stoklu/fiyat uygun ürünü aktif ekler ve idempotency uygular.

## Golden Scenario Coverage

- OK: 22/22 golden senaryo parametrik test ile doğrulanır.
- OK: Expected tool calls ve must_match alanları kontrol edilir.
- OK: must_not_call ve must_not_recommend alanları kontrol edilir.
- OK: expected_sources kontrol edilir.
- OK: quote assertions gerçek DB state’i üzerinden doğrulanır.
- OK: Streaming retry/idempotency tekrar miktar artırmaz.

## Pricing

- OK: `RUL-PARTNER-3` test edildi.
- OK: `RUL-ACC-5` test edildi.
- OK: `RUL-BUNDLE-NO-STACK` test edildi.
- OK: `RUL-SVC-URGENT` test edildi.
- OK: `RUL-SW-BUNDLE` test edildi.
- OK: `RUL-PLUS-QTY` test edildi.

## Verification

- OK: `.venv/bin/pytest backend/tests` -> 37 passed.
- OK: `python3 -m py_compile backend/app/*.py`.
- OK: `docker compose config`.
- NEEDS ATTENTION: `docker compose up --build -d` requires a running local Docker daemon; the daemon socket was not available in this environment.
- NEEDS ATTENTION: `npm install` for web/mobile did not complete in this environment; package files and run scripts are present for standard Node environments.
