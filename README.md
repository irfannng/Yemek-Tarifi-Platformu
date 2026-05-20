# 🏥 Online Doktor Randevu Sistemi

Bu proje, Python programlama dili kullanılarak **Nesne Yönelimli Programlama (OOP)** prensiplerine uygun şekilde geliştirilmiş bir konsol tabanlı randevu yönetim sistemidir. Sistem; hastaların, doktorların ve randevuların birbirleriyle olan ilişkilerini dinamik bir şekilde yönetirken, veri tutarlılığını ve doğrulama kurallarını arka planda otomatik olarak işletir.

---

## ✨ Öne Çıkan Özellikler

* **👤 Gelişmiş Hasta Kaydı ve Doğrulama:** Boş veri girişlerini engelleme ve TC Kimlik numaraları için 11 haneli rakam zorunluluğu gibi katı veri doğrulama kuralları.
* **👨‍⚕️ Dinamik Doktor Takvimi:** Doktorların belirli tarihlere göre müsait saat dilimlerinin (`dict[date, list[str]]`) esnek bir şekilde yönetilmesi.
* **📅 Akıllı Randevu Çakışma Engelleme:** Bir randevu oluşturulduğunda sistem otomatik olarak doktorun o saatteki müsaitliğini kaldırır; böylece çift rezervasyon (çakışma) tamamen engellenir.
* **🔄 Gelişmiş İptal Mekanizması:** Randevu iptal edildiğinde ilgili saat dilimi doktorun takvimine otomatik olarak geri iade edilir ve hastanın aktif randevu listesinden temizlenir.
* **📊 Günlük Randevu Raporlama:** Seçilen bir güne ait tüm aktif randevuları saat bazlı sıralı ve okunaklı bir tablo şeklinde konsola yazdırma yeteneği.

---

## 🛠️ Kullanılan Teknolojiler

Proje, herhangi bir harici kütüphaneye (`pip install`) ihtiyaç duymadan tamamen Python'ın güçlü yerleşik modülleriyle geliştirilmiştir:

* **Dil:** Python 3.8+
* **Zaman Yönetimi:** `datetime` (`date`, `datetime`)
* **Tip Belirleme:** `typing` (`Optional`)

---

## ⚙️ Kurulum ve Çalıştırma

Projeyi yerel bilgisayarınızda çalıştırmak için aşağıdaki adımları takip edebilirsiniz:

### 1. Depoyu Klonlayın
```bash
git clone [https://github.com/kullaniciadi/doktor-randevu-sistemi.git](https://github.com/kullaniciadi/doktor-randevu-sistemi.git)
cd doktor-randevu-sistemi
