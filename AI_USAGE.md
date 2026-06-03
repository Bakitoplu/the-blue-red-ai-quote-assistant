# AI Usage

Bu proje Codex ile geliştirilmiştir.

Kullanılan AI desteği:

- Case promptu, `tool_contracts.json`, `golden_test_scenarios.json` ve dataset dosyaları karşılaştırıldı.
- Backend model, seed loader, tool fonksiyonları, deterministic chat router ve SSE event akışı üretildi.
- Kritik iş kuralları için pytest testleri yazıldı.
- React web admin ve Expo mobil istemci iskeleti üretildi.
- README, Docker Compose ve bilinen sınırlamalar dokümante edildi.

AI tarafından üretilen kod lokal testlerle doğrulandı:

```bash
.venv/bin/pytest backend/tests
```

Gizli değer kullanılmadı; `.env` commit dışı bırakıldı, `.env.example` eklendi.

