# Known Limitations

- Retrieval embedding tabanlı değildir; case kapsamı için SQL/alias/tag/category tabanlı deterministic retrieval kullanır.
- Auth, role management ve production-grade audit policy demo kapsamı dışındadır.
- LLM opsiyoneldir ve varsayılan kapalıdır; LLM açılsa bile ana güvenlik ve mutasyon kararları deterministic safety layer’dan geçer.
- Mobil UI demo seviyesindedir ancak gerçek backend quote ve chat endpointlerine bağlıdır.
- Deterministic router case kapsamındaki ürün/politika/teklif niyetlerini hedefler; serbest genel amaçlı asistan davranışı kapsam dışıdır.
- Yoğun eşzamanlı mutation yükleri için ek isolation/locking testleri production öncesi genişletilmelidir.

# Known Limitations

Bu dosya, teslimde bilinçli olarak kapsam dışında bırakılan veya sınırlı tutulan noktaları açıkça belirtmek için hazırlanmıştır. Buradaki maddeler sistemin çalışmadığı anlamına gelmez; production seviyesine geçerken genişletilmesi gereken alanları gösterir.

## 1. Retrieval yaklaşımı

Bu projede embedding veya vector index kullanılmadı. Dataset küçük, yapılandırılmış ve fiyat/stok gibi kesin filtreler gerektirdiği için SQL/JSON tabanlı deterministic retrieval tercih edildi.

Ürün aramada alias, tag, kategori, marka, fiyat ve stok alanları kullanılır. Politika cevaplarında knowledge kayıtları kaynak olarak gösterilir.

Production ortamında ürün kataloğu büyürse embedding, full-text search veya hibrit retrieval yaklaşımı eklenebilir.

## 2. LLM ile canlı test

Uygulama LLM destekli çalışabilecek şekilde yapılandırıldı; ancak bu teslimde gerçek bir OpenAI API key ile canlı LLM testi yapılmadı.

Bunun yerine ana case davranışları deterministic fallback akışıyla doğrulandı. Product Q&A, Policy Q&A, tool-call fonksiyonları, kaynak gösterimi, fiyat/stok kontrolleri, pending action ve quote mutation senaryoları LLM kapalı modda test edildi.

Bu tercih bilinçli yapıldı. Çünkü fiyat, stok, kaynak ve teklif mutasyonu gibi kritik kararların LLM’ye bırakılmaması gerekiyordu. LLM açıldığında da bu kararların backend safety layer’dan geçmesi beklenir.

Production öncesinde `LLM_ENABLED=true` ve gerçek `OPENAI_API_KEY` ile ek smoke test yapılmalıdır.

## 3. Authentication ve role management

Bu teslimde production-grade kullanıcı hesabı, parola, JWT/session yönetimi, role-based access control ve admin/customer ayrımı eklenmedi.

Demo akışında müşteri ID ile giriş yapılır ve backend customer/quote eşleşmesini kontrol eder. Bu sayede müşteri yalnızca kendi tekliflerini görür. Ancak gerçek production sisteminde bunun yerine güvenli authentication ve authorization katmanı kullanılmalıdır.

## 4. Admin ve müşteri ayrımı

Web arayüzünde ürün ve bilgi kayıtlarını görüntüleme/düzenleme ekranları demo/admin amaçlı tutuldu. Müşteri-facing akışta Loglar gösterilmez; raw tool JSON ve debug bilgileri müşteri ekranında yer almaz.

Production ortamında admin paneli ve müşteri uygulaması ayrı route, ayrı yetki ve ayrı UI policy ile ayrılmalıdır.

## 5. Mobil uygulama kapsamı

Mobil uygulama Expo ile hazırlanmış demo istemcidir. Gerçek backend chat ve quote endpointlerine bağlanır; yani fake/local quote state kullanmaz.

Ancak production mobil uygulama için ek olarak şu konular geliştirilmelidir:

- cihaz bazlı oturum yönetimi
- kalıcı login/session saklama
- offline davranış
- push notification
- farklı ekran boyutlarında daha geniş UI testi
- store build/release süreci

## 6. Eşzamanlılık ve transaction testleri

Teklif mutasyonları gerçek PostgreSQL state üzerinde çalışır ve idempotency kontrolleri içerir. Aynı mesaj tekrar geldiğinde aynı mutation ikinci kez uygulanmamalıdır.

Buna rağmen yüksek eşzamanlı yük, çoklu kullanıcı aynı teklif üzerinde aynı anda işlem yapması ve load test senaryoları bu teslimin kapsamı dışında bırakıldı.

Production öncesinde transaction isolation, row-level locking, retry policy ve concurrency/load testleri genişletilmelidir.

## 7. Genel amaçlı asistan davranışı

Bu asistan genel amaçlı sohbet botu olarak tasarlanmadı. Kapsam ürün, politika, stok, fiyat, uyumluluk ve teklif işlemleriyle sınırlıdır.

Alan dışı isteklerde sistem kontrollü cevap verir veya kullanıcıyı ürün/teklif bağlamına yönlendirir. Bu tercih, case gereksinimindeki güvenli ve kaynaklı teklif asistanı davranışını korumak için yapıldı.

## 8. Intent parsing sınırları

Türkçe kullanıcı mesajları için geniş deterministic intent parsing eklendi. Örneğin fiyat ifadeleri, yazım hataları, ürün aliasları, ekleme/onay ayrımı, kaldırma, miktar güncelleme ve alternatif değiştirme gibi akışlar desteklenir.

Yine de bu yapı sınırsız doğal dil anlama sağlamaz. Çok belirsiz mesajlarda sistem doğrudan işlem yapmak yerine netleştirme sorusu sormalıdır. Production ortamında gerçek kullanıcı verileriyle intent kapsamı genişletilebilir.

## 9. Veri ve fiyat güncelliği

Bu teslimde ürün, stok, fiyat, müşteri, teklif, knowledge ve fiyat kuralı verileri case datasetinden seed edilir.

Gerçek bir ticari sistemde bu veriler ERP, stok sistemi, fiyat motoru veya canlı katalog servisinden gelmelidir. Bu entegrasyonlar kapsam dışıdır.

## 10. Audit ve observability

Tool-call logları DB’de tutulur ve backend endpointleri üzerinden izlenebilir. Bu case için test edilebilir log katmanı sağlar.

Production seviyesinde ek olarak merkezi loglama, tracing, metrics, alerting, audit retention policy ve kişisel veri maskeleme gibi observability gereksinimleri eklenmelidir.