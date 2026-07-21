# SmartMail Router

Kuruma gelen e-postaları konu, öncelik, risk ve ilgili birim açısından analiz eden; güven skoru, insan onayı, yönlendirme, geri bildirim, ek dosya risk analizi ve operasyon dashboard'u sunan MVP uygulaması.

## Amaç

SmartMail Router, kurumsal ortak posta kutularına gelen mailleri otomatik olarak ön incelemeden geçirip doğru kategoriye, ilgili birime ve uygun öncelik seviyesine yönlendirmeyi hedefler. Sistem özellikle yoğun evrak, başvuru, şikayet, KVKK, tebligat ve teknik destek trafiği olan kurumlarda operatör yükünü azaltmak için tasarlanmıştır.

## MVP Kapsamı

- Sentetik e-posta verisi ile ortak posta kutusu simülasyonu
- Mail ön işleme: HTML temizleme, imza temizleme, sınıflandırma metni üretme
- Kural tabanlı sınıflandırma ve API key varsa OpenAI LLM, yoksa demo cevap üreten ikinci görüş katmanı
- Seed veri ve feedback kayıtlarıyla eğitilebilen TF-IDF + Logistic Regression modeli
- Birim yönlendirme, güven skoru ve insan onayı kuyruğu
- Ek dosya adı üzerinden dosya türü, OCR ihtiyacı, risk ve evrak kaydı önerisi
- PDF, DOCX, TXT ve CSV eklerinden metin çıkarma ve sınıflandırmaya dahil etme
- Yapılandırılmış bilgi çıkarımı: dosya no, başvuru no, mevzuat, telefon, T.C. kimlik, tutar vb.
- Cevap önerisi taslağı
- Kategori bazlı SLA / süre takibi ve geciken kayıt uyarıları
- SLA durumuna göre mail kuyruğu filtreleme ve öncelikli sıralama
- Konu, gönderen, posta kutusu ve durum bazlı mail kuyruğu arama/filtreleme
- Kategori, birim ve risk dağılımlarını gösteren operasyon barları
- Yanlış yönlendirme düzeltme ve feedback kaydı
- Feedback kayıtlarından training JSONL dışa aktarma
- Admin, operatör, birim kullanıcısı ve izleyici rolleriyle rol bazlı yetki kontrolü
- React Flow ile mail iş akışı görselleştirme
- Audit log ve operasyon dashboard'u
- React tabanlı admin/operatör paneli

## Mimari

Proje üç ana parçadan oluşur:

- `frontend`: React + Vite tabanlı operatör paneli.
- `backend`: FastAPI servisleri, sınıflandırma, analiz, routing, feedback ve model eğitimi API'leri.
- `database`: PostgreSQL üzerinde e-posta, sınıflandırma, feedback ve audit log kayıtları.

Genel akış:

1. Sentetik veya manuel girilen mail backend'e alınır.
2. Ön işleme servisi konu, gövde, kaynak posta kutusu ve ek metinlerinden sınıflandırma metni üretir.
3. Kural tabanlı sınıflandırma kategori, birim, öncelik ve insan onayı ihtiyacını belirler.
4. Analiz servisleri risk, cevap ihtiyacı, SLA durumu ve yönlendirme önerisi üretir.
5. Operatör paneli mail kuyruğu, detay analizi, React Flow iş akışı ve operasyon metriklerini gösterir.
6. Operatör düzeltme yaparsa feedback kaydı oluşur ve bu kayıt eğitim verisine katılır.

## AI / ML Yaklaşımı

Bu MVP'de üç katmanlı bir yaklaşım kullanılır:

- Kural tabanlı sınıflandırma: Anahtar kelime ve bağlam kurallarıyla hızlı, açıklanabilir karar üretir.
- LLM ikinci görüş: `OPENAI_API_KEY` tanımlıysa OpenAI Responses API üzerinden yapılandırılmış JSON sınıflandırma ve özet üretir; key yoksa aynı arayüzle demo cevap döner.
- Eğitilebilir lokal model: Seed veri ve feedback kayıtlarından `TF-IDF + Logistic Regression` modeli eğitilir.

Lokal model gerçek bir makine öğrenmesi modelidir, fakat LLM fine-tune değildir. Mail metinleri TF-IDF ile sayısal özelliklere çevrilir; model kategori, birim ve öncelik için ayrı tahminler üretir. Eğitilmiş model `backend/model_artifacts/` altında saklanır ve bu klasör git'e eklenmez.

LLM katmanı doğrudan nihai karar vermez. Ön işlenmiş mail, eklerden çıkarılan metin, kural tabanlı sonuç ve izinli kategori/birim listesi modele gönderilir. Model sadece özet, gerekçe, kategori, birim, öncelik ve güven skorunu JSON olarak döndürür; kritik kategorilerde insan onayı kuralı korunur. Varsayılan model `OPENAI_MODEL` ile değiştirilebilir, tanımlı değilse maliyet odaklı `gpt-5.6-luna` kullanılır.

Model API'leri:

- `GET /emails/model/status`
- `POST /emails/model/train`
- `GET /emails/{email_id}/model-prediction`
- `GET /emails/{email_id}/ai-analysis`

Bu yaklaşım, az veriyle çalışabilen, yerelde koşan ve veri gizliliği açısından daha kontrollü bir eğitim mekanizması sağlar. LLM tarafı ise gerçek API veya demo fallback ile aynı ürün akışında gösterilebilir.

## Öne Çıkan Modüller

- E-posta alma: `webmaster@rekabet.gov.tr` ortak kutusundan sentetik senkronizasyon ve manuel mail girişi.
- Sınıflandırma: Kategori, departman, öncelik ve güven skoru.
- SLA takibi: Kategoriye göre son tarih ve gecikme durumu.
- Ek analizi: PDF/Word/TXT/CSV metin çıkarma; Excel, PowerPoint, görsel, arşiv, e-imzalı ve KEP/UYAP benzeri dosyalarda tür tespiti, OCR/güvenlik/şifre uyarısı, kişisel veri ve dosya no analizi.
- Evrak/talep kaydı: Otomatik kayıt numarası, birim/sorumlu atama, SLA son tarihi, durum takibi, not ve cevap/kapanış alanları.
- Feedback: Yanlış yönlendirme düzeltmesi ve eğitim verisi üretimi.
- Rol bazlı yetki: Admin, operatör, birim kullanıcısı ve izleyici rolleri.
- Operasyon dashboard'u: Metrikler, dağılımlar, filtreler ve audit log.

## Çalıştırma

PostgreSQL'i başlat:

```bash
docker compose up -d
```

Backend ortam değişkenlerini hazırla:

```bash
cp backend/.env.example backend/.env
```

Backend tablolarını oluştur ve sentetik veriyi yükle:

```bash
cd backend
.venv/bin/python scripts/create_tables.py
.venv/bin/python scripts/seed_emails.py
```

Backend'i başlat:

```bash
cd backend
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend'i başlat:

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

Uygulama: http://127.0.0.1:5173  
API dokümantasyonu: http://127.0.0.1:8000/docs

## Test

Backend servis testlerini çalıştır:

```bash
cd backend
.venv/bin/python -m unittest discover -s tests
```

## Demo Akışı

1. Dashboard metriklerinden toplam mail, kritik risk, insan onayı, doğruluk oranı ve operasyon dağılımlarını göster.
2. Mail kuyruğundan KVKK, tebligat veya ihbar örneğini seç.
3. Mail kuyruğunda arama, durum filtresi ve SLA filtresiyle geciken/yaklaşan kayıtları öne çıkar.
4. Sınıflandırma, güven skoru, risk nedenleri, SLA son tarihi, bilgi çıkarımı ve cevap önerisini incele.
5. Ek yükleme alanından PDF/DOCX/TXT/CSV dosyası yükleyip çıkan metnin sınıflandırmaya katıldığını göster.
6. React Flow iş akışında mailin hangi aşamalardan geçtiğini göster.
7. Oluşan evrak/talep kaydında kayıt no, birim, sorumlu, durum ve SLA son tarihini göster.
8. Onay bekleyen maili `Onayla` veya `Yönlendir` aksiyonuyla işleme al.
9. Aktif rolü `İzleyici` yaparak aksiyon butonlarının kapandığını, `Operatör` rolünde tekrar açıldığını göster.
10. Yanlış yönlendirme simülasyonu için düzeltme formundan yeni kategori/birim seçip feedback kaydet.
11. Eğitim verisi bölümünden modeli eğit, model tahminini kural/LLM kararıyla karşılaştır ve JSONL çıktısını göster.
12. `Posta Kutusunu Senkronize Et` aksiyonuyla webmaster ortak kutusuna gelen e-postaların alınmasını, analiz edilmesini ve ilgili birim akışına yönlendirilmesini göster.
13. Manuel e-posta formuna kısa bir örnek girerek sistemin yeni maili otomatik işlemesini ve SLA durumunun oluşmasını göster.

## Rol Bazlı Yetki

MVP'de dört rol bulunur:

- `admin`: tüm operasyonel işlemleri yapabilir.
- `operator`: mail işleme, ek yükleme, onay, yönlendirme ve feedback işlemlerini yapabilir.
- `department_user`: dashboard ve eğitim verisini görüntüleyebilir.
- `viewer`: yalnızca dashboard/analiz ekranlarını görüntüler.

Frontend rol seçimine göre butonları aktif/pasif yapar. Backend de aynı aksiyonlarda rol izni kontrol eder ve yetkisiz isteklerde `403 Forbidden` döndürür.

## Notlar

Bu sürüm gerçek IMAP/Exchange bağlantısı ve gerçek OCR yerine sentetik veri kullanır. PDF/DOCX/TXT/CSV eklerinden metin çıkarma desteklenir; görsel/taranmış belgeler için OCR entegrasyonu ileriki aşamaya bırakılmıştır. Mimari bu servislerin ileride gerçek connector, OCR ve LLM servisleriyle değiştirilmesine uygun olacak şekilde ayrıştırılmıştır.

## Geliştirilebilir Alanlar

- Gerçek IMAP, Exchange veya Microsoft Graph bağlantısı.
- Taranmış PDF ve görseller için OCR entegrasyonu.
- Daha büyük etiketli veri setiyle model başarım ölçümü.
- LLM tabanlı özetleme, cevap üretimi ve karar açıklaması.
- Departman bazlı kullanıcı yönetimi ve gerçek kimlik doğrulama.
- SLA politikalarının admin panelinden düzenlenebilmesi.
