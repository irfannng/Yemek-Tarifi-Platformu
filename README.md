# 🍽️ TarifDünyası — Modern Yemek Tarif Platformu (PyQt5 GUI)

TarifDünyası, Python programlama dili ve **PyQt5** kütüphanesi kullanılarak geliştirilmiş, **Tam Nesne Yönelimli Programlama (OOP)** mimarisine sahip, modern ve şık arayüzlü bir masaüstü yemek tarif platformudur. Uygulama; kart tabanlı tasarımı, dinamik arama/filtreleme algoritmaları ve koyu (dark) tema desteğiyle kullanıcılara üst düzey bir dijital deneyim sunar.

---

## ✨ Öne Çıkan Özellikler

* **🎨 Modern Koyu Tema & Akıcı Tasarım:** Canlı turuncu (`#FF6B35`) vurgu renkleri, özel gölgelendirmeler, yuvarlatılmış köşeler ve modern tipografi içeren profesyonel renk paleti.
* **🏠 Dinamik Anasayfa:** Sistemdeki toplam tarif, kullanıcı ve yüksek puanlı tarif sayılarını anlık gösteren istatistik kartları ve en beğenilen tariflerin listelendiği vitrin alanı.
* **📖 Gelişmiş Tarif Listeleme:** Katmanlı arayüz üzerinde gerçek zamanlı (yazarken filtreleyen) arama motoru ve kategori tabanlı süzgeçler.
* **➕ İnteraktif Tarif Ekleme:** Dinamik malzeme ekleme modülü (miktar ve birim kontrollü), hazırlama süresi (SpinBox) ve kategori seçimi sunan gelişmiş modal diyalog penceresi.
* **⭐ Detaylı Değerlendirme & Puanlama:** Tariflere özel yıldızlama (`★` ve `☆` karakter tabanlı), kullanıcı adı ile yorum bırakma ve dinamik ağırlıklı ortalama puan hesaplama lojistiği.
* **🧩 Özel Widget Bileşenleri:** Yeniden kullanılabilir `ModernButon`, `EtiketBadge`, `TarifKarti` ve `NavButon` sınıfları sayesinde temiz ve sürdürülebilir kod yapısı.

---

## 🛠️ Teknik Mimari ve Sınıf Yapısı (OOP)

Proje, verilerin manipülasyonu ile arayüz katmanını tamamen birbirinden ayıran temiz bir yazılım mimarisine dayanmaktadır:

### 1. Veri Modeli Katmanı
* **`Malzeme`**: Malzemenin adı, miktarı ve birimini (gr, adet, su bardağı vb.) yönetir.
* **`Tarif`**: Reçete bilgilerini, malzemeler listesini ve değerlendirmeleri tutar. Ortalama puanı dinamik hesaplar ve puana uygun yıldız karakter katarını (`yildiz_str()`) oluşturur.
* **`Kullanici`**: Profil bilgilerini ve favori tariflerin benzersiz kimliklerini (`ID`) saklar.
* **`Platform`**: Tüm veri tabanı lojistiğini taklit eder; demo verileri yükler, tarif arama (`ara()`) ve sıralama (`en_iyiler()`) algoritmalarını koşturur.

### 2. Arayüz (GUI) Katmanı
* **`AnaPencere`**: Sol navigasyon paneli ve sayfa geçişlerini kontrol eden `QStackedWidget` yapısını barındıran ana iskelet.
* **`AnasayfaSayfasi` & `TarifListesiSayfasi`**: Grid (ızgara) yapısında `TarifKarti` bileşenlerini listeleyen pencereler.
* **`TarifDetaySayfasi`**: Seçilen tarifin malzemelerini ve geçmiş yorumlarını okunaklı bir dikey akışta sunan detay ekranı.
* **`TarifEkleDiyalogu` & `DegerlendirmeDiyalogu`**: Kullanıcıdan veri alan ve doğruluğunu denetleyen modal pencereler.

---

## 🚀 Kurulum ve Çalıştırma

Proje herhangi bir harici veri tabanı motoruna ihtiyaç duymaz, verileri çalışma zamanında (bellekte) saklar. Çalıştırmak için sisteminizde Python ve PyQt5'in kurulu olması yeterlidir.

### 1. Gereksinimlerin Yüklenmesi
Terminal veya komut satırını açarak aşağıdaki komutla PyQt5 kütüphanesini yükleyin:
```bash
pip install PyQt5
