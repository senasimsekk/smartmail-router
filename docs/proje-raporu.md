# SmartMail Router Proje Raporu

## 1. Projenin Amacı

SmartMail Router, Rekabet Kurumu gibi kurumsal yapılarda ortak posta kutularına gelen e-postaların otomatik olarak analiz edilmesi, özetlenmesi, sınıflandırılması ve ilgili birime yönlendirilmesi amacıyla geliştirilmiş bir MVP uygulamasıdır.

Proje, özellikle `webmaster@rekabet.gov.tr` benzeri ortak bir posta kutusuna gelen e-postaların manuel olarak tek tek okunması, ilgili daireye aktarılması, eklerinin kontrol edilmesi ve gerektiğinde evrak/talep kaydına dönüştürülmesi süreçlerini desteklemeyi hedefler.

Temel problem şudur:

- Gelen e-postaların konusu her zaman açık değildir.
- Mail gövdesi bazen sadece "ekte sunulmuştur" gibi kısa bir ifade içerir.
- Asıl bilgi PDF, Word, görsel, ZIP veya e-imzalı dosya gibi eklerde olabilir.
- Aynı e-postada birden fazla daireye benzeyen anahtar kelimeler geçebilir.
- Kurumsal süreçlerde kritik, süreli veya kişisel veri içeren maillerin insan onayına düşmesi gerekir.

Bu nedenle sistem sadece e-posta listeleyen bir panel değil; e-postayı uçtan uca işleyen bir karar destek hattı olarak tasarlanmıştır.

## 2. Kapsam

MVP kapsamında geliştirilen ana özellikler:

- E-posta alma modülü
- Gmail / IMAP entegrasyon hazırlığı
- Sentetik demo posta kutusu
- Ön işleme modülü
- Ek analizi ve ek metni kullanımı
- Özetleme modülü
- Kural tabanlı sınıflandırma
- Bağlama göre yönlendirme kararı
- İnsan onayı ve yanlış yönlendirme düzeltme
- Feedback kaydı
- TF-IDF + Logistic Regression tabanlı eğitilebilir model
- Evrak/talep kaydı modülü
- İşlem hattı görünümü
- Raporlama ekranı
- Model değerlendirme ekranı
- Demo senaryo veri seti

MVP dışında bırakılan veya ileride geliştirilebilecek alanlar:

- Gerçek kurumsal LDAP / Active Directory bağlantısı
- EBYS / KEP / DMS gibi kurumsal sistemlerle canlı entegrasyon
- Gerçek antivirüs motoru entegrasyonu
- Üretim seviyesinde OCR servisi
- Kurum içi SSO / Keycloak bağlantısı
- LLM tabanlı üretim sınıflandırma servisi

## 3. Genel Mimari

Sistemin temel mimari akışı aşağıdaki gibidir:

```text
Mail Connector
-> Ingestion Service
-> Preprocessor
-> Attachment Parser / OCR Hazırlığı
-> Summary Service
-> Classification Engine
-> Routing Engine
-> Human Review
-> Ticket / Workflow
-> Reporting / Audit
```

Backend tarafında Python tabanlı servis katmanları kullanılır. Frontend tarafında React ile yönetim paneli geliştirilmiştir. Veri akışı servisler üzerinden ayrıştırılmıştır; böylece e-posta alma, ön işleme, sınıflandırma, yönlendirme, model eğitimi ve raporlama ayrı sorumluluklara sahiptir.

## 4. E-posta Alma Modülü

Sistem farklı kaynaklardan e-posta alabilecek şekilde düşünülmüştür:

- IMAP / SMTP
- Gmail
- Microsoft Exchange / Microsoft 365
- Ortak posta kutuları
- Birim posta kutuları
- API ile mail aktarımı
- E-posta arşivinden toplu aktarım

MVP'de iki kaynak desteklenir:

1. Canlı Gmail IMAP bağlantısı
2. Sentetik demo posta kutusu

Gmail bağlantısı için demo hesap kullanılır:

```text
webmaster.rekabet.demo@gmail.com
```

Canlı bağlantı bilgileri `.env` dosyasında saklanır. Bu bilgiler Git deposuna eklenmez. Sentetik demo posta kutusu ise `data/synthetic_emails.json` dosyasından beslenir.

Frontend üzerinde `E-posta Alma` ekranında iki farklı aksiyon bulunur:

- `Posta Kutusunu Senkronize Et`: Gmail / IMAP üzerinden yeni e-posta alır.
- `Demo Senaryolarını Yükle`: Hazırlanan 30 adet demo e-postayı sisteme aktarır.

## 5. Ön İşleme Modülü

E-posta doğrudan sınıflandırma modeline verilmez. Önce temizlenir ve anlamlı parçalara ayrılır.

Ön işleme adımları:

- HTML gövdeden düz metin çıkarma
- Bozuk Türkçe karakter düzeltme
- İmza temizleme
- Footer temizleme
- Önceki yazışma zincirlerini ayırma
- Gönderen, alıcı, konu ve tarih bilgisini ayrıştırma
- Ek dosya adlarını çıkarma
- Dil algılama
- Spam / otomatik cevap sinyali tespiti

Bu modül özellikle kurumsal e-postalarda önemlidir. Çünkü mail gövdesinde imza, gizlilik metni, önceki cevaplar ve otomatik footer gibi sınıflandırmayı yanıltabilecek çok fazla metin bulunabilir.

## 6. Ek Analizi

Mail sınıflandırmada ekler kritik öneme sahiptir. Birçok kurumsal başvuruda mail gövdesi kısa olur, asıl bilgi ekte yer alır.

Desteklenen ek türleri:

- PDF
- Word
- Excel
- PowerPoint
- Görsel / taranmış belge
- ZIP / RAR / 7z
- E-imzalı dosyalar
- KEP / UYAP benzeri resmi doküman çıktıları

MVP seviyesinde yapılan analizler:

- Dosya türü tespiti
- OCR ihtiyacı tespiti
- Şifreli dosya uyarısı
- ZIP / RAR güvenlik uyarısı
- Kişisel veri sinyali tespiti
- Dosya adından konu çıkarımı
- Dosya adından tarih / dosya numarası çıkarımı
- Ek risk seviyesi belirleme

Örneğin `tarama_dilekce_kimlik.pdf` ve `kimlik_on_yuz.png` ekleri OCR ve kişisel veri açısından riskli kabul edilir. `sifreli_ihbar_belgeleri.zip` gibi arşiv dosyaları ise güvenlik kontrolü ve insan onayı gerektirir.

## 7. Özetleme Yaklaşımı

Özetleme modülü, yalnızca sabit kategori cümlesi üretmez. Mail gövdesi ve eklerden çıkarılan metinleri birlikte değerlendirir.

Mevcut MVP yaklaşımı:

- Mail gövdesi ve ek metinleri birleştirilir.
- Metin cümlelere ayrılır.
- Önemsiz kelimeler elenir.
- TF-IDF benzeri puanlama ile anlamlı kelimeler öne çıkarılır.
- En bilgi yoğun cümleler seçilir.
- Seçilen cümleler özet ve bağlam sinyali olarak gösterilir.

Bu yöntem LLM kadar derin anlam üretmez; ancak hızlı, açıklanabilir ve API kotasına bağlı olmayan bir çözümdür. Özellikle demo için avantajı, sistemin hangi metin parçalarına bakarak karar verdiğinin anlatılabilmesidir.

Büyük ekler için önerilen yaklaşım:

- Ek metni parçalara bölünür.
- Her parça ayrı özetlenir.
- Ara özetlerden nihai özet üretilir.
- Kritik tarih, dosya numarası, kurum, kişi ve konu sinyalleri ayrıca korunur.

Bu yapı ileride LLM destekli özetlemeye geçildiğinde token limiti ve maliyet yönetimi açısından da doğru bir temel sağlar.

## 8. Sınıflandırma ve Bağlama Göre Yönlendirme

Sistem ilk aşamada kural tabanlı sınıflandırma kullanır. Mail konusu, temizlenmiş gövde, ek adları ve eklerden çıkarılan metin birlikte değerlendirilir.

Desteklenen temel kategoriler:

- KVKK Başvurusu
- Teknik Destek
- Basın Talebi
- Satın Alma
- Hukuki Tebligat
- Şikayet
- İhbar
- Bilgi Edinme
- Fatura / Ödeme
- İnsan Kaynakları
- Evrak Kayıt
- Genel Başvuru

Sınıflandırma yalnızca kelime saymaya dayanmaz. Sistem ayrıca niyet sinyallerini değerlendirir.

Örnek:

```text
KVKK başvuru formu açılmıyor, portal hata veriyor.
```

Bu mailde `KVKK` kelimesi geçse de ana niyet kişisel veri başvurusu değil, teknik erişim sorunudur. Bu nedenle sistem maili Hukuk Müşavirliği yerine Bilgi İşlem birimine yönlendirir.

Benzer şekilde `fatura`, `satın alma`, `teklif`, `ödeme`, `dekont` gibi ifadeler aynı mailde geçebilir. Sistem ana eylemin ödeme sorgusu olduğunu tespit ederse Strateji / Mali İşler birimini önerir.

## 9. İnsan Onayı ve Feedback Mekanizması

Her mail otomatik olarak kapatılmaz. Aşağıdaki durumlarda insan onayı devreye girer:

- Kritik öncelik
- Düşük güven skoru
- KVKK / kişisel veri sinyali
- Hukuki tebligat
- İhbar
- Şifreli veya sıkıştırılmış ek dosya
- Taranmış belge / OCR ihtiyacı
- Birden fazla birime benzeyen belirsiz içerik

Operatör yanlış yönlendirme gördüğünde düzeltme yapabilir:

- Doğru kategori seçilir.
- Doğru birim seçilir.
- Öncelik güncellenir.
- Geri bildirim notu eklenir.

Bu kayıt feedback verisi olarak saklanır. Böylece sistem yalnızca başlangıçtaki sentetik veriye değil, operatör düzeltmelerine de dayanarak geliştirilebilir.

## 10. Eğitilebilir Model

Projede LLM dışında çalışan eğitilebilir bir model de bulunmaktadır. Bu model TF-IDF + Logistic Regression yaklaşımıyla geliştirilmiştir.

Modelin kullandığı veri kaynakları:

- Sentetik e-posta örnekleri
- Operatör feedback kayıtları
- Mail konusu
- Mail gövdesi
- Ek dosya adları
- Eklerden çıkarılan metinler

Model üç hedef için tahmin üretir:

- Kategori
- Birim
- Öncelik

Bu modelin avantajları:

- API anahtarına ihtiyaç duymaz.
- Açıklanabilir yapıdadır.
- Küçük veri setleriyle hızlı eğitilebilir.
- Operatör feedback verisiyle iyileştirilebilir.

LLM opsiyonel olarak kullanılabilir. LLM kullanıldığında özellikle özetleme, bağlam anlama ve karar gerekçesi üretme alanlarında daha güçlü sonuçlar alınabilir. Ancak LLM kullanımı API key, kota, maliyet ve veri gizliliği kararlarını beraberinde getirir.

## 11. Evrak / Talep Kaydı Modülü

Mail sadece yönlendirilmez; gerekiyorsa kayıt altına alınır.

Desteklenen özellikler:

- Otomatik kayıt numarası
- Mail ve eklerini kayıtla ilişkilendirme
- Başvuru türü
- Birim atama
- Sorumlu kişi
- SLA / süre takibi
- Durum takibi
- Not ekleme
- Cevap metni bağlama
- Kapatma gerekçesi

Kullanılan örnek durumlar:

- Yeni
- Sınıflandırıldı
- Onay bekliyor
- Birimine yönlendirildi
- İşlemde
- Cevap bekleniyor
- Tamamlandı
- Arşivlendi
- Hatalı yönlendirme

Bu modül, sistemi yalnızca mail yönlendirme aracı olmaktan çıkarıp kurumsal iş takibi aracına yaklaştırır.

## 12. Raporlama ve Değerlendirme

Raporlama modülü yönetim için operasyonel görünürlük sağlar.

Takip edilen metrikler:

- Günlük gelen e-posta sayısı
- Otomatik sınıflandırılan e-posta sayısı
- Operatör onayına düşen işler
- Kritik iş sayısı
- Hatalı yönlendirme oranı
- Ortalama yönlendirme süresi
- Ortalama kapanma süresi
- AI doğruluk oranı
- Operatör müdahale oranı
- Bekleyen işler
- SLA aşımı olan işler
- Birim bazlı iş yükü
- Konu bazlı dağılım

Değerlendirme ekranı, modelin başarı durumunu ve hangi kategorilerde zorlandığını göstermek için kullanılır.

## 13. Demo Veri Seti

Demo veri seti `data/synthetic_emails.json` dosyasında tutulur. Toplam 30 e-posta örneği bulunmaktadır.

Öne çıkan demo senaryoları:

| Senaryo | Amaç | Beklenen yönlendirme |
| --- | --- | --- |
| Ekte sunulmuştur | Mail gövdesi zayıf, asıl bilgi ekte | Hukuk Müşavirliği |
| KVKK formu açılmıyor | KVKK kelimesi geçer ama niyet teknik hata | Bilgi İşlem |
| Şifreli ihbar arşivi | ZIP ve şifreli dosya uyarısı | İlgili Uzman Daire |
| Taranmış dilekçe ve kimlik | OCR ve kişisel veri sinyali | Hukuk Müşavirliği |
| KEP / UYAP tebligatı | Resmi evrak ve süre hassasiyeti | Evrak Kayıt |
| Fatura + satın alma referansı | Karma içerikte mali niyet | Strateji / Mali İşler |
| Basın açıklaması + karar metni | Basın ve bilgi talebi ayrımı | Basın ve Halkla İlişkiler |
| Otomatik cevap / reklam | Ön işleme ve spam sinyali | Evrak Kayıt |

Bu senaryolar demo sırasında sistemin sadece anahtar kelimeye göre değil, bağlama ve eylem niyetine göre karar verdiğini göstermek için hazırlanmıştır.

## 14. Kullanılan Teknolojiler

Backend:

- Python
- FastAPI
- SQLAlchemy
- IMAP bağlantısı
- scikit-learn
- TF-IDF
- Logistic Regression

Frontend:

- React
- Vite
- React Flow
- CSS tabanlı kurumsal panel tasarımı

Veri / model:

- JSON sentetik veri seti
- Feedback kayıtları
- Joblib model çıktısı

## 15. Test ve Doğrulama

Backend tarafında servis testleri bulunmaktadır. Son doğrulamada:

```text
44 test OK
```

Frontend tarafında production build kontrolü yapılmıştır:

```text
npm run build
```

Build başarılıdır.

Testlerin kapsadığı örnek alanlar:

- Sınıflandırma kuralları
- Bağlama göre teknik hata yönlendirmesi
- Fatura / ödeme ayrımı
- Özetleme
- Ek analizi
- Ön işleme
- Pipeline üretimi
- Raporlama
- Model eğitim verisi
- Demo dataset doğrulaması

## 16. Güçlü Yönler

Projenin güçlü tarafları:

- Kurumsal e-posta iş akışını uçtan uca ele alır.
- Mail gövdesi ve ek metnini birlikte değerlendirir.
- İnsan onayı ve feedback mekanizması içerir.
- Sadece LLM'e bağlı değildir; API kotası olmadan çalışabilir.
- Eğitilebilir model altyapısı vardır.
- Demo veri seti kontrollü ve anlatılabilir senaryolardan oluşur.
- Raporlama ve değerlendirme ekranları yönetim görünürlüğü sağlar.
- Gerçek Gmail / IMAP bağlantısı için hazırlık yapılmıştır.

## 17. Sınırlılıklar

MVP seviyesindeki sınırlılıklar:

- OCR gerçek motorla yapılmamaktadır; ihtiyaç tespiti simüle edilir.
- Antivirüs taraması gerçek motorla yapılmamaktadır; risk uyarısı simüle edilir.
- LLM kullanımı opsiyoneldir ve kota / API key durumuna bağlıdır.
- Kurumsal LDAP, EBYS, KEP, DMS entegrasyonları canlı değildir.
- Sınıflandırma kuralları sınırlı sayıda senaryo için optimize edilmiştir.
- Büyük eklerin parça parça özetlenmesi üretim seviyesinde tamamlanmamıştır.

## 18. Gelecek Geliştirmeler

Önerilen sonraki geliştirmeler:

1. LLM destekli özetleme servisi eklenmesi
2. Büyük ekler için chunk tabanlı özetleme yapılması
3. OCR motoru entegrasyonu
4. Antivirüs servisi entegrasyonu
5. EBYS / KEP sistemleriyle canlı entegrasyon
6. Model başarı metriklerinin gerçek feedback verisiyle izlenmesi
7. Rol bazlı yetkilendirmenin SSO / Keycloak ile bağlanması
8. Operatör ekranlarında daha gelişmiş filtreleme ve arama
9. SLA aşımı için bildirim mekanizması
10. Raporların PDF / Excel olarak dışa aktarılması

## 19. Sonuç

SmartMail Router, kurumsal ortak posta kutularına gelen e-postaların manuel iş yükünü azaltmak ve doğru birimlere daha hızlı yönlendirilmesini sağlamak için geliştirilmiş bir MVP'dir.

Proje, e-posta alma, ön işleme, ek analizi, özetleme, sınıflandırma, yönlendirme, insan onayı, model eğitimi, evrak kaydı ve raporlama süreçlerini tek bir panelde birleştirir. Özellikle mail gövdesi + ek metni birlikte değerlendirme, bağlama göre yönlendirme ve operatör feedback mekanizması projenin en önemli katkılarıdır.

Bu haliyle sistem, gerçek kurumsal entegrasyonlar eklenmeden önce kavramsal olarak güçlü ve demo edilebilir bir karar destek uygulaması sunmaktadır.
