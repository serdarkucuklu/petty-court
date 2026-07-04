# Design — Internet Drama Podcast (autonomous daily 2-host reaction show)

**Tarih:** 2026-07-04
**Klasör:** `D:\AI\Playground\14-drama-podcast\`
**Durum:** Onaylandı (brainstorming) → writing-plans'e geçiliyor

---

## 1. Amaç & tek cümle

Her gün otonom olarak Reddit'ten en "podcast'lik" internet-drama/intikam hikayesini çekip,
iki AI host'un doğal, esprili konuştuğu bir diyalog bölümüne dönüştüren, seslendiren ve hem
RSS podcast (Spotify/Apple) hem YouTube'a otomatik yayınlayan sıfır-marjinal-maliyet içerik motoru.

**Show kimliği:** İnternet draması & intikam reaksiyonu — iki host, sabit persona/ton.
(Çalışma adı: *"Petty Court"* — değiştirilebilir.)

## 2. Onaylanan çekirdek kararlar

| Karar | Seçim | Gerekçe |
|-------|-------|---------|
| Pazar/dil | İngilizce, global | En büyük kitle + gelir potansiyeli |
| Format | 2-host çok-sesli diyalog/reaksiyon | En "podcast" format; transformative (telif güvenli) |
| Script beyni | **Gemini 2.5 Flash** (bedava tier) | En iyi ücretsiz; TTS ile tek ekosistem/tek key |
| TTS | **Gemini 2.5 native multi-speaker** | Tam bu iş için; tek çağrıyla iki-sesli diyalog, doğal |
| Yayın | RSS (Spotify/Apple) + YouTube — **baştan ikisi** | Geniş erişim; bileşenler ayrı, yönetilebilir |
| Orkestrasyon | **GitHub Actions** günlük cron | 7/24, makine kapalıyken de çalışır |
| Maliyet | ~Sıfır marjinal | Bedava tier'lar + GHA/Pages/YouTube bedava |

## 3. Pipeline mimarisi (her gün 1 bölüm)

```
[1 Fetch]   Reddit public JSON (keysiz): rotating subreddit havuzu, top?t=day
     ↓
[2 Curate]  Filtre (min upvote / uzunluk penceresi / NSFW / deleted)
            + dedupe (state/history.json) → Gemini "en sesli-anlatıya uygun" adayı seçer
     ↓
[3 Script]  Gemini 2.5 Flash: ham hikaye → 2-host diyalog senaryosu
            (cold-open hook, anlatım, host tepkileri/şaka, kapanış+CTA) — [S1]/[S2] etiketli
     ↓
[4 Voice]   Gemini 2.5 multi-speaker: tek çağrı → tam diyalog audio (WAV)
     ↓
[5 Audio]   ffmpeg: intro/outro müzik + loudness normalize (-16 LUFS mono/stereo) → MP3
     ↓
[6a RSS]    MP3 → GitHub Pages storage + feed.xml güncelle (Spotify/Apple otomatik pull)
[6b Video]  ffmpeg: kapak + waveform → MP4 → YouTube Data API upload
     ↓
[7 State]   history.json güncelle (kullanılan post ID'leri + bölüm arşivi) → commit
```

Her aşama tek-sorumlu, bağımsız test edilebilir modül. Bir aşama patlarsa (örn. YouTube
kotası) diğer çıktı (RSS) yayınlanmaya devam eder — kısmi başarı > tam başarısızlık.

## 4. Modül sınırları (bileşenler)

Her modül net girdi/çıktı ile, ayrı dosya:

- **`sources/reddit.py`** — subreddit havuzundan ham post listesi çeker. Girdi: config (sub listesi,
  eşikler). Çıktı: `list[RawPost]`. Bağımlılık: yok (stdlib http / requests).
- **`curate.py`** — filtre + dedupe + Gemini-tabanlı seçim. Girdi: `list[RawPost]` + history.
  Çıktı: tek `SelectedStory`. Bağımlılık: Gemini client, history store.
- **`script.py`** — hikaye → diyalog senaryosu. Girdi: `SelectedStory` + persona config.
  Çıktı: `DialogueScript` (konuşmacı-etiketli satırlar + başlık/açıklama/etiket metadata).
- **`voice.py`** — senaryo → audio. Girdi: `DialogueScript`. Çıktı: WAV path. Bağımlılık: Gemini TTS.
  Fallback: edge-tts (opsiyonel, kota dolarsa).
- **`audio.py`** — WAV → yayına hazır MP3 (müzik, normalize). ffmpeg wrapper.
- **`video.py`** — MP3 + kapak → MP4 (statik görsel + waveform). ffmpeg wrapper.
- **`publish/rss.py`** — MP3'ü storage'a koy + feed.xml (RSS 2.0 + iTunes namespace) üret/güncelle.
- **`publish/youtube.py`** — MP4 upload (Data API v3, OAuth refresh token).
- **`state.py`** — history.json oku/yaz (kullanılan post ID, bölüm arşivi, sayaç).
- **`main.py`** — orkestrasyon; aşamaları sırayla çağırır, hata izolasyonu, log.
- **`config.yaml`** — subreddit havuzu, eşikler, persona (host isim/ton), TTS ses seçimi, show metadata.

## 5. Kritik detaylar & gotcha'lar

- **Telif/orijinallik:** Verbatim okuma YOK. 2-host transformative yorum/reaksiyon. Açıklamada
  kaynak subreddit atfı. Bu format doğal olarak dönüştürücü → takedown riski düşük.
- **RSS host:** GitHub Pages bedava; `feed.xml` + MP3 dosyaları. Spotify for Podcasters & Apple'a
  RSS URL'i **bir kez manuel** eklenir (API yok), sonrası otomatik pull. Bu tek manuel adım.
- **Depolama büyümesi:** ~20-40 MB/gün MP3 repo/Pages'te birikir. İlk aşama için sorun değil;
  ~1 yıl sonra bucket'a (R2/S3) taşıma gerekebilir → günlüğe not, şimdilik YAGNI.
- **YouTube OAuth:** Bir kez local'de refresh token üretilir, GHA secret olarak saklanır.
  Data API günlük upload kotası (varsayılan ~6 upload/gün eşdeğeri) 1 bölüm için fazlasıyla yeter.
- **Gemini bedava tier limitleri:** Günde 1 script + 1 TTS çağrısı rahatça sığar. Rate-limit
  hatası için basit retry + fallback.
- **İlk 10 saniye:** Cold-open hook script prompt'unda zorunlu — retention'ın en kritik anı.
- **Loudness:** Podcast standardı -16 LUFS (stereo) / -19 (mono). ffmpeg `loudnorm` ile.

## 6. Sır & konfigürasyon (GHA Secrets)

- `GEMINI_API_KEY` — script + TTS (tek key)
- `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`
- (Reddit okuma keysiz; gerekirse `REDDIT_CLIENT_ID/SECRET` ileride)

## 7. Maliyet & gerçekçi beklenti

- **Marjinal maliyet ~0:** Gemini bedava tier, GHA/Pages/YouTube bedava. "Pasif" mekanik doğru.
- **Gelir otomatik DEĞİL:** YouTube reklam eşiği (1k abone / 4k saat), Spotify/sponsor kitle ister.
  İlk 2-3 ay gelir ~0 — kitle kurma dönemi. Otomasyonun asıl değeri: **maliyetsiz, insan emeği
  harcamadan her gün yayında kalıp kitlenin büyümesini bekleyebilmek.**
- **Başarı ölçütü (v1):** Her gün otomatik, insan müdahalesiz, kaliteli bir bölüm hem RSS hem
  YouTube'da yayınlanıyor. Gelir v1 hedefi değil; altyapı hedefi.

## 8. Kapsam dışı (v1 YAGNI)

- Çoklu dil / TR versiyonu
- Bucket depolama (Pages yeterli olduğu sürece)
- Shorts/klip otomatik üretimi (v2 büyüme aracı)
- Web sitesi/landing page
- Dinamik reklam ekleme (dynamic ad insertion)

## 9. Stack

- **Dil:** Python 3.11+ (`.venv` klasör içinde), Playground standardı
- **Bağımlılıklar:** `google-genai` (Gemini), `requests`, `google-api-python-client` (+auth) YouTube,
  `feedgen` veya elle RSS, ffmpeg (sistem binary, GHA'da hazır)
- **Çalışma:** GitHub Actions `schedule` cron (günlük) + `workflow_dispatch` (manuel tetik/test)
- **Güvenlik:** key'ler `.env` (local) / GHA Secrets (prod); `.env`+`.venv` gitignore

## 10. Canlı doğrulama sonuçları (2026-07-04) & production caveat'leri

**Uçtan uca CANLI test geçti** (gerçek Gemini + gerçek ffmpeg, Reddit yerine kanıt hikaye enjekte edildi):
script (Gemini 2.5 Flash) → 34 replikli 2-host diyalog; TTS (multi-speaker) → 5:20 dk gerçek konuşma
(15.3MB WAV, 24kHz mono); ffmpeg → 5.1MB MP3 (loudnorm) + 34.5MB MP4; RSS feed.xml üretildi. Zincirin
tamamı gerçekten çalışıyor.

**Production'a çıkmadan çözülmesi gereken operasyonel bulgular:**
1. **DEDİKE Gemini key/proje şart.** Test sırasında Playground'ın ortak `AIzaSy…` key'i (01/02/04'te aynı)
   `gemini-2.5-flash` free-tier limitine (**20 istek/gün/proje**) takıldı (`429 RESOURCE_EXHAUSTED`).
   Bu podcast kendi Google AI Studio projesinde kendi key'ini kullanmalı; yoksa diğer botlarla kota çakışır.
   Günlük kullanım ~2-3 Flash çağrısı + 1 TTS → dedike 20/gün'e rahat sığar, ama ölçek/ekstra çalıştırma
   için ücretli tier düşünülmeli.
2. **Reddit 403 (CI IP bloğu).** `reddit.fetch` public JSON, datacenter/GitHub Actions IP'lerinden 403 alıyor
   (bu makineden de doğrulandı). Mitigasyon: Reddit OAuth ("script" app, `REDDIT_CLIENT_ID/SECRET` →
   `oauth.reddit.com`) veya residential proxy. Aksi halde CI'da sık "aday yok / boş gün" olur. **v1'in ilk
   gerçek işi bu.**
3. **Gemini 503 spike'ları → retry eklendi.** Canlı testte geçici `503 UNAVAILABLE` görüldü; `src/gemini_retry.py`
   ile 5xx'e üstel backoff retry eklendi (429/kota retry edilmez). Gözetimsiz günlük iş için kritik.
4. **TTS uzunluk tavanı (izle):** 700-1200 kelime tek `generate_content` çağrısıyla üretiliyor; çok uzun
   script'te truncation riski — ilk gerçek bölümlerde audio süresini kontrol et, gerekirse chunk'la.
