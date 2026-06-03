-- The Blue Red candidate case seed data
-- Candidate evaluation seed data. Safe to run in a local demo database.
CREATE SCHEMA IF NOT EXISTS case_seed;
DROP TABLE IF EXISTS case_seed.quote_items;
DROP TABLE IF EXISTS case_seed.quotes;
DROP TABLE IF EXISTS case_seed.price_rules;
DROP TABLE IF EXISTS case_seed.customers;
DROP TABLE IF EXISTS case_seed.knowledge_entries;
DROP TABLE IF EXISTS case_seed.products;

CREATE TABLE case_seed.products (
  product_id TEXT PRIMARY KEY,
  sku TEXT NOT NULL,
  name_tr TEXT NOT NULL,
  category TEXT NOT NULL,
  brand TEXT NOT NULL,
  price_try NUMERIC NOT NULL,
  stock_qty INTEGER NOT NULL,
  active BOOLEAN NOT NULL,
  min_order_qty INTEGER NOT NULL,
  delivery_days INTEGER NOT NULL,
  warranty_months INTEGER NOT NULL,
  tags JSONB NOT NULL,
  aliases JSONB NOT NULL,
  substitute_product_ids JSONB NOT NULL,
  notes TEXT NOT NULL
);

CREATE TABLE case_seed.knowledge_entries (
  knowledge_id TEXT PRIMARY KEY,
  topic TEXT NOT NULL,
  locale TEXT NOT NULL,
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  source TEXT NOT NULL,
  applies_to JSONB NOT NULL,
  effective_from DATE NOT NULL
);

CREATE TABLE case_seed.customers (
  customer_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  segment TEXT NOT NULL,
  city TEXT NOT NULL,
  price_tier TEXT NOT NULL,
  credit_limit_try NUMERIC NOT NULL,
  allow_backorder BOOLEAN NOT NULL,
  default_locale TEXT NOT NULL,
  notes TEXT NOT NULL
);

CREATE TABLE case_seed.price_rules (
  rule_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  condition TEXT NOT NULL,
  discount_percent NUMERIC NOT NULL
);

CREATE TABLE case_seed.quotes (
  quote_id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL REFERENCES case_seed.customers(customer_id),
  status TEXT NOT NULL,
  created_by_channel TEXT NOT NULL,
  currency TEXT NOT NULL,
  notes TEXT NOT NULL
);

CREATE TABLE case_seed.quote_items (
  quote_item_id TEXT PRIMARY KEY,
  quote_id TEXT NOT NULL REFERENCES case_seed.quotes(quote_id),
  product_id TEXT NOT NULL REFERENCES case_seed.products(product_id),
  quantity INTEGER NOT NULL,
  unit_price_try NUMERIC NOT NULL,
  status TEXT NOT NULL,
  source_message_id TEXT NOT NULL,
  idempotency_key TEXT NOT NULL UNIQUE
);

INSERT INTO case_seed.products VALUES ('PRD-BC-100', 'TBR-BC-100', 'BlueScan Lite 1D USB Barkod Okuyucu', 'barcode_scanner', 'BlueScan', 2450, 44, TRUE, 1, 2, 24, '["1d","usb","kablolu","giris"]'::jsonb, '{"tr":["barkod okuyucu","kablolu okuyucu","1d scanner"]}'::jsonb, '["PRD-BC-110","PRD-BC-140"]'::jsonb, 'Entry-level wired scanner. No QR support.');
INSERT INTO case_seed.products VALUES ('PRD-BC-110', 'TBR-BC-110', 'BlueScan Air 2D Bluetooth Barkod Okuyucu', 'barcode_scanner', 'BlueScan', 7990, 18, TRUE, 1, 2, 24, '["2d","qr","bluetooth","kablosuz"]'::jsonb, '{"tr":["kablosuz barkod okuyucu","qr okuyucu","2d scanner"]}'::jsonb, '["PRD-BC-120","PRD-BC-140"]'::jsonb, 'Default wireless 2D scanner for retail counters.');
INSERT INTO case_seed.products VALUES ('PRD-BC-120', 'TBR-BC-120', 'BlueScan Pro Rugged 2D Endüstriyel Okuyucu', 'barcode_scanner', 'BlueScan', 12950, 4, TRUE, 1, 3, 36, '["2d","rugged","depo","endustriyel"]'::jsonb, '{"tr":["endüstriyel okuyucu","dayanıklı scanner","rugged okuyucu"]}'::jsonb, '["PRD-BC-110","PRD-BC-140"]'::jsonb, 'Rugged device; should be excluded under low price ceilings.');
INSERT INTO case_seed.products VALUES ('PRD-BC-130', 'TBR-BC-130', 'RedScan Mini Pocket 2D Okuyucu', 'barcode_scanner', 'RedScan', 6750, 0, TRUE, 1, 10, 24, '["2d","cep","pocket","bluetooth"]'::jsonb, '{"tr":["cep tipi okuyucu","mini scanner","pocket okuyucu"]}'::jsonb, '["PRD-BC-140","PRD-BC-110"]'::jsonb, 'Out of stock. Use for replacement and stock-rule tests.');
INSERT INTO case_seed.products VALUES ('PRD-BC-140', 'TBR-BC-140', 'GreenScan Eco 1D Kablosuz Okuyucu', 'barcode_scanner', 'GreenScan', 5350, 20, TRUE, 1, 2, 18, '["1d","kablosuz","ekonomik"]'::jsonb, '{"tr":["ucuz kablosuz okuyucu","ekonomik scanner"]}'::jsonb, '["PRD-BC-110","PRD-BC-100"]'::jsonb, 'Budget alternative; no 2D/QR support.');
INSERT INTO case_seed.products VALUES ('PRD-POS-210', 'TBR-POS-210', 'BluePOS Android El Terminali 4G', 'pos_terminal', 'BluePOS', 18250, 7, TRUE, 1, 3, 24, '["android","4g","saha","offline"]'::jsonb, '{"tr":["4g el terminali","saha satış terminali","android terminal"]}'::jsonb, '["PRD-POS-230"]'::jsonb, 'Use when user says field sales or no local network.');
INSERT INTO case_seed.products VALUES ('PRD-POS-220', 'TBR-POS-220', 'RedPOS Android El Terminali WiFi', 'pos_terminal', 'RedPOS', 11900, 0, TRUE, 1, 12, 24, '["android","wifi","magaza"]'::jsonb, '{"tr":["wifi el terminali","android terminal wifi"]}'::jsonb, '["PRD-POS-230","PRD-POS-210"]'::jsonb, 'Out of stock; tests should not recommend by default.');
INSERT INTO case_seed.products VALUES ('PRD-POS-230', 'TBR-POS-230', 'BluePOS Lite WiFi El Terminali', 'pos_terminal', 'BluePOS', 9800, 15, TRUE, 1, 2, 18, '["android","wifi","ekonomik"]'::jsonb, '{"tr":["uygun fiyatlı el terminali","wifi terminal"]}'::jsonb, '["PRD-POS-210"]'::jsonb, 'Store-only WiFi terminal.');
INSERT INTO case_seed.products VALUES ('PRD-PRN-310', 'TBR-PRN-310', 'RedPrint 58 Termal Fiş Yazıcı', 'receipt_printer', 'RedPrint', 4250, 12, TRUE, 1, 2, 24, '["58mm","usb","fis"]'::jsonb, '{"tr":["fiş yazıcı","58mm yazıcı","termal yazıcı"]}'::jsonb, '["PRD-PRN-320"]'::jsonb, 'Low-cost USB printer.');
INSERT INTO case_seed.products VALUES ('PRD-PRN-320', 'TBR-PRN-320', 'BluePrint 80 Ethernet Fiş Yazıcı', 'receipt_printer', 'BluePrint', 7350, 6, TRUE, 1, 2, 24, '["80mm","ethernet","fis"]'::jsonb, '{"tr":["ethernet fiş yazıcı","80mm yazıcı"]}'::jsonb, '["PRD-PRN-310"]'::jsonb, 'Network printer. Existing quote item in Q-1003.');
INSERT INTO case_seed.products VALUES ('PRD-PRN-330', 'TBR-PRN-330', 'BluePrint Mobile Bluetooth Yazıcı', 'receipt_printer', 'BluePrint', 8900, 0, TRUE, 1, 14, 24, '["mobil","bluetooth","saha"]'::jsonb, '{"tr":["mobil fiş yazıcı","bluetooth yazıcı"]}'::jsonb, '["PRD-PRN-320","PRD-PRN-310"]'::jsonb, 'Out of stock; useful for refusal/alternative tests.');
INSERT INTO case_seed.products VALUES ('PRD-LBL-410', 'TBR-LBL-410', 'BlueLabel 203 Barkod Etiket Yazıcı', 'label_printer', 'BlueLabel', 11200, 11, TRUE, 1, 3, 24, '["etiket","203dpi","depo"]'::jsonb, '{"tr":["etiket yazıcı","barkod etiketi","203dpi"]}'::jsonb, '["PRD-LBL-420"]'::jsonb, 'Default label printer.');
INSERT INTO case_seed.products VALUES ('PRD-LBL-420', 'TBR-LBL-420', 'RedLabel Pro 300dpi Etiket Yazıcı', 'label_printer', 'RedLabel', 16800, 5, TRUE, 1, 4, 36, '["etiket","300dpi","profesyonel"]'::jsonb, '{"tr":["300dpi etiket yazıcı","yüksek çözünürlük etiket"]}'::jsonb, '["PRD-LBL-410"]'::jsonb, 'High-resolution label printer.');
INSERT INTO case_seed.products VALUES ('PRD-SW-510', 'TBR-SW-510', 'BlueStock Starter Lisans 12 Ay', 'software', 'BlueStock', 5900, 999, TRUE, 1, 0, 12, '["stok","lisans","starter"]'::jsonb, '{"tr":["stok programı","starter lisans","depo yazılımı"]}'::jsonb, '["PRD-SW-520"]'::jsonb, 'Basic inventory license.');
INSERT INTO case_seed.products VALUES ('PRD-SW-520', 'TBR-SW-520', 'BlueStock Pro Lisans 12 Ay', 'software', 'BlueStock', 14900, 999, TRUE, 1, 0, 12, '["stok","lisans","pro","offline"]'::jsonb, '{"tr":["offline stok lisansı","pro lisans","saha senkron"]}'::jsonb, '["PRD-SW-510","PRD-SW-530"]'::jsonb, 'Required for offline field synchronization.');
INSERT INTO case_seed.products VALUES ('PRD-SW-530', 'TBR-SW-530', 'BlueStock Şubeler Arası Senkron Modülü', 'software', 'BlueStock', 9900, 999, TRUE, 1, 0, 12, '["senkron","sube","modul"]'::jsonb, '{"tr":["şube senkron","çok şube modülü"]}'::jsonb, '["PRD-SW-520"]'::jsonb, 'Optional module for multi-branch retailers.');
INSERT INTO case_seed.products VALUES ('PRD-KIT-610', 'TBR-KIT-610', 'Depo Başlangıç Kiti', 'bundle', 'The Blue Red', 27900, 3, TRUE, 1, 4, 24, '["depo","kit","barkod","yazici"]'::jsonb, '{"tr":["depo kiti","başlangıç kiti"]}'::jsonb, '[]'::jsonb, 'Bundle containing scanner, label printer and starter license.');
INSERT INTO case_seed.products VALUES ('PRD-KIT-620', 'TBR-KIT-620', 'Saha Satış Kiti', 'bundle', 'The Blue Red', 32900, 2, TRUE, 1, 4, 24, '["saha","kit","terminal","lisans"]'::jsonb, '{"tr":["saha satış kiti","mobil satış paketi"]}'::jsonb, '[]'::jsonb, 'Bundle for field sales operations.');
INSERT INTO case_seed.products VALUES ('PRD-ACC-710', 'TBR-ACC-710', 'Koruyucu Silikon Kılıf', 'accessory', 'The Blue Red', 950, 50, TRUE, 1, 1, 6, '["aksesuar","kilif","terminal"]'::jsonb, '{"tr":["kılıf","koruyucu kılıf"]}'::jsonb, '[]'::jsonb, 'Accessory discount applies at qty >= 5.');
INSERT INTO case_seed.products VALUES ('PRD-ACC-720', 'TBR-ACC-720', 'Yedek Batarya 5000mAh', 'accessory', 'The Blue Red', 1450, 2, TRUE, 1, 1, 6, '["aksesuar","batarya","terminal"]'::jsonb, '{"tr":["yedek batarya","pil"]}'::jsonb, '[]'::jsonb, 'Low stock; useful for stock warning tests.');
INSERT INTO case_seed.products VALUES ('PRD-ACC-730', 'TBR-ACC-730', 'Araç Şarj Adaptörü', 'accessory', 'The Blue Red', 1100, 0, TRUE, 1, 9, 6, '["aksesuar","arac","sarj"]'::jsonb, '{"tr":["araç şarj","oto şarj"]}'::jsonb, '["PRD-ACC-740"]'::jsonb, 'Out of stock; replace with USB-C fast charger if acceptable.');
INSERT INTO case_seed.products VALUES ('PRD-ACC-740', 'TBR-ACC-740', 'USB-C Hızlı Şarj Adaptörü', 'accessory', 'The Blue Red', 890, 30, TRUE, 1, 1, 6, '["aksesuar","usb-c","sarj"]'::jsonb, '{"tr":["usb-c şarj","hızlı şarj"]}'::jsonb, '["PRD-ACC-730"]'::jsonb, 'In-stock alternative for vehicle charger.');
INSERT INTO case_seed.products VALUES ('PRD-SVC-810', 'TBR-SVC-810', 'Yerinde Kurulum Hizmeti', 'service', 'The Blue Red', 4500, 999, TRUE, 1, 5, 0, '["kurulum","servis"]'::jsonb, '{"tr":["kurulum","yerinde kurulum"]}'::jsonb, '["PRD-SVC-820"]'::jsonb, 'Scheduled service. Cite service policy before promising date.');
INSERT INTO case_seed.products VALUES ('PRD-SVC-820', 'TBR-SVC-820', 'Acil Kurulum Hizmeti', 'service', 'The Blue Red', 7900, 2, TRUE, 1, 1, 0, '["kurulum","acil","servis"]'::jsonb, '{"tr":["acil kurulum","hızlı kurulum"]}'::jsonb, '["PRD-SVC-810"]'::jsonb, 'Only Istanbul and Ankara on weekdays.');
INSERT INTO case_seed.products VALUES ('PRD-BC-100-PLUS', 'TBR-BC-100-PLUS', 'BlueScan Lite 1D USB Barkod Okuyucu Plus', 'barcode_scanner', 'BlueScan', 2890, 50, TRUE, 1, 3, 36, '["1d","genisletilmis","giris","kablolu","plus","usb"]'::jsonb, '{"tr":["barkod okuyucu","kablolu okuyucu","1d scanner","BlueScan Lite 1D USB Barkod Okuyucu plus","plus model"]}'::jsonb, '["PRD-BC-110-PLUS","PRD-BC-140-PLUS"]'::jsonb, 'Daha büyük müşteri kurulumları için Plus varyant. Temel ürün: PRD-BC-100.');
INSERT INTO case_seed.products VALUES ('PRD-BC-110-PLUS', 'TBR-BC-110-PLUS', 'BlueScan Air 2D Bluetooth Barkod Okuyucu Plus', 'barcode_scanner', 'BlueScan', 9430, 24, TRUE, 1, 3, 36, '["2d","bluetooth","genisletilmis","kablosuz","plus","qr"]'::jsonb, '{"tr":["kablosuz barkod okuyucu","qr okuyucu","2d scanner","BlueScan Air 2D Bluetooth Barkod Okuyucu plus","plus model"]}'::jsonb, '["PRD-BC-120-PLUS","PRD-BC-140-PLUS"]'::jsonb, 'Daha büyük müşteri kurulumları için Plus varyant. Temel ürün: PRD-BC-110.');
INSERT INTO case_seed.products VALUES ('PRD-BC-120-PLUS', 'TBR-BC-120-PLUS', 'BlueScan Pro Rugged 2D Endüstriyel Okuyucu Plus', 'barcode_scanner', 'BlueScan', 15280, 10, TRUE, 1, 4, 48, '["2d","depo","endustriyel","genisletilmis","plus","rugged"]'::jsonb, '{"tr":["endüstriyel okuyucu","dayanıklı scanner","rugged okuyucu","BlueScan Pro Rugged 2D Endüstriyel Okuyucu plus","plus model"]}'::jsonb, '["PRD-BC-110-PLUS","PRD-BC-140-PLUS"]'::jsonb, 'Daha büyük müşteri kurulumları için Plus varyant. Temel ürün: PRD-BC-120.');
INSERT INTO case_seed.products VALUES ('PRD-BC-130-PLUS', 'TBR-BC-130-PLUS', 'RedScan Mini Pocket 2D Okuyucu Plus', 'barcode_scanner', 'RedScan', 7960, 8, TRUE, 1, 11, 36, '["2d","bluetooth","cep","genisletilmis","plus","pocket"]'::jsonb, '{"tr":["cep tipi okuyucu","mini scanner","pocket okuyucu","RedScan Mini Pocket 2D Okuyucu plus","plus model"]}'::jsonb, '["PRD-BC-140-PLUS","PRD-BC-110-PLUS"]'::jsonb, 'Daha büyük müşteri kurulumları için Plus varyant. Temel ürün: PRD-BC-130.');
INSERT INTO case_seed.products VALUES ('PRD-BC-140-PLUS', 'TBR-BC-140-PLUS', 'GreenScan Eco 1D Kablosuz Okuyucu Plus', 'barcode_scanner', 'GreenScan', 6310, 26, TRUE, 1, 3, 30, '["1d","ekonomik","genisletilmis","kablosuz","plus"]'::jsonb, '{"tr":["ucuz kablosuz okuyucu","ekonomik scanner","GreenScan Eco 1D Kablosuz Okuyucu plus","plus model"]}'::jsonb, '["PRD-BC-110-PLUS","PRD-BC-100-PLUS"]'::jsonb, 'Daha büyük müşteri kurulumları için Plus varyant. Temel ürün: PRD-BC-140.');
INSERT INTO case_seed.products VALUES ('PRD-POS-210-PLUS', 'TBR-POS-210-PLUS', 'BluePOS Android El Terminali 4G Plus', 'pos_terminal', 'BluePOS', 21540, 13, TRUE, 1, 4, 36, '["4g","android","genisletilmis","offline","plus","saha"]'::jsonb, '{"tr":["4g el terminali","saha satış terminali","android terminal","BluePOS Android El Terminali 4G plus","plus model"]}'::jsonb, '["PRD-POS-230-PLUS"]'::jsonb, 'Daha büyük müşteri kurulumları için Plus varyant. Temel ürün: PRD-POS-210.');
INSERT INTO case_seed.products VALUES ('PRD-POS-220-PLUS', 'TBR-POS-220-PLUS', 'RedPOS Android El Terminali WiFi Plus', 'pos_terminal', 'RedPOS', 14040, 8, TRUE, 1, 13, 36, '["android","genisletilmis","magaza","plus","wifi"]'::jsonb, '{"tr":["wifi el terminali","android terminal wifi","RedPOS Android El Terminali WiFi plus","plus model"]}'::jsonb, '["PRD-POS-230-PLUS","PRD-POS-210-PLUS"]'::jsonb, 'Daha büyük müşteri kurulumları için Plus varyant. Temel ürün: PRD-POS-220.');
INSERT INTO case_seed.products VALUES ('PRD-POS-230-PLUS', 'TBR-POS-230-PLUS', 'BluePOS Lite WiFi El Terminali Plus', 'pos_terminal', 'BluePOS', 11560, 21, TRUE, 1, 3, 30, '["android","ekonomik","genisletilmis","plus","wifi"]'::jsonb, '{"tr":["uygun fiyatlı el terminali","wifi terminal","BluePOS Lite WiFi El Terminali plus","plus model"]}'::jsonb, '["PRD-POS-210-PLUS"]'::jsonb, 'Daha büyük müşteri kurulumları için Plus varyant. Temel ürün: PRD-POS-230.');
INSERT INTO case_seed.products VALUES ('PRD-PRN-310-PLUS', 'TBR-PRN-310-PLUS', 'RedPrint 58 Termal Fiş Yazıcı Plus', 'receipt_printer', 'RedPrint', 5020, 18, TRUE, 1, 3, 36, '["58mm","fis","genisletilmis","plus","usb"]'::jsonb, '{"tr":["fiş yazıcı","58mm yazıcı","termal yazıcı","RedPrint 58 Termal Fiş Yazıcı plus","plus model"]}'::jsonb, '["PRD-PRN-320-PLUS"]'::jsonb, 'Daha büyük müşteri kurulumları için Plus varyant. Temel ürün: PRD-PRN-310.');
INSERT INTO case_seed.products VALUES ('PRD-PRN-320-PLUS', 'TBR-PRN-320-PLUS', 'BluePrint 80 Ethernet Fiş Yazıcı Plus', 'receipt_printer', 'BluePrint', 8670, 12, TRUE, 1, 3, 36, '["80mm","ethernet","fis","genisletilmis","plus"]'::jsonb, '{"tr":["ethernet fiş yazıcı","80mm yazıcı","BluePrint 80 Ethernet Fiş Yazıcı plus","plus model"]}'::jsonb, '["PRD-PRN-310-PLUS"]'::jsonb, 'Daha büyük müşteri kurulumları için Plus varyant. Temel ürün: PRD-PRN-320.');
INSERT INTO case_seed.products VALUES ('PRD-PRN-330-PLUS', 'TBR-PRN-330-PLUS', 'BluePrint Mobile Bluetooth Yazıcı Plus', 'receipt_printer', 'BluePrint', 10500, 8, TRUE, 1, 15, 36, '["bluetooth","genisletilmis","mobil","plus","saha"]'::jsonb, '{"tr":["mobil fiş yazıcı","bluetooth yazıcı","BluePrint Mobile Bluetooth Yazıcı plus","plus model"]}'::jsonb, '["PRD-PRN-320-PLUS","PRD-PRN-310-PLUS"]'::jsonb, 'Daha büyük müşteri kurulumları için Plus varyant. Temel ürün: PRD-PRN-330.');
INSERT INTO case_seed.products VALUES ('PRD-LBL-410-PLUS', 'TBR-LBL-410-PLUS', 'BlueLabel 203 Barkod Etiket Yazıcı Plus', 'label_printer', 'BlueLabel', 13220, 17, TRUE, 1, 4, 36, '["203dpi","depo","etiket","genisletilmis","plus"]'::jsonb, '{"tr":["etiket yazıcı","barkod etiketi","203dpi","BlueLabel 203 Barkod Etiket Yazıcı plus","plus model"]}'::jsonb, '["PRD-LBL-420-PLUS"]'::jsonb, 'Daha büyük müşteri kurulumları için Plus varyant. Temel ürün: PRD-LBL-410.');
INSERT INTO case_seed.products VALUES ('PRD-LBL-420-PLUS', 'TBR-LBL-420-PLUS', 'RedLabel Pro 300dpi Etiket Yazıcı Plus', 'label_printer', 'RedLabel', 19820, 11, TRUE, 1, 5, 48, '["300dpi","etiket","genisletilmis","plus","profesyonel"]'::jsonb, '{"tr":["300dpi etiket yazıcı","yüksek çözünürlük etiket","RedLabel Pro 300dpi Etiket Yazıcı plus","plus model"]}'::jsonb, '["PRD-LBL-410-PLUS"]'::jsonb, 'Daha büyük müşteri kurulumları için Plus varyant. Temel ürün: PRD-LBL-420.');
INSERT INTO case_seed.products VALUES ('PRD-SW-510-PLUS', 'TBR-SW-510-PLUS', 'BlueStock Starter Lisans 12 Ay Plus', 'software', 'BlueStock', 6960, 1005, TRUE, 1, 0, 24, '["genisletilmis","lisans","plus","starter","stok"]'::jsonb, '{"tr":["stok programı","starter lisans","depo yazılımı","BlueStock Starter Lisans 12 Ay plus","plus model"]}'::jsonb, '["PRD-SW-520-PLUS"]'::jsonb, 'Daha büyük müşteri kurulumları için Plus varyant. Temel ürün: PRD-SW-510.');
INSERT INTO case_seed.products VALUES ('PRD-SW-520-PLUS', 'TBR-SW-520-PLUS', 'BlueStock Pro Lisans 12 Ay Plus', 'software', 'BlueStock', 17580, 1005, TRUE, 1, 0, 24, '["genisletilmis","lisans","offline","plus","pro","stok"]'::jsonb, '{"tr":["offline stok lisansı","pro lisans","saha senkron","BlueStock Pro Lisans 12 Ay plus","plus model"]}'::jsonb, '["PRD-SW-510-PLUS","PRD-SW-530-PLUS"]'::jsonb, 'Daha büyük müşteri kurulumları için Plus varyant. Temel ürün: PRD-SW-520.');
INSERT INTO case_seed.products VALUES ('PRD-SW-530-PLUS', 'TBR-SW-530-PLUS', 'BlueStock Şubeler Arası Senkron Modülü Plus', 'software', 'BlueStock', 11680, 1005, TRUE, 1, 0, 24, '["genisletilmis","modul","plus","senkron","sube"]'::jsonb, '{"tr":["şube senkron","çok şube modülü","BlueStock Şubeler Arası Senkron Modülü plus","plus model"]}'::jsonb, '["PRD-SW-520-PLUS"]'::jsonb, 'Daha büyük müşteri kurulumları için Plus varyant. Temel ürün: PRD-SW-530.');
INSERT INTO case_seed.products VALUES ('PRD-KIT-610-PLUS', 'TBR-KIT-610-PLUS', 'Depo Başlangıç Kiti Plus', 'bundle', 'The Blue Red', 32920, 9, TRUE, 1, 5, 36, '["barkod","depo","genisletilmis","kit","plus","yazici"]'::jsonb, '{"tr":["depo kiti","başlangıç kiti","Depo Başlangıç Kiti plus","plus model"]}'::jsonb, '[]'::jsonb, 'Daha büyük müşteri kurulumları için Plus varyant. Temel ürün: PRD-KIT-610.');
INSERT INTO case_seed.products VALUES ('PRD-KIT-620-PLUS', 'TBR-KIT-620-PLUS', 'Saha Satış Kiti Plus', 'bundle', 'The Blue Red', 38820, 8, TRUE, 1, 5, 36, '["genisletilmis","kit","lisans","plus","saha","terminal"]'::jsonb, '{"tr":["saha satış kiti","mobil satış paketi","Saha Satış Kiti plus","plus model"]}'::jsonb, '[]'::jsonb, 'Daha büyük müşteri kurulumları için Plus varyant. Temel ürün: PRD-KIT-620.');
INSERT INTO case_seed.products VALUES ('PRD-ACC-710-PLUS', 'TBR-ACC-710-PLUS', 'Koruyucu Silikon Kılıf Plus', 'accessory', 'The Blue Red', 1120, 56, TRUE, 1, 2, 6, '["aksesuar","genisletilmis","kilif","plus","terminal"]'::jsonb, '{"tr":["kılıf","koruyucu kılıf","Koruyucu Silikon Kılıf plus","plus model"]}'::jsonb, '[]'::jsonb, 'Daha büyük müşteri kurulumları için Plus varyant. Temel ürün: PRD-ACC-710.');
INSERT INTO case_seed.products VALUES ('PRD-ACC-720-PLUS', 'TBR-ACC-720-PLUS', 'Yedek Batarya 5000mAh Plus', 'accessory', 'The Blue Red', 1710, 8, TRUE, 1, 2, 6, '["aksesuar","batarya","genisletilmis","plus","terminal"]'::jsonb, '{"tr":["yedek batarya","pil","Yedek Batarya 5000mAh plus","plus model"]}'::jsonb, '[]'::jsonb, 'Daha büyük müşteri kurulumları için Plus varyant. Temel ürün: PRD-ACC-720.');
INSERT INTO case_seed.products VALUES ('PRD-ACC-730-PLUS', 'TBR-ACC-730-PLUS', 'Araç Şarj Adaptörü Plus', 'accessory', 'The Blue Red', 1300, 8, TRUE, 1, 10, 6, '["aksesuar","arac","genisletilmis","plus","sarj"]'::jsonb, '{"tr":["araç şarj","oto şarj","Araç Şarj Adaptörü plus","plus model"]}'::jsonb, '["PRD-ACC-740-PLUS"]'::jsonb, 'Daha büyük müşteri kurulumları için Plus varyant. Temel ürün: PRD-ACC-730.');
INSERT INTO case_seed.products VALUES ('PRD-ACC-740-PLUS', 'TBR-ACC-740-PLUS', 'USB-C Hızlı Şarj Adaptörü Plus', 'accessory', 'The Blue Red', 1050, 36, TRUE, 1, 2, 6, '["aksesuar","genisletilmis","plus","sarj","usb-c"]'::jsonb, '{"tr":["usb-c şarj","hızlı şarj","USB-C Hızlı Şarj Adaptörü plus","plus model"]}'::jsonb, '["PRD-ACC-730-PLUS"]'::jsonb, 'Daha büyük müşteri kurulumları için Plus varyant. Temel ürün: PRD-ACC-740.');
INSERT INTO case_seed.products VALUES ('PRD-SVC-810-PLUS', 'TBR-SVC-810-PLUS', 'Yerinde Kurulum Hizmeti Plus', 'service', 'The Blue Red', 5310, 1005, TRUE, 1, 6, 0, '["genisletilmis","kurulum","plus","servis"]'::jsonb, '{"tr":["kurulum","yerinde kurulum","Yerinde Kurulum Hizmeti plus","plus model"]}'::jsonb, '["PRD-SVC-820-PLUS"]'::jsonb, 'Daha büyük müşteri kurulumları için Plus varyant. Temel ürün: PRD-SVC-810.');
INSERT INTO case_seed.products VALUES ('PRD-SVC-820-PLUS', 'TBR-SVC-820-PLUS', 'Acil Kurulum Hizmeti Plus', 'service', 'The Blue Red', 9320, 8, TRUE, 1, 2, 0, '["acil","genisletilmis","kurulum","plus","servis"]'::jsonb, '{"tr":["acil kurulum","hızlı kurulum","Acil Kurulum Hizmeti plus","plus model"]}'::jsonb, '["PRD-SVC-810-PLUS"]'::jsonb, 'Daha büyük müşteri kurulumları için Plus varyant. Temel ürün: PRD-SVC-820.');

INSERT INTO case_seed.knowledge_entries VALUES ('KNE-RET-001', 'return_policy', 'tr', 'Donanım ve yazılım iade politikası', 'Stoktan satılan donanım ürünleri teslimden itibaren 14 gün içinde, kutusu açılmamış ve seri numarası eşleşir durumdaysa iade edilebilir. Aktivasyonu yapılmış yazılım lisansları ve özel kurulum hizmetleri iade kapsamında değildir.', 'policy/returns/v2026-04', '["hardware","software","service"]'::jsonb, '2026-04-01');
INSERT INTO case_seed.knowledge_entries VALUES ('KNE-SHIP-001', 'delivery_policy', 'tr', 'Teslimat süreleri', 'Stokta olan ürünler İstanbul içine 1-2 iş günü, Ankara ve İzmir''e 2-3 iş günü, diğer illere 3-5 iş günü içinde sevk edilir. Stokta olmayan ürünler varsayılan öneri listesine alınmaz.', 'policy/delivery/v2026-04', '["hardware","accessory"]'::jsonb, '2026-04-01');
INSERT INTO case_seed.knowledge_entries VALUES ('KNE-WAR-001', 'warranty', 'tr', 'Garanti kapsamı', 'Barkod okuyucu, yazıcı ve el terminalleri 24 ay garanti kapsamındadır. Rugged seri ürünlerde garanti 36 aydır. Batarya ve sarf aksesuarlarında garanti süresi 6 aydır.', 'policy/warranty/v2026-01', '["hardware","accessory"]'::jsonb, '2026-01-01');
INSERT INTO case_seed.knowledge_entries VALUES ('KNE-QUOTE-001', 'quote_validity', 'tr', 'Teklif geçerliliği ve stok rezervasyonu', 'Taslak teklifler stok rezervasyonu yapmaz. Onay bekleyen teklifler 7 gün geçerlidir ve satış temsilcisi onayından sonra stok rezervasyonu başlar.', 'policy/quotes/v2026-03', '["quote"]'::jsonb, '2026-03-10');
INSERT INTO case_seed.knowledge_entries VALUES ('KNE-DIS-001', 'discount_policy', 'tr', 'Miktar ve partner indirimleri', 'Partner fiyat seviyesindeki müşterilerde barkod okuyucu, fiş yazıcı ve etiket yazıcı kategorilerinde aynı kategori içinde 3 ve üzeri adet için yüzde 7 indirim uygulanır. Aksesuar kategorisinde 5 ve üzeri adet için yüzde 5 indirim uygulanır. Kit ürünlerinde ek indirim yoktur.', 'policy/discounts/v2026-05', '["barcode_scanner","receipt_printer","label_printer","accessory","bundle"]'::jsonb, '2026-05-01');
INSERT INTO case_seed.knowledge_entries VALUES ('KNE-STOCK-001', 'stock_rule', 'tr', 'Stokta olmayan ürün önerme kuralı', 'Stok miktarı 0 olan ürünler varsayılan olarak önerilmez ve teklif taslağına eklenmez. Kullanıcı açıkça bekleyebileceğini belirtir ve müşteri backorder için uygunsa, ürün beklemeli teklif kalemi olarak işaretlenebilir.', 'policy/stock/v2026-05', '["product_selection","quote"]'::jsonb, '2026-05-01');
INSERT INTO case_seed.knowledge_entries VALUES ('KNE-SVC-001', 'service_policy', 'tr', 'Kurulum hizmeti kapsamı', 'Yerinde kurulum hizmeti randevulu verilir. Acil kurulum yalnızca İstanbul ve Ankara içinde, hafta içi günlerde ve ekip müsaitliği varsa 1 iş günü içinde planlanabilir.', 'policy/services/v2026-02', '["service"]'::jsonb, '2026-02-15');
INSERT INTO case_seed.knowledge_entries VALUES ('KNE-COMP-001', 'compatibility', 'tr', 'Saha terminali ve offline senkron uyumluluğu', 'Saha kullanımı ve yerel ağ olmayan mağazalar için 4G destekli el terminali önerilir. Offline senkron ihtiyacı varsa BlueStock Pro lisansı gerekir; Starter lisans offline senkron içermez.', 'kb/compatibility/field-sales-2026', '["pos_terminal","software"]'::jsonb, '2026-03-20');
INSERT INTO case_seed.knowledge_entries VALUES ('KNE-IDEMP-001', 'quote_idempotency', 'tr', 'Teklif kalemi tekrar ekleme davranışı', 'Aynı ürün aynı teklif taslağına tekrar eklenirse yeni satır oluşturulmaz; miktar artırılır. Aynı idempotency anahtarıyla gelen tekrar istekleri ikinci kez miktar artırmaz.', 'engineering/quote-rules/v1', '["quote","quote_item"]'::jsonb, '2026-04-20');
INSERT INTO case_seed.knowledge_entries VALUES ('KNE-PRICE-001', 'price_ceiling', 'tr', 'Fiyat limiti kesin kuralı', 'Kullanıcı bir üst fiyat limiti verdiğinde, bu limitin üzerindeki ürünler öneri cevabında ana öneri olarak sunulmaz ve teklif taslağına otomatik eklenmez. Alternatifler limitin altında ve stokta olmalıdır.', 'policy/pricing/v2026-05', '["product_selection"]'::jsonb, '2026-05-05');
INSERT INTO case_seed.knowledge_entries VALUES ('KNE-FALL-001', 'fallback', 'tr', 'LLM başarısız olduğunda minimum yanıt', 'OPENAI_API_KEY yoksa veya LLM çağrısı başarısız olursa sistem retrieval sonuçları ve teklif durumu üzerinden kontrollü yanıt üretir. Bu modda kaynaklar yine döndürülür; emin olunmayan mutasyonlar yapılmaz.', 'engineering/fallback/v1', '["chat","retrieval","quote"]'::jsonb, '2026-04-25');
INSERT INTO case_seed.knowledge_entries VALUES ('KNE-RET-001-SUP', 'return_policy', 'tr', 'İade değerlendirme uygulama notu', 'İade cevabı verilirken ürün tipi, aktivasyon durumu ve teslim tarihi birlikte kontrol edilmelidir. Aktivasyonu yapılmış lisanslarda kullanıcıya iade yapılamayacağı açık ve kaynaklı şekilde söylenmelidir.', 'policy/returns/v2026-04#uygulama-notu', '["hardware","software","service"]'::jsonb, '2026-04-01');
INSERT INTO case_seed.knowledge_entries VALUES ('KNE-SHIP-001-SUP', 'delivery_policy', 'tr', 'Teslimat cevabı uygulama notu', 'Teslimat cevabı kesin tarih vaadi olarak yazılmamalıdır. Stok, şehir ve hizmet tipi birlikte kontrol edilmeli; stokta olmayan ürün için varsayılan teslimat sözü verilmemelidir.', 'policy/delivery/v2026-04#uygulama-notu', '["hardware","accessory"]'::jsonb, '2026-04-01');
INSERT INTO case_seed.knowledge_entries VALUES ('KNE-WAR-001-SUP', 'warranty', 'tr', 'Garanti cevabı uygulama notu', 'Garanti cevabı kategoriye göre verilmelidir. Rugged ürünlerde 36 ay, ana donanımlarda 24 ay, batarya ve sarf aksesuarlarda 6 ay bilgisi ayrı ayrı korunmalıdır.', 'policy/warranty/v2026-01#uygulama-notu', '["hardware","accessory"]'::jsonb, '2026-01-01');
INSERT INTO case_seed.knowledge_entries VALUES ('KNE-QUOTE-001-SUP', 'quote_validity', 'tr', 'Teklif durumu uygulama notu', 'Taslak teklif müşteriye fiyat görünürlüğü sağlar ancak stok rezervasyonu yapmaz. Kullanıcı stok garantisi isterse satış temsilcisi onayı gerektiği belirtilmelidir.', 'policy/quotes/v2026-03#uygulama-notu', '["quote"]'::jsonb, '2026-03-10');
INSERT INTO case_seed.knowledge_entries VALUES ('KNE-DIS-001-SUP', 'discount_policy', 'tr', 'İndirim hesaplama uygulama notu', 'İndirim cevabı verilirken müşteri fiyat seviyesi, kategori ve miktar birlikte değerlendirilmelidir. Kit ürünlerinde ek indirim uygulanmamalıdır.', 'policy/discounts/v2026-05#uygulama-notu', '["barcode_scanner","receipt_printer","label_printer","accessory","bundle"]'::jsonb, '2026-05-01');
INSERT INTO case_seed.knowledge_entries VALUES ('KNE-STOCK-001-SUP', 'stock_rule', 'tr', 'Stok dışı ürün uygulama notu', 'Stokta olmayan ürün kullanıcı açıkça beklemeyi kabul etmeden teklif taslağına eklenmemelidir. Uygun alternatif varsa önce stoklu alternatif sunulmalıdır.', 'policy/stock/v2026-05#uygulama-notu', '["product_selection","quote"]'::jsonb, '2026-05-01');
INSERT INTO case_seed.knowledge_entries VALUES ('KNE-SVC-001-SUP', 'service_policy', 'tr', 'Servis planlama uygulama notu', 'Kurulum cevabı şehir ve ekip müsaitliği kontrol edilmeden kesinleştirilmemelidir. Acil kurulum yalnızca kapsam dahilindeki şehirlerde kaynakla açıklanmalıdır.', 'policy/services/v2026-02#uygulama-notu', '["service"]'::jsonb, '2026-02-15');
INSERT INTO case_seed.knowledge_entries VALUES ('KNE-COMP-001-SUP', 'compatibility', 'tr', 'Uyumluluk değerlendirme uygulama notu', 'Saha kullanımı, internet erişimi ve offline senkron ihtiyacı ayrı gereksinimler olarak ele alınmalıdır. Offline senkron gerekiyorsa Starter lisans yeterli gösterilmemelidir.', 'kb/compatibility/field-sales-2026#uygulama-notu', '["pos_terminal","software"]'::jsonb, '2026-03-20');
INSERT INTO case_seed.knowledge_entries VALUES ('KNE-IDEMP-001-SUP', 'quote_idempotency', 'tr', 'Tekrarlı istek uygulama notu', 'Aynı mesaj veya aynı idempotency anahtarı tekrar işlenirse miktar ikinci kez artırılmamalıdır. Kullanıcı aynı üründen ek miktar istediğinde ise mevcut satır miktarı artırılmalıdır.', 'engineering/quote-rules/v1#uygulama-notu', '["quote","quote_item"]'::jsonb, '2026-04-20');
INSERT INTO case_seed.knowledge_entries VALUES ('KNE-PRICE-001-SUP', 'price_ceiling', 'tr', 'Fiyat limiti uygulama notu', 'Fiyat üst limiti kullanıcı tarafından açık verildiyse pazarlık önerisi gibi yorumlanmamalıdır. Otomatik ekleme ve değiştirme kararlarında limit kesin filtre olarak uygulanmalıdır.', 'policy/pricing/v2026-05#uygulama-notu', '["product_selection"]'::jsonb, '2026-05-05');
INSERT INTO case_seed.knowledge_entries VALUES ('KNE-FALL-001-SUP', 'fallback', 'tr', 'Yedek mod uygulama notu', 'Yedek modda sistem yalnızca retrieval sonucu ve teklif durumu üzerinden güvenli cevap vermelidir. Emin olunmayan ürün mutasyonları yapılmamalı ve kaynaklar yine döndürülmelidir.', 'engineering/fallback/v1#uygulama-notu', '["chat","retrieval","quote"]'::jsonb, '2026-04-25');

INSERT INTO case_seed.customers VALUES ('CUST-IST-001', 'Mavi Kırmızı Market A.Ş.', 'retail', 'İstanbul', 'standard', 50000, FALSE, 'tr', 'Strict stock rule. Main web/mobile sync customer.');
INSERT INTO case_seed.customers VALUES ('CUST-ANK-002', 'Ankara Toptan Depo Ltd.', 'wholesale', 'Ankara', 'partner', 120000, TRUE, 'tr', 'Eligible for partner quantity discounts and backorder.');
INSERT INTO case_seed.customers VALUES ('CUST-IZM-003', 'İzmir Fresh Gıda', 'food_retail', 'İzmir', 'standard', 35000, FALSE, 'tr', 'Uses delivery policy scenarios.');
INSERT INTO case_seed.customers VALUES ('CUST-EXT-001', 'Mavi Kırmızı Market A.Ş. Pilot Şube', 'retail', 'İstanbul', 'partner', 70000, TRUE, 'tr', 'Genişletilmiş JSON dataset müşterisi; temel müşteri: CUST-IST-001.');
INSERT INTO case_seed.customers VALUES ('CUST-EXT-002', 'Ankara Toptan Depo Ltd. Pilot Şube', 'wholesale', 'Ankara', 'partner', 168000, TRUE, 'tr', 'Genişletilmiş JSON dataset müşterisi; temel müşteri: CUST-ANK-002.');
INSERT INTO case_seed.customers VALUES ('CUST-EXT-003', 'İzmir Fresh Gıda Pilot Şube', 'food_retail', 'İzmir', 'partner', 49000, TRUE, 'tr', 'Genişletilmiş JSON dataset müşterisi; temel müşteri: CUST-IZM-003.');

INSERT INTO case_seed.price_rules VALUES ('RUL-PARTNER-3', 'Partner category quantity discount', 'customer.price_tier == partner and category in barcode_scanner,receipt_printer,label_printer and category_qty >= 3', 7);
INSERT INTO case_seed.price_rules VALUES ('RUL-ACC-5', 'Accessory quantity discount', 'category == accessory and product_qty >= 5', 5);
INSERT INTO case_seed.price_rules VALUES ('RUL-BUNDLE-NO-STACK', 'Bundle no extra discount', 'category == bundle', 0);
INSERT INTO case_seed.price_rules VALUES ('RUL-SVC-URGENT', 'Urgent service no discount', 'category == service and tags contains acil', 0);
INSERT INTO case_seed.price_rules VALUES ('RUL-SW-BUNDLE', 'Software plus module bundle discount', 'category == software and quote contains PRD-SW-520 and PRD-SW-530', 8);
INSERT INTO case_seed.price_rules VALUES ('RUL-PLUS-QTY', 'Plus variant volume discount', 'sku ends_with PLUS and product_qty >= 4', 6);

INSERT INTO case_seed.quotes VALUES ('Q-1001', 'CUST-IST-001', 'draft', 'mobile', 'TRY', 'Contains one wireless scanner for duplicate/idempotency tests.');
INSERT INTO case_seed.quotes VALUES ('Q-1002', 'CUST-ANK-002', 'draft', 'web', 'TRY', 'Empty partner quote for add and discount scenarios.');
INSERT INTO case_seed.quotes VALUES ('Q-1003', 'CUST-IST-001', 'draft', 'web', 'TRY', 'Contains Ethernet printers for update quantity test.');
INSERT INTO case_seed.quotes VALUES ('Q-1004', 'CUST-IST-001', 'draft', 'mobile', 'TRY', 'Contains expensive rugged scanner for replace-with-alternative test.');
INSERT INTO case_seed.quotes VALUES ('Q-1005', 'CUST-IST-001', 'draft', 'web', 'TRY', 'Contains out-of-stock pocket scanner for stock replacement test.');
INSERT INTO case_seed.quotes VALUES ('Q-2001', 'CUST-EXT-001', 'draft', 'mobile', 'TRY', 'Genişletilmiş JSON dataset teklifi; yedek mod ve tekrar ekleme senaryoları için.');
INSERT INTO case_seed.quotes VALUES ('Q-2002', 'CUST-EXT-002', 'draft', 'web', 'TRY', 'Genişletilmiş JSON dataset teklifi; iş ortağı indirimi ve servis senaryoları için.');
INSERT INTO case_seed.quotes VALUES ('Q-2003', 'CUST-EXT-003', 'draft', 'mobile', 'TRY', 'Genişletilmiş JSON dataset teklifi; aksesuar ve kaynaklı cevap senaryoları için.');
INSERT INTO case_seed.quotes VALUES ('Q-2004', 'CUST-EXT-001', 'draft', 'web', 'TRY', 'Genişletilmiş JSON dataset teklifi; değiştirme senaryoları için.');
INSERT INTO case_seed.quotes VALUES ('Q-2005', 'CUST-EXT-002', 'draft', 'mobile', 'TRY', 'Genişletilmiş JSON dataset teklifi; güncelleme senaryoları için.');

INSERT INTO case_seed.quote_items VALUES ('QI-1001-1', 'Q-1001', 'PRD-BC-110', 1, 7990, 'active', 'seed', 'seed-Q-1001-PRD-BC-110');
INSERT INTO case_seed.quote_items VALUES ('QI-1003-1', 'Q-1003', 'PRD-PRN-320', 2, 7350, 'active', 'seed', 'seed-Q-1003-PRD-PRN-320');
INSERT INTO case_seed.quote_items VALUES ('QI-1004-1', 'Q-1004', 'PRD-BC-120', 1, 12950, 'active', 'seed', 'seed-Q-1004-PRD-BC-120');
INSERT INTO case_seed.quote_items VALUES ('QI-1005-1', 'Q-1005', 'PRD-BC-130', 2, 6750, 'active', 'seed', 'seed-Q-1005-PRD-BC-130');
INSERT INTO case_seed.quote_items VALUES ('QI-2001-1', 'Q-2001', 'PRD-BC-110-PLUS', 1, 9430, 'active', 'seed', 'seed-Q-2001-PRD-BC-110-PLUS');
INSERT INTO case_seed.quote_items VALUES ('QI-2003-1', 'Q-2003', 'PRD-ACC-710-PLUS', 4, 1120, 'active', 'seed', 'seed-Q-2003-PRD-ACC-710-PLUS');
INSERT INTO case_seed.quote_items VALUES ('QI-2004-1', 'Q-2004', 'PRD-PRN-330', 1, 8900, 'active', 'seed', 'seed-Q-2004-PRD-PRN-330');
INSERT INTO case_seed.quote_items VALUES ('QI-2005-1', 'Q-2005', 'PRD-SVC-810', 1, 4500, 'active', 'seed', 'seed-Q-2005-PRD-SVC-810');
