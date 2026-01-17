import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from datetime import datetime
from typing import Literal
from flask import Flask, render_template_string, request, jsonify, redirect, session, url_for
from threading import Thread
import secrets
import requests
from urllib.parse import urlencode
import asyncio

# ==================== KONFIGURATION ====================
class Config:
    TOKEN = os.getenv('BOT_TOKEN')
    SECRET_KEY = os.getenv('SECRET_KEY', secrets.token_hex(16))

    # Discord OAuth2
    CLIENT_ID = os.getenv('DISCORD_CLIENT_ID')
    CLIENT_SECRET = os.getenv('DISCORD_CLIENT_SECRET')
    REDIRECT_URI = os.getenv('REDIRECT_URI', 'http://localhost:5000/callback')
    GUILD_ID = os.getenv('GUILD_ID')  # WICHTIG: Deine Server-ID hier eintragen!
    OAUTH2_URL = 'https://discord.com/api/oauth2/authorize'
    TOKEN_URL = 'https://discord.com/api/oauth2/token'
    API_ENDPOINT = 'https://discord.com/api/v10'

    # Rollen für Berechtigungen
    AUSBILDERLEITUNG_ROLES = ['1461433250865086772', '1461486247447892141']
    AUSBILDER_ROLES = ['1461433535297486963']

    ROLES = {
        'theorie': {'pending': '1461435536576090213', 'passed': '1461435507065094316'},
        'grund': {'pending': '1461435499741974558', 'passed': '1461435470192967823'},
        'stvo': {'pending': '1461435445303840859', 'passed': '1461435381907062870'}
    }

    CHANNELS = {
        'theorie': {'announcement': '1461451680670548063', 'evaluation': '1461451722856599653'},
        'grund': {'announcement': '1461453475589259519', 'evaluation': '1461453525157675152'},
        'stvo': {'announcement': '1461453734931333130', 'evaluation': '1461453784034181202'}
    }

    REACTION_EMOJI = '<:Dokument:1461765293847347262>'

    BANNERS = {
        'theorie': 'https://media.discordapp.net/attachments/1461429300241895579/1461748446636675308/image.png',
        'grund': 'https://media.discordapp.net/attachments/1461429300241895579/1461748584343928975/image.png',
        'stvo': 'https://media.discordapp.net/attachments/1461429300241895579/1461748684269031486/image.png'
    }

DATA_FILE = 'bot_data.json'

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'templates' not in data:
                    data['templates'] = get_default_templates()
                if 'messages' not in data:
                    data['messages'] = {}
                return data
        except:
            pass
    return {
        'announcements': [], 
        'evaluations': [],
        'templates': get_default_templates(),
        'messages': {}
    }

def get_default_templates():
    return {
        'theorie': {
            'title': 'Theorie-Ausbildung',
            'intro': 'Eine Theorie-Ausbildung findet statt. Hier sind die wichtigsten Informationen.',
            'topics': ['1. Begrüßung', '2. Einführung Theorie', '3. Rechtliche Grundlagen', '4. Theoretische Prüfung', '5. Auswertung'],
            'additional_info': ['Reagiere mit <:Dokument:1461765293847347262> um teilzunehmen.', 'Bei **Verspätung** wird eine Teilnahme nur schwer möglich sein.'],
            'grading': ['Sehr gut: 50 – 45', 'Gut: 44 – 40', 'Befriedigend: 39 – 33', 'Ausreichend: 32 – 25', 'Mangelhaft: 24 – 15', 'Ungenügend: 14 – 0'],
            'benefits': ['In dieser Theorie-Ausbildung werden dir die ersten wichtigsten Kenntnisse beigebracht.', 'Jeder der das Training erfolgreich absolviert, bekommt die {passed_role} Rolle.', 'Du kannst nun an der Grundausbildung teilnehmen.']
        },
        'grund': {
            'title': 'Grund-Ausbildung',
            'intro': 'Eine Grundausbildung findet statt. Hier sind die wichtigsten Informationen.',
            'topics': ['1. Wiederholung', '2. Statusmeldungen/Funkausbildung', '3. Absperrtraining', '4. Geiselnahme-Szenarien', '5. Räuber-Simulation', '6. Schusstraining', '7. Auswertung'],
            'additional_info': ['Reagiere mit <:Dokument:1461765293847347262> um teilzunehmen.', 'Bei **Verspätung** wird eine Teilnahme nur schwer möglich sein.'],
            'grading': ['Sehr gut: 50 – 45', 'Gut: 44 – 40', 'Befriedigend: 39 – 33', 'Ausreichend: 32 – 25', 'Mangelhaft: 24 – 15', 'Ungenügend: 14 – 0'],
            'benefits': ['In dieser Grundausbildung werden dir wichtige Grundkenntnisse für den Polizeidienst beigebracht.', 'Jeder der das Training erfolgreich absolviert, bekommt die {passed_role} Rolle.', 'Du besitzt nun den Dienstgrad **Polizeimeister-Anwärter**.']
        },
        'stvo': {
            'title': 'StVO-Ausbildung',
            'intro': 'Eine StVO Ausbildung findet statt. Hier sind die wichtigsten Informationen.',
            'topics': ['1. Begrüßung', '2. Verkehrsschilder', '3. Bußgeldkatalog', '4. Fit-Manöver', '5. Straßenverkehrsordnung (StVO)', '6. Praktischer Teil', '7. Quiz'],
            'additional_info': ['Reagiere mit <:Dokument:1461765293847347262> um teilzunehmen.', 'Bei **Verspätung** wird eine Teilnahme nur schwer möglich sein.'],
            'grading': ['Sehr gut: 25 – 22', 'Gut: 21 – 17', 'Befriedigend: 16 – 13', 'Ausreichend: 12 – 9', 'Mangelhaft: 8 – 4', 'Ungenügend: 3 – 0'],
            'benefits': ['In dieser StVO-Ausbildung werden dir die letzten wichtigsten Kenntnisse für den Polizeidienst beigebracht.', 'Jeder der das Training erfolgreich absolviert, bekommt die {passed_role} Rolle.', 'Du besitzt anschließend den Dienstgrad **Polizeimeister**.']
        }
    }

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

bot_data = load_data()
active_evaluations = {}

# OAuth2 Helper Funktionen
def get_user_info(access_token):
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(f'{Config.API_ENDPOINT}/users/@me', headers=headers)
    if response.status_code == 200:
        return response.json()
    return None

def get_guild_member(guild_id, user_id, bot_token):
    headers = {'Authorization': f'Bot {bot_token}'}
    response = requests.get(f'{Config.API_ENDPOINT}/guilds/{guild_id}/members/{user_id}', headers=headers)
    if response.status_code == 200:
        return response.json()
    return None

def check_user_roles(user_id, guild_id):
    member = get_guild_member(guild_id, user_id, Config.TOKEN)
    if not member:
        return None

    user_roles = member.get('roles', [])

    if any(role in Config.AUSBILDERLEITUNG_ROLES for role in user_roles):
        return 'ausbilderleitung'

    if any(role in Config.AUSBILDER_ROLES for role in user_roles):
        return 'ausbilder'

    return None

# ==================== FLASK WEB APP ====================
app = Flask(__name__)
app.secret_key = Config.SECRET_KEY

# HTML Template wird wegen Länge als separater String definiert
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% if user_role == 'ausbilderleitung' %}Ausbilderleitung{% else %}Ausbilder{% endif %} Portal</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; background: white; border-radius: 15px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); overflow: hidden; }
        .header { background: linear-gradient(135deg, #02244b 0%, #034078 100%); color: white; padding: 30px; position: relative; }
        .header h1 { font-size: 2em; margin-bottom: 10px; }
        .user-info { position: absolute; top: 20px; right: 30px; display: flex; align-items: center; gap: 15px; }
        .avatar { width: 50px; height: 50px; border-radius: 50%; border: 3px solid white; }
        .nav { background: #f8f9fa; padding: 15px 30px; display: flex; gap: 15px; border-bottom: 2px solid #e9ecef; flex-wrap: wrap; }
        .nav button { padding: 10px 20px; border: none; background: #02244b; color: white; border-radius: 5px; cursor: pointer; transition: all 0.3s; }
        .nav button:hover { background: #034078; transform: translateY(-2px); }
        .nav button.active { background: #667eea; }
        .content { padding: 30px; }
        .login-container { max-width: 500px; margin: 100px auto; background: white; padding: 50px; border-radius: 15px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); text-align: center; }
        .login-container h2 { color: #02244b; margin-bottom: 20px; font-size: 2em; }
        .discord-btn { display: inline-block; padding: 15px 40px; background: #5865F2; color: white; text-decoration: none; border-radius: 8px; font-weight: 600; transition: all 0.3s; }
        .discord-btn:hover { background: #4752C4; transform: translateY(-2px); }
        .form-group { margin-bottom: 20px; }
        .form-group label { display: block; font-weight: 600; margin-bottom: 8px; }
        .form-group input, .form-group textarea, .form-group select { width: 100%; padding: 12px; border: 2px solid #e9ecef; border-radius: 5px; }
        .form-group textarea { min-height: 100px; resize: vertical; }
        .save-btn { padding: 15px 40px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; transition: transform 0.3s; }
        .save-btn:hover { transform: scale(1.05); }
        .success { background: #d4edda; color: #155724; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .error { background: #f8d7da; color: #721c24; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .page { display: none; }
        .page.active { display: block; }
        .participant-row { display: grid; grid-template-columns: 2fr 1fr 1fr 100px; gap: 15px; margin-bottom: 15px; padding: 15px; background: #f8f9fa; border-radius: 8px; }
        .editor-container { display: grid; grid-template-columns: 1fr 400px; gap: 20px; }
        .editor-preview { background: #36393f; padding: 20px; border-radius: 10px; position: sticky; top: 20px; max-height: 80vh; overflow-y: auto; }
        .embed-preview { background: #2f3136; border-left: 4px solid; border-radius: 4px; padding: 16px; color: #dcddde; }
        .channel-selector { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 20px; }
        .channel-option { padding: 20px; background: #f8f9fa; border: 2px solid #e9ecef; border-radius: 10px; cursor: pointer; text-align: center; transition: all 0.3s; }
        .channel-option:hover, .channel-option.selected { border-color: #667eea; background: #e8eafe; }
        .list-editor { background: white; border: 2px solid #e9ecef; border-radius: 5px; padding: 15px; }
        .list-item { display: flex; gap: 10px; margin-bottom: 10px; }
        .list-item input { flex: 1; padding: 8px; border: 1px solid #dee2e6; border-radius: 3px; }
        .template-card { background: #f8f9fa; border-radius: 10px; padding: 20px; margin-bottom: 20px; border-left: 5px solid #667eea; }
    </style>
</head>
<body>
    {% if not session.get('user') %}
    <div class="login-container">
        <h2>🔐 Portal Login</h2>
        <p style="color: #666; margin-bottom: 30px;">Melde dich mit Discord an</p>
        {% if request.args.get('error') == 'no_permission' %}
        <div class="error">❌ Keine Berechtigung!</div>
        {% endif %}
        <a href="/login" class="discord-btn">Mit Discord anmelden</a>
    </div>
    {% else %}
    <div class="container">
        <div class="header">
            <h1>{% if user_role == 'ausbilderleitung' %}Ausbilderleitungs{% else %}Ausbilder{% endif %}-Portal</h1>
            <p>Willkommen, {{ session.user.username }}!</p>
            <div class="user-info">
                {% if session.user.avatar %}
                <img src="https://cdn.discordapp.com/avatars/{{ session.user.id }}/{{ session.user.avatar }}.png" class="avatar">
                {% endif %}
                <div style="text-align: left;">
                    <div style="font-weight: 600;">{{ session.user.username }}</div>
                    <div style="font-size: 0.9em; opacity: 0.8;">{{ 'Ausbilderleitung' if user_role == 'ausbilderleitung' else 'Ausbilder' }}</div>
                </div>
            </div>
        </div>
        <div class="nav">
            {% if user_role == 'ausbilderleitung' %}
            <button onclick="showPage('templates')" class="active">Templates</button>
            <button onclick="showPage('editor')">Embed Editor</button>
            {% endif %}
            <button onclick="showPage('evaluations')" {% if user_role != 'ausbilderleitung' %}class="active"{% endif %}>Auswertungen</button>
            <button onclick="location.href='/logout'" style="margin-left: auto; background: #dc3545;">Abmelden</button>
        </div>
        <div class="content">
            {% if success %}<div class="success">✅ {{ success }}</div>{% endif %}
            {% if error %}<div class="error">❌ {{ error }}</div>{% endif %}

            {% if user_role == 'ausbilderleitung' %}
            <div class="page active" id="page-templates">
                <h2 style="margin-bottom: 20px;">📋 Templates</h2>
                {% for type in ['theorie', 'grund', 'stvo'] %}
                <div class="template-card">
                    <h3>{{ templates[type].title }}</h3>
                    <form method="POST" action="/save/{{ type }}">
                        <div class="form-group"><label>Titel:</label><input type="text" name="title" value="{{ templates[type].title }}" required></div>
                        <div class="form-group"><label>Intro:</label><textarea name="intro" required>{{ templates[type].intro }}</textarea></div>
                        <div class="form-group"><label>Themen:</label><div class="list-editor" id="topics-{{ type }}">{% for topic in templates[type].topics %}<div class="list-item"><input type="text" name="topics[]" value="{{ topic }}"><button type="button" onclick="this.parentElement.remove()">❌</button></div>{% endfor %}</div><button type="button" onclick="addListItem('topics-{{ type }}', 'topics[]')" style="padding: 8px 16px; background: #28a745; color: white; border: none; border-radius: 5px; cursor: pointer; margin-top: 10px;">+ Thema</button></div>
                        <button type="submit" class="save-btn">Speichern</button>
                    </form>
                </div>
                {% endfor %}
            </div>

            <div class="page" id="page-editor">
                <h2 style="margin-bottom: 20px;">✏️ Embed Editor</h2>
                <div class="editor-container">
                    <div>
                        <form id="embed-form" method="POST" action="/send_embed">
                            <div class="form-group"><label>Nachricht:</label><textarea name="content" id="embed-content" rows="3"></textarea></div>
                            <div class="form-group"><label>Titel:</label><input type="text" name="title" id="embed-title" required></div>
                            <div class="form-group"><label>Beschreibung:</label><textarea name="description" id="embed-description" rows="5" required></textarea></div>
                            <div class="form-group"><label>Farbe (Hex):</label><input type="text" name="color" id="embed-color" value="#667eea"></div>
                            <div class="form-group"><label>Typ:</label><select name="message_type" id="message-type"><option value="theorie">Theorie</option><option value="grund">Grund</option><option value="stvo">StVO</option></select></div>
                            <button type="button" class="save-btn" onclick="showChannelSelector()" style="margin-right: 10px;">Senden</button>
                            <button type="button" class="save-btn" onclick="updatePreview()" style="background: #5865f2;">Vorschau</button>
                            <div id="channel-selector-container" style="display: none;">
                                <div class="channel-selector">
                                    <div class="channel-option" onclick="selectChannel(this, 'announcement')">📢 Ankündigung</div>
                                    <div class="channel-option" onclick="selectChannel(this, 'evaluation')">📊 Auswertung</div>
                                    <div class="channel-option" onclick="selectChannel(this, 'custom')">🎯 Custom</div>
                                </div>
                                <input type="hidden" name="channel_type" id="channel-type-input">
                                <div id="custom-channel-input" style="display: none; margin-top: 15px;"><input type="text" name="custom_channel_id" placeholder="Kanal-ID" style="width: 100%; padding: 12px; border: 2px solid #e9ecef; border-radius: 5px;"></div>
                                <button type="submit" class="save-btn" style="margin-top: 20px; width: 100%;">📤 Jetzt senden</button>
                            </div>
                        </form>
                    </div>
                    <div class="editor-preview">
                        <h3 style="color: white; margin-bottom: 15px;">Vorschau:</h3>
                        <div id="live-preview"><div class="embed-preview" style="border-left-color: #667eea;"><div style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">Titel</div><div style="font-size: 14px;">Beschreibung</div></div></div>
                    </div>
                </div>
            </div>
            {% endif %}

            <div class="page {% if user_role != 'ausbilderleitung' %}active{% endif %}" id="page-evaluations">
                <h2 style="margin-bottom: 20px;">📊 Auswertungen</h2>
                <form method="POST" action="/create_evaluation">
                    <div class="form-group"><label>Typ:</label><select name="training_type" id="training-type" onchange="updateMaxPoints()" required><option value="">Wählen</option><option value="theorie">Theorie</option><option value="grund">Grund</option><option value="stvo">StVO</option></select></div>
                    <div id="participants-container"></div>
                    <button type="button" onclick="addParticipant()" style="padding: 8px 16px; background: #28a745; color: white; border: none; border-radius: 5px; cursor: pointer;">+ Teilnehmer</button>
                    <button type="submit" class="save-btn" style="margin-top: 20px;">Senden</button>
                </form>
            </div>
        </div>
    </div>
    <script>
        function showPage(p) { document.querySelectorAll('.page').forEach(x => x.classList.remove('active')); document.querySelectorAll('.nav button').forEach(x => x.classList.remove('active')); document.getElementById('page-' + p).classList.add('active'); event.target.classList.add('active'); }
        function addListItem(c, f) { const d = document.createElement('div'); d.className = 'list-item'; d.innerHTML = '<input type="text" name="' + f + '" value=""><button type="button" onclick="this.parentElement.remove()">❌</button>'; document.getElementById(c).appendChild(d); }
        function updateMaxPoints() { const t = document.getElementById('training-type').value; const m = (t === 'theorie' || t === 'grund') ? 50 : 25; document.querySelectorAll('.points-input').forEach(i => { i.max = m; i.placeholder = '0-' + m; }); }
        function addParticipant() { const t = document.getElementById('training-type').value; if (!t) { alert('Typ wählen!'); return; } const m = (t === 'theorie' || t === 'grund') ? 50 : 25; const d = document.createElement('div'); d.className = 'participant-row'; d.innerHTML = '<input type="text" name="user_id[]" placeholder="User ID" required><input type="number" name="points[]" class="points-input" min="0" max="' + m + '" placeholder="0-' + m + '" required><input type="number" name="grade[]" min="1" max="6" placeholder="Note" required><button type="button" onclick="this.parentElement.remove()" style="padding: 10px 20px; background: #dc3545; color: white; border: none; border-radius: 5px; cursor: pointer;">❌</button>'; document.getElementById('participants-container').appendChild(d); }
        function updatePreview() { const t = document.getElementById('embed-title').value || 'Titel'; const d = document.getElementById('embed-description').value || 'Beschreibung'; const c = document.getElementById('embed-color').value || '#667eea'; document.getElementById('live-preview').innerHTML = '<div class="embed-preview" style="border-left-color: ' + c + ';"><div style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">' + t + '</div><div style="font-size: 14px;">' + d + '</div></div>'; }
        function showChannelSelector() { const f = document.getElementById('embed-form'); if (!f.checkValidity()) { f.reportValidity(); return; } document.getElementById('channel-selector-container').style.display = 'block'; }
        function selectChannel(e, t) { document.querySelectorAll('.channel-option').forEach(x => x.classList.remove('selected')); e.classList.add('selected'); document.getElementById('channel-type-input').value = t; document.getElementById('custom-channel-input').style.display = t === 'custom' ? 'block' : 'none'; }
        ['embed-title', 'embed-description', 'embed-color'].forEach(id => { const el = document.getElementById(id); if (el) el.addEventListener('input', updatePreview); });
    </script>
    {% endif %}
</body>
</html>'''

@app.route('/')
def index():
    if not session.get('user'):
        return render_template_string(HTML_TEMPLATE, session=session, request=request)

    user_role = session.get('user_role')
    if not user_role:
        return redirect('/logout')

    return render_template_string(HTML_TEMPLATE, templates=bot_data['templates'], session=session, user_role=user_role, success=request.args.get('success'), error=request.args.get('error'), request=request)

@app.route('/login')
def login():
    params = {'client_id': Config.CLIENT_ID, 'redirect_uri': Config.REDIRECT_URI, 'response_type': 'code', 'scope': 'identify guilds'}
    return redirect(f'{Config.OAUTH2_URL}?{urlencode(params)}')

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        print("❌ Kein Code erhalten")
        return redirect('/?error=no_code')

    data = {'client_id': Config.CLIENT_ID, 'client_secret': Config.CLIENT_SECRET, 'grant_type': 'authorization_code', 'code': code, 'redirect_uri': Config.REDIRECT_URI}
    response = requests.post(Config.TOKEN_URL, data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'})

    print(f"📡 Token Response Status: {response.status_code}")

    if response.status_code != 200:
        print(f"❌ Token Fehler: {response.text}")
        return redirect('/?error=token_failed')

    token_data = response.json()
    access_token = token_data.get('access_token')
    user_info = get_user_info(access_token)

    if not user_info:
        print("❌ User Info konnte nicht abgerufen werden")
        return redirect('/?error=user_failed')

    print(f"✅ User: {user_info.get('username')} (ID: {user_info.get('id')})")

    # Guild-ID verwenden (entweder aus ENV oder aus Bot)
    guild_id = Config.GUILD_ID
    if not guild_id and bot.guilds:
        guild_id = str(bot.guilds[0].id)
        print(f"🏰 Guild ID (vom Bot): {guild_id}")
    elif guild_id:
        print(f"🏰 Guild ID (aus Config): {guild_id}")
    else:
        print("❌ Keine Guild-ID verfügbar")
        return redirect('/?error=no_guild')

    user_role = check_user_roles(user_info['id'], guild_id)
    print(f"👤 Rolle gefunden: {user_role}")

    if not user_role:
        print(f"❌ Keine Berechtigung für User {user_info.get('username')}")
        # Debug: Zeige alle Rollen des Users
        member = get_guild_member(guild_id, user_info['id'], Config.TOKEN)
        if member:
            print(f"📋 User Rollen: {member.get('roles', [])}")
        return redirect('/?error=no_permission')

    session['user'] = user_info
    session['user_role'] = user_role
    session['access_token'] = access_token

    print(f"✅ Login erfolgreich: {user_info.get('username')} als {user_role}")
    return redirect('/?success=Angemeldet!')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/save/<type>', methods=['POST'])
def save_template(type):
    if not session.get('user') or session.get('user_role') != 'ausbilderleitung':
        return redirect('/')

    bot_data['templates'][type] = {
        'title': request.form.get('title'),
        'intro': request.form.get('intro'),
        'topics': request.form.getlist('topics[]'),
        'additional_info': request.form.getlist('additional_info[]') or [],
        'grading': request.form.getlist('grading[]') or [],
        'benefits': request.form.getlist('benefits[]') or []
    }
    save_data(bot_data)
    return redirect('/?success=Gespeichert!')

@app.route('/send_embed', methods=['POST'])
def send_embed():
    if not session.get('user') or session.get('user_role') != 'ausbilderleitung':
        return redirect('/')

    try:
        content = request.form.get('content', '')
        title = request.form.get('title')
        description = request.form.get('description')
        color = request.form.get('color', '#667eea').replace('#', '')
        message_type = request.form.get('message_type')
        channel_type = request.form.get('channel_type')
        custom_channel_id = request.form.get('custom_channel_id', '')

        if channel_type == 'custom' and custom_channel_id:
            channel_id = custom_channel_id
        elif channel_type in ['announcement', 'evaluation']:
            channel_id = Config.CHANNELS[message_type][channel_type]
        else:
            return redirect('/?error=Kein Kanal!')

        embed_data = {
            'content': content,
            'embed': {
                'title': title,
                'description': description,
                'color': int(color, 16) if color else 6736106
            },
            'channel_id': channel_id,
            'type': message_type,
            'created_at': datetime.now().isoformat()
        }

        new_id = f"msg_{int(datetime.now().timestamp())}"
        bot_data['messages'][new_id] = embed_data
        active_evaluations[f'send_{new_id}'] = embed_data
        save_data(bot_data)

        return redirect('/?success=Wird gesendet...')
    except Exception as e:
        return redirect(f'/?error={str(e)}')

@app.route('/create_evaluation', methods=['POST'])
def create_evaluation():
    if not session.get('user'):
        return redirect('/')

    try:
        training_type = request.form.get('training_type')
        user_ids = request.form.getlist('user_id[]')
        points = request.form.getlist('points[]')
        grades = request.form.getlist('grade[]')

        if not training_type or not user_ids:
            return redirect('/?error=Felder ausfüllen!')

        evaluation_data = {'training_type': training_type, 'entries': []}

        for i in range(len(user_ids)):
            user_id_str = user_ids[i].strip().strip('<@!>')
            try:
                user_id = int(user_id_str)
                evaluation_data['entries'].append({
                    'user_id': user_id,
                    'points': int(points[i]),
                    'grade': int(grades[i]),
                    'passed': int(grades[i]) <= 4
                })
            except ValueError:
                continue

        if not evaluation_data['entries']:
            return redirect('/?error=Keine Teilnehmer!')

        eval_id = f"web_eval_{int(datetime.now().timestamp())}"
        active_evaluations[eval_id] = evaluation_data

        return redirect('/?success=Wird verarbeitet...')
    except Exception as e:
        return redirect(f'/?error={str(e)}')

def run_flask():
    port = int(os.getenv('PORT', 5000))
    print(f"\n{'='*50}")
    print(f"🌐 Dashboard: http://localhost:{port}")
    print(f"{'='*50}\n")
    app.run(host='0.0.0.0', port=port, debug=False)

# ==================== BOT ====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

def get_grade_from_points(points: int, training_type: str) -> int:
    if training_type in ['theorie', 'grund']:
        if points >= 45: return 1
        elif points >= 40: return 2
        elif points >= 33: return 3
        elif points >= 25: return 4
        elif points >= 15: return 5
        else: return 6
    else:
        if points >= 22: return 1
        elif points >= 17: return 2
        elif points >= 13: return 3
        elif points >= 9: return 4
        elif points >= 4: return 5
        else: return 6

async def assign_role(member: discord.Member, training_type: str) -> bool:
    try:
        if training_type == 'theorie':
            await member.remove_roles(member.guild.get_role(int(Config.ROLES['theorie']['pending'])))
            await member.add_roles(member.guild.get_role(int(Config.ROLES['theorie']['passed'])))
            await member.add_roles(member.guild.get_role(int(Config.ROLES['grund']['pending'])))
        elif training_type == 'grund':
            await member.remove_roles(member.guild.get_role(int(Config.ROLES['grund']['pending'])))
            await member.add_roles(member.guild.get_role(int(Config.ROLES['grund']['passed'])))
            await member.add_roles(member.guild.get_role(int(Config.ROLES['stvo']['pending'])))
        elif training_type == 'stvo':
            await member.remove_roles(member.guild.get_role(int(Config.ROLES['stvo']['pending'])))
            await member.add_roles(member.guild.get_role(int(Config.ROLES['stvo']['passed'])))
        return True
    except:
        return False

async def send_evaluation_to_channel(guild, eval_data):
    try:
        training_type = eval_data['training_type']
        channel_id = int(Config.CHANNELS[training_type]['evaluation'])
        channel = guild.get_channel(channel_id)

        if not channel:
            print(f"❌ Kanal nicht gefunden!")
            return False

        for entry in eval_data['entries']:
            if entry['passed']:
                member = guild.get_member(entry['user_id'])
                if member:
                    await assign_role(member, training_type)

        passed_list = [e for e in eval_data['entries'] if e['passed']]
        failed_list = [e for e in eval_data['entries'] if not e['passed']]

        training_map = {'theorie': 'Theorie', 'grund': 'Grundausbildung', 'stvo': 'StVO Grundausbildung'}
        training_name = training_map.get(training_type, training_type)
        max_points = 50 if training_type in ['theorie', 'grund'] else 25

        msg = f"⚜️ **Auswertung der {training_name}** ⚜️\n\n**bestanden haben:**\n\n"
        for e in passed_list:
            msg += f"Name: <@{e['user_id']}>\nPunkte: {e['points']}/{max_points}\nNote: {e['grade']}\nDatum: {datetime.now().strftime('%d.%m.%Y')}\n\n"

        if failed_list:
            msg += "**Nicht Bestanden Haben:**\n\n"
            for e in failed_list:
                msg += f"Name: <@{e['user_id']}>\nPunkte: {e['points']}/{max_points}\nNote: {e['grade']}\nDatum: {datetime.now().strftime('%d.%m.%Y')}\n\n"
        else:
            msg += "**Nicht Bestanden Haben:**\n\nKeiner 🎉\n\n"

        msg += "Eure Ausbilder wünschen euch alles gute!\nÜber ein 🔥 - Feedback würden wir uns freuen!\n\nMfg\nDas Ausbilderteam\n@Ausbilder"

        await channel.send(msg)

        bot_data['evaluations'].append({
            'type': training_type,
            'entries': eval_data['entries'],
            'created_at': datetime.now().isoformat()
        })
        save_data(bot_data)

        print(f"✅ Auswertung gesendet!")
        return True
    except Exception as e:
        print(f"❌ Fehler: {e}")
        return False

class EvaluationButton(discord.ui.View):
    def __init__(self, eval_url: str):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Zur Auswertung", url=eval_url, style=discord.ButtonStyle.link))

@bot.tree.command(name="ausbildung_ankündigen", description="Kündige eine Ausbildung an")
@app_commands.describe(typ="Typ", datum="TT.MM.JJJJ", uhrzeit="HH:MM", veranstalter="Veranstalter")
async def announce(interaction: discord.Interaction, typ: Literal['theorie', 'grund', 'stvo'], datum: str, uhrzeit: str, veranstalter: discord.Member):
    if not interaction.user.guild_permissions.manage_messages:
        return await interaction.response.send_message("❌ Keine Berechtigung", ephemeral=True)

    try:
        dt = datetime.strptime(f"{datum} {uhrzeit}", "%d.%m.%Y %H:%M")
        timestamp = int(dt.timestamp())
        template = bot_data['templates'][typ]

        channel_id = int(Config.CHANNELS[typ]['announcement'])
        channel = interaction.guild.get_channel(channel_id)

        if not channel:
            return await interaction.response.send_message("❌ Kanal nicht gefunden!", ephemeral=True)

        pending_role = interaction.guild.get_role(int(Config.ROLES[typ]['pending']))
        passed_role = interaction.guild.get_role(int(Config.ROLES[typ]['passed']))

        embed = discord.Embed(title=template['title'], description=template['intro'], color=0x02244b)
        embed.add_field(name="", value=f"📅 **Datum:** <t:{timestamp}:D>\n🕐 **Uhrzeit:** <t:{timestamp}:t>\n⏱️ **Dauer:** ca. 45-90 Min\n\n👤 **Veranstalter:** {veranstalter.mention}", inline=False)
        embed.add_field(name="**Themen:**", value="\n".join(f"> - {t}" for t in template['topics']), inline=False)

        if template.get('additional_info'):
            embed.add_field(name="**Zusätzliche Informationen:**", value="\n".join(f"> - {i}" for i in template['additional_info']), inline=False)

        if template.get('grading'):
            embed.add_field(name="**Notenspiegel:**", value="\n".join(f"> - {g}" for g in template['grading']), inline=False)

        if template.get('benefits'):
            benefits = "\n".join(f"> - {b}" for b in template['benefits'])
            benefits = benefits.replace('{passed_role}', passed_role.mention if passed_role else '✅')
            embed.add_field(name="**Vorteile:**", value=benefits, inline=False)

        if typ in Config.BANNERS:
            embed.set_image(url=Config.BANNERS[typ])

        message = await channel.send(content=pending_role.mention if pending_role else "@everyone", embed=embed, allowed_mentions=discord.AllowedMentions(roles=True))

        try:
            emoji_id = Config.REACTION_EMOJI.split(':')[-1].rstrip('>')
            emoji = discord.utils.get(interaction.guild.emojis, id=int(emoji_id))
            await message.add_reaction(emoji if emoji else '📝')
        except:
            await message.add_reaction('📝')

        await interaction.response.send_message(f"✅ Gesendet in {channel.mention}!", ephemeral=True)

        bot_data['announcements'].append({
            'type': typ,
            'date': datum,
            'time': uhrzeit,
            'timestamp': timestamp,
            'host': veranstalter.id,
            'created_at': datetime.now().isoformat()
        })
        save_data(bot_data)
    except ValueError:
        await interaction.response.send_message("❌ Ungültiges Format!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Fehler: {str(e)}", ephemeral=True)

@bot.tree.command(name="auswertung", description="Auswertung über Web-Portal erstellen")
async def evaluate(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_messages:
        return await interaction.response.send_message("❌ Keine Berechtigung", ephemeral=True)

    eval_url = Config.REDIRECT_URI.rsplit('/', 1)[0] + "/"
    view = EvaluationButton(eval_url)

    embed = discord.Embed(
        title="📊 Auswertung erstellen",
        description="Klicke auf den Button, um zur Auswertungsseite zu gelangen.\n\nDort kannst du alle Teilnehmer hinzufügen und die Auswertung durchführen.",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Die Auswertung wird automatisch im richtigen Kanal gesendet")

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.event
async def on_ready():
    print(f'✅ Bot: {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f'✅ Commands: {len(synced)}')
        bot.loop.create_task(check_web_tasks())
    except Exception as e:
        print(f'❌ Fehler: {e}')

async def check_web_tasks():
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            guild = bot.guilds[0] if bot.guilds else None
            if not guild:
                await asyncio.sleep(5)
                continue

            # Web-Auswertungen
            web_evals = [k for k in list(active_evaluations.keys()) if k.startswith('web_eval_')]
            for eval_id in web_evals:
                eval_data = active_evaluations[eval_id]
                success = await send_evaluation_to_channel(guild, eval_data)
                if success:
                    del active_evaluations[eval_id]

            # Nachrichten senden
            send_tasks = [k for k in list(active_evaluations.keys()) if k.startswith('send_')]
            for task_id in send_tasks:
                msg_data = active_evaluations[task_id]
                try:
                    channel = guild.get_channel(int(msg_data['channel_id']))
                    if not channel:
                        del active_evaluations[task_id]
                        continue

                    content = msg_data.get('content', '')
                    title = msg_data['embed']['title']
                    description = msg_data['embed']['description']

                    msg_type = msg_data['type']
                    pending_role = guild.get_role(int(Config.ROLES[msg_type]['pending']))
                    passed_role = guild.get_role(int(Config.ROLES[msg_type]['passed']))

                    content = content.replace('{pending_role}', pending_role.mention if pending_role else '@everyone')
                    content = content.replace('{passed_role}', passed_role.mention if passed_role else '✅')
                    title = title.replace('{passed_role}', passed_role.mention if passed_role else '✅')
                    description = description.replace('{passed_role}', passed_role.mention if passed_role else '✅')

                    now = datetime.now()
                    content = content.replace('{date}', now.strftime('%d.%m.%Y'))
                    content = content.replace('{time}', now.strftime('%H:%M'))
                    description = description.replace('{date}', now.strftime('%d.%m.%Y'))
                    description = description.replace('{time}', now.strftime('%H:%M'))

                    embed = discord.Embed(
                        title=title,
                        description=description,
                        color=msg_data['embed']['color']
                    )

                    await channel.send(content=content if content else None, embed=embed)

                    del active_evaluations[task_id]
                    print(f"✅ Nachricht gesendet in #{channel.name}")
                except Exception as e:
                    print(f"❌ Fehler: {e}")
                    del active_evaluations[task_id]

            await asyncio.sleep(5)
        except Exception as e:
            print(f"❌ Task-Fehler: {e}")
            await asyncio.sleep(10)

if __name__ == '__main__':
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    bot.run(Config.TOKEN)