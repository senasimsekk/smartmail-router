# SmartMail Router Demo Anlatim Notu

Bu not, projeyi anlatirken kullanilacak kisa demo akisini ve teknik aciklamalari toplar. Amac, sistemin sadece e-posta listeleyen bir ekran olmadigini; e-postayi alip temizleyen, ekleri dikkate alan, ozetleyen, siniflandiran, ilgili birime yonlendiren ve operator geri bildiriminden ogrenebilen bir is akisi oldugunu net gostermektir.

## 1. Proje ne yapiyor?

SmartMail Router, Rekabet Kurumu icin `webmaster@rekabet.gov.tr` benzeri ortak posta kutusuna gelen e-postalari analiz edip ilgili daireye yonlendirmeyi hedefleyen bir MVP'dir.

Sistem temel olarak su akisi izler:

```text
E-posta alma
-> On isleme
-> Ek analizi
-> Ozetleme
-> Siniflandirma
-> Birim yonlendirme
-> Insan onayi
-> Kayit / is akisi
-> Raporlama
```

## 2. Demo akisi

1. `E-posta Alma` ekraninda demo Gmail hesabindan yeni e-postalar senkronize edilir.
2. Gelen e-postalar `Operasyon` ekraninda gorulur.
3. Secilen e-posta icin sistem karari incelenir:
   - kategori
   - onerilen birim
   - guven skoru
   - oncelik
   - onay ihtiyaci
   - karar gerekcesi
4. `Analiz` ekraninda e-posta govdesi, ek bilgisi, ozet ve baglam sinyalleri incelenir.
5. `Islem Hatti` ekraninda e-postanin pipeline adimlari gorulur.
6. Yanlis yonlendirme varsa operator `Yonlendirme Duzeltme` alanindan dogru kategori ve birimi kaydeder.
7. Bu duzeltme feedback olarak egitim verisine eklenir.
8. `Model Egitimi` ekraninda sentetik veri + operator feedback kayitlariyla modelin nasil beslendigi gosterilir.
9. `Raporlama` ve `Degerlendirme` ekranlarinda operasyon metrikleri ve model basarisi anlatilir.

## 3. E-posta alma nasil calisiyor?

MVP'de canli veri kaynagi olarak demo Gmail hesabi kullanilir:

```text
webmaster.rekabet.demo@gmail.com
```

Backend tarafinda IMAP ile Gmail posta kutusuna baglanilir. Yeni e-postalar alinir, veritabanina kaydedilir ve isleme hazir hale getirilir.

Gercek kurum senaryosunda ayni yapi su kaynaklara genisletilebilir:

- IMAP / SMTP
- Microsoft Exchange
- Outlook / Microsoft 365
- Gmail
- ortak posta kutulari
- birim posta kutulari
- API ile mail aktarimi
- arsivden toplu aktarim

API sifreleri ve posta kutusu bilgileri `.env` dosyasinda tutulur. Bu bilgiler Git'e eklenmez.

## 4. On isleme modulu

E-posta modele dogrudan verilmez. Once temizlenir ve parcalara ayrilir.

On isleme adimlari:

- HTML govdeden duz metin cikarma
- imza ve footer temizleme
- onceki yazisma zincirlerini ayirma
- spam / otomatik cevap sinyallerini yakalama
- gonderen, alici, konu ve tarih bilgisini ayirma
- ek listesini cikarma
- bozuk karakterleri duzeltme
- dil ve ivedilik sinyallerini belirleme

Bu adim onemli cunku e-postalarda asil talep bazen cok kisa olur; geri kalan kisim imza, onceki cevaplar veya otomatik footer olabilir.

## 5. Ek analizi

Mail siniflandirmada sadece govdeye bakmak yeterli degildir. Ornegin govdede sadece "ekte sunulmustur" yazabilir; asil bilgi PDF ya da Word dosyasindadir.

Sistem ekleri analiz edilebilir veri olarak ele alir:

- PDF
- Word
- Excel
- PowerPoint
- gorsel / taranmis belge
- ZIP icindeki dosyalar
- KEP / UYAP benzeri dokuman ciktilari

MVP seviyesinde dosya turu, boyut, ek metni, sifreli dosya uyarisi, OCR ihtiyaci ve kisisel veri sinyalleri gibi bilgiler takip edilir. Daha profesyonel kurulumda antivurus servisi, OCR servisi ve object storage gibi bilesenler eklenebilir.

## 6. Ozetleme nasil yapiliyor?

Ozetleme modulu sadece sabit kategori cumlesi basmaz. Mail govdesi ve eklerden cikarilan metin birlikte degerlendirilir.

Mevcut MVP yaklasimi:

- metin cumlelere bolunur
- onemsiz kelimeler ayiklanir
- TF-IDF benzeri puanlama ile anlamli kelimeler one cikarilir
- bu kelimeleri tasiyan en bilgi yogun cumleler secilir
- secilen cumleler "baglam sinyali" olarak ozet alaninda gosterilir

Bu yontem LLM kadar derin anlam uretmez; metindeki guclu sinyalleri yakalar. Avantaji hizli, aciklanabilir ve API kotasina bagli olmamasidir.

Buyuk eklerde tum dosyayi tek seferde ozetlemek yerine metin parcalara bolunmeli, her parcanin kisa ozeti alinmali ve sonra bu ara ozetlerden nihai ozet uretilmelidir. Bu yaklasim LLM kullanildiginda token limitini, LLM kullanilmadiginda ise gurultuyu azaltir.

## 7. Baglama gore daireye yonlendirme

Siniflandirma sadece anahtar kelime saymak seklinde dusunulmemelidir. Ayni e-postada birden fazla daireye benzeyen kelimeler gecebilir.

Ornek:

```text
KVKK basvuru formuna giris yapamiyorum, sistem hata veriyor.
```

Bu metinde `KVKK` gecse bile asil islem niyeti teknik hatadir. Bu nedenle sistem iki ayri sinyali birlikte degerlendirir:

- konu sinyali: KVKK, basin, satin alma, fatura, tebligat, sikayet
- niyet sinyali: hata, erisim, basvuru, odeme, bilgi talebi, hukuki tebligat

Eger teknik hata niyeti guclu ise e-posta Bilgi Islem tarafina yonlendirilir. Eger hukuki basvuru ya da kisisel veri talebi asil baglam ise Hukuk Musavirligi onerilir.

## 8. Insan onayi ve duzeltme

Sistem her e-postayi otomatik kapatmaz. Guven skoru dusukse, kritik risk varsa veya birden fazla birim benzer skor aldiysa insan onayi gerekir.

Operator yanlis yonlendirmeyi duzelttiginde:

- dogru kategori secilir
- dogru birim secilir
- oncelik guncellenir
- geri bildirim notu eklenir
- bu kayit egitim verisine yazilir

Boylece sistem yalnizca sentetik veriye degil, gercek operator davranisina da dayanmaya baslar.

## 9. Model egitimi

MVP'de model egitimi aciklanabilir ve hafif bir yapiyla ele alinir:

- sentetik e-posta ornekleri
- operator duzeltmeleri
- metin ozellikleri
- kategori ve birim etiketleri

Bu veriyle TF-IDF + klasik makine ogrenmesi yaklasimi kullanilabilir. LLM kullanimi ise opsiyonel bir katmandir.

LLM kullanilirse sistem su alanlarda gelisir:

- daha dogal ozet
- daha iyi baglam anlama
- birden fazla daireye benzeyen metinlerde daha guclu karar
- karar gerekcesini daha okunur yazma

Ancak LLM icin API key, kota, maliyet ve veri gizliligi kararlarinin ayrica yonetilmesi gerekir.

## 10. Raporlama ve degerlendirme

Yonetim tarafinda sistemin degeri raporlarla gorulur.

Takip edilen ornek metrikler:

- bugun gelen e-posta sayisi
- otomatik siniflandirilan e-posta sayisi
- operator onayina dusen isler
- kritik is sayisi
- hatali yonlendirme orani
- ortalama yonlendirme suresi
- AI dogruluk orani
- bekleyen isler
- SLA asimi olan isler

Degerlendirme ekrani modelin sadece calisip calismadigini degil, ne kadar basarili oldugunu gostermek icin kullanilir.

## 11. Demo icin test e-postalari

Demo veri setinde su tiplerde e-postalar bulunur. Bu liste demo sirasinda hangi
maili neden sectigini anlatmak icin kullanilabilir:

| Senaryo | Ne gosterir? | Beklenen karar |
| --- | --- | --- |
| KVKK basvuru talebi | Kisisel veri basvurusu | Hukuk Musavirligi |
| Ekte sunulmustur | Mail govdesi zayif, asil bilgi PDF metninde | Hukuk Musavirligi |
| KVKK formu acilmiyor | KVKK kelimesi gecse de asil niyet teknik hata | Bilgi Islem |
| Sifreli ihbar arsivi | ZIP/RAR ve sifreli dosya guvenlik uyarisi | Ilgili Uzman Daire |
| Taranmis dilekce ve kimlik | OCR ihtiyaci ve kisisel veri sinyali | Hukuk Musavirligi |
| KEP / UYAP tebligati | E-imzali resmi evrak ve sure hassasiyeti | Evrak Kayit |
| Fatura odeme bilgisi ve satin alma referansi | Iki birime benzeyen ama mali niyeti agir basan mail | Strateji / Mali Isler |
| Basin aciklamasi ve karar metni talebi | Basin + karar metni iceren karma talep | Basin ve Halkla Iliskiler |
| Toplu basvuru belgeleri | Arsiv dosyasi ve evrak kaydi ihtiyaci | Evrak Kayit |
| Otomatik cevap / reklam aboneligi | On isleme tarafinda otomatik cevap/spam sinyali | Evrak Kayit |

Bu testler ozellikle baglam kararini gostermek icin faydalidir. Ayni kelime baska bir niyetle kullanildiginda sistemin farkli birime yonlendirebilmesi projenin guclu tarafidir.

## 12. Anlatimda kullanilabilecek kisa cumleler

- "Bu proje gelen e-postayi sadece listelemiyor; kurumsal is akisine donusturuyor."
- "Mail govdesi ve ekler birlikte analiz ediliyor."
- "Sistem kararini guven skoru ve gerekceyle acikliyor."
- "Dusuk guven veya kritik durumlarda insan onayi devreye giriyor."
- "Operator duzeltmeleri feedback verisi olarak modele geri donuyor."
- "LLM opsiyonel; MVP aciklanabilir ve kotasiz calisabilen bir siniflandirma mantigina sahip."

## 13. Demo kontrol listesi

- Backend calisiyor mu?
- Frontend calisiyor mu?
- Gmail `.env` bilgileri girildi mi?
- Demo hesabina yeni test e-postalari geldi mi?
- `E-posta Alma` ekraninda senkronizasyon denendi mi?
- `Operasyon` ekraninda yeni e-postalar gorundu mu?
- `Analiz` ekraninda ozet ve sistem karari kontrol edildi mi?
- `Islem Hatti` ekraninda pipeline gorundu mu?
- Yanlis yonlendirme duzeltmesi denenebilir mi?
- Model egitimi ekraninda feedback kayitlari anlatilabilir mi?
- Raporlama ve degerlendirme ekranlari temiz gorunuyor mu?
