# AI Usage

Bu projede AI desteği gereksinim çözümleme, uygulama planlama, boilerplate üretimi ve test taslaklarının hazırlanmasında kullanıldı.

Nihai iş kuralları, tool contract davranışları, fiyat/stok/idempotency kararları ve doğrulama kapsamı geliştirici kontrolünden geçirildi. Üretilen kod backend testleriyle doğrulandı.

Gizli değer, API anahtarı veya kişisel credential paylaşılmadı. `.env` dosyası commit dışı bırakıldı; yalnızca `.env.example` eklendi.

Doğrulama komutu:

```bash
.venv/bin/pytest backend/tests
```

