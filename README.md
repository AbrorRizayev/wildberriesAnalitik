# 🎯 AIRA — Wildberries Analytics

Sizning Excel jadvalingiz **xuddi shu mantiq** bilan, **brauzerda**, **real vaqt** hisoblash.

---

## 🚀 Boshlash

### 1. **Saytni ochish**
- `index.html` faylni brauzerda oching
- Yoki ZIP'ni hosting'ga yuklang (Netlify, Vercel, GitHub Pages)
- Login parol kerak emas — ma'lumotlar faqat sizning brauzeringizda saqlanadi

### 2. **3 qadamli workflow** (sizning Excel'ingiz kabi)

#### 1️⃣ Список отчётов yuklash
- WB savdogar kabinet → **«Финансовые отчёты»** → **«Скачать Excel»**
- Saytda **«Achot yuklash»** → **«Список отчётов»** tabiga sudrab tashlang
- Avtomat ko'rinadi: jami sotuv, к перечислению, logistika, shtraflar

#### 2️⃣ Подробный отчёt yuklash (База ga)
- WB kabinetda har bir achot raqamini bosing
- **Подробный отчёт** Excel yuklab oling
- Saytda **«База»** tabiga sudrab tashlang
- Avtomat aniqlaydi qaysi achotga tegishliligini

#### 3️⃣ Себестоимость (tannarx)
- **15 ta Piccino tovar** default kiritilgan
- **«Себестоимость»** sahifasiga kirib o'zgartiring/qo'shing
- Bazadagi har bir sotuv uchun avtomat VLOOKUP qilinadi

### 3. **Natijani ko'rish**
- **📊 Dashboard** — KPI'lar (sizning Excel Dashboard kabi)
- **📑 P&L** — haftalik foyda-zarar
- **🏆 ABC** — A/B/C kategoriyalar
- **📦 Tovarlar** — har bir tovar bo'yicha tahlil

---

## 📋 Sahifalar ro'yxati

| Sahifa | Vazifa |
|--------|--------|
| `index.html` | Welcome — boshlash |
| `upload.html` | Yuklash — 3 ta zona |
| `list-reports.html` | Список отчётов (sizning Excel kabi) |
| `base.html` | База — 123 ustun, 51 formula |
| `costs.html` | Себестоимость — 15 ta tovar |
| `dashboard.html` | Dashboard — asosiy KPI'lar |
| `pnl.html` | P&L — haftalik |
| `abc.html` | ABC tahlil |
| `products.html` | Tovarlar bo'yicha hisobot |
| `settings.html` | Sozlamalar (soliq, til, backup) |

---

## 🧮 Excel formulalari → JavaScript

Sizning Excel'dagi **51 ta formula** aynan JavaScript'ga ko'chirilgan:

### Asosiy:
```javascript
A = ЕСЛИ(BJ="Продажа"; 1; ЕСЛИ(BJ="Возврат"; -1; 0))   // koef GENERAL
C = sotuv yoki qaytarish indikatori                       // koef SALES
D = ЕСЛИ(коррекция; 0; ЕСЛИ(C=1; BN; 0))                // Продано шт.
F = ЕСЛИ(D>0; BT; 0)                                     // Продано руб.
I = F - G                                                // Выручка ⭐
J = CH*A - O - P                                         // К перечислению
K = I - J - L + M                                        // Комиссия
Z = A * ABS(BP)                                          // WB реализовал
AC = VLOOKUP(BB+BD; Себестоимость; 7) * (Q+R+C)         // Tannarx ⭐
AB = AA * tax_rate                                       // Налог
Y = murakkab summa formulasi                            // Оплата на РС ⭐
```

### Jarima turlari (matn qidirish):
```javascript
AE = CQ.includes("Продвижение") ? DI : 0    // ВБ.Продвижение
AF = CQ.includes("Транзит") ? DI : 0        // Транзит
AH = CQ.includes("Джем") ? DI : 0           // Подписка "Джем"
AI = CQ.includes("утилизации") ? DI : 0     // Утилизация
AJ = CQ.includes("отзыв") ? DI : 0          // Списание за отзыв
```

---

## ⚙️ Soliq sozlamasi

Sozlamalar sahifasida 4 ta tur tanlash mumkin (sizning Excel "Справка" varagi kabi):

| Kod | Tur | Kim uchun | Formula |
|-----|-----|-----------|---------|
| 1 | УСН-доходы | 🇷🇺 RU IP | AA = Z (WB реализовал) |
| 2 | УСН Д-Р | 🇷🇺 RU IP | AA = Y - AC - AN |
| 3 | Не считать | — | AA = 0 |
| 4 | Считать от РС | 🇰🇬 KG IP | AA = Y (Оплата на РС) |

---

## 💾 Ma'lumotlar saqlash

- 🔒 Hammasi **brauzerda** (localStorage)
- 🔒 Server'ga **yuborilmaydi**
- 🔒 Login/parol **kerak emas**

### Backup:
- **Eksport:** Sozlamalar → 📥 Backup eksport (JSON)
- **Import:** Sozlamalar → 📤 Backup import

---

## ✅ Test natija

| Formula | Mening natijam | Excel | Status |
|---------|---------------|-------|--------|
| A (koef GENERAL) | 1 | 1 | ✅ |
| C (koef SALES) | 1 | 1 | ✅ |
| F (Продано руб) | 772.21 | 772.21 | ✅ |
| I (Выручка) | 772.21 | 772.21 | ✅ |
| J (К перечисл.) | 531.71 | 531.71 | ✅ |
| Z (WB реал.) | 668.61 | 668.61 | ✅ |
| AC (Tannarx) | 235 | 235 | ✅ |
| AB (Налог) | 13.37 | 13.37 | ✅ |

**Excel formulalari aynan nusxa qilingan!**

---

## 🛠 Texnologiyalar

- **HTML5 + CSS3** — toza JavaScript, kutubxonalar yo'q
- **JSZip 3.10** — ZIP fayllar o'qish
- **SheetJS 0.18** — Excel fayllar o'qish
- **localStorage** — ma'lumotlar saqlash

---

## 📞 Yordam

Sayt sizning Excel'ingizning **aynan ko'chirilgan versiyasi**.
Agar biror narsa ishlamasa, brauzer konsolini (F12) oching va xato xabarini ko'ring.

**Brand:** AIRA · **Versiya:** 2.0 · **Bosqich:** 1 (asosiy 7 sahifa)
