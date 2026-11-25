# -*- coding: utf-8 -*-
"""Glutensiz Kontrol — liste derleyici (dernek sayfalarından site/data.json).

Katmanlar (her biri yalnızca kendinden öncekileri kullanır):
  metin → kategoriler → markalar → ortak → ayristir → zenginlestir → esles → cikti
Giriş noktası scripts/pipeline.py; haftalık güncelleme (update.py) onu çağırır.
"""
from .cikti import PIPELINE_VERSION, build, assign_uids, diff_changes  # noqa: F401
from .metin import norm, clean  # noqa: F401
