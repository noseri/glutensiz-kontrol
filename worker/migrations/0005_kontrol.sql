-- 0005: Bizim listemiz için "kontrol ettim" kayıtları; dokunma kaydına olası neden (26 Kasım 2026)
-- Yalnızca ekleme yapar; var olan kayıtlara dokunmaz.
ALTER TABLE dokunmalar ADD COLUMN neden TEXT CHECK (neden IN ('bulasma', 'agir', 'baska', 'bilinmiyor'));

-- "Kontrol ettim": Bizim listemiz ürününün paketi yeniden okundu (kim, ne zaman). Kayıt değiştirilemez ve silinmez.
-- urun: o anki kaydın id'si; düzeltmeden sonra da eski kayda bağlı kontroller sayılır (uygulama zinciri izler).
CREATE TABLE IF NOT EXISTS kontroller (
  id    INTEGER PRIMARY KEY AUTOINCREMENT,
  urun  INTEGER NOT NULL,
  kisi  TEXT NOT NULL,
  zaman TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS kontroller_urun ON kontroller (urun);
CREATE TRIGGER IF NOT EXISTS kontroller_degismez
BEFORE UPDATE ON kontroller
BEGIN
  SELECT RAISE(ABORT, 'Kontrol kaydı değiştirilemez.');
END;
CREATE TRIGGER IF NOT EXISTS kontroller_silinmez
BEFORE DELETE ON kontroller
BEGIN
  SELECT RAISE(ABORT, 'Kontrol kaydı silinemez.');
END;
