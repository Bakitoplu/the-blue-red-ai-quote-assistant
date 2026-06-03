# Known Limitations

- Retrieval embedding tabanlı değildir; case kapsamı için SQL/alias/tag/category tabanlı deterministic retrieval kullanır.
- Auth, role management ve production-grade audit policy demo kapsamı dışındadır.
- LLM opsiyoneldir ve varsayılan kapalıdır; ana karar mekanizması deterministic router’dır.
- Mobil UI demo seviyesindedir ancak gerçek backend quote ve chat endpointlerine bağlıdır.
- Deterministic router case kapsamındaki satış/teklif niyetlerini hedefler; serbest genel amaçlı asistan davranışı kapsam dışıdır.
- Yoğun eşzamanlı mutation yükleri için ek isolation/locking testleri production öncesi genişletilmelidir.
