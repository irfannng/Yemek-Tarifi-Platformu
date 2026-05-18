"""
Yemek Tarif Platformu — v3.0 (TheMealDB API Entegrasyonu)
===========================================================
YENİ ÖZELLİKLER (v3.0):
  - TheMealDB ücretsiz API entegrasyonu (API anahtarı gerektirmez)
  - "API'den Keşfet" sayfası: arama, kategori filtresi, rastgele tarif
  - Arka planda asenkron HTTP (QThread) — UI donmaz
  - API'den gelen tarifi yerel platforma tek tıkla kaydet
  - Tarif görselleri URL'den yüklenir (async), önbelleğe alınır
  - Bağlantı hatası / timeout için kullanıcı dostu mesaj kutusu
  - Tüm v2.0 özellikleri korundu
Gereksinim: pip install PyQt5
"""

import sys
import json
import urllib.request
import urllib.parse
import urllib.error
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QScrollArea,
    QFrame, QStackedWidget, QComboBox, QSpinBox, QMessageBox,
    QGridLayout, QDialog, QFormLayout, QListWidget,
    QAbstractItemView, QSizePolicy, QProgressBar
)
from PyQt5.QtCore import (
    Qt, QTimer, pyqtSignal, QThread, QObject, QRunnable,
    QThreadPool, pyqtSlot
)
from PyQt5.QtGui import (
    QFont, QColor, QPalette, QPixmap, QClipboard
)


# ═══════════════════════════════════════════════════════════════════
#  RENK PALETİ & STİL SABİTLERİ
# ═══════════════════════════════════════════════════════════════════

RENKLER = {
    "bg_dark":        "#0D0F12",
    "bg_card":        "#161A20",
    "bg_card2":       "#1C2128",
    "bg_input":       "#1E2530",
    "accent":         "#FF6B35",
    "accent2":        "#FF8C5A",
    "accent_dim":     "#3D2318",
    "text_primary":   "#F0EDE8",
    "text_secondary": "#8B8F96",
    "text_hint":      "#4A5060",
    "border":         "#252B35",
    "border_active":  "#FF6B35",
    "success":        "#2ECC71",
    "warning":        "#F39C12",
    "danger":         "#E74C3C",
    "star":           "#F5C518",
    "purple":         "#9B59B6",
    "blue":           "#3498DB",
    "api_accent":     "#1ABC9C",
    "api_dim":        "#0D2E28",
}

STYLE_SHEET = f"""
QMainWindow, QWidget {{
    background-color: {RENKLER['bg_dark']};
    color: {RENKLER['text_primary']};
    font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', sans-serif;
}}
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollBar:vertical {{
    background: {RENKLER['bg_card']};
    width: 6px;
    border-radius: 3px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {RENKLER['text_hint']};
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
QScrollBar:horizontal {{ height: 0px; }}
QLineEdit, QTextEdit, QSpinBox, QComboBox {{
    background: {RENKLER['bg_input']};
    color: {RENKLER['text_primary']};
    border: 1px solid {RENKLER['border']};
    border-radius: 10px;
    padding: 10px 14px;
    font-size: 14px;
    selection-background-color: {RENKLER['accent_dim']};
}}
QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border: 1px solid {RENKLER['accent']};
    background: #1A2030;
}}
QComboBox::drop-down {{ border: none; padding-right: 10px; }}
QComboBox QAbstractItemView {{
    background: {RENKLER['bg_card2']};
    border: 1px solid {RENKLER['border']};
    selection-background-color: {RENKLER['accent_dim']};
    color: {RENKLER['text_primary']};
    padding: 4px;
    outline: none;
}}
QSpinBox::up-button, QSpinBox::down-button {{
    background: {RENKLER['bg_card2']};
    border: none;
    width: 20px;
    border-radius: 4px;
}}
QListWidget {{
    background: transparent;
    border: none;
    outline: none;
}}
QListWidget::item {{ padding: 2px 4px; border: none; }}
QListWidget::item:selected {{
    background: {RENKLER['accent_dim']};
    border-radius: 6px;
    color: {RENKLER['text_primary']};
}}
QDialog {{
    background: {RENKLER['bg_card']};
    border: 1px solid {RENKLER['border']};
    border-radius: 16px;
}}
QToolTip {{
    background: {RENKLER['bg_card2']};
    color: {RENKLER['text_primary']};
    border: 1px solid {RENKLER['border']};
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 12px;
}}
QMessageBox {{
    background: {RENKLER['bg_card']};
    color: {RENKLER['text_primary']};
}}
QMessageBox QPushButton {{
    background: {RENKLER['accent']};
    color: white;
    border: none;
    border-radius: 8px;
    padding: 8px 20px;
    font-weight: 600;
    min-width: 80px;
}}
QMessageBox QPushButton:hover {{ background: {RENKLER['accent2']}; }}
QProgressBar {{
    background: {RENKLER['bg_card2']};
    border: none;
    border-radius: 3px;
    height: 4px;
}}
QProgressBar::chunk {{
    background: {RENKLER['api_accent']};
    border-radius: 3px;
}}
"""


# ═══════════════════════════════════════════════════════════════════
#  VERİ MODELİ
# ═══════════════════════════════════════════════════════════════════

class Malzeme:
    def __init__(self, adi, miktar, birim="adet"):
        self.adi = adi
        self.miktar = miktar
        self.birim = birim

    def __str__(self):
        return f"{self.miktar} {self.birim} — {self.adi}"


class Tarif:
    _sayac = 1

    def __init__(self, adi, kategori, sure, aciklama="", zorluk="Orta"):
        self.id = Tarif._sayac
        Tarif._sayac += 1
        self.adi = adi
        self.kategori = kategori
        self.sure = sure
        self.aciklama = aciklama
        self.zorluk = zorluk
        self.malzemeler: list = []
        self.degerlendirmeler: list = []
        self.adimlar: list = []
        self.gorsel_url: str = ""   # API'den gelen görsel URL'si

    def ortalama_puan(self):
        if not self.degerlendirmeler:
            return 0.0
        return round(sum(p for p, _, _ in self.degerlendirmeler) / len(self.degerlendirmeler), 1)

    def degerlendir(self, puan, yorum, kullanici_adi):
        self.degerlendirmeler.append((puan, yorum, kullanici_adi))

    def yildiz_str(self):
        p = self.ortalama_puan()
        if p == 0:
            return "☆☆☆☆☆"
        dolu = int(round(p))
        return "★" * dolu + "☆" * (5 - dolu)

    def zorluk_renk(self):
        return {"Kolay": "success", "Orta": "warning", "Zor": "danger"}.get(self.zorluk, "warning")


class Kullanici:
    _sayac = 1

    def __init__(self, ad):
        self.id = Kullanici._sayac
        Kullanici._sayac += 1
        self.ad = ad
        self.favoriler: list = []

    def favoriye_ekle(self, tarif_id):
        if tarif_id not in self.favoriler:
            self.favoriler.append(tarif_id)
            return True
        return False

    def favoriden_cikar(self, tarif_id):
        if tarif_id in self.favoriler:
            self.favoriler.remove(tarif_id)
            return True
        return False


class Platform:
    def __init__(self):
        self.tarifler: dict = {}
        self.kullanicilar: dict = {}
        self.aktif_kullanici: Kullanici = None
        self.kategoriler = ["Ana Yemek", "Çorba", "Tatlı", "Salata", "Kahvaltı", "İçecek", "Atıştırmalık"]
        self.zorluk_seviyeleri = ["Kolay", "Orta", "Zor"]
        self._demo_yukle()

    def _demo_yukle(self):
        u1 = self.kullanici_ekle("Ayşe")
        u2 = self.kullanici_ekle("Mehmet")
        self.aktif_kullanici = u1

        t1 = Tarif("Çikolatalı Kek", "Tatlı", 60,
                   "Nefis, nemli ve yoğun çikolatalı kek. Her kutlamaya yakışır.", "Orta")
        t1.malzemeler = [
            Malzeme("Un", 2, "su bardağı"), Malzeme("Şeker", 1, "su bardağı"),
            Malzeme("Yumurta", 3, "adet"), Malzeme("Kakao", 4, "yemek kaşığı"),
            Malzeme("Tereyağı", 100, "gr"), Malzeme("Süt", 1, "su bardağı"),
            Malzeme("Kabartma tozu", 1, "tatlı kaşığı"),
        ]
        t1.adimlar = [
            "Fırını 180°C'ye önceden ısıtın.",
            "Yumurta ve şekeri krem kıvamına gelene kadar çırpın.",
            "Erimiş tereyağını ekleyip karıştırın.",
            "Un, kakao ve kabartma tozunu eleyin, sütle birlikte yavaşça katın.",
            "Yağlanmış kalıba dökün ve 35–40 dakika pişirin.",
        ]
        self.tarifler[t1.id] = t1
        t1.degerlendir(5, "Mükemmel lezzet!", "Mehmet")
        t1.degerlendir(4, "Harika oldu.", "Zeynep")

        t2 = Tarif("Tavuk Sote", "Ana Yemek", 35,
                   "Sebzeli, hafif baharatlı nefis bir tavuk sote.", "Kolay")
        t2.malzemeler = [
            Malzeme("Tavuk but", 4, "adet"), Malzeme("Soğan", 2, "adet"),
            Malzeme("Domates", 3, "adet"), Malzeme("Zeytinyağı", 3, "yemek kaşığı"),
        ]
        t2.adimlar = [
            "Tavukları küp doğrayın.", "Yağda soğanları kavurun.",
            "Tavukları ekleyip mühürleyin.", "Domates ekleyip 20 dk pişirin.",
        ]
        self.tarifler[t2.id] = t2
        t2.degerlendir(5, "Çok başarılı!", "Ayşe")

        t3 = Tarif("Mercimek Çorbası", "Çorba", 25,
                   "Geleneksel Türk mutfağının vazgeçilmezi.", "Kolay")
        t3.malzemeler = [
            Malzeme("Kırmızı mercimek", 1, "su bardağı"), Malzeme("Soğan", 1, "adet"),
            Malzeme("Havuç", 1, "adet"), Malzeme("Tereyağı", 1, "yemek kaşığı"),
        ]
        t3.adimlar = [
            "Soğan ve havucu kavurun.", "Mercimeği ekleyip haşlayın.",
            "Blender ile püre yapın.", "Üzerine kırmızı biberli tereyağı dökün.",
        ]
        self.tarifler[t3.id] = t3
        t3.degerlendir(5, "Tam kıvamında!", "Mehmet")
        t3.degerlendir(5, "Enfes.", "Ayşe")

        u1.favoriye_ekle(t2.id)
        u2.favoriye_ekle(t1.id)

    def kullanici_ekle(self, ad) -> Kullanici:
        k = Kullanici(ad)
        self.kullanicilar[k.id] = k
        return k

    def tarif_ekle(self, tarif: Tarif):
        self.tarifler[tarif.id] = tarif

    def tarif_sil(self, tarif_id: int):
        if tarif_id in self.tarifler:
            del self.tarifler[tarif_id]
            for k in self.kullanicilar.values():
                k.favoriden_cikar(tarif_id)

    def ara(self, sorgu):
        s = sorgu.lower()
        return [t for t in self.tarifler.values()
                if s in t.adi.lower() or s in t.kategori.lower()
                or s in t.aciklama.lower()
                or any(s in m.adi.lower() for m in t.malzemeler)]

    def kategori_filtrele(self, kat, siralama="puan"):
        if kat == "Tümü":
            tarifler = list(self.tarifler.values())
        else:
            tarifler = [t for t in self.tarifler.values() if t.kategori == kat]
        return self._sirala(tarifler, siralama)

    def _sirala(self, tarifler, siralama):
        if siralama == "puan":
            return sorted(tarifler, key=lambda t: t.ortalama_puan(), reverse=True)
        elif siralama == "sure_asc":
            return sorted(tarifler, key=lambda t: t.sure)
        elif siralama == "sure_desc":
            return sorted(tarifler, key=lambda t: t.sure, reverse=True)
        elif siralama == "ad":
            return sorted(tarifler, key=lambda t: t.adi.lower())
        return tarifler

    def en_iyiler(self, n=6):
        return sorted(self.tarifler.values(),
                      key=lambda t: t.ortalama_puan(), reverse=True)[:n]

    def favoriler(self, kullanici: Kullanici):
        return [self.tarifler[fid] for fid in kullanici.favoriler if fid in self.tarifler]

    def istatistik(self):
        return {
            "toplam": len(self.tarifler),
            "yuksek_puan": sum(1 for t in self.tarifler.values() if t.ortalama_puan() >= 4.5),
            "toplam_malzeme": sum(len(t.malzemeler) for t in self.tarifler.values()),
        }


# ═══════════════════════════════════════════════════════════════════
#  API KATMANI — TheMealDB
# ═══════════════════════════════════════════════════════════════════

MEALDB_BASE = "https://www.themealdb.com/api/json/v1/1"

KATEGORI_MAP = {
    "Beef":          "Ana Yemek",
    "Chicken":       "Ana Yemek",
    "Lamb":          "Ana Yemek",
    "Pork":          "Ana Yemek",
    "Seafood":       "Ana Yemek",
    "Pasta":         "Ana Yemek",
    "Vegetarian":    "Ana Yemek",
    "Vegan":         "Salata",
    "Side":          "Salata",
    "Starter":       "Atıştırmalık",
    "Dessert":       "Tatlı",
    "Breakfast":     "Kahvaltı",
    "Soup":          "Çorba",
    "Miscellaneous": "Ana Yemek",
}


def api_get(url: str, timeout: int = 10) -> dict:
    """Senkron GET isteği — QThread içinde çağrılır."""
    req = urllib.request.Request(url, headers={"User-Agent": "TarifDunyasi/3.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def meal_to_tarif(meal: dict) -> Tarif:
    """TheMealDB meal dict → Tarif nesnesi dönüşümü."""
    kat_ing = meal.get("strCategory", "")
    kategori = KATEGORI_MAP.get(kat_ing, "Ana Yemek")

    area = meal.get("strArea", "")
    aciklama = meal.get("strInstructions", "")[:300].strip()
    if area:
        aciklama = f"🌍 {area} mutfağından — " + aciklama

    tarif = Tarif(
        adi=meal.get("strMeal", ""),
        kategori=kategori,
        sure=30,
        aciklama=aciklama,
        zorluk="Orta",
    )
    tarif.gorsel_url = meal.get("strMealThumb", "")

    for i in range(1, 21):
        ing = (meal.get(f"strIngredient{i}") or "").strip()
        meas = (meal.get(f"strMeasure{i}") or "").strip()
        if not ing:
            break
        parts = meas.split(None, 1)
        if parts:
            try:
                miktar = float(parts[0].replace(",", "."))
                birim = parts[1] if len(parts) > 1 else "adet"
            except ValueError:
                miktar = 1
                birim = meas or "adet"
        else:
            miktar = 1
            birim = "adet"
        tarif.malzemeler.append(Malzeme(ing, miktar, birim))

    instructions = meal.get("strInstructions", "")
    for satir in instructions.splitlines():
        satir = satir.strip()
        if satir and len(satir) > 10:
            tarif.adimlar.append(satir[:200])
        if len(tarif.adimlar) >= 12:
            break

    return tarif


# ── Worker sınıfları ─────────────────────────────────────────────

class ApiSinyaller(QObject):
    bitti    = pyqtSignal(list)
    hata     = pyqtSignal(str)
    yuklendi = pyqtSignal(bytes, str)


class ApiAramaWorker(QRunnable):
    def __init__(self, sorgu: str, sinyaller: ApiSinyaller):
        super().__init__()
        self.sorgu = sorgu
        self.sig = sinyaller
        self.setAutoDelete(True)

    @pyqtSlot()
    def run(self):
        try:
            url = f"{MEALDB_BASE}/search.php?s={urllib.parse.quote(self.sorgu)}"
            data = api_get(url)
            meals = data.get("meals") or []
            self.sig.bitti.emit([meal_to_tarif(m) for m in meals])
        except Exception as e:
            self.sig.hata.emit(str(e))


class ApiKategoriWorker(QRunnable):
    def __init__(self, kategori: str, sinyaller: ApiSinyaller):
        super().__init__()
        self.kategori = kategori
        self.sig = sinyaller
        self.setAutoDelete(True)

    @pyqtSlot()
    def run(self):
        try:
            url = f"{MEALDB_BASE}/filter.php?c={urllib.parse.quote(self.kategori)}"
            data = api_get(url)
            meals_summary = (data.get("meals") or [])[:12]
            tarifler = []
            for s in meals_summary:
                mid = s.get("idMeal", "")
                if not mid:
                    continue
                det = api_get(f"{MEALDB_BASE}/lookup.php?i={mid}")
                mlist = det.get("meals") or []
                if mlist:
                    tarifler.append(meal_to_tarif(mlist[0]))
            self.sig.bitti.emit(tarifler)
        except Exception as e:
            self.sig.hata.emit(str(e))


class ApiRastgeleWorker(QRunnable):
    def __init__(self, adet: int, sinyaller: ApiSinyaller):
        super().__init__()
        self.adet = adet
        self.sig = sinyaller
        self.setAutoDelete(True)

    @pyqtSlot()
    def run(self):
        try:
            tarifler = []
            ids_seen = set()
            for _ in range(self.adet):
                data = api_get(f"{MEALDB_BASE}/random.php")
                meals = data.get("meals") or []
                if meals:
                    m = meals[0]
                    mid = m.get("idMeal")
                    if mid and mid not in ids_seen:
                        ids_seen.add(mid)
                        tarifler.append(meal_to_tarif(m))
            self.sig.bitti.emit(tarifler)
        except Exception as e:
            self.sig.hata.emit(str(e))


class GorselWorker(QRunnable):
    def __init__(self, url: str, meal_id: str, sinyaller: ApiSinyaller):
        super().__init__()
        self.url = url
        self.meal_id = meal_id
        self.sig = sinyaller
        self.setAutoDelete(True)

    @pyqtSlot()
    def run(self):
        try:
            req = urllib.request.Request(
                self.url + "/medium",
                headers={"User-Agent": "TarifDunyasi/3.0"}
            )
            with urllib.request.urlopen(req, timeout=8) as r:
                self.sig.yuklendi.emit(r.read(), self.meal_id)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════
#  ÖZEL WİDGET'LAR
# ═══════════════════════════════════════════════════════════════════

def temizle_layout(widget):
    eski = widget.layout()
    if eski is not None:
        while eski.count():
            item = eski.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        eski.deleteLater()


class AyiriciCizgi(QFrame):
    def __init__(self, dikey=False):
        super().__init__()
        if dikey:
            self.setFrameShape(QFrame.VLine)
            self.setFixedWidth(1)
        else:
            self.setFrameShape(QFrame.HLine)
            self.setFixedHeight(1)
        self.setStyleSheet(f"color:{RENKLER['border']}; background:{RENKLER['border']};")


class ModernButon(QPushButton):
    def __init__(self, text, birincil=True, kucuk=False, tehlikeli=False, api=False):
        super().__init__(text)
        self.setCursor(Qt.PointingHandCursor)
        h = "34px" if kucuk else "42px"
        px = "14px" if kucuk else "22px"
        fs = "13px" if kucuk else "14px"

        if tehlikeli:
            bg, hover, pressed, color = RENKLER['danger'], "#C0392B", "#A93226", "white"
        elif api:
            bg, hover, pressed, color = RENKLER['api_accent'], "#17A589", "#148F77", "white"
        elif birincil:
            bg, hover, pressed, color = RENKLER['accent'], RENKLER['accent2'], "#E55A25", "white"
        else:
            bg, hover, pressed = RENKLER['bg_card2'], RENKLER['bg_input'], RENKLER['border']
            color = RENKLER['text_primary']

        border = "none" if (birincil or tehlikeli or api) else f"1px solid {RENKLER['border']}"
        self.setStyleSheet(f"""
            QPushButton {{
                background:{bg}; color:{color}; border:{border};
                border-radius:10px; padding:0 {px}; height:{h};
                font-size:{fs}; font-weight:600; letter-spacing:0.3px;
            }}
            QPushButton:hover {{ background:{hover}; }}
            QPushButton:pressed {{ background:{pressed}; }}
            QPushButton:disabled {{ background:{RENKLER['bg_card2']}; color:{RENKLER['text_hint']}; }}
        """)


class EtiketBadge(QLabel):
    RENK_MAP = {
        "accent":  ("#3D2318", "#FF8C5A"),
        "success": ("#1A3D2B", "#2ECC71"),
        "warning": ("#3D2E0A", "#F39C12"),
        "danger":  ("#3D1010", "#E74C3C"),
        "info":    ("#162033", "#5DADE2"),
        "purple":  ("#2A1A3D", "#9B59B6"),
        "api":     ("#0D2E28", "#1ABC9C"),
    }

    def __init__(self, text, renk="accent"):
        super().__init__(text)
        bg, fg = self.RENK_MAP.get(renk, self.RENK_MAP["accent"])
        self.setStyleSheet(f"""
            QLabel {{
                background:{bg}; color:{fg}; border-radius:6px;
                padding:3px 10px; font-size:12px; font-weight:600;
            }}
        """)
        self.setFixedHeight(24)


class StatKarti(QFrame):
    def __init__(self, ikon, deger, etiket, renk_kodu):
        super().__init__()
        self.setStyleSheet(f"""
            QFrame {{background:{RENKLER['bg_card']}; border:1px solid {RENKLER['border']}; border-radius:14px;}}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(4)
        il = QLabel(ikon)
        il.setStyleSheet("font-size:26px; background:transparent;")
        lay.addWidget(il)
        self.deger_lbl = QLabel(str(deger))
        self.deger_lbl.setStyleSheet(
            f"color:{renk_kodu}; font-size:30px; font-weight:800; background:transparent;")
        lay.addWidget(self.deger_lbl)
        el = QLabel(etiket)
        el.setStyleSheet(f"color:{RENKLER['text_secondary']}; font-size:13px; background:transparent;")
        lay.addWidget(el)

    def guncelle(self, v):
        self.deger_lbl.setText(str(v))


class TarifKarti(QFrame):
    kart_tiklandi = pyqtSignal(int)

    def __init__(self, tarif: Tarif, favori_ids=None):
        super().__init__()
        self.tarif = tarif
        self.favori_ids = favori_ids or []
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QFrame {{background:{RENKLER['bg_card']};border:1px solid {RENKLER['border']};border-radius:14px;}}
            QFrame:hover {{border:1px solid {RENKLER['accent_dim']};background:{RENKLER['bg_card2']};}}
        """)
        self._kur()

    def _kur(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(10)

        ust = QHBoxLayout()
        ust.addWidget(EtiketBadge(self.tarif.kategori, "info"))
        ust.addWidget(EtiketBadge(self.tarif.zorluk, self.tarif.zorluk_renk()))
        ust.addStretch()
        kalp = QLabel("❤" if self.tarif.id in self.favori_ids else "♡")
        kalp.setStyleSheet(f"color:{RENKLER['danger']}; font-size:16px; background:transparent;")
        ust.addWidget(kalp)
        sl = QLabel(f"⏱ {self.tarif.sure} dk")
        sl.setStyleSheet(f"color:{RENKLER['text_secondary']}; font-size:12px; background:transparent;")
        ust.addWidget(sl)
        lay.addLayout(ust)

        adi = QLabel(self.tarif.adi)
        adi.setStyleSheet(f"color:{RENKLER['text_primary']}; font-size:16px; font-weight:700; background:transparent;")
        adi.setWordWrap(True)
        lay.addWidget(adi)

        if self.tarif.aciklama:
            acik = QLabel(self.tarif.aciklama[:85] + ("…" if len(self.tarif.aciklama) > 85 else ""))
            acik.setStyleSheet(f"color:{RENKLER['text_secondary']}; font-size:13px; background:transparent;")
            acik.setWordWrap(True)
            lay.addWidget(acik)

        lay.addWidget(AyiriciCizgi())
        alt = QHBoxLayout()
        yl = QLabel(f"{self.tarif.yildiz_str()}  {self.tarif.ortalama_puan()}")
        yl.setStyleSheet(f"color:{RENKLER['star']}; font-size:13px; background:transparent;")
        alt.addWidget(yl)
        alt.addStretch()
        ml = QLabel(f"🧂 {len(self.tarif.malzemeler)} malzeme")
        ml.setStyleSheet(f"color:{RENKLER['text_hint']}; font-size:12px; background:transparent;")
        alt.addWidget(ml)
        lay.addLayout(alt)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.kart_tiklandi.emit(self.tarif.id)


class ApiTarifKarti(QFrame):
    """API'den gelen tarif önizleme kartı (3 sütunlu grid için)."""
    kaydet_istendi = pyqtSignal(object)

    def __init__(self, tarif: Tarif):
        super().__init__()
        self.tarif = tarif
        self.setStyleSheet(f"""
            QFrame {{
                background:{RENKLER['bg_card']};
                border:1px solid {RENKLER['border']};
                border-radius:14px;
            }}
            QFrame:hover {{
                border:1px solid {RENKLER['api_dim']};
                background:{RENKLER['bg_card2']};
            }}
        """)
        self._kur()

    def _kur(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)

        # Görsel placeholder
        self.gorsel_lbl = QLabel("📸")
        self.gorsel_lbl.setAlignment(Qt.AlignCenter)
        self.gorsel_lbl.setFixedHeight(120)
        self.gorsel_lbl.setStyleSheet(f"""
            background:{RENKLER['bg_card2']};
            border-radius:10px;
            font-size:36px;
        """)
        lay.addWidget(self.gorsel_lbl)

        ust = QHBoxLayout()
        ust.addWidget(EtiketBadge("🌐 TheMealDB", "api"))
        ust.addStretch()
        ust.addWidget(EtiketBadge(self.tarif.kategori, "info"))
        lay.addLayout(ust)

        adi = QLabel(self.tarif.adi)
        adi.setStyleSheet(f"color:{RENKLER['text_primary']}; font-size:15px; font-weight:700; background:transparent;")
        adi.setWordWrap(True)
        lay.addWidget(adi)

        meta = QHBoxLayout()
        ml = QLabel(f"🧂 {len(self.tarif.malzemeler)} malzeme")
        ml.setStyleSheet(f"color:{RENKLER['text_hint']}; font-size:12px; background:transparent;")
        meta.addWidget(ml)
        meta.addStretch()
        al = QLabel(f"📋 {len(self.tarif.adimlar)} adım")
        al.setStyleSheet(f"color:{RENKLER['text_hint']}; font-size:12px; background:transparent;")
        meta.addWidget(al)
        lay.addLayout(meta)

        kaydet_btn = ModernButon("＋ Platforma Kaydet", api=True, kucuk=True)
        kaydet_btn.clicked.connect(lambda: self.kaydet_istendi.emit(self.tarif))
        lay.addWidget(kaydet_btn)

    def gorsel_yukle(self, pixmap: QPixmap):
        scaled = pixmap.scaled(
            self.gorsel_lbl.width() or 200, 120,
            Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
        )
        self.gorsel_lbl.setPixmap(scaled)
        self.gorsel_lbl.setScaledContents(False)


class NavButon(QPushButton):
    def __init__(self, icon_text, label, aktif=False):
        super().__init__()
        self._aktif = aktif
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(True)
        self.setChecked(aktif)
        self._guncelle_stil()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.setSpacing(10)
        self.icon_lbl = QLabel(icon_text)
        self.icon_lbl.setStyleSheet("font-size:18px; background:transparent; border:none;")
        self.text_lbl = QLabel(label)
        rk = RENKLER['text_primary'] if aktif else RENKLER['text_secondary']
        self.text_lbl.setStyleSheet(
            f"font-size:14px; font-weight:600; background:transparent; border:none; color:{rk};")
        lay.addWidget(self.icon_lbl); lay.addWidget(self.text_lbl); lay.addStretch()
        self.setFixedHeight(48)
        self.toggled.connect(self._on_toggle)

    def _guncelle_stil(self):
        a = self._aktif
        self.setStyleSheet(f"""
            QPushButton {{
                background:{"rgba(255,107,53,0.12)" if a else "transparent"};
                border:none;
                border-left:{"3px solid " + RENKLER['accent'] if a else "3px solid transparent"};
                border-radius:10px; text-align:left;
            }}
            QPushButton:hover {{ background:rgba(255,107,53,0.07); }}
        """)

    def _on_toggle(self, checked):
        self._aktif = checked
        rk = RENKLER['text_primary'] if checked else RENKLER['text_secondary']
        if hasattr(self, 'text_lbl'):
            self.text_lbl.setStyleSheet(
                f"font-size:14px; font-weight:600; background:transparent; border:none; color:{rk};")
        self._guncelle_stil()

    def aktif_yap(self):
        self.setChecked(True); self._aktif = True; self._on_toggle(True)

    def pasif_yap(self):
        self.setChecked(False); self._aktif = False; self._on_toggle(False)


# ═══════════════════════════════════════════════════════════════════
#  SAYFA: ANASAYFA
# ═══════════════════════════════════════════════════════════════════

class AnasayfaSayfasi(QWidget):
    tarif_sec = pyqtSignal(int)

    def __init__(self, platform: Platform):
        super().__init__()
        self.platform = platform
        self._kur()

    def _kur(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(22)

        baslik_row = QHBoxLayout()
        baslik = QLabel("Bugün Ne Pişirelim? 🍽")
        baslik.setStyleSheet(
            f"color:{RENKLER['text_primary']}; font-size:26px; font-weight:800; background:transparent;")
        baslik_row.addWidget(baslik)
        baslik_row.addStretch()
        kul_lbl = QLabel(f"👤 {self.platform.aktif_kullanici.ad}")
        kul_lbl.setStyleSheet(f"color:{RENKLER['text_secondary']}; font-size:13px; background:transparent;")
        baslik_row.addWidget(kul_lbl)
        lay.addLayout(baslik_row)

        ist = self.platform.istatistik()
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        self.stat_kartlar = []
        for ikon, deger, etiket, rk in [
            ("📖", ist["toplam"],         "Toplam Tarif",  RENKLER['accent']),
            ("⭐", ist["yuksek_puan"],    "Yüksek Puanlı", RENKLER['star']),
            ("🧂", ist["toplam_malzeme"], "Toplam Malzeme",RENKLER['success']),
            ("👥", len(self.platform.kullanicilar), "Kullanıcı", RENKLER['blue']),
        ]:
            kart = StatKarti(ikon, deger, etiket, rk)
            self.stat_kartlar.append(kart)
            stats_row.addWidget(kart)
        lay.addLayout(stats_row)

        en_iyi_baslik = QLabel("✨ En Beğenilen Tarifler")
        en_iyi_baslik.setStyleSheet(
            f"color:{RENKLER['text_primary']}; font-size:18px; font-weight:700; background:transparent;")
        lay.addWidget(en_iyi_baslik)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("background:transparent; border:none;")
        self.icerik_widget = QWidget()
        self.icerik_widget.setStyleSheet("background:transparent;")
        self._kart_guncelle()
        self.scroll.setWidget(self.icerik_widget)
        lay.addWidget(self.scroll)

    def _kart_guncelle(self):
        temizle_layout(self.icerik_widget)
        grid = QGridLayout(self.icerik_widget)
        grid.setSpacing(14)
        grid.setContentsMargins(0, 0, 0, 0)
        fav = self.platform.aktif_kullanici.favoriler
        for i, t in enumerate(self.platform.en_iyiler(6)):
            k = TarifKarti(t, fav)
            k.kart_tiklandi.connect(self.tarif_sec)
            grid.addWidget(k, i // 2, i % 2)

    def yenile(self):
        self._kart_guncelle()
        ist = self.platform.istatistik()
        vals = [ist["toplam"], ist["yuksek_puan"], ist["toplam_malzeme"],
                len(self.platform.kullanicilar)]
        for kart, v in zip(self.stat_kartlar, vals):
            kart.guncelle(v)


# ═══════════════════════════════════════════════════════════════════
#  SAYFA: TARİF LİSTESİ
# ═══════════════════════════════════════════════════════════════════

class TarifListesiSayfasi(QWidget):
    tarif_sec = pyqtSignal(int)

    def __init__(self, platform: Platform):
        super().__init__()
        self.platform = platform
        self._kur()

    def _kur(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(16)

        ust = QHBoxLayout()
        baslik = QLabel("Tüm Tarifler")
        baslik.setStyleSheet(
            f"color:{RENKLER['text_primary']}; font-size:24px; font-weight:800; background:transparent;")
        ust.addWidget(baslik)
        ust.addStretch()
        self.ekle_btn = ModernButon("＋ Yeni Tarif", birincil=True)
        self.ekle_btn.setFixedWidth(130)
        self.ekle_btn.clicked.connect(self._tarif_ekle_diyalog)
        ust.addWidget(self.ekle_btn)
        lay.addLayout(ust)

        filtre = QHBoxLayout()
        filtre.setSpacing(10)
        self.arama = QLineEdit()
        self.arama.setPlaceholderText("🔍  Tarif veya malzeme ara...")
        self.arama.textChanged.connect(self._filtrele)
        filtre.addWidget(self.arama, 3)
        self.kat_combo = QComboBox()
        self.kat_combo.addItem("Tümü")
        self.kat_combo.addItems(self.platform.kategoriler)
        self.kat_combo.currentTextChanged.connect(self._filtrele)
        filtre.addWidget(self.kat_combo, 1)
        self.sir_combo = QComboBox()
        self.sir_combo.addItems(["Puana Göre", "Süre (Az→Çok)", "Süre (Çok→Az)", "Ada Göre"])
        self.sir_combo.currentIndexChanged.connect(self._filtrele)
        filtre.addWidget(self.sir_combo, 1)
        lay.addLayout(filtre)

        self.sonuc_lbl = QLabel("")
        self.sonuc_lbl.setStyleSheet(
            f"color:{RENKLER['text_hint']}; font-size:13px; background:transparent;")
        lay.addWidget(self.sonuc_lbl)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("background:transparent; border:none;")
        self.liste_icerik = QWidget()
        self.liste_icerik.setStyleSheet("background:transparent;")
        self.scroll.setWidget(self.liste_icerik)
        lay.addWidget(self.scroll)
        self._liste_yenile()

    def _siralama_kodu(self):
        return ["puan", "sure_asc", "sure_desc", "ad"][self.sir_combo.currentIndex()]

    def _liste_yenile(self, tarifler=None):
        temizle_layout(self.liste_icerik)
        grid = QGridLayout(self.liste_icerik)
        grid.setSpacing(14)
        grid.setContentsMargins(0, 0, 6, 12)

        if tarifler is None:
            tarifler = self.platform.kategori_filtrele("Tümü", self._siralama_kodu())

        self.sonuc_lbl.setText(f"{len(tarifler)} tarif bulundu")

        if not tarifler:
            bos = QLabel("Hiç tarif bulunamadı 🍽")
            bos.setAlignment(Qt.AlignCenter)
            bos.setStyleSheet(f"color:{RENKLER['text_hint']}; font-size:16px;")
            grid.addWidget(bos, 0, 0, 1, 2)
            return

        fav = self.platform.aktif_kullanici.favoriler
        for i, t in enumerate(tarifler):
            k = TarifKarti(t, fav)
            k.kart_tiklandi.connect(self.tarif_sec)
            grid.addWidget(k, i // 2, i % 2)

    def _filtrele(self):
        sorgu = self.arama.text().strip()
        kat = self.kat_combo.currentText()
        sir = self._siralama_kodu()
        tarifler = (self.platform._sirala(self.platform.ara(sorgu), sir)
                    if sorgu else self.platform.kategori_filtrele(kat, sir))
        self._liste_yenile(tarifler)

    def _tarif_ekle_diyalog(self):
        dlg = TarifEkleDiyalogu(self.platform, self)
        if dlg.exec_() == QDialog.Accepted:
            self._liste_yenile()

    def yenile(self):
        self._liste_yenile()


# ═══════════════════════════════════════════════════════════════════
#  SAYFA: FAVORİLER
# ═══════════════════════════════════════════════════════════════════

class FavorilerSayfasi(QWidget):
    tarif_sec = pyqtSignal(int)

    def __init__(self, platform: Platform):
        super().__init__()
        self.platform = platform
        self._kur()

    def _kur(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(20)
        baslik = QLabel("❤  Favorilerim")
        baslik.setStyleSheet(
            f"color:{RENKLER['text_primary']}; font-size:24px; font-weight:800; background:transparent;")
        lay.addWidget(baslik)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("background:transparent; border:none;")
        self.icerik = QWidget()
        self.icerik.setStyleSheet("background:transparent;")
        self.scroll.setWidget(self.icerik)
        lay.addWidget(self.scroll)
        self._liste_yenile()

    def _liste_yenile(self):
        temizle_layout(self.icerik)
        grid = QGridLayout(self.icerik)
        grid.setSpacing(14)
        grid.setContentsMargins(0, 0, 6, 12)
        tarifler = self.platform.favoriler(self.platform.aktif_kullanici)
        if not tarifler:
            bos = QLabel("Henüz favori tarif yok ❤\nTarif detayından favoriye ekleyebilirsiniz.")
            bos.setAlignment(Qt.AlignCenter)
            bos.setStyleSheet(f"color:{RENKLER['text_hint']}; font-size:15px;")
            grid.addWidget(bos, 0, 0)
            return
        fav = self.platform.aktif_kullanici.favoriler
        for i, t in enumerate(tarifler):
            k = TarifKarti(t, fav)
            k.kart_tiklandi.connect(self.tarif_sec)
            grid.addWidget(k, i // 2, i % 2)

    def yenile(self):
        self._liste_yenile()


# ═══════════════════════════════════════════════════════════════════
#  SAYFA: API'DEN KEŞFET
# ═══════════════════════════════════════════════════════════════════

MEALDB_KATEGORILER = [
    "Beef", "Chicken", "Dessert", "Lamb", "Miscellaneous",
    "Pasta", "Pork", "Seafood", "Side", "Starter",
    "Vegan", "Vegetarian", "Breakfast", "Soup",
]


class KesfetSayfasi(QWidget):
    tarif_kaydedildi = pyqtSignal()

    def __init__(self, platform: Platform):
        super().__init__()
        self.platform = platform
        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(4)
        self._gorsel_onbellek: dict = {}
        self._api_kart_map: dict = {}
        self._kur()

    def _kur(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(18)

        # Başlık
        baslik_row = QHBoxLayout()
        baslik = QLabel("🌐  API'den Keşfet")
        baslik.setStyleSheet(
            f"color:{RENKLER['text_primary']}; font-size:24px; font-weight:800; background:transparent;")
        baslik_row.addWidget(baslik)
        baslik_row.addStretch()
        baslik_row.addWidget(EtiketBadge("TheMealDB  •  Ücretsiz", "api"))
        lay.addLayout(baslik_row)

        aciklama = QLabel(
            "Dünya mutfaklarından 300+ tarife anında erişin. "
            "Görsel önizleme ile istediğiniz tarifi tek tıkla kütüphanenize ekleyin."
        )
        aciklama.setStyleSheet(
            f"color:{RENKLER['text_secondary']}; font-size:13px; background:transparent;")
        aciklama.setWordWrap(True)
        lay.addWidget(aciklama)

        # Arama kartı
        arama_kart = QFrame()
        arama_kart.setStyleSheet(f"""
            QFrame {{
                background:{RENKLER['bg_card']};
                border:1px solid {RENKLER['border']};
                border-radius:14px;
            }}
        """)
        ak = QVBoxLayout(arama_kart)
        ak.setContentsMargins(20, 16, 20, 16)
        ak.setSpacing(12)

        # Satır 1: metin arama
        s1 = QHBoxLayout()
        s1.setSpacing(10)
        self.arama_input = QLineEdit()
        self.arama_input.setPlaceholderText("🔍  Tarif adı ara (İngilizce)  —  örn: chicken, pasta, soup, beef...")
        self.arama_input.returnPressed.connect(self._ara)
        s1.addWidget(self.arama_input, 1)
        ara_btn = ModernButon("Ara", api=True)
        ara_btn.setFixedWidth(90)
        ara_btn.clicked.connect(self._ara)
        s1.addWidget(ara_btn)
        ak.addLayout(s1)

        # Satır 2: kategori + rastgele
        s2 = QHBoxLayout()
        s2.setSpacing(10)
        kl = QLabel("Kategori:")
        kl.setStyleSheet(f"color:{RENKLER['text_secondary']}; font-size:13px; background:transparent;")
        s2.addWidget(kl)
        self.kat_combo = QComboBox()
        self.kat_combo.addItems(MEALDB_KATEGORILER)
        s2.addWidget(self.kat_combo, 1)
        kat_btn = ModernButon("Kategoriye Göre Getir", api=True)
        kat_btn.setFixedWidth(195)
        kat_btn.clicked.connect(self._kategori_getir)
        s2.addWidget(kat_btn)
        s2.addSpacing(12)
        rand_btn = ModernButon("🎲 Rastgele 6 Tarif", birincil=False)
        rand_btn.setFixedWidth(165)
        rand_btn.clicked.connect(self._rastgele)
        s2.addWidget(rand_btn)
        ak.addLayout(s2)
        lay.addWidget(arama_kart)

        # İlerleme + durum
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFixedHeight(4)
        self.progress.setVisible(False)
        lay.addWidget(self.progress)

        self.durum_lbl = QLabel("")
        self.durum_lbl.setStyleSheet(
            f"color:{RENKLER['text_hint']}; font-size:13px; background:transparent;")
        lay.addWidget(self.durum_lbl)

        # Sonuç alanı
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("background:transparent; border:none;")
        self.sonuc_widget = QWidget()
        self.sonuc_widget.setStyleSheet("background:transparent;")
        self.scroll.setWidget(self.sonuc_widget)
        lay.addWidget(self.scroll)

        self._bos_goster("Yukarıdan arama yapın veya bir kategori seçin 🍽")

    # ── API çağrıları ─────────────────────────────────────────────

    def _baslat_yukleme(self, mesaj="Tarifler yükleniyor..."):
        self.progress.setVisible(True)
        self.durum_lbl.setText(f"⏳  {mesaj}")
        self._bos_goster("")

    def _bitis_yukleme(self):
        self.progress.setVisible(False)

    def _yeni_sinyaller(self) -> ApiSinyaller:
        sig = ApiSinyaller()
        sig.bitti.connect(self._sonuclari_goster)
        sig.hata.connect(self._hata_goster)
        return sig

    def _ara(self):
        sorgu = self.arama_input.text().strip()
        if not sorgu:
            return
        self._baslat_yukleme(f'"{sorgu}" aranıyor...')
        self.thread_pool.start(ApiAramaWorker(sorgu, self._yeni_sinyaller()))

    def _kategori_getir(self):
        kat = self.kat_combo.currentText()
        self._baslat_yukleme(f"{kat} kategorisi yükleniyor... (birkaç saniye sürebilir)")
        self.thread_pool.start(ApiKategoriWorker(kat, self._yeni_sinyaller()))

    def _rastgele(self):
        self._baslat_yukleme("Rastgele tarifler seçiliyor...")
        self.thread_pool.start(ApiRastgeleWorker(6, self._yeni_sinyaller()))

    # ── Sonuç gösterimi ───────────────────────────────────────────

    def _sonuclari_goster(self, tarifler: list):
        self._bitis_yukleme()
        if not tarifler:
            self.durum_lbl.setText("⚠  Sonuç bulunamadı. Farklı bir arama deneyin.")
            self._bos_goster("Sonuç bulunamadı 🔍")
            return

        self.durum_lbl.setText(f"✅  {len(tarifler)} tarif bulundu")
        temizle_layout(self.sonuc_widget)
        self._api_kart_map.clear()

        grid = QGridLayout(self.sonuc_widget)
        grid.setSpacing(14)
        grid.setContentsMargins(0, 0, 6, 12)

        for i, tarif in enumerate(tarifler):
            kart = ApiTarifKarti(tarif)
            kart.kaydet_istendi.connect(self._tarif_kaydet)
            grid.addWidget(kart, i // 3, i % 3)

            if tarif.gorsel_url:
                if tarif.gorsel_url in self._gorsel_onbellek:
                    kart.gorsel_yukle(self._gorsel_onbellek[tarif.gorsel_url])
                else:
                    self._api_kart_map[tarif.gorsel_url] = kart
                    gs = ApiSinyaller()
                    gs.yuklendi.connect(self._gorsel_guncelle)
                    self.thread_pool.start(GorselWorker(tarif.gorsel_url, tarif.gorsel_url, gs))

    def _gorsel_guncelle(self, data: bytes, url: str):
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            self._gorsel_onbellek[url] = pixmap
            kart = self._api_kart_map.get(url)
            if kart:
                kart.gorsel_yukle(pixmap)

    def _hata_goster(self, mesaj: str):
        self._bitis_yukleme()
        self.durum_lbl.setText("❌  Bağlantı hatası — internet bağlantınızı kontrol edin")
        QMessageBox.warning(
            self, "API Bağlantı Hatası",
            f"TheMealDB'ye erişilemedi:\n\n{mesaj}\n\n"
            "İnternet bağlantınızı kontrol edip tekrar deneyin."
        )

    def _bos_goster(self, mesaj: str):
        temizle_layout(self.sonuc_widget)
        if mesaj:
            lay = QVBoxLayout(self.sonuc_widget)
            lbl = QLabel(mesaj)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"color:{RENKLER['text_hint']}; font-size:15px;")
            lay.addStretch()
            lay.addWidget(lbl)
            lay.addStretch()

    def _tarif_kaydet(self, tarif: Tarif):
        for t in self.platform.tarifler.values():
            if t.adi.strip().lower() == tarif.adi.strip().lower():
                QMessageBox.information(
                    self, "Zaten Mevcut",
                    f"'{tarif.adi}' zaten kütüphanenizde mevcut."
                )
                return
        self.platform.tarif_ekle(tarif)
        self.tarif_kaydedildi.emit()
        QMessageBox.information(
            self, "Kaydedildi ✅",
            f"'{tarif.adi}' kütüphanenize eklendi!\n\n"
            f"📋 {len(tarif.malzemeler)} malzeme  •  "
            f"👨‍🍳 {len(tarif.adimlar)} hazırlama adımı\n\n"
            "Tarifler sayfasından görebilirsiniz."
        )


# ═══════════════════════════════════════════════════════════════════
#  SAYFA: TARİF DETAY
# ═══════════════════════════════════════════════════════════════════

class TarifDetaySayfasi(QWidget):
    geri_don = pyqtSignal()
    tarif_silindi = pyqtSignal(int)
    favori_degisti = pyqtSignal()

    def __init__(self, platform: Platform):
        super().__init__()
        self.platform = platform
        self.tarif: Tarif = None
        self.ana_lay = QVBoxLayout(self)
        self.ana_lay.setContentsMargins(32, 28, 32, 28)
        self.ana_lay.setSpacing(0)
        self.icerik_widget = QWidget()
        self.icerik_widget.setStyleSheet("background:transparent;")
        self.ana_lay.addWidget(self.icerik_widget)

    def tarifi_goster(self, tarif_id: int):
        self.tarif = self.platform.tarifler.get(tarif_id)
        if not self.tarif:
            return
        temizle_layout(self.icerik_widget)
        lay = QVBoxLayout(self.icerik_widget)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(16)

        # Toolbar
        toolbar = QHBoxLayout()
        geri = ModernButon("← Geri", birincil=False, kucuk=True)
        geri.setFixedWidth(90)
        geri.clicked.connect(self.geri_don)
        toolbar.addWidget(geri)
        toolbar.addStretch()

        fav_ids = self.platform.aktif_kullanici.favoriler
        fav_txt = "❤  Favoriden Çıkar" if tarif_id in fav_ids else "♡  Favoriye Ekle"
        self.fav_btn = ModernButon(fav_txt, birincil=False, kucuk=True)
        self.fav_btn.setFixedWidth(160)
        self.fav_btn.clicked.connect(self._favori_toggle)
        toolbar.addWidget(self.fav_btn)

        duz_btn = ModernButon("✏  Düzenle", birincil=False, kucuk=True)
        duz_btn.setFixedWidth(100)
        duz_btn.clicked.connect(self._duzenle)
        toolbar.addWidget(duz_btn)

        sil_btn = ModernButon("🗑  Sil", tehlikeli=True, kucuk=True)
        sil_btn.setFixedWidth(80)
        sil_btn.clicked.connect(self._sil)
        toolbar.addWidget(sil_btn)
        lay.addLayout(toolbar)

        # Scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background:transparent; border:none;")
        icerik = QWidget()
        icerik.setStyleSheet("background:transparent;")
        ilay = QVBoxLayout(icerik)
        ilay.setContentsMargins(0, 0, 8, 24)
        ilay.setSpacing(20)

        # Başlık kartı
        bk = QFrame()
        bk.setStyleSheet(f"""
            QFrame {{background:{RENKLER['bg_card']};border:1px solid {RENKLER['border']};border-radius:16px;}}
        """)
        bkl = QVBoxLayout(bk)
        bkl.setContentsMargins(24, 20, 24, 20)
        bkl.setSpacing(12)

        ust = QHBoxLayout()
        ust.setSpacing(8)
        ust.addWidget(EtiketBadge(self.tarif.kategori, "info"))
        ust.addWidget(EtiketBadge(self.tarif.zorluk, self.tarif.zorluk_renk()))
        if self.tarif.gorsel_url:
            ust.addWidget(EtiketBadge("🌐 API", "api"))
        ust.addStretch()
        sl = QLabel(f"⏱  {self.tarif.sure} dakika")
        sl.setStyleSheet(f"color:{RENKLER['text_secondary']}; font-size:14px; background:transparent;")
        ust.addWidget(sl)
        bkl.addLayout(ust)

        al = QLabel(self.tarif.adi)
        al.setStyleSheet(
            f"color:{RENKLER['text_primary']}; font-size:26px; font-weight:800; background:transparent;")
        al.setWordWrap(True)
        bkl.addWidget(al)

        if self.tarif.aciklama:
            acl = QLabel(self.tarif.aciklama[:400])
            acl.setStyleSheet(f"color:{RENKLER['text_secondary']}; font-size:14px; background:transparent;")
            acl.setWordWrap(True)
            bkl.addWidget(acl)

        bkl.addWidget(AyiriciCizgi())
        pr = QHBoxLayout()
        yl = QLabel(f"{self.tarif.yildiz_str()}  {self.tarif.ortalama_puan()}/5")
        yl.setStyleSheet(f"color:{RENKLER['star']}; font-size:16px; font-weight:600; background:transparent;")
        pr.addWidget(yl)
        pr.addStretch()
        ds = QLabel(f"{len(self.tarif.degerlendirmeler)} değerlendirme")
        ds.setStyleSheet(f"color:{RENKLER['text_hint']}; font-size:13px; background:transparent;")
        pr.addWidget(ds)
        bkl.addLayout(pr)
        ilay.addWidget(bk)

        # Malzemeler
        if self.tarif.malzemeler:
            mr = QHBoxLayout()
            mb = QLabel("🧂  Malzemeler")
            mb.setStyleSheet(
                f"color:{RENKLER['text_primary']}; font-size:17px; font-weight:700; background:transparent;")
            mr.addWidget(mb)
            mr.addStretch()
            kopyala = ModernButon("📋 Kopyala", birincil=False, kucuk=True)
            kopyala.setFixedWidth(100)
            kopyala.clicked.connect(self._malzemeleri_kopyala)
            mr.addWidget(kopyala)
            ilay.addLayout(mr)

            mkart = QFrame()
            mkart.setStyleSheet(f"""
                QFrame {{background:{RENKLER['bg_card']};border:1px solid {RENKLER['border']};border-radius:14px;}}
            """)
            mkl = QVBoxLayout(mkart)
            mkl.setContentsMargins(20, 16, 20, 16)
            mkl.setSpacing(8)
            for i, m in enumerate(self.tarif.malzemeler):
                row = QHBoxLayout()
                dot = QLabel("•")
                dot.setStyleSheet(f"color:{RENKLER['accent']}; font-size:18px; background:transparent;")
                dot.setFixedWidth(16)
                row.addWidget(dot)
                mn = QLabel(m.adi)
                mn.setStyleSheet(f"color:{RENKLER['text_primary']}; font-size:14px; background:transparent;")
                row.addWidget(mn)
                row.addStretch()
                mv = QLabel(f"{m.miktar} {m.birim}")
                mv.setStyleSheet(f"color:{RENKLER['text_secondary']}; font-size:14px; background:transparent;")
                row.addWidget(mv)
                mkl.addLayout(row)
                if i < len(self.tarif.malzemeler) - 1:
                    mkl.addWidget(AyiriciCizgi())
            ilay.addWidget(mkart)

        # Hazırlama adımları
        if self.tarif.adimlar:
            ab = QLabel("👨‍🍳  Hazırlama Adımları")
            ab.setStyleSheet(
                f"color:{RENKLER['text_primary']}; font-size:17px; font-weight:700; background:transparent;")
            ilay.addWidget(ab)
            akart = QFrame()
            akart.setStyleSheet(f"""
                QFrame {{background:{RENKLER['bg_card']};border:1px solid {RENKLER['border']};border-radius:14px;}}
            """)
            akl = QVBoxLayout(akart)
            akl.setContentsMargins(20, 16, 20, 16)
            akl.setSpacing(12)
            for i, adim in enumerate(self.tarif.adimlar, 1):
                row = QHBoxLayout()
                row.setSpacing(12)
                num = QLabel(str(i))
                num.setFixedSize(28, 28)
                num.setAlignment(Qt.AlignCenter)
                num.setStyleSheet(f"""
                    background:{RENKLER['accent_dim']};color:{RENKLER['accent']};
                    border-radius:14px;font-size:13px;font-weight:700;
                """)
                row.addWidget(num)
                adim_lbl = QLabel(adim)
                adim_lbl.setStyleSheet(f"color:{RENKLER['text_primary']}; font-size:14px; background:transparent;")
                adim_lbl.setWordWrap(True)
                row.addWidget(adim_lbl, 1)
                akl.addLayout(row)
                if i < len(self.tarif.adimlar):
                    akl.addWidget(AyiriciCizgi())
            ilay.addWidget(akart)

        # Değerlendirmeler
        db = QLabel("💬  Değerlendirmeler")
        db.setStyleSheet(
            f"color:{RENKLER['text_primary']}; font-size:17px; font-weight:700; background:transparent;")
        ilay.addWidget(db)

        if self.tarif.degerlendirmeler:
            for puan, yorum, kullanici in reversed(self.tarif.degerlendirmeler):
                dk = QFrame()
                dk.setStyleSheet(f"""
                    QFrame {{background:{RENKLER['bg_card']};border:1px solid {RENKLER['border']};border-radius:12px;}}
                """)
                dkl = QVBoxLayout(dk)
                dkl.setContentsMargins(16, 14, 16, 14)
                dkl.setSpacing(6)
                ud = QHBoxLayout()
                kl = QLabel(f"👤 {kullanici}")
                kl.setStyleSheet(f"color:{RENKLER['text_primary']}; font-size:13px; font-weight:600; background:transparent;")
                ud.addWidget(kl)
                ud.addStretch()
                yl2 = QLabel("★" * puan + "☆" * (5 - puan))
                yl2.setStyleSheet(f"color:{RENKLER['star']}; font-size:14px; background:transparent;")
                ud.addWidget(yl2)
                dkl.addLayout(ud)
                if yorum:
                    yl3 = QLabel(yorum)
                    yl3.setStyleSheet(f"color:{RENKLER['text_secondary']}; font-size:13px; background:transparent;")
                    yl3.setWordWrap(True)
                    dkl.addWidget(yl3)
                ilay.addWidget(dk)
        else:
            bl = QLabel("Henüz değerlendirme yok. İlk siz olun! ⭐")
            bl.setStyleSheet(f"color:{RENKLER['text_hint']}; font-size:14px; background:transparent;")
            ilay.addWidget(bl)

        deg_btn = ModernButon("⭐ Değerlendir", birincil=True)
        deg_btn.clicked.connect(self._degerlendir)
        ilay.addWidget(deg_btn)
        ilay.addStretch()

        scroll.setWidget(icerik)
        lay.addWidget(scroll)

    def _malzemeleri_kopyala(self):
        if not self.tarif:
            return
        metin = f"📋 {self.tarif.adi} — Malzemeler\n\n"
        for m in self.tarif.malzemeler:
            metin += f"• {m.miktar} {m.birim} {m.adi}\n"
        QApplication.clipboard().setText(metin)
        QMessageBox.information(self, "Kopyalandı", "Malzeme listesi panoya kopyalandı! ✅")

    def _favori_toggle(self):
        if not self.tarif:
            return
        kul = self.platform.aktif_kullanici
        if self.tarif.id in kul.favoriler:
            kul.favoriden_cikar(self.tarif.id)
            self.fav_btn.setText("♡  Favoriye Ekle")
        else:
            kul.favoriye_ekle(self.tarif.id)
            self.fav_btn.setText("❤  Favoriden Çıkar")
        self.favori_degisti.emit()

    def _degerlendir(self):
        if not self.tarif:
            return
        dlg = DegerlendirmeDiyalogu(self.tarif, self)
        if dlg.exec_() == QDialog.Accepted:
            self.tarifi_goster(self.tarif.id)

    def _duzenle(self):
        if not self.tarif:
            return
        dlg = TarifEkleDiyalogu(self.platform, self, duzenle_tarif=self.tarif)
        if dlg.exec_() == QDialog.Accepted:
            self.tarifi_goster(self.tarif.id)

    def _sil(self):
        if not self.tarif:
            return
        cevap = QMessageBox.question(
            self, "Tarifi Sil",
            f"'{self.tarif.adi}' silinsin mi?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if cevap == QMessageBox.Yes:
            tid = self.tarif.id
            self.platform.tarif_sil(tid)
            self.tarif = None
            self.tarif_silindi.emit(tid)
            self.geri_don.emit()


# ═══════════════════════════════════════════════════════════════════
#  DİYALOGLAR
# ═══════════════════════════════════════════════════════════════════

class TarifEkleDiyalogu(QDialog):
    def __init__(self, platform: Platform, parent=None, duzenle_tarif: Tarif = None):
        super().__init__(parent)
        self.platform = platform
        self.duzenle = duzenle_tarif
        self.setWindowTitle("Tarifi Düzenle" if duzenle_tarif else "Yeni Tarif Ekle")
        self.setMinimumWidth(540)
        self.setMinimumHeight(600)
        self.setStyleSheet(f"""
            QDialog {{background:{RENKLER['bg_card']}; border-radius:16px;}}
            QLabel {{color:{RENKLER['text_primary']}; font-size:13px; font-weight:600; background:transparent;}}
        """)
        self.malzemeler: list = []
        self.adimlar: list = []
        self._kur()
        if duzenle_tarif:
            self._doldur(duzenle_tarif)

    def _kur(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(14)

        baslik = QLabel("Tarifi Düzenle" if self.duzenle else "Yeni Tarif Ekle")
        baslik.setStyleSheet(
            f"color:{RENKLER['text_primary']}; font-size:20px; font-weight:800; background:transparent;")
        lay.addWidget(baslik)
        lay.addWidget(AyiriciCizgi())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background:transparent; border:none;")
        fw = QWidget()
        fw.setStyleSheet("background:transparent;")
        fl = QVBoxLayout(fw)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(14)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.adi_input = QLineEdit(); self.adi_input.setPlaceholderText("Tarif adını girin")
        form.addRow("Tarif Adı:", self.adi_input)
        self.kat_combo = QComboBox(); self.kat_combo.addItems(self.platform.kategoriler)
        form.addRow("Kategori:", self.kat_combo)
        self.zorluk_combo = QComboBox(); self.zorluk_combo.addItems(self.platform.zorluk_seviyeleri)
        form.addRow("Zorluk:", self.zorluk_combo)
        self.sure_spin = QSpinBox(); self.sure_spin.setRange(1, 480); self.sure_spin.setValue(30)
        self.sure_spin.setSuffix(" dakika")
        form.addRow("Süre:", self.sure_spin)
        self.acik_input = QTextEdit(); self.acik_input.setPlaceholderText("Kısa açıklama...")
        self.acik_input.setMaximumHeight(80)
        form.addRow("Açıklama:", self.acik_input)
        fl.addLayout(form)

        # Malzemeler
        mal_lbl = QLabel("🧂  Malzemeler")
        mal_lbl.setStyleSheet(f"color:{RENKLER['text_primary']}; font-size:14px; font-weight:700; background:transparent;")
        fl.addWidget(mal_lbl)
        mr = QHBoxLayout()
        self.mal_adi = QLineEdit(); self.mal_adi.setPlaceholderText("Malzeme adı")
        self.mal_miktar = QLineEdit(); self.mal_miktar.setPlaceholderText("Miktar"); self.mal_miktar.setFixedWidth(75)
        self.mal_birim = QLineEdit(); self.mal_birim.setPlaceholderText("Birim"); self.mal_birim.setFixedWidth(75)
        eb = ModernButon("+ Ekle", birincil=False, kucuk=True); eb.setFixedWidth(72)
        eb.clicked.connect(self._malzeme_ekle); self.mal_adi.returnPressed.connect(self._malzeme_ekle)
        mr.addWidget(self.mal_adi); mr.addWidget(self.mal_miktar); mr.addWidget(self.mal_birim); mr.addWidget(eb)
        fl.addLayout(mr)
        self.mal_liste = QListWidget(); self.mal_liste.setFixedHeight(100)
        self.mal_liste.setStyleSheet(f"""
            QListWidget {{background:{RENKLER['bg_input']};border:1px solid {RENKLER['border']};border-radius:10px;padding:6px;color:{RENKLER['text_primary']};font-size:13px;}}
        """)
        fl.addWidget(self.mal_liste)
        msb = ModernButon("Seçili Malzemeyi Sil", birincil=False, kucuk=True)
        msb.clicked.connect(self._malzeme_sil); fl.addWidget(msb)

        # Adımlar
        adim_lbl = QLabel("👨‍🍳  Hazırlama Adımları")
        adim_lbl.setStyleSheet(f"color:{RENKLER['text_primary']}; font-size:14px; font-weight:700; background:transparent;")
        fl.addWidget(adim_lbl)
        ar = QHBoxLayout()
        self.adim_input = QLineEdit(); self.adim_input.setPlaceholderText("Adım ekle...")
        self.adim_input.returnPressed.connect(self._adim_ekle)
        abe = ModernButon("+ Ekle", birincil=False, kucuk=True); abe.setFixedWidth(72)
        abe.clicked.connect(self._adim_ekle)
        ar.addWidget(self.adim_input); ar.addWidget(abe)
        fl.addLayout(ar)
        self.adim_liste = QListWidget(); self.adim_liste.setFixedHeight(90)
        self.adim_liste.setStyleSheet(f"""
            QListWidget {{background:{RENKLER['bg_input']};border:1px solid {RENKLER['border']};border-radius:10px;padding:6px;color:{RENKLER['text_primary']};font-size:13px;}}
        """)
        fl.addWidget(self.adim_liste)
        scroll.setWidget(fw); lay.addWidget(scroll)

        br = QHBoxLayout()
        iptal = ModernButon("İptal", birincil=False); iptal.clicked.connect(self.reject)
        kaydet = ModernButon("✓ Kaydet", birincil=True); kaydet.clicked.connect(self._kaydet)
        br.addWidget(iptal); br.addWidget(kaydet)
        lay.addLayout(br)

    def _doldur(self, t: Tarif):
        self.adi_input.setText(t.adi)
        idx = self.kat_combo.findText(t.kategori)
        if idx >= 0: self.kat_combo.setCurrentIndex(idx)
        zidx = self.zorluk_combo.findText(t.zorluk)
        if zidx >= 0: self.zorluk_combo.setCurrentIndex(zidx)
        self.sure_spin.setValue(t.sure)
        self.acik_input.setPlainText(t.aciklama)
        for m in t.malzemeler:
            self.malzemeler.append(m); self.mal_liste.addItem(str(m))
        for adim in t.adimlar:
            self.adimlar.append(adim); self.adim_liste.addItem(f"{len(self.adimlar)}. {adim}")

    def _malzeme_ekle(self):
        adi = self.mal_adi.text().strip()
        if not adi: return
        try:
            miktar = float(self.mal_miktar.text()) if self.mal_miktar.text().strip() else 1
        except ValueError:
            miktar = 1
        birim = self.mal_birim.text().strip() or "adet"
        m = Malzeme(adi, miktar, birim)
        self.malzemeler.append(m); self.mal_liste.addItem(str(m))
        self.mal_adi.clear(); self.mal_miktar.clear(); self.mal_birim.clear()
        self.mal_adi.setFocus()

    def _malzeme_sil(self):
        row = self.mal_liste.currentRow()
        if row >= 0:
            self.mal_liste.takeItem(row); del self.malzemeler[row]

    def _adim_ekle(self):
        adim = self.adim_input.text().strip()
        if not adim: return
        self.adimlar.append(adim)
        self.adim_liste.addItem(f"{len(self.adimlar)}. {adim}")
        self.adim_input.clear(); self.adim_input.setFocus()

    def _kaydet(self):
        adi = self.adi_input.text().strip()
        if not adi:
            QMessageBox.warning(self, "Eksik Bilgi", "Tarif adı boş olamaz!"); return
        if self.duzenle:
            self.duzenle.adi = adi
            self.duzenle.kategori = self.kat_combo.currentText()
            self.duzenle.zorluk = self.zorluk_combo.currentText()
            self.duzenle.sure = self.sure_spin.value()
            self.duzenle.aciklama = self.acik_input.toPlainText().strip()
            self.duzenle.malzemeler = self.malzemeler
            self.duzenle.adimlar = self.adimlar
        else:
            t = Tarif(adi, self.kat_combo.currentText(), self.sure_spin.value(),
                      self.acik_input.toPlainText().strip(), self.zorluk_combo.currentText())
            t.malzemeler = self.malzemeler; t.adimlar = self.adimlar
            self.platform.tarif_ekle(t)
        self.accept()


class DegerlendirmeDiyalogu(QDialog):
    def __init__(self, tarif: Tarif, parent=None):
        super().__init__(parent)
        self.tarif = tarif
        self.setWindowTitle("Değerlendir")
        self.setMinimumWidth(420)
        self.setStyleSheet(f"""
            QDialog {{background:{RENKLER['bg_card']}; border-radius:16px;}}
            QLabel {{color:{RENKLER['text_primary']}; background:transparent;}}
        """)
        self._kur()

    def _kur(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(14)
        baslik = QLabel(f'"{self.tarif.adi}" Değerlendir')
        baslik.setStyleSheet(
            f"color:{RENKLER['text_primary']}; font-size:17px; font-weight:700; background:transparent;")
        baslik.setWordWrap(True)
        lay.addWidget(baslik)
        lay.addWidget(AyiriciCizgi())
        lay.addWidget(QLabel("Adınız:"))
        self.kul_input = QLineEdit(); self.kul_input.setPlaceholderText("Adınızı girin (boş = Anonim)")
        lay.addWidget(self.kul_input)
        lay.addWidget(QLabel("Puanınız (1-5):"))
        self.puan_spin = QSpinBox(); self.puan_spin.setRange(1, 5); self.puan_spin.setValue(5)
        self.yildiz_lbl = QLabel("★★★★★")
        self.yildiz_lbl.setStyleSheet(f"color:{RENKLER['star']}; font-size:22px; background:transparent;")
        self.puan_spin.valueChanged.connect(lambda v: self.yildiz_lbl.setText("★" * v + "☆" * (5 - v)))
        pr = QHBoxLayout(); pr.addWidget(self.puan_spin); pr.addWidget(self.yildiz_lbl); pr.addStretch()
        lay.addLayout(pr)
        lay.addWidget(QLabel("Yorumunuz (isteğe bağlı):"))
        self.yorum_input = QTextEdit(); self.yorum_input.setPlaceholderText("Deneyiminizi paylaşın...")
        self.yorum_input.setMaximumHeight(90)
        lay.addWidget(self.yorum_input)
        br = QHBoxLayout()
        iptal = ModernButon("İptal", birincil=False); iptal.clicked.connect(self.reject)
        gonder = ModernButon("⭐ Gönder", birincil=True); gonder.clicked.connect(self._gonder)
        br.addWidget(iptal); br.addWidget(gonder)
        lay.addLayout(br)

    def _gonder(self):
        kul = self.kul_input.text().strip() or "Anonim"
        self.tarif.degerlendir(self.puan_spin.value(), self.yorum_input.toPlainText().strip(), kul)
        self.accept()


# ═══════════════════════════════════════════════════════════════════
#  ANA PENCERE
# ═══════════════════════════════════════════════════════════════════

class AnaPencere(QMainWindow):
    def __init__(self):
        super().__init__()
        self.platform = Platform()
        self.setWindowTitle("TarifDünyası  🍽")
        self.setMinimumSize(1140, 720)
        self.resize(1360, 860)
        self._kur_arayuz()

    def _kur_arayuz(self):
        merkez = QWidget()
        self.setCentralWidget(merkez)
        ana = QHBoxLayout(merkez)
        ana.setContentsMargins(0, 0, 0, 0)
        ana.setSpacing(0)

        # Sol nav
        nav = QWidget()
        nav.setFixedWidth(235)
        nav.setStyleSheet(f"""
            QWidget {{background:{RENKLER['bg_card']}; border-right:1px solid {RENKLER['border']};}}
        """)
        nl = QVBoxLayout(nav)
        nl.setContentsMargins(12, 24, 12, 24)
        nl.setSpacing(4)

        logo = QLabel("🍽  TarifDünyası")
        logo.setStyleSheet(f"""
            color:{RENKLER['accent']}; font-size:18px; font-weight:800;
            padding:0 8px 16px 8px; background:transparent;
        """)
        nl.addWidget(logo)
        nl.addWidget(AyiriciCizgi())
        nl.addSpacing(8)

        self.nav_butonlar = []
        for ikon, etiket, idx in [
            ("🏠", "Anasayfa",       0),
            ("📖", "Tarifler",       1),
            ("❤",  "Favoriler",      2),
            ("🌐", "API'den Keşfet", 3),
        ]:
            btn = NavButon(ikon, etiket, aktif=(idx == 0))
            btn.clicked.connect(lambda checked, i=idx: self._sayfa_degistir(i))
            self.nav_butonlar.append(btn)
            nl.addWidget(btn)

        nl.addStretch()
        nl.addWidget(AyiriciCizgi())
        nl.addSpacing(8)

        kul_frame = QFrame()
        kul_frame.setStyleSheet(f"""
            QFrame {{background:{RENKLER['bg_card2']};border:1px solid {RENKLER['border']};border-radius:10px;}}
        """)
        kfl = QHBoxLayout(kul_frame)
        kfl.setContentsMargins(12, 10, 12, 10)
        ki = QLabel("👤"); ki.setStyleSheet("font-size:18px; background:transparent;")
        ka = QLabel(self.platform.aktif_kullanici.ad)
        ka.setStyleSheet(f"color:{RENKLER['text_primary']}; font-size:13px; font-weight:600; background:transparent;")
        kfl.addWidget(ki); kfl.addWidget(ka); kfl.addStretch()
        nl.addWidget(kul_frame)
        nl.addSpacing(8)

        ver = QLabel("v3.0  •  TheMealDB API")
        ver.setStyleSheet(f"color:{RENKLER['text_hint']}; font-size:11px; padding:0 8px; background:transparent;")
        nl.addWidget(ver)
        ana.addWidget(nav)

        # İçerik stack
        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background:{RENKLER['bg_dark']};")

        self.anasayfa = AnasayfaSayfasi(self.platform)
        self.anasayfa.tarif_sec.connect(self._tarif_detay_goster)

        self.tarif_listesi = TarifListesiSayfasi(self.platform)
        self.tarif_listesi.tarif_sec.connect(self._tarif_detay_goster)

        self.favoriler = FavorilerSayfasi(self.platform)
        self.favoriler.tarif_sec.connect(self._tarif_detay_goster)

        self.kesfet = KesfetSayfasi(self.platform)
        self.kesfet.tarif_kaydedildi.connect(self._herkesi_yenile)

        self.tarif_detay = TarifDetaySayfasi(self.platform)
        self.tarif_detay.geri_don.connect(self._geri_don)
        self.tarif_detay.tarif_silindi.connect(self._herkesi_yenile)
        self.tarif_detay.favori_degisti.connect(lambda: self.favoriler.yenile())

        self.stack.addWidget(self.anasayfa)      # 0
        self.stack.addWidget(self.tarif_listesi) # 1
        self.stack.addWidget(self.favoriler)     # 2
        self.stack.addWidget(self.kesfet)        # 3
        self.stack.addWidget(self.tarif_detay)   # 4

        ana.addWidget(self.stack)
        self._onceki_sayfa = 0

    def _sayfa_degistir(self, idx):
        self._onceki_sayfa = idx
        for i, btn in enumerate(self.nav_butonlar):
            btn.aktif_yap() if i == idx else btn.pasif_yap()
        if idx == 2:
            self.favoriler.yenile()
        self.stack.setCurrentIndex(idx)

    def _tarif_detay_goster(self, tarif_id: int):
        self._onceki_sayfa = self.stack.currentIndex()
        self.tarif_detay.tarifi_goster(tarif_id)
        self.stack.setCurrentIndex(4)

    def _geri_don(self):
        self._herkesi_yenile()
        self.stack.setCurrentIndex(self._onceki_sayfa)

    def _herkesi_yenile(self, *_):
        self.tarif_listesi.yenile()
        self.anasayfa.yenile()
        self.favoriler.yenile()


# ═══════════════════════════════════════════════════════════════════
#  BAŞLAT
# ═══════════════════════════════════════════════════════════════════

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE_SHEET)

    palette = QPalette()
    palette.setColor(QPalette.Window,          QColor(RENKLER['bg_dark']))
    palette.setColor(QPalette.WindowText,      QColor(RENKLER['text_primary']))
    palette.setColor(QPalette.Base,            QColor(RENKLER['bg_input']))
    palette.setColor(QPalette.AlternateBase,   QColor(RENKLER['bg_card']))
    palette.setColor(QPalette.ToolTipBase,     QColor(RENKLER['bg_card2']))
    palette.setColor(QPalette.ToolTipText,     QColor(RENKLER['text_primary']))
    palette.setColor(QPalette.Text,            QColor(RENKLER['text_primary']))
    palette.setColor(QPalette.Button,          QColor(RENKLER['bg_card2']))
    palette.setColor(QPalette.ButtonText,      QColor(RENKLER['text_primary']))
    palette.setColor(QPalette.Highlight,       QColor(RENKLER['accent']))
    palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(palette)

    pencere = AnaPencere()
    pencere.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
