// Glutensiz Kontrol — Ortak yardımcılar, simgeler, sabitler ve sayfanın durumu (liste verisi, seçili sekme).
// Sayfanın betikleri ortak bir kapsamda, şu sırayla çalışır: temel → cevrimdisi → kisisel → ekle → veri → liste → tepki → gorunum → baslat.
const $ = s => document.querySelector(s);
const out = $('#out'), qi = $('#q'), clearB = $('#clear');
const ICON = {
  ok2: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M2.5 12.5l4 4L13 9"/><path d="M10.5 15.5l1 1L21.5 7"/></svg>',
  ok: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>',
  half: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M6 12h12"/></svg>',
  eye: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>',
  no: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M5.6 5.6l12.8 12.8"/></svg>',
  warn: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3 2 20h20L12 3z"/><path d="M12 10v4M12 17h.01"/></svg>',
  back: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 18l-6-6 6-6"/></svg>',
  lab: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 3h6M10 3v6.5l-5.2 8.7A2 2 0 0 0 6.5 21h11a2 2 0 0 0 1.7-2.8L14 9.5V3"/><path d="M7.4 15h9.2"/></svg>',
  ext: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17 17 7M9 7h8v8"/></svg>'
};
ICON.us = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M6.5 3.5h11v17l-5.5-3.8-5.5 3.8z"/></svg>';
ICON.plus = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>';
ICON.x = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M7 7l10 10M17 7 7 17"/></svg>';
ICON.down = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>';
ICON.heart = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>';
ICON.up = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/></svg>';
ICON.dn = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17"/></svg>';
ICON.iki = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>';
const DOMAINS = [['gida','Gıda'],['ilac','İlaç'],['kozmetik','Bakım & kozmetik'],['takviye','Takviye']];
const SRC = {ist:'İST', ank:'ANK'};
const SRCN = {ist:'İstanbul', ank:'Ankara'};
const MONTHS = ['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık'];
let REP = {}, D, CAT = {}, BN = {}, LBY = {}, GRP = {}, GBY = {}, CATL = {}, BNORM = {}, LN = [], PB = new Set();
// pick: kullanıcının seçtiği sekme (kalıcı); dom: o an gösterilen. Aramadaki otomatik geçiş yalnızca dom'u değiştirir.
const st = {q:'', dom:'gida', pick:'gida', view:'home', cat:null, open:new Set(), noAuto:false, keyOpen:false};
try { const s = localStorage.getItem('gk-dom'); if (s && DOMAINS.some(d => d[0] === s)){ st.dom = s; st.pick = s; } } catch (e) {}

function esc(s){return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function norm(s){
  s = String(s || '').normalize('NFC').replace(/[​‍﻿]/g, '').replace(/ /g, ' ');
  s = s.replace(/I/g, 'ı').replace(/İ/g, 'i').toLowerCase();
  s = s.replace(/[’'`´‘ʼ](nın|nin|nun|nün|ın|in|un|ün|ı|i|u|ü|a|e|da|de|ta|te|dan|den|tan|ten|yla|yle|la|le)(?![a-zçğıöşü])/g, '');
  s = s.replace(/[’'`´‘ʼ]/g, '');
  s = s.replace(/[çğıöşüâîû]/g, c => ({'ç':'c','ğ':'g','ı':'i','ö':'o','ş':'s','ü':'u','â':'a','î':'i','û':'u'}[c]));
  s = s.normalize('NFKD').replace(/[̀-ͯ]/g, '');
  s = s.replace(/&/g, ' & ').replace(/[^a-z0-9%&+]+/g, ' ').replace(/\s+/g, ' ').trim();
  s = s.replace(/\b(?:[a-z0-9] ){2,}[a-z0-9]\b/g, m => m.replace(/ /g, ''));
  return s;
}
function fmtMonth(ym){ const [y, m] = String(ym).split('-').map(Number); return m ? MONTHS[m-1] + ' ' + y : String(y); }
function fmtDate(iso){ if(!iso) return ''; const [y,m,d] = iso.slice(0,10).split('-').map(Number); return d + ' ' + MONTHS[m-1] + ' ' + y; }
function lev(a, b){
  if (Math.abs(a.length - b.length) > 2) return 9;
  const m = a.length, n = b.length; let prev = Array.from({length:n+1}, (_, j) => j);
  for (let i = 1; i <= m; i++){ const cur = [i]; for (let j = 1; j <= n; j++){ cur[j] = Math.min(prev[j]+1, cur[j-1]+1, prev[j-1] + (a[i-1] === b[j-1] ? 0 : 1)); } prev = cur; }
  return prev[n];
}
const KAT_DIS = new Set(['etiket-oku', 'kozmetik-oku', 'ilac-firma']);  // ürün kategorisi olmayan dernek başlıkları
// bildirim ve yeniden çizim (her bölüm kullanır)
let toastT;
function toast(msg){
  const el = $('#toast'); el.textContent = msg; el.classList.add('on');
  clearTimeout(toastT); toastT = setTimeout(() => el.classList.remove('on'), 3400);
}
function rerender(){ if (D) route(); }
