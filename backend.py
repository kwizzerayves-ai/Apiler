import os
import re
import json
from quart import Quart, request, jsonify, Response
from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaDocument
from telethon.sessions import StringSession
import asyncio
import uuid
import unicodedata

API_ID = int(os.environ.get('API_ID', '17570480'))
API_HASH = os.environ.get('API_HASH', '18c5be05094b146ef29b0cb6f6601f1f')
SESSION_STRING = os.environ.get('SESSION_STRING', "1ApWapzMBu1wXAV-OQ96vPLrZJKlykz7d2N9c2Ciwmz7vGsKu5a5xIWh3cz0b84V9xxoQ26vNlc27SCWyWfICQPHoVpHMW4egjl1MXevd0FUB_dGIUg0ubmfoi1h_O3HAOR66Q7wfbr9F181riPQsAAJgTClo0DWqf1Gp-H5T1jUo2ppDM-avvOTrkk2hn76kBNDs-kmmmcEsSARwKU4JOphN4qQ3Vj4KXWVOf-_dNQubeLD5jcmkWURmpZN63GEQNEiCqvHmtEAmzJI6PdP2wiOrsNmiAKZHCz4Oc9T6Zn60feckf4qfAFkgX-N4tJhIsnr6H5zx_EjNquHmDYN_wTW8pDlpjn4=")

BOT_USERNAME = "Sorgii_bot"

app = Quart(__name__)
app.config['JSON_AS_ASCII'] = False  # 🔥 KARAKTER SORUNUNU ÇÖZEN ANA AYAR

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
sorgu_sonuclari = {}

def temizle(text):
    """Türkçe karakterleri düzelt"""
    if not text or text == 'None':
        return ''
    # Unicode normalizasyonu
    text = unicodedata.normalize('NFC', str(text))
    # Fazla boşlukları temizle
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def dosya_oku(dosya_yolu):
    """Dosyayı doğru encoding ile oku"""
    encodings = ['utf-8', 'cp1254', 'latin-1', 'iso-8859-9', 'cp857', 'utf-16']
    
    for encoding in encodings:
        try:
            with open(dosya_yolu, 'r', encoding=encoding, errors='strict') as f:
                icerik = f.read()
            print(f"✅ Dosya {encoding} ile okundu")
            return icerik
        except (UnicodeDecodeError, UnicodeError):
            continue
    
    # Hiçbiri olmazsa son çare
    with open(dosya_yolu, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()

@client.on(events.NewMessage(from_users=BOT_USERNAME))
async def bot_yaniti_handler(event):
    message = event.message
    
    bekleyenler = [sid for sid in sorgu_sonuclari if sorgu_sonuclari[sid]['durum'] == 'bekliyor']
    if not bekleyenler:
        return
    
    sorgu_id = bekleyenler[0]
    
    try:
        # DOSYA GELDİ Mİ?
        if message.media and isinstance(message.media, MessageMediaDocument):
            dosya_yolu = await message.download_media()
            if dosya_yolu:
                icerik = dosya_oku(dosya_yolu)
                os.remove(dosya_yolu)
                sorgu_sonuclari[sorgu_id]['durum'] = 'tamam'
                sorgu_sonuclari[sorgu_id]['sonuc'] = icerik
                print(f"✅ Dosya alındı! {len(icerik)} karakter")
                return
        
        # BUTONLU MESAJ
        if message.text and 'kayit bulundu' in message.text.lower():
            print(f"🔘 Butonlu mesaj geldi")
            
            if message.buttons:
                try:
                    for row in message.buttons:
                        for button in row:
                            if 'dosya' in button.text.lower() or 'txt' in button.text.lower():
                                await button.click()
                                sorgu_sonuclari[sorgu_id]['durum'] = 'dosya_bekleniyor'
                                print(f"📁 Butona basıldı: {button.text}")
                                return
                    
                    if len(message.buttons[0]) >= 2:
                        await message.buttons[0][1].click()
                        sorgu_sonuclari[sorgu_id]['durum'] = 'dosya_bekleniyor'
                        print(f"📁 2. butona basıldı")
                        return
                    
                    await message.buttons[0][0].click()
                    sorgu_sonuclari[sorgu_id]['durum'] = 'dosya_bekleniyor'
                    print(f"📁 1. butona basıldı")
                    return
                    
                except Exception as e:
                    print(f"❌ Buton basma hatası: {e}")
            return
        
        # DİREKT MESAJ
        if message.text and not message.media and len(message.text) > 50:
            sorgu_sonuclari[sorgu_id]['durum'] = 'tamam'
            sorgu_sonuclari[sorgu_id]['sonuc'] = temizle(message.text)
            print(f"📝 Direkt mesaj alındı")
            return
            
    except Exception as e:
        print(f"Hata: {e}")

async def bot_sorgula(komut: str, sorgu_id: str):
    sorgu_sonuclari[sorgu_id] = {'durum': 'bekliyor', 'sonuc': None}
    await client.send_message(BOT_USERNAME, komut)
    print(f"📤 {komut}")
    
    for _ in range(60):
        await asyncio.sleep(1)
        if sorgu_sonuclari.get(sorgu_id, {}).get('durum') == 'tamam':
            sonuc = sorgu_sonuclari[sorgu_id]['sonuc']
            del sorgu_sonuclari[sorgu_id]
            return sonuc
    
    if sorgu_id in sorgu_sonuclari:
        del sorgu_sonuclari[sorgu_id]
    print("❌ Zaman aşımı")
    return None

def parse_adsoyad_dosya(icerik):
    """Ad soyad dosyasını parse et - TÜRKÇE KARAKTER DESTEKLİ"""
    if not icerik:
        return []
    
    veriler = []
    satirlar = icerik.strip().split('\n')
    
    for satir in satirlar:
        satir = satir.strip()
        if not satir:
            continue
        
        # Gereksiz satırları atla
        if any(x in satir.lower() for x in ['kayit bulundu', 'listelendi', 'dosya', 'parametreler', '---', 'toplam']):
            continue
        
        # TC ile başlayan satırları bul
        if re.match(r'^\d{11}', satir):
            tc_match = re.search(r'^(\d{11})', satir)
            tc = tc_match.group(1) if tc_match else ''
            
            # Ad soyad ve doğum tarihi
            isim_match = re.search(r'\d{11}\s*[-–]\s*([^(]+?)\s*\(([^)]+)\)', satir)
            if isim_match:
                ad_soyad = temizle(isim_match.group(1))
                dogum = temizle(isim_match.group(2))
            else:
                ad_soyad = ''
                dogum = ''
            
            # İl/İlçe
            yer_match = re.search(r'\|\s*([^|]+?)\s*\|', satir)
            yer = temizle(yer_match.group(1)) if yer_match else ''
            
            il = yer
            ilce = ''
            if '/' in yer:
                parcalar = yer.split('/')
                il = temizle(parcalar[0])
                ilce = temizle(parcalar[1]) if len(parcalar) > 1 else ''
            
            # Anne
            anne = ''
            anne_match = re.search(r'Anne:\s*([^,|]+)', satir)
            if anne_match:
                anne_raw = anne_match.group(1).strip()
                anne = temizle(re.sub(r'\(None\)|None', '', anne_raw).strip())
            
            # Baba
            baba = ''
            baba_match = re.search(r'Baba:\s*([^,|\)]+)', satir)
            if baba_match:
                baba_raw = baba_match.group(1).strip()
                baba = temizle(re.sub(r'\(None\)|None', '', baba_raw).strip())
            
            veriler.append({
                'tc': tc,
                'ad_soyad': ad_soyad,
                'dogum_tarihi': dogum,
                'il': il if il != 'None' else '',
                'ilce': ilce if ilce != 'None' else '',
                'anne': anne,
                'baba': baba
            })
    
    return veriler

def json_utf8_yanit(data, status=200):
    """UTF-8 destekli JSON yanıtı"""
    return Response(
        response=json.dumps(data, ensure_ascii=False, indent=2),
        status=status,
        mimetype='application/json; charset=utf-8'
    )

# ============ ENDPOINTLER ============

@app.route('/adsoyad', methods=['GET'])
async def adsoyad_sorgu():
    ad = request.args.get('ad', '').strip()
    soyad = request.args.get('soyad', '').strip()
    il = request.args.get('il', '').strip()
    ilce = request.args.get('ilce', '').strip()
    
    if not ad or not soyad:
        return json_utf8_yanit({'hata': 'ad ve soyad gerekli', 'ornek': '/adsoyad?ad=eymen&soyad=yavuz'}, 400)
    
    komut = f"/adsoyad -ad {ad.upper()} -soyad {soyad.upper()}"
    if il:
        komut += f" -il {il.upper()}"
    if ilce:
        komut += f" -ilce {ilce.upper()}"
    
    sorgu_id = str(uuid.uuid4())
    sonuc = await bot_sorgula(komut, sorgu_id)
    
    if not sonuc:
        return json_utf8_yanit({'hata': 'Zaman aşımı', 'success': False}, 408)
    
    veriler = parse_adsoyad_dosya(sonuc)
    
    return json_utf8_yanit({
        'success': True,
        'sorgu_tipi': 'adsoyad',
        'parametreler': {'ad': ad, 'soyad': soyad, 'il': il, 'ilce': ilce},
        'kayit_sayisi': len(veriler),
        'veriler': veriler
    })

@app.route('/adres', methods=['GET'])
async def adres_sorgu():
    tc = request.args.get('tc', '').strip()
    if not tc:
        return json_utf8_yanit({'hata': 'tc gerekli'}, 400)
    
    sorgu_id = str(uuid.uuid4())
    sonuc = await bot_sorgula(f"/adres {tc}", sorgu_id)
    
    if not sonuc:
        return json_utf8_yanit({'hata': 'Zaman aşımı', 'success': False}, 408)
    
    return json_utf8_yanit({
        'success': True,
        'sorgu_tipi': 'adres',
        'parametreler': {'tc': tc},
        'sonuc': temizle(sonuc)
    })

@app.route('/sulale', methods=['GET'])
async def sulale_sorgu():
    tc = request.args.get('tc', '').strip()
    if not tc:
        return json_utf8_yanit({'hata': 'tc gerekli'}, 400)
    
    sorgu_id = str(uuid.uuid4())
    sonuc = await bot_sorgula(f"/sulale {tc}", sorgu_id)
    
    if not sonuc:
        return json_utf8_yanit({'hata': 'Zaman aşımı', 'success': False}, 408)
    
    return json_utf8_yanit({
        'success': True,
        'sorgu_tipi': 'sulale',
        'parametreler': {'tc': tc},
        'sonuc': temizle(sonuc)
    })

@app.route('/tc', methods=['GET'])
async def tc_sorgu():
    tc = request.args.get('tc', '').strip()
    if not tc:
        return json_utf8_yanit({'hata': 'tc gerekli'}, 400)
    
    sorgu_id = str(uuid.uuid4())
    sonuc = await bot_sorgula(f"/tc {tc}", sorgu_id)
    
    if not sonuc:
        return json_utf8_yanit({'hata': 'Zaman aşımı', 'success': False}, 408)
    
    return json_utf8_yanit({
        'success': True,
        'sorgu_tipi': 'tc',
        'parametreler': {'tc': tc},
        'sonuc': temizle(sonuc)
    })

@app.route('/aile', methods=['GET'])
async def aile_sorgu():
    tc = request.args.get('tc', '').strip()
    if not tc:
        return json_utf8_yanit({'hata': 'tc gerekli'}, 400)
    
    sorgu_id = str(uuid.uuid4())
    sonuc = await bot_sorgula(f"/aile {tc}", sorgu_id)
    
    if not sonuc:
        return json_utf8_yanit({'hata': 'Zaman aşımı', 'success': False}, 408)
    
    return json_utf8_yanit({
        'success': True,
        'sorgu_tipi': 'aile',
        'parametreler': {'tc': tc},
        'sonuc': temizle(sonuc)
    })

@app.route('/cocuk', methods=['GET'])
async def cocuk_sorgu():
    tc = request.args.get('tc', '').strip()
    if not tc:
        return json_utf8_yanit({'hata': 'tc gerekli'}, 400)
    
    sorgu_id = str(uuid.uuid4())
    sonuc = await bot_sorgula(f"/cocuk {tc}", sorgu_id)
    
    if not sonuc:
        return json_utf8_yanit({'hata': 'Zaman aşımı', 'success': False}, 408)
    
    return json_utf8_yanit({
        'success': True,
        'sorgu_tipi': 'cocuk',
        'parametreler': {'tc': tc},
        'sonuc': temizle(sonuc)
    })

@app.route('/gsm', methods=['GET'])
async def gsm_sorgu():
    gsm = request.args.get('gsm', '').strip()
    if not gsm:
        return json_utf8_yanit({'hata': 'gsm gerekli'}, 400)
    
    sorgu_id = str(uuid.uuid4())
    sonuc = await bot_sorgula(f"/gsm {gsm}", sorgu_id)
    
    if not sonuc:
        return json_utf8_yanit({'hata': 'Zaman aşımı', 'success': False}, 408)
    
    tcler = re.findall(r'\b\d{11}\b', sonuc)
    
    return json_utf8_yanit({
        'success': True,
        'sorgu_tipi': 'gsm',
        'parametreler': {'gsm': gsm},
        'tcler': list(set(tcler))
    })

@app.route('/isyeri', methods=['GET'])
async def isyeri_sorgu():
    tc = request.args.get('tc', '').strip()
    if not tc:
        return json_utf8_yanit({'hata': 'tc gerekli'}, 400)
    
    sorgu_id = str(uuid.uuid4())
    sonuc = await bot_sorgula(f"/isyeri {tc}", sorgu_id)
    
    if not sonuc:
        return json_utf8_yanit({'hata': 'Zaman aşımı', 'success': False}, 408)
    
    return json_utf8_yanit({
        'success': True,
        'sorgu_tipi': 'isyeri',
        'parametreler': {'tc': tc},
        'sonuc': temizle(sonuc)
    })

@app.route('/ip', methods=['GET'])
async def ip_sorgu():
    ip = request.args.get('ip', '').strip()
    if not ip:
        return json_utf8_yanit({'hata': 'ip gerekli'}, 400)
    
    sorgu_id = str(uuid.uuid4())
    sonuc = await bot_sorgula(f"/ip {ip}", sorgu_id)
    
    if not sonuc:
        return json_utf8_yanit({'hata': 'Zaman aşımı', 'success': False}, 408)
    
    return json_utf8_yanit({
        'success': True,
        'sorgu_tipi': 'ip',
        'parametreler': {'ip': ip},
        'sonuc': temizle(sonuc)
    })

@app.route('/sms', methods=['GET'])
async def sms_sorgu():
    gsm = request.args.get('gsm', '').strip()
    if not gsm:
        return json_utf8_yanit({'hata': 'gsm gerekli'}, 400)
    
    sorgu_id = str(uuid.uuid4())
    sonuc = await bot_sorgula(f"/sms {gsm}", sorgu_id)
    
    if not sonuc:
        return json_utf8_yanit({'hata': 'Zaman aşımı', 'success': False}, 408)
    
    return json_utf8_yanit({
        'success': True,
        'sorgu_tipi': 'sms',
        'parametreler': {'gsm': gsm},
        'sonuc': temizle(sonuc)
    })

@app.route('/', methods=['GET'])
async def ana_sayfa():
    return json_utf8_yanit({
        'bot': BOT_USERNAME,
        'durum': 'calisiyor',
        'karakter_destegi': 'UTF-8 (Türkçe karakterler destekleniyor)',
        'endpointler': {
            'adsoyad': '/adsoyad?ad=&soyad=',
            'adres': '/adres?tc=',
            'sulale': '/sulale?tc=',
            'tc': '/tc?tc=',
            'aile': '/aile?tc=',
            'cocuk': '/cocuk?tc=',
            'gsm': '/gsm?gsm=',
            'isyeri': '/isyeri?tc=',
            'ip': '/ip?ip=',
            'sms': '/sms?gsm='
        }
    })

async def main():
    await client.start()
    print("✅ Telethon bağlandı!")
    print(f"🤖 Bot: {BOT_USERNAME}")
    print("🚀 API http://localhost:5000 adresinde çalışıyor")
    print("✅ Türkçe karakter desteği AKTİF")
    await app.run_task(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    asyncio.run(main())
