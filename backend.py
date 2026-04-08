import os
import re
import json
from quart import Quart, request
from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaDocument, ReplyKeyboardMarkup
from telethon.sessions import StringSession
import asyncio
import uuid

API_ID = int(os.environ.get('API_ID', '17570480'))
API_HASH = os.environ.get('API_HASH', '18c5be05094b146ef29b0cb6f6601f1f')
SESSION_STRING = os.environ.get('SESSION_STRING', "1ApWapzMBu1wXAV-OQ96vPLrZJKlykz7d2N9c2Ciwmz7vGsKu5a5xIWh3cz0b84V9xxoQ26vNlc27SCWyWfICQPHoVpHMW4egjl1MXevd0FUB_dGIUg0ubmfoi1h_O3HAOR66Q7wfbr9F181riPQsAAJgTClo0DWqf1Gp-H5T1jUo2ppDM-avvOTrkk2hn76kBNDs-kmmmcEsSARwKU4JOphN4qQ3Vj4KXWVOf-_dNQubeLD5jcmkWURmpZN63GEQNEiCqvHmtEAmzJI6PdP2wiOrsNmiAKZHCz4Oc9T6Zn60feckf4qfAFkgX-N4tJhIsnr6H5zx_EjNquHmDYN_wTW8pDlpjn4=")

BOT_USERNAME = "Sorgii_bot"

app = Quart(__name__)
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

sorgu_sonuclari = {}

def custom_jsonify(data, status=200):
    return Quart.response_class(
        response=json.dumps(data, ensure_ascii=False, indent=2),
        status=status,
        mimetype='application/json; charset=utf-8'
    )

@client.on(events.NewMessage(from_users=BOT_USERNAME))
async def bot_yaniti_handler(event):
    message = event.message
    
    # SADECE reply edilen mesajları işle
    if not message.reply_to_msg_id:
        return
    
    # Reply edilen mesaj ID'sine göre sorguyu bul
    sorgu_id = None
    for sid, data in sorgu_sonuclari.items():
        if data.get('msg_id') == message.reply_to_msg_id:
            sorgu_id = sid
            break
    
    if not sorgu_id:
        print(f"⚠️ Eşleşen sorgu bulunamadı: reply_to={message.reply_to_msg_id}")
        return
    
    try:
        # DOSYA GELDİ Mİ?
        if message.media and isinstance(message.media, MessageMediaDocument):
            dosya_yolu = await message.download_media()
            if dosya_yolu:
                with open(dosya_yolu, 'r', encoding='utf-8', errors='replace') as f:
                    icerik = f.read()
                os.remove(dosya_yolu)
                sorgu_sonuclari[sorgu_id]['durum'] = 'tamam'
                sorgu_sonuclari[sorgu_id]['sonuc'] = icerik
                print(f"✅ Dosya alındı! Sorgu: {sorgu_id[:8]}")
                return
        
        # BUTONLU MESAJ
        if message.text and 'kayit bulundu' in message.text.lower():
            print(f"🔘 Butonlu mesaj geldi - Sorgu: {sorgu_id[:8]}")
            
            if message.reply_markup and isinstance(message.reply_markup, ReplyKeyboardMarkup):
                for row in message.reply_markup.rows:
                    for button in row.buttons:
                        if 'dosya' in button.text.lower() or 'txt' in button.text.lower():
                            await button.click()
                            sorgu_sonuclari[sorgu_id]['durum'] = 'dosya_bekleniyor'
                            print(f"📁 Butona basıldı: {button.text}")
                            return
            
            # Alternatif
            await client.send_message(BOT_USERNAME, "Dosya (TXT)", reply_to=message.id)
            sorgu_sonuclari[sorgu_id]['durum'] = 'dosya_bekleniyor'
            print(f"📁 'Dosya (TXT)' gönderildi")
            return
        
        # DİREKT MESAJ
        if message.text and not message.media:
            sorgu_sonuclari[sorgu_id]['durum'] = 'tamam'
            sorgu_sonuclari[sorgu_id]['sonuc'] = message.text
            print(f"📝 Direkt mesaj alındı - Sorgu: {sorgu_id[:8]}")
            return
            
    except Exception as e:
        print(f"Hata: {e}")

async def bot_sorgula(komut: str, sorgu_id: str):
    # Komutu gönder ve mesaj ID'sini al
    msg = await client.send_message(BOT_USERNAME, komut)
    
    sorgu_sonuclari[sorgu_id] = {
        'durum': 'bekliyor',
        'sonuc': None,
        'msg_id': msg.id
    }
    print(f"📤 {komut} (msg_id: {msg.id})")
    
    # 60 saniye bekle
    for _ in range(60):
        await asyncio.sleep(1)
        if sorgu_sonuclari.get(sorgu_id, {}).get('durum') == 'tamam':
            sonuc = sorgu_sonuclari[sorgu_id]['sonuc']
            del sorgu_sonuclari[sorgu_id]
            return sonuc
    
    if sorgu_id in sorgu_sonuclari:
        del sorgu_sonuclari[sorgu_id]
    print(f"❌ Zaman aşımı - Sorgu: {sorgu_id[:8]}")
    return None

def fix_unicode(text):
    if not text:
        return text
    try:
        return text.encode('latin1').decode('utf-8', errors='replace')
    except:
        return text

def parse_adsoyad_dosya(icerik):
    veriler = []
    satirlar = icerik.strip().split('\n')
    
    for satir in satirlar:
        satir = satir.strip()
        if not satir:
            continue
        
        if any(x in satir.lower() for x in ['kayit bulundu', 'listelendi', 'dosya', 'parametreler']):
            continue
        
        if re.match(r'^\d{11}', satir):
            tc_match = re.search(r'^(\d{11})', satir)
            tc = tc_match.group(1) if tc_match else ''
            
            isim_match = re.search(r'\d{11}\s*-\s*([^(]+?)\s*\(([^)]+)\)', satir)
            if isim_match:
                ad_soyad = isim_match.group(1).strip()
                dogum = isim_match.group(2).strip()
            else:
                ad_soyad = ''
                dogum = ''
            
            yer_match = re.search(r'\|\s*([^|]+?)\s*\|', satir)
            yer = yer_match.group(1).strip() if yer_match else ''
            
            il = yer
            ilce = ''
            if '/' in yer:
                parcalar = yer.split('/')
                il = parcalar[0].strip()
                ilce = parcalar[1].strip() if len(parcalar) > 1 else ''
            
            anne = ''
            baba = ''
            anne_match = re.search(r'Anne:\s*([^,]+)', satir)
            if anne_match:
                anne = anne_match.group(1).strip()
            baba_match = re.search(r'Baba:\s*(.+?)(?:\)|$)', satir)
            if baba_match:
                baba = baba_match.group(1).strip()
            
            veriler.append({
                'tc': tc,
                'ad_soyad': fix_unicode(ad_soyad),
                'dogum_tarihi': dogum,
                'il': fix_unicode(il),
                'ilce': fix_unicode(ilce),
                'anne': fix_unicode(anne),
                'baba': fix_unicode(baba)
            })
    
    return veriler

# ============ ENDPOINTLER ============

@app.route('/adsoyad', methods=['GET'])
async def adsoyad_sorgu():
    ad = request.args.get('ad')
    soyad = request.args.get('soyad')
    il = request.args.get('il', '')
    ilce = request.args.get('ilce', '')
    
    if not ad or not soyad:
        return custom_jsonify({'hata': 'ad ve soyad gerekli'}, 400)
    
    komut = f"/adsoyad -ad {ad.upper()} -soyad {soyad.upper()}"
    if il:
        komut += f" -il {il.upper()}"
    if ilce:
        komut += f" -ilce {ilce.upper()}"
    
    sorgu_id = str(uuid.uuid4())
    sonuc = await bot_sorgula(komut, sorgu_id)
    
    if not sonuc:
        return custom_jsonify({'hata': 'Zaman aşımı', 'success': False}, 408)
    
    veriler = parse_adsoyad_dosya(sonuc)
    
    return custom_jsonify({
        'success': True,
        'sorgu_tipi': 'adsoyad',
        'parametreler': {'ad': ad, 'soyad': soyad, 'il': il, 'ilce': ilce},
        'kayit_sayisi': len(veriler),
        'veriler': veriler
    })

@app.route('/adres', methods=['GET'])
async def adres_sorgu():
    tc = request.args.get('tc')
    if not tc:
        return custom_jsonify({'hata': 'tc gerekli'}, 400)
    
    sorgu_id = str(uuid.uuid4())
    sonuc = await bot_sorgula(f"/adres {tc}", sorgu_id)
    
    if not sonuc:
        return custom_jsonify({'hata': 'Zaman aşımı', 'success': False}, 408)
    
    return custom_jsonify({
        'success': True,
        'sorgu_tipi': 'adres',
        'parametreler': {'tc': tc},
        'sonuc': fix_unicode(sonuc)
    })

@app.route('/sulale', methods=['GET'])
async def sulale_sorgu():
    tc = request.args.get('tc')
    if not tc:
        return custom_jsonify({'hata': 'tc gerekli'}, 400)
    
    sorgu_id = str(uuid.uuid4())
    sonuc = await bot_sorgula(f"/sulale {tc}", sorgu_id)
    
    if not sonuc:
        return custom_jsonify({'hata': 'Zaman aşımı', 'success': False}, 408)
    
    return custom_jsonify({
        'success': True,
        'sorgu_tipi': 'sulale',
        'parametreler': {'tc': tc},
        'sonuc': fix_unicode(sonuc)
    })

@app.route('/tc', methods=['GET'])
async def tc_sorgu():
    tc = request.args.get('tc')
    if not tc:
        return custom_jsonify({'hata': 'tc gerekli'}, 400)
    
    sorgu_id = str(uuid.uuid4())
    sonuc = await bot_sorgula(f"/tc {tc}", sorgu_id)
    
    if not sonuc:
        return custom_jsonify({'hata': 'Zaman aşımı', 'success': False}, 408)
    
    return custom_jsonify({
        'success': True,
        'sorgu_tipi': 'tc',
        'parametreler': {'tc': tc},
        'sonuc': fix_unicode(sonuc)
    })

@app.route('/aile', methods=['GET'])
async def aile_sorgu():
    tc = request.args.get('tc')
    if not tc:
        return custom_jsonify({'hata': 'tc gerekli'}, 400)
    
    sorgu_id = str(uuid.uuid4())
    sonuc = await bot_sorgula(f"/aile {tc}", sorgu_id)
    
    if not sonuc:
        return custom_jsonify({'hata': 'Zaman aşımı', 'success': False}, 408)
    
    return custom_jsonify({
        'success': True,
        'sorgu_tipi': 'aile',
        'parametreler': {'tc': tc},
        'sonuc': fix_unicode(sonuc)
    })

@app.route('/cocuk', methods=['GET'])
async def cocuk_sorgu():
    tc = request.args.get('tc')
    if not tc:
        return custom_jsonify({'hata': 'tc gerekli'}, 400)
    
    sorgu_id = str(uuid.uuid4())
    sonuc = await bot_sorgula(f"/cocuk {tc}", sorgu_id)
    
    if not sonuc:
        return custom_jsonify({'hata': 'Zaman aşımı', 'success': False}, 408)
    
    return custom_jsonify({
        'success': True,
        'sorgu_tipi': 'cocuk',
        'parametreler': {'tc': tc},
        'sonuc': fix_unicode(sonuc)
    })

@app.route('/gsm', methods=['GET'])
async def gsm_sorgu():
    gsm = request.args.get('gsm')
    if not gsm:
        return custom_jsonify({'hata': 'gsm gerekli'}, 400)
    
    sorgu_id = str(uuid.uuid4())
    sonuc = await bot_sorgula(f"/gsm {gsm}", sorgu_id)
    
    if not sonuc:
        return custom_jsonify({'hata': 'Zaman aşımı', 'success': False}, 408)
    
    tcler = re.findall(r'\b\d{11}\b', sonuc)
    
    return custom_jsonify({
        'success': True,
        'sorgu_tipi': 'gsm',
        'parametreler': {'gsm': gsm},
        'tcler': list(set(tcler))
    })

@app.route('/isyeri', methods=['GET'])
async def isyeri_sorgu():
    tc = request.args.get('tc')
    if not tc:
        return custom_jsonify({'hata': 'tc gerekli'}, 400)
    
    sorgu_id = str(uuid.uuid4())
    sonuc = await bot_sorgula(f"/isyeri {tc}", sorgu_id)
    
    if not sonuc:
        return custom_jsonify({'hata': 'Zaman aşımı', 'success': False}, 408)
    
    return custom_jsonify({
        'success': True,
        'sorgu_tipi': 'isyeri',
        'parametreler': {'tc': tc},
        'sonuc': fix_unicode(sonuc)
    })

@app.route('/ip', methods=['GET'])
async def ip_sorgu():
    ip = request.args.get('ip')
    if not ip:
        return custom_jsonify({'hata': 'ip gerekli', 'ornek': '/ip?ip=8.8.8.8'}, 400)
    
    sorgu_id = str(uuid.uuid4())
    sonuc = await bot_sorgula(f"/ip {ip}", sorgu_id)
    
    if not sonuc:
        return custom_jsonify({'hata': 'Zaman aşımı', 'success': False}, 408)
    
    return custom_jsonify({
        'success': True,
        'sorgu_tipi': 'ip',
        'parametreler': {'ip': ip},
        'sonuc': fix_unicode(sonuc)
    })

@app.route('/sms', methods=['GET'])
async def sms_sorgu():
    gsm = request.args.get('gsm')
    if not gsm:
        return custom_jsonify({'hata': 'gsm gerekli'}, 400)
    
    sorgu_id = str(uuid.uuid4())
    sonuc = await bot_sorgula(f"/sms {gsm}", sorgu_id)
    
    if not sonuc:
        return custom_jsonify({'hata': 'Zaman aşımı', 'success': False}, 408)
    
    return custom_jsonify({
        'success': True,
        'sorgu_tipi': 'sms',
        'parametreler': {'gsm': gsm},
        'sonuc': fix_unicode(sonuc)
    })

@app.route('/', methods=['GET'])
async def ana_sayfa():
    return custom_jsonify({
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
    print(f"✅ Telethon bağlandı! Bot: {BOT_USERNAME}")
    print("🚀 API http://localhost:5000")
    await app.run_task(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    asyncio.run(main())
