# AI Usage

Bu projede AI desteği gereksinim çözümleme, uygulama planlama, boilerplate üretimi, dokümantasyon ve test taslaklarının hazırlanmasında kullanıldı.

Nihai iş kuralları, tool contract davranışları, fiyat/stok/idempotency kararları, Product Q&A sınırları, pending action akışı ve doğrulama kapsamı geliştirici kontrolünden geçirildi. Üretilen kod backend testleriyle doğrulandı.

Runtime’da `LLM_ENABLED=false` varsayılandır. `LLM_ENABLED=true` ve `OPENAI_API_KEY` verildiğinde LLM yalnızca doğal Türkçe cevap yazımı/intent yardımcısı olarak kullanılabilir; fiyat, stok, ürün seçimi, teklif mutasyonu ve kaynak kararları backend safety layer tarafından belirlenir. LLM çağrısı başarısız olursa deterministic fallback cevap çalışmaya devam eder.

Gizli değer, API anahtarı veya kişisel credential paylaşılmadı. `.env` dosyası commit dışı bırakıldı; yalnızca `.env.example` eklendi.

Doğrulama komutu:

```bash
.venv/bin/pytest backend/tests --basetemp=/Users/bakitoplu/Desktop/case/.pytest_tmp -p no:cacheprovider
```

## 1. Geliştirme sürecinde AI kullanımı

Bu projeyi geliştirirken AI araçlarını aktif şekilde kullandım. Kodun önemli bir bölümünde AI’dan kod taslağı, dosya düzeni, fonksiyon önerisi, test senaryosu ve dokümantasyon desteği aldım.

Bu kullanımda benim rolüm yalnızca kodu kopyalamak olmadı. Daha çok ürün gereksinimlerini yorumlayan, karar veren, hataları yakalayan, test eden ve çıktıları düzelttiren geliştirici rolünde ilerledim.

AI desteği aldığım başlıca alanlar şunlardır:

- case dokümanındaki beklentileri parçalara ayırmak
- backend, web ve mobil tarafındaki işleri sıraya koymak
- FastAPI endpointleri, SQLAlchemy modelleri ve tool fonksiyonları için kod taslakları üretmek
- React web arayüzü ve Expo mobil arayüzü için UI/UX kod taslakları üretmek
- Docker, README ve kurulum dokümantasyonu için metin ve yapı önerileri almak
- tool-call senaryolarını kontrol listesine çevirmek
- fiyat, stok, idempotency, kaynak gösterimi ve müşteri bazlı teklif erişimi gibi edge-case’leri düşünmek
- test senaryoları ve golden scenario kapsamı için taslaklar üretmek
- manuel doğrulama adımlarını listelemek
- olası diskalifiye risklerini kontrol listesine çevirmek

AI özellikle kod üretiminde yardımcı oldu; ancak hangi davranışın doğru olduğuna, hangi cevabın müşteri açısından anlamlı olduğuna, hangi akışın case dokümanıyla uyumlu olduğuna ve hangi hataların düzeltilmesi gerektiğine manuel kontrolle karar verdim.

## Neden AI kullandım?

...

## AI kullanımının sınırı

AI bu projede yoğun şekilde yardımcı geliştirme aracı olarak kullanıldı. Kod taslaklarının önemli bir kısmı AI yardımıyla üretildi veya düzenlendi. Buna rağmen AI çıktıları tek başına doğru kabul edilmedi.

Benim odaklandığım kısım; gereksinimleri yorumlamak, iş kurallarına karar vermek, hatalı veya eksik davranışları yakalamak, testleri çalıştırmak, manuel senaryolarla doğrulamak ve AI’nın ürettiği çıktıları case beklentisine göre tekrar düzenletmek oldu.

Özellikle aşağıdaki kararlar ve kontroller geliştirici kontrolünde tutuldu:

- fiyat ve stok kuralının ihlal edilmemesi
- politika cevaplarının kaynaklı olması
- teklif mutasyonlarının mock değil gerçek veri tabanı değişikliği yapması
- web ve mobilin aynı teklif durumunu göstermesi
- müşteri arayüzünde raw debug/tool loglarının görünmemesi
- gizli değerlerin commit edilmemesi
- testlerin ve manuel doğrulama adımlarının geçmesi

Bu nedenle AI kullanımı projede geliştirmeyi hızlandıran bir araç olarak kullanıldı; final davranışlar test, manuel kontrol ve geliştirici kararıyla doğrulandı.

## Gizli değerler

...

# AI Usage

Bu dosya, bu projeyi geliştirirken yapay zekâ araçlarını nerelerde, neden ve hangi sınırlarla kullandığımı açıklamak için hazırlanmıştır.

## 1. Nerelerde AI kullandım?

Bu projeyi geliştirirken AI araçlarını aktif şekilde kullandım. Kodun önemli bir bölümünde AI’dan kod taslağı, dosya düzeni, fonksiyon önerisi, test senaryosu ve dokümantasyon desteği aldım.

AI desteği aldığım başlıca alanlar şunlardır:

- case dokümanındaki beklentileri parçalara ayırmak
- backend, web ve mobil tarafındaki işleri sıraya koymak
- FastAPI endpointleri, SQLAlchemy modelleri ve tool fonksiyonları için kod taslakları üretmek
- React web arayüzü ve Expo mobil arayüzü için UI/UX kod taslakları üretmek
- Docker, README ve kurulum dokümantasyonu için metin ve yapı önerileri almak
- tool-call senaryolarını kontrol listesine çevirmek
- fiyat, stok, idempotency, kaynak gösterimi ve müşteri bazlı teklif erişimi gibi edge-case’leri düşünmek
- test senaryoları ve golden scenario kapsamı için taslaklar üretmek
- manuel doğrulama adımlarını listelemek
- olası diskalifiye risklerini kontrol listesine çevirmek

## 2. Neden AI kullandım?

Case kapsamı backend, web, mobil, Docker, testler, kaynaklı cevap üretimi, tool-call logları ve müşteri bazlı teklif akışı gibi birden fazla parçadan oluşuyordu. AI’yı bu parçaları daha düzenli takip etmek, geliştirme sürecini hızlandırmak ve eksik kalabilecek noktaları erken fark etmek için kullandım.

Özellikle şu konularda AI kullanımı faydalı oldu:

- case maddelerini yapılabilir görevlere bölmek
- aynı anda birden fazla platformu takip ederken kontrol listesi oluşturmak
- farklı kullanıcı cümleleri için edge-case düşünmek
- test kapsamını genişletmek
- teslim öncesi rubrik ve diskalifiye maddelerini tek tek kontrol etmek
- dokümantasyon dilini daha anlaşılır hale getirmek

## 3. Benim rolüm neydi?

AI özellikle kod üretiminde yardımcı oldu; ancak bu projede benim rolüm yalnızca kodu kopyalamak olmadı. Daha çok ürün gereksinimlerini yorumlayan, karar veren, hataları yakalayan, test eden ve AI çıktısını düzelttiren geliştirici rolünde ilerledim.

AI’dan gelen önerilerden sonra şu kontrolleri manuel olarak yaptım:

- iş kuralı case dokümanıyla uyumlu mu?
- müşteri cevabı doğal ve anlaşılır mı?
- kaynak gösterimi doğru mu?
- fiyat ve stok kuralları ihlal ediliyor mu?
- teklif mutasyonu gerçekten veri tabanına yazılıyor mu?
- web ve mobil aynı teklif durumunu gösteriyor mu?
- testler geçiyor mu?
- gizli değer veya kişisel credential commit edilmiş mi?

## 4. AI kullanımının sınırı

AI bu projede yoğun şekilde yardımcı geliştirme aracı olarak kullanıldı. Kod taslaklarının önemli bir kısmı AI yardımıyla üretildi veya düzenlendi. Buna rağmen AI çıktıları tek başına doğru kabul edilmedi.

Aşağıdaki kararlar ve kontroller geliştirici kontrolünde tutuldu:

- fiyat ve stok kuralının ihlal edilmemesi
- politika cevaplarının kaynaklı olması
- ürün cevaplarının ürün verisine dayanması
- teklif mutasyonlarının mock değil gerçek veri tabanı değişikliği yapması
- idempotency/retry davranışının korunması
- müşteri bazlı teklif erişiminin korunması
- web ve mobilin aynı teklif durumunu göstermesi
- müşteri arayüzünde raw debug/tool loglarının görünmemesi
- gizli değerlerin commit edilmemesi
- testlerin ve manuel doğrulama adımlarının geçmesi

Bu nedenle AI kullanımı projede geliştirmeyi hızlandıran bir araç olarak kullanıldı; final davranışlar test, manuel kontrol ve geliştirici kararıyla doğrulandı.

## 5. Gizli değerler

AI araçlarıyla gerçek API anahtarı, token, private key veya kişisel credential paylaşılmadı. `.env` dosyası repoya eklenmedi. Repoda yalnızca örnek yapılandırma için `.env.example` tutuldu.

Demo PostgreSQL kullanıcı/parolası local development içindir. Gerçek production secret olarak kullanılmaz.

## 6. Doğrulama

Backend testleri için kullanılan komut:

```bash
.venv/bin/pytest backend/tests --basetemp=.pytest_tmp -p no:cacheprovider
```

Python syntax kontrolü için kullanılan komut:

```bash
python3 -m py_compile backend/app/*.py
```

Gizli değer kontrolü için kullanılan temel komutlar:

```bash
git grep -n "sk-\|OPENAI_API_KEY=.*[A-Za-z0-9]\|private_key\|api_key\|secret\|token\|password"
git log --all -S "sk-" --source --all
git log --all -S "OPENAI_API_KEY" --source --all
```