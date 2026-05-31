# ROADSoS AI - Folder Structure Reference
# Generated automatically

app/
├── main.py                      # FastAPI app entrypoint
├── config/
│   ├── __init__.py
│   └── settings.py              # Pydantic settings
├── database/
│   ├── __init__.py
│   └── connection.py            # SQLAlchemy engine + session
├── models/
│   ├── __init__.py
│   ├── user.py
│   ├── medical_profile.py
│   ├── incident.py
│   ├── blackbox.py
│   ├── report.py
│   ├── evidence.py
│   ├── disaster.py
│   └── community.py
├── schemas/
│   └── schemas.py               # All Pydantic schemas
├── services/
│   ├── __init__.py
│   ├── user_service.py
│   ├── incident_service.py
│   ├── report_generator.py
│   └── qr_generator.py
├── emergency/
│   ├── incident_service.py      # SOS orchestrator
│   └── resource_finder.py       # Overpass API GIS
├── ai/
│   └── gemini_assistant.py      # Gemini AI integration
├── routes/
│   ├── __init__.py
│   ├── auth.py                  # Login/Register/Logout
│   ├── api.py                   # REST API endpoints
│   └── pages.py                 # Jinja2 template routes
├── utils/
│   ├── __init__.py
│   └── session.py               # Cookie session management
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── dashboard.html
│   ├── sos.html
│   ├── map.html
│   ├── profile.html
│   ├── reports.html
│   ├── disaster.html
│   ├── ai_assistant.html
│   ├── admin.html
│   ├── incident_detail.html
│   ├── 404.html
│   └── auth/
│       ├── login.html
│       └── register.html
└── static/
    ├── js/
    │   ├── sw.js                # Service Worker (PWA)
    │   ├── theme.js             # Dark mode manager
    │   ├── offline.js           # Offline status
    │   └── pwa.js               # Install prompt
    ├── icons/
    │   ├── icon-192.png         # PWA icon (generate separately)
    │   └── icon-512.png         # PWA icon (generate separately)
    ├── reports/                 # Generated PDF/TXT/JSON reports
    ├── qr/                      # Generated QR codes
    └── uploads/                 # Evidence uploads

.env                             # Environment variables
requirements.txt                 # Python dependencies
