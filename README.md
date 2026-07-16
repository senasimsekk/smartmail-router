# SmartMail Router

Kuruma gelen e-postaları konu, öncelik, risk ve ilgili birim açısından analiz eden; güven skoru, insan onayı, yönlendirme, geri bildirim, ek dosya risk analizi ve operasyon dashboard'u sunan MVP uygulaması.

## MVP Kapsamı

- Sentetik e-posta verisi ile ortak posta kutusu simülasyonu
- Mail ön işleme: HTML temizleme, imza temizleme, sınıflandırma metni üretme
- Kural tabanlı sınıflandırma ve mock AI ikinci görüş katmanı
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

## Çalıştırma

PostgreSQL'i başlat:

```bash
docker compose up -d
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

## Demo Akışı

1. Dashboard metriklerinden toplam mail, kritik risk, insan onayı, doğruluk oranı ve operasyon dağılımlarını göster.
2. Mail kuyruğundan KVKK, tebligat veya ihbar örneğini seç.
3. Mail kuyruğunda arama, durum filtresi ve SLA filtresiyle geciken/yaklaşan kayıtları öne çıkar.
4. Sınıflandırma, güven skoru, risk nedenleri, SLA son tarihi, bilgi çıkarımı ve cevap önerisini incele.
5. Ek yükleme alanından PDF/DOCX/TXT/CSV dosyası yükleyip çıkan metnin sınıflandırmaya katıldığını göster.
6. React Flow iş akışında mailin hangi aşamalardan geçtiğini göster.
7. Onay bekleyen maili `Onayla` veya `Yönlendir` aksiyonuyla işleme al.
8. Aktif rolü `İzleyici` yaparak aksiyon butonlarının kapandığını, `Operatör` rolünde tekrar açıldığını göster.
9. Yanlış yönlendirme simülasyonu için düzeltme formundan yeni kategori/birim seçip feedback kaydet.
10. Eğitim verisi bölümünden feedback sayısını ve JSONL çıktısını göster.
11. Manuel sentetik mail formuna kısa bir örnek girerek sistemin yeni maili otomatik işlemesini ve SLA durumunun oluşmasını göster.

## Rol Bazlı Yetki

MVP'de dört rol bulunur:

- `admin`: tüm operasyonel işlemleri yapabilir.
- `operator`: mail işleme, ek yükleme, onay, yönlendirme ve feedback işlemlerini yapabilir.
- `department_user`: dashboard ve eğitim verisini görüntüleyebilir.
- `viewer`: yalnızca dashboard/analiz ekranlarını görüntüler.

Frontend rol seçimine göre butonları aktif/pasif yapar. Backend de aynı aksiyonlarda rol izni kontrol eder ve yetkisiz isteklerde `403 Forbidden` döndürür.

## Notlar

Bu sürüm gerçek IMAP/Exchange bağlantısı ve gerçek OCR yerine sentetik veri kullanır. PDF/DOCX/TXT/CSV eklerinden metin çıkarma desteklenir; görsel/taranmış belgeler için OCR entegrasyonu ileriki aşamaya bırakılmıştır. Mimari bu servislerin ileride gerçek connector, OCR ve LLM servisleriyle değiştirilmesine uygun olacak şekilde ayrıştırılmıştır.
