# Known Limitations

- PDF içeriği bu ortamda metne çevrilemedi. Kabul kriterleri `tool_contracts.json`, `golden_test_scenarios.json`, dataset README ve JSON seed dosyalarından çıkarıldı.
- Router golden niyetleri deterministik olarak yakalar; serbest doğal dil kapsamı sınırlı ama güvenli fallback davranışı vardır.
- PostgreSQL transaction davranışı uygulama kodunda SQLAlchemy session commit sınırında çalışır; daha yoğun eşzamanlılık için satır kilidi ve isolation testleri eklenmelidir.
- Web Docker image statik build sunar; geliştirme için `npm run dev` ayrıca kullanılabilir.
- Expo mobil app Docker Compose içine alınmadı; mobil geliştirme yerel `expo start` ile yapılır.
