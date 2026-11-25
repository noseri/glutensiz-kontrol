/**
 * Glutensiz Kontrol — "Bizim listemiz" sunucusu (Cloudflare Worker + D1)
 *
 *   GET  /liste  → listedeki ve listeden çıkarılmış ürünler (herkese açık, yalnızca okuma)
 *   GET  /ben    → bu şifre kimin?                      (Authorization: Bearer <şifre>)
 *   POST /ekle   → ürün ekle   {alan, marka, urun, kategori?, dayanak, notu?}
 *   POST /cikar  → listeden çıkar {id}
 *   POST /duzelt → düzelt {id, alan, marka, urun, kategori?, dayanak, notu?}: eski kayıt "düzeltildi" olarak
 *                  geçmişe alınır, düzeltilmiş hali yeni kayıt olarak eklenir (onceki = eski kaydın id'si)
 *
 * Kimin eklediğini ya da çıkardığını şifre belirler (KISILER: gizli değerin adı → görünen ad),
 * zamanı sunucunun saati belirler. Uygulamadan gelen bir ad ya da tarih hiç kullanılmaz.
 * Kayıtlar silinmez; veritabanındaki tetikleyiciler eklenme ve çıkarma kaydının sonradan
 * değiştirilmesini de engeller (bkz. schema.sql).
 */

const ALANLAR = new Set(['gida', 'ilac', 'kozmetik', 'takviye']);
const DAYANAKLAR = new Set(['paket', 'uretici', 'analiz', 'deneyim', 'diger']);
const SINIR = { marka: 60, urun: 120, kategori: 60, notu: 280 };
const ETIKET = { marka: 'Marka', urun: 'Ürün adı', kategori: 'Kategori', notu: 'Not' };
const SUTUNLAR = 'id, alan, marka, urun, kategori, dayanak, notu, ekleyen, eklendi, cikaran, cikarildi, onceki';
const enc = new TextEncoder();

class Hata extends Error {
  constructor(durum, mesaj, ek) {
    super(mesaj);
    this.durum = durum;
    this.ek = ek || null;
  }
}

const bekle = ms => new Promise(r => setTimeout(r, ms));

function yanit(veri, durum, cors) {
  return new Response(JSON.stringify(veri), {
    status: durum,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'no-store',
      'X-Content-Type-Options': 'nosniff',
      ...cors,
    },
  });
}

function corsBasliklari(req, env) {
  const origin = req.headers.get('Origin');
  const izinli = String(env.IZINLI_KOKENLER || '').split(',').map(s => s.trim()).filter(Boolean);
  const h = { Vary: 'Origin' };
  if (origin && izinli.includes(origin)) h['Access-Control-Allow-Origin'] = origin;
  return h;
}

// Görünmez ve yön değiştiren karakterleri at, boşlukları sadeleştir, uzunluğu denetle.
function temizle(deger, alan, zorunlu) {
  const s = deger == null ? '' : String(deger)
    .normalize('NFC')
    .replace(/[\u0000-\u001f\u007f-\u009f\u200b-\u200f\u2028-\u202e\u2066-\u2069\ufeff]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  if (zorunlu && !s) throw new Hata(400, ETIKET[alan] + ' boş olamaz.');
  if (s.length > SINIR[alan]) throw new Hata(400, ETIKET[alan] + ' en fazla ' + SINIR[alan] + ' karakter olabilir.');
  return s || null;
}

// Aynı ürünü iki kez eklememek için karşılaştırma anahtarı (Türkçe harf ve büyük/küçük harf farkı yok sayılır).
function esasla(s) {
  return String(s || '')
    .normalize('NFC')
    .replace(/I/g, 'ı').replace(/İ/g, 'i')
    .toLowerCase()
    .replace(/[çğıöşüâîû]/g, c => ({ 'ç': 'c', 'ğ': 'g', 'ı': 'i', 'ö': 'o', 'ş': 's', 'ü': 'u', 'â': 'a', 'î': 'i', 'û': 'u' })[c])
    .normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9%&+]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

// ---- kimlik
async function ozet(s) {
  return new Uint8Array(await crypto.subtle.digest('SHA-256', enc.encode(s)));
}

function ayni(a, b) {
  if (a.byteLength !== b.byteLength) return false;
  if (crypto.subtle.timingSafeEqual) return crypto.subtle.timingSafeEqual(a, b);
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a[i] ^ b[i];
  return d === 0;
}

function kisiler(env) {
  try {
    return Object.entries(JSON.parse(env.KISILER || '{}'))
      .filter(([ad, gorunen]) => /^ANAHTAR_[A-Z0-9_]+$/.test(ad) && typeof gorunen === 'string' && gorunen.trim());
  } catch {
    return [];
  }
}

// Uygulama şifreyi encodeURIComponent ile gönderir: başlıklar yalnızca Latin-1 taşıyabildiği için
// ı, ş, ğ, İ gibi harfler kodlanmadan gönderilemez. Kodlanmamış (eski) biçim de kabul edilir.
function sifreAdaylari(ham) {
  let cozulmus = ham;
  try { cozulmus = decodeURIComponent(ham); } catch { /* kodlanmamış */ }
  return [...new Set([cozulmus, ham].map(s => s.normalize('NFC').trim()))].filter(s => s.length >= 8 && s.length <= 256);
}

async function kim(req, env) {
  const m = (req.headers.get('Authorization') || '').match(/^Bearer\s+([\s\S]+)$/);
  if (!m) return null;
  const adaylar = sifreAdaylari(m[1].trim());
  if (!adaylar.length) return null;
  const ozetler = await Promise.all(adaylar.map(ozet));
  let bulunan = null;
  for (const [degisken, gorunen] of kisiler(env)) {
    const gizli = typeof env[degisken] === 'string' ? env[degisken].normalize('NFC').trim() : '';
    if (gizli.length < 8) continue;
    const go = await ozet(gizli);
    // erken çıkmadan hepsini karşılaştır: yanıt süresi hangi şifrenin denendiğini ele vermesin
    for (const vo of ozetler) if (ayni(vo, go) && !bulunan) bulunan = gorunen.trim();
  }
  return bulunan;
}

// ---- istek gövdesi
async function govde(req) {
  if (!(req.headers.get('Content-Type') || '').includes('application/json')) throw new Hata(415, 'İstek JSON olmalı.');
  const metin = await req.text();
  if (metin.length > 4096) throw new Hata(413, 'İstek çok büyük.');
  let v = null;
  try { v = JSON.parse(metin); } catch { /* aşağıda */ }
  if (!v || typeof v !== 'object' || Array.isArray(v)) throw new Hata(400, 'İstek okunamadı.');
  return v;
}

// ---- işlemler
async function liste(env) {
  const { results } = await env.DB.prepare(`SELECT ${SUTUNLAR} FROM urunler ORDER BY id DESC`).all();
  const urunler = [], cikarilanlar = [];
  for (const r of results) (r.cikarildi ? cikarilanlar : urunler).push(r);
  return { zaman: new Date().toISOString(), urunler, cikarilanlar };
}

// ürün alanlarını denetle ve sadeleştir (ekleme ve düzeltmede ortak)
function alanlar(g) {
  const alan = String(g.alan || '');
  if (!ALANLAR.has(alan)) throw new Hata(400, 'Hangi listeye (Gıda, İlaç…) ekleneceğini seçin.');
  const dayanak = String(g.dayanak || '');
  if (!DAYANAKLAR.has(dayanak)) throw new Hata(400, 'Neye dayanarak eklediğinizi seçin.');
  const marka = temizle(g.marka, 'marka', true);
  const urun = temizle(g.urun, 'urun', true);
  const kategori = temizle(g.kategori, 'kategori', false);
  const notu = temizle(g.notu, 'notu', false);
  const em = esasla(marka), eu = esasla(urun);
  if (!em || !eu) throw new Hata(400, 'Marka ve ürün adında harf ya da rakam olmalı.');
  return { alan, marka, urun, kategori, dayanak, notu, esas: alan + '|' + em + '|' + eu };
}

async function zatenVar(env, esas, mesaj) {
  const mevcut = await env.DB.prepare(`SELECT ${SUTUNLAR} FROM urunler WHERE esas = ? AND cikarildi IS NULL`).bind(esas).first();
  return new Hata(409, mesaj, { urun: mevcut });
}

async function ekle(req, env, ad) {
  const v = alanlar(await govde(req));
  try {
    return await env.DB.prepare(
      `INSERT INTO urunler (alan, marka, urun, kategori, dayanak, notu, ekleyen, eklendi, esas)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING ${SUTUNLAR}`
    ).bind(v.alan, v.marka, v.urun, v.kategori, v.dayanak, v.notu, ad, new Date().toISOString(), v.esas).first();
  } catch (e) {
    if (/UNIQUE/i.test(String(e && e.message))) throw await zatenVar(env, v.esas, 'Bu ürün zaten listede.');
    throw e;
  }
}

// Düzeltme: iki adım tek işlemde (D1 batch). Eski kayıt düzeltenin adı ve saatiyle geçmişe alınır,
// düzeltilmiş hali "onceki" ile ona bağlı yeni kayıt olur. Adımlardan biri olmazsa hiçbiri olmaz.
async function duzelt(req, env, ad) {
  const g = await govde(req);
  const id = Number(g.id);
  if (!Number.isSafeInteger(id) || id < 1) throw new Hata(400, 'Hangi ürünün düzeltileceği belirtilmemiş.');
  const v = alanlar(g);
  const yok = () => new Hata(404, 'Bu ürün listede değil; az önce çıkarılmış ya da düzeltilmiş olabilir.');
  const eski = await env.DB.prepare(`SELECT ${SUTUNLAR} FROM urunler WHERE id = ?`).bind(id).first();
  if (!eski || eski.cikarildi) throw yok();
  if (['alan', 'marka', 'urun', 'kategori', 'dayanak', 'notu'].every(k => (eski[k] || null) === (v[k] || null))) {
    throw new Hata(400, 'Değişiklik yapmadınız.');
  }
  const zaman = new Date().toISOString();
  let sonuc;
  try {
    sonuc = await env.DB.batch([
      env.DB.prepare('UPDATE urunler SET cikaran = ?, cikarildi = ? WHERE id = ? AND cikarildi IS NULL').bind(ad, zaman, id),
      env.DB.prepare(
        `INSERT INTO urunler (alan, marka, urun, kategori, dayanak, notu, ekleyen, eklendi, esas, onceki)
         SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
         WHERE EXISTS (SELECT 1 FROM urunler WHERE id = ? AND cikarildi = ? AND cikaran = ?)
         RETURNING ${SUTUNLAR}`
      ).bind(v.alan, v.marka, v.urun, v.kategori, v.dayanak, v.notu, ad, zaman, v.esas, id, id, zaman, ad),
    ]);
  } catch (e) {
    if (/UNIQUE/i.test(String(e && e.message))) throw await zatenVar(env, v.esas, 'Bu adla başka bir ürün zaten listede.');
    throw e;
  }
  const yeni = sonuc[1] && sonuc[1].results && sonuc[1].results[0];
  if (!yeni) throw yok();  // bu arada başkası çıkardı ya da düzeltti
  const eskiSon = await env.DB.prepare(`SELECT ${SUTUNLAR} FROM urunler WHERE id = ?`).bind(id).first();
  return { eski: eskiSon, yeni };
}

async function cikar(req, env, ad) {
  const g = await govde(req);
  const id = Number(g.id);
  if (!Number.isSafeInteger(id) || id < 1) throw new Hata(400, 'Hangi ürünün çıkarılacağı belirtilmemiş.');
  const r = await env.DB.prepare(
    `UPDATE urunler SET cikaran = ?, cikarildi = ? WHERE id = ? AND cikarildi IS NULL RETURNING ${SUTUNLAR}`
  ).bind(ad, new Date().toISOString(), id).first();
  if (!r) throw new Hata(404, 'Bu ürün listede değil; az önce çıkarılmış olabilir.');
  return r;
}

export default {
  async fetch(req, env) {
    const cors = corsBasliklari(req, env);
    const yol = new URL(req.url).pathname.replace(/\/+$/, '') || '/';
    if (req.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: {
          ...cors,
          'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Authorization, Content-Type',
          'Access-Control-Max-Age': '86400',
        },
      });
    }
    try {
      if (req.method === 'GET' && yol === '/liste') return yanit(await liste(env), 200, cors);
      if (req.method === 'GET' && yol === '/') return yanit({ ad: 'Glutensiz Kontrol · Bizim listemiz', durum: 'çalışıyor' }, 200, cors);
      const islem = req.method + ' ' + yol;
      if (!['GET /ben', 'POST /ekle', 'POST /cikar', 'POST /duzelt'].includes(islem)) throw new Hata(404, 'Böyle bir adres yok.');
      const ad = await kim(req, env);
      if (!ad) {
        await bekle(700); // tahmin denemelerini yavaşlat
        throw new Hata(401, 'Şifre tanınmadı.');
      }
      if (islem === 'GET /ben') return yanit({ ad }, 200, cors);
      if (islem === 'POST /ekle') return yanit({ urun: await ekle(req, env, ad) }, 201, cors);
      if (islem === 'POST /duzelt') return yanit(await duzelt(req, env, ad), 200, cors);
      return yanit({ urun: await cikar(req, env, ad) }, 200, cors);
    } catch (e) {
      if (e instanceof Hata) return yanit({ hata: e.message, ...(e.ek || {}) }, e.durum, cors);
      console.error(e);
      return yanit({ hata: 'Sunucuda bir sorun oldu; biraz sonra yeniden deneyin.' }, 500, cors);
    }
  },
};
