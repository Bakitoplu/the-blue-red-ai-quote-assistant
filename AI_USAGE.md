# AI Usage

Bu projede AI desteği gereksinim çözümleme, uygulama planlama, boilerplate üretimi, dokümantasyon ve test taslaklarının hazırlanmasında kullanıldı.

Nihai iş kuralları, tool contract davranışları, fiyat/stok/idempotency kararları, Product Q&A sınırları, pending action akışı ve doğrulama kapsamı geliştirici kontrolünden geçirildi. Üretilen kod backend testleriyle doğrulandı.

Runtime’da `LLM_ENABLED=false` varsayılandır. `LLM_ENABLED=true` ve `OPENAI_API_KEY` verildiğinde LLM yalnızca doğal Türkçe cevap yazımı/intent yardımcısı olarak kullanılabilir; fiyat, stok, ürün seçimi, teklif mutasyonu ve kaynak kararları backend safety layer tarafından belirlenir. LLM çağrısı başarısız olursa deterministic fallback cevap çalışmaya devam eder.

Gizli değer, API anahtarı veya kişisel credential paylaşılmadı. `.env` dosyası commit dışı bırakıldı; yalnızca `.env.example` eklendi.

Doğrulama komutu:

```bash
.venv/bin/pytest backend/tests --basetemp=/Users/bakitoplu/Desktop/case/.pytest_tmp -p no:cacheprovider
```
