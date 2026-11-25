-- 0002: "Düzelt" özelliği (26 Kasım 2026)
-- Düzeltilmiş kayıt, düzelttiği eski kayda onceki sütunuyla bağlanır. Bu sütun da eklenme kaydı gibi değiştirilemez.
ALTER TABLE urunler ADD COLUMN onceki INTEGER REFERENCES urunler(id);
DROP TRIGGER IF EXISTS urunler_ekleme_degismez;
CREATE TRIGGER urunler_ekleme_degismez
BEFORE UPDATE OF alan, marka, urun, kategori, dayanak, notu, ekleyen, eklendi, esas, onceki ON urunler
BEGIN
  SELECT RAISE(ABORT, 'Eklenme kaydı değiştirilemez.');
END;
