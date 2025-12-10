# Phase 6: Multi-User Account System

> **Status**: 🔄 In Progress  
> **Started**: 2025-12-08  
> **Goal**: Multi-User Account System mit SQLite, JWT-Auth und per-User Secrets

---

## Übersicht

Diese Phase implementiert ein Multi-User Account System, das mehreren Benutzern erlaubt:
- Eigene Accounts zu erstellen und sich anzumelden
- Eigene API-Secrets (Bitget, LLM) zu verwalten
- Isolierte Conversations und Charts zu haben

### Design-Entscheidungen

| Komponente | Jetzt (Lokal/Container) | Später (Azure Nativ) |
|------------|-------------------------|----------------------|
| Datenbank | **SQLite** (Datei in Volume) | Azure SQL Database |
| Auth | **JWT + bcrypt** (self-hosted) | Azure Entra ID / B2C |
| Secrets | **User-namespaced Vault** (Fernet) | Azure Key Vault + Managed Identity |
| Sessions | **JWT Tokens** | Azure Entra ID Tokens |
| Container | Docker Compose | Azure Container Apps (ASPIRE) |

### Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  Login   │  │ Register │  │Protected │  │  Auth    │    │
│  │  Page    │  │  Page    │  │  Routes  │  │  Store   │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
│       │             │             │             │           │
│       └─────────────┴─────────────┴─────────────┘           │
│                           │                                  │
│                    Authorization: Bearer <token>             │
└───────────────────────────┼─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                        Backend                               │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                   Auth Middleware                     │   │
│  │              get_current_user() Dependency            │   │
│  └──────────────────────────┬───────────────────────────┘   │
│                             │                                │
│  ┌──────────┐  ┌──────────┐│┌──────────┐  ┌──────────┐     │
│  │  /auth   │  │  /chat   │││ /charts  │  │/settings │     │
│  │ register │  │  (user)  │││  (user)  │  │  (user)  │     │
│  │  login   │  │          │││          │  │          │     │
│  └────┬─────┘  └────┬─────┘│└────┬─────┘  └────┬─────┘     │
│       │             │      │     │             │            │
│       ▼             ▼      │     ▼             ▼            │
│  ┌──────────┐  ┌──────────┐│┌──────────────────────────┐   │
│  │   User   │  │ Conversa-│││    SecretsVault          │   │
│  │Repository│  │  tions   │││  (user-namespaced)       │   │
│  └────┬─────┘  └────┬─────┘│└──────────┬───────────────┘   │
│       │             │      │           │                    │
│       ▼             ▼      │           ▼                    │
│  ┌─────────────────────────┴───────────────────────────┐   │
│  │                    SQLite Database                   │   │
│  │     /app/data/app.db (User, Conversations, etc.)     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │               Encrypted Vault Files                  │   │
│  │   /app/data/.secrets.enc (user_{id}_{key} format)    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Steps

### Step 1: Dokumentation ✅
- [x] PHASE_6_MULTIUSER.md erstellen
- [x] PROGRESS.md aktualisieren
- [x] CHECKLIST.md aktualisieren  
- [x] copilot-instructions.md erweitern

### Step 2: SQLite + SQLAlchemy Setup ✅
- [x] Dependencies hinzufügen (`sqlalchemy[asyncio]`, `aiosqlite`, `python-jose`, `passlib[bcrypt]`)
- [x] `backend/app/core/database.py` erstellen (async engine, session)
- [x] `backend/app/models/database.py` erstellen (User, Conversation Models)
- [x] DB-Initialisierung in `main.py` hinzufügen

**Dateien:**
```
backend/app/core/database.py     # Async SQLAlchemy Engine
backend/app/models/database.py   # SQLAlchemy Models
backend/requirements.txt         # Neue Dependencies
```

### Step 3: User Repository Interface ✅
- [x] `backend/app/core/repositories.py` erstellen
- [x] `UserRepositoryProtocol` (Abstract Interface)
- [x] `SQLiteUserRepository` (Konkrete Implementierung)
- [x] CRUD: create_user, get_by_email, get_by_id, update_password

**Dateien:**
```
backend/app/core/repositories.py
```

### Step 4: JWT-Auth Module ✅
- [x] `backend/app/core/auth.py` erstellen
- [x] Password Hashing (bcrypt)
- [x] JWT Token Creation/Validation
- [x] Config: JWT_SECRET_KEY, JWT_EXPIRE_MINUTES
- [x] Admin-Bootstrap: User mit ADMIN_EMAIL bei Startup anlegen

**Dateien:**
```
backend/app/core/auth.py
```

### Step 5: Auth-Endpoints ✅
- [x] `backend/app/api/routes/auth.py` erstellen
- [x] POST /api/v1/auth/register
- [x] POST /api/v1/auth/login  
- [x] GET /api/v1/auth/me
- [x] Router in main.py registrieren

**Dateien:**
```
backend/app/api/routes/auth.py
backend/app/main.py (Router hinzufügen)
```

### Step 6: SecretsVault User-Namespace ✅
- [x] `security.py` erweitern
- [x] `save_user_secret(user_id, key, value)`
- [x] `get_user_secret(user_id, key)`
- [x] `delete_user_secret(user_id, key)`
- [x] `list_user_secrets(user_id)`
- [x] Prefix-Schema: `user_{user_id}_{key}`

**Dateien:**
```
backend/app/core/security.py (erweitern)
```

### Step 7: Route-Protection ✅
- [x] `get_current_user()` Dependency in dependencies.py
- [ ] Alle Routes absichern:
  - [ ] chat.py
  - [ ] charts.py
  - [ ] settings.py
- [ ] Daten an user.id scopen

**Dateien:**
```
backend/app/core/dependencies.py
backend/app/api/routes/chat.py
backend/app/api/routes/charts.py
backend/app/api/routes/settings.py
```

### Step 8: WebSocket Auth ⏳
- [ ] Token-Validierung bei Connect
- [ ] Query-Parameter: `?token=xxx`
- [ ] User-Context in ConnectionManager speichern

**Dateien:**
```
backend/app/api/websocket/handlers.py
```

### Step 9: Frontend Auth-Flow ⏳
- [ ] `frontend/src/stores/authStore.ts` (Zustand)
- [ ] `frontend/src/services/authService.ts`
- [ ] Login/Register Pages
- [ ] Protected Route Wrapper
- [ ] Axios Interceptor für Authorization Header
- [ ] WebSocket Token-Parameter

**Dateien:**
```
frontend/src/stores/authStore.ts
frontend/src/services/authService.ts
frontend/src/components/features/LoginPage.tsx
frontend/src/components/features/RegisterPage.tsx
frontend/src/components/layout/ProtectedRoute.tsx
frontend/src/services/api.ts (erweitern)
frontend/src/services/websocket.ts (erweitern)
```

### Step 10: Environment & Docker ⏳
- [ ] ADMIN_EMAIL zu .env.example
- [ ] JWT_SECRET_KEY zu .env.example
- [ ] docker-compose.dev.yml aktualisieren

**Dateien:**
```
.env.example
docker-compose.dev.yml
```

---

## Technische Details

### User Model (SQLAlchemy)

```python
class User(Base):
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, onupdate=datetime.utcnow)
```

### JWT Token Structure

```python
{
    "sub": "user_id",
    "email": "user@example.com",
    "is_admin": false,
    "exp": 1733745600  # Expiration timestamp
}
```

### User-Scoped Secrets

```python
# Prefix-Schema für User-Secrets
def _user_key(user_id: str, key: str) -> str:
    return f"user_{user_id}_{key}"

# Beispiel: user_abc123_bitget_api_key
```

### Environment Variables (Neu)

```bash
# Admin User (wird bei Startup erstellt falls nicht existiert)
ADMIN_EMAIL=admin@example.com

# JWT Configuration
JWT_SECRET_KEY=your-secret-key-here  # Auto-generiert falls nicht gesetzt
JWT_EXPIRE_MINUTES=60                # Token-Gültigkeit
```

---

## API Endpoints (Neu)

```
POST /api/v1/auth/register    → Register new user
     Body: { "email": "...", "password": "..." }
     Returns: { "access_token": "...", "token_type": "bearer", "user": {...} }

POST /api/v1/auth/login       → Login existing user
     Body: { "email": "...", "password": "..." }
     Returns: { "access_token": "...", "token_type": "bearer", "user": {...} }

GET  /api/v1/auth/me          → Get current user info
     Header: Authorization: Bearer <token>
     Returns: { "id": "...", "email": "...", "is_admin": false }
```

---

## Testing

### Backend Tests
```bash
# Auth-Endpunkte testen
pytest tests/test_auth.py -v

# User Repository testen
pytest tests/test_repositories.py -v
```

### Manual Testing
```bash
# Register
curl -X POST http://localhost:8500/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "secret123"}'

# Login
curl -X POST http://localhost:8500/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "secret123"}'

# Protected Route
curl http://localhost:8500/api/v1/auth/me \
  -H "Authorization: Bearer <token>"
```

---

## Migration zu Azure (Später)

Wenn die App nach Azure migriert wird:

1. **SQLite → Azure SQL Database**
   - Connection String ändern
   - `SQLiteUserRepository` → `AzureSQLUserRepository`

2. **JWT → Azure Entra ID**
   - MSAL Library integrieren
   - Token-Validierung gegen Azure AD

3. **User-Vault → Azure Key Vault**
   - Managed Identity konfigurieren
   - Key Vault Client integrieren

Die Abstraktion über Repository-Pattern und austauschbare Auth-Module macht diese Migration einfach.

---

## Troubleshooting

### Problem: "Database is locked"
SQLite erlaubt nur einen Writer. Lösung: Async Session mit `aiosqlite`.

### Problem: "JWT Token expired"
Token nach JWT_EXPIRE_MINUTES ungültig. Lösung: Refresh-Token implementieren oder Expire-Zeit erhöhen.

### Problem: "Admin user not created"
ADMIN_EMAIL Env-Variable nicht gesetzt. Lösung: In `.env` setzen.

---

*Erstellt: 2025-12-08*
