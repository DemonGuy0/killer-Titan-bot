# 🤖 TITAN BOT

User-bot avanzado para Telegram con múltiples funciones de IA y automatización.

## ✨ Características

- **Chat con IA** - Gemini + Groq
- **Generación de imágenes** - IA integrada
- **Descarga de música** - Spotify
- **Descarga de series** - La Cartoon
- **Reacciones automáticas** - Premium (hasta 3 emojis por usuario)
- **Sistema de trolls** - Respuestas automáticas personalizables
- **ChatFight Auto-Responder** - Detecta y responde juegos automáticamente
- **Streaming de video** - Tiempo real
- **Historias de Instagram** - Subida automática
- **Renvío masivo** - Entre canales
- **Modo AFK** - Ausencias automáticas
- **Citas automáticas** - Inspiradoras (24h) + Canal
- **Servidor y Speedtest** - Monitoreo del servidor

## 📋 Comandos

### Generales
| Comando | Descripción |
|---------|-------------|
| `-start` | Inicia el User-bot |
| `-help` | Muestra este mensaje de ayuda |
| `-ping` | Verifica si el bot está activo |
| `-changelog` | Muestra el historial de cambios |
| `-userinfo [reply\|user_id]` | Muestra información de un usuario |
| `-chatinfo [reply\|chat_id]` | Muestra información de un chat |

### IA y Chat
| Comando | Descripción |
|---------|-------------|
| `-ai [texto]` | Genera una respuesta de la IA |
| `-aiaudio` | Genera una respuesta de la IA en audio |
| `-reset` | Resetea el chat con la IA |

### Multimedia
| Comando | Descripción |
|---------|-------------|
| `-cartoon [url]` | Descarga series de La Cartoon |
| `-dlmusic [url] [play]` | Descarga música de Spotify |
| `-stopdlmusic` | Detiene la descarga en progreso |
| `-story [caption] [reply]` | Sube multimedia a historias |
| `-image [prompt]` | Genera una imagen con IA |

### Streaming
| Comando | Descripción |
|---------|-------------|
| `-stream [url] [key]` | Inicia un stream de video |
| `-stopstream [id]` | Detiene un stream en progreso |

### Mensajes y Canales
| Comando | Descripción |
|---------|-------------|
| `-urlsave [enlace] [cantidad] [channel_id] [topic_id]` | Guarda mensajes de un enlace |
| `-save [id canal] [cantidad] [channel_id] [topic_id]` | Renvío masivo entre canales |
| `-clear` | Limpia la carpeta de descargas |

### Estado
| Comando | Descripción |
|---------|-------------|
| `-afk` | Activa/desactiva el modo AFK |

### Servidor y Sistema
| Comando | Descripción |
|---------|-------------|
| `-server` | Muestra info del servidor y ejecuta speedtest |

### Sistema de Citas Automáticas
| Comando | Descripción |
|---------|-------------|
| `-quote` | Publica una cita inspiradora aleatoria (imagen) |
| `-quotedaily` | Activa/desactiva citas cada 24 horas |

### Sistema de ChatFight Auto-Responder
| Comando | Descripción |
|---------|-------------|
| `-chatfight` | Activa/desactiva el auto-respondedor |
| `-chatfightstats` | Muestra estadísticas del módulo |

### Sistema de Reacciones (Premium)
| Comando | Descripción |
|---------|-------------|
| `-re add [emoji]` | Agrega reacción (responde a un mensaje) |
| `-re del [emoji\|all]` | Elimina reacción(es) |
| `-re toggle` | Activa/desactiva reacciones |
| `-res` | Lista reacciones del grupo |

### Sistema de Trolls
| Comando | Descripción |
|---------|-------------|
| `-trolladd [id] [texto]` | Agrega un troll |
| `-trolldel [id]` | Elimina un troll |
| `-trolls` | Lista todos los trolls |
| `-troll` | Activa/desactiva todos los trolls |

### Respuestas Automáticas
| Comando | Descripción |
|---------|-------------|
| `-random` | Activa/desactiva respuestas aleatorias |
| `-uf` | Activa/desactiva respuestas con insultos |

## 🛠️ Instalación

### Requisitos
- Python 3.8+
- MongoDB
- FFmpeg

### Variables de Entorno
```env
# Telegram
API_ID=tu_api_id
API_HASH=tu_api_hash
MOBILE_NUMBER=tu_numero
SESSION_STRING=tu_session_string

# IA
GROQ=tu_api_key_groq
GEMINI=tu_api_key_gemini

# Otros
PORT=7860
```

### Docker
```bash
docker build -t titan-bot .
docker run -d --name titan-bot \
  -e API_ID=tu_api_id \
  -e API_HASH=tu_api_hash \
  -e SESSION_STRING=tu_session \
  -e GROQ=tu_groq_key \
  titan-bot
```

### Local
```bash
# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# o
.venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar
python bot.py
```

## 📁 Estructura

```
TITAN-BOT/
├── bot.py              # Archivo principal
├── modules/
│   ├── config.py       # Configuración
│   ├── reactions.py    # Sistema de reacciones
│   ├── troll.py        # Sistema de trolls
│   ├── gemini.py       # IA Gemini
│   ├── groq_chat.py    # IA Groq
│   ├── quotes.py       # Citas inspiradoras
│   ├── lacartoon.py    # La Cartoon
│   ├── spp.py          # Spotify
│   ├── chatfight.py    # ChatFight Auto-Responder
│   └── server_info.py  # Info del servidor y speedtest
├── Dockerfile
├── requirements.txt
└── README.md
```

## 📊 Base de Datos

### MongoDB
- **Host:** Cluster0 de MongoDB Atlas
- **Base de datos:** TITAN
- **Colecciones:**
  - `Trolls` - Sistema de trolls
  - `Reactions` - Sistema de reacciones
  - `QuotesConfig` - Configuración de citas automáticas
  - `ChatFight` - Estadísticas del auto-respondedor

## 🔒 Seguridad

- Solo el propietario puede usar los comandos
- Los mensajes sensibles se eliminan automáticamente
- Modo AFK para ausencias

## 📝 Notas

- El bot debe estar en el grupo para reaccionar
- Las reacciones son específicas por grupo
- Premium permite hasta 3 reacciones por usuario
- Sistema de citas: configuración persistida en MongoDB
- Las citas se publican cada 24 horas automáticamente
- ChatFight detecta y responde automáticamente al bot ChatFight
- Reinicia el bot después de modificar código
- Usa `-server` para monitorear el servidor y ejecutar speedtest

## 📄 Licencia

MIT License

---

**Titan Bot** v3.2 - Creado con ❤️
