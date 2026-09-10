# ANGWood Backend API

Backend REST API for **ANGWood**, a wood commerce platform based in Buenaventura, Cali, Colombia. The platform manages raw wood inventory, customer quotations, MercadoPago payments, an AI-powered chatbot for product inquiries, and an administrative panel with NL2SQL capabilities.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          CLIENTS                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │   Frontend   │  │  Admin Panel │  │  Mobile App  │                  │
│  │  (React/Vite)│  │              │  │              │                  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                  │
└─────────┼─────────────────┼─────────────────┼──────────────────────────┘
          │                 │                 │
          ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     FastAPI Application (Port 8000)                     │
│                                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  │
│  │  Auth JWT   │  │   RBAC      │  │   CORS      │  │   Sentry     │  │
│  │  Argon2     │  │  Middleware  │  │  Middleware  │  │   Errors     │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └──────────────┘  │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                        Route Groups                             │   │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────────┐  │   │
│  │  │  Auth  │ │ Users  │ │  Cart  │ │ Lotes  │ │  Quotations  │  │   │
│  │  └────────┘ └────────┘ └────────┘ └────────┘ └──────────────┘  │   │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────────┐  │   │
│  │  │Pieces  │ │  Wood  │ │  Suppl.│ │ Config │ │   Payments   │  │   │
│  │  │Inventory│ │ Types  │ │        │ │(Admin) │ │ (MercadoPago)│  │   │
│  │  └────────┘ └────────┘ └────────┘ └────────┘ └──────────────┘  │   │
│  │  ┌──────────────────────────┐  ┌──────────────────────────────┐ │   │
│  │  │  AI Assistant (Gemini)   │  │  Legacy Chatbot (NL→SQL)    │ │   │
│  │  │  Tool Calling + Images   │  │  Google GenAI               │ │   │
│  │  └──────────────────────────┘  └──────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                        Services Layer                           │   │
│  │  Config │ Quotation │ Cost Calc │ Gemini LLM │ Assistant Tools │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  PostgreSQL  │  │   Mercado    │  │   Google     │
│     16       │  │    Pago      │  │   Gemini     │
│  (Database)  │  │  (Payments)  │  │   (LLM AI)   │
└──────────────┘  └──────────────┘  └──────────────┘
```

### Data Flow

1. **Product Catalog**: Admin uploads wood types, measurements, and categories; wood pieces are added in batches (lotes) linked to suppliers
2. **Shopping Flow**: Customer browses catalog → adds pieces to cart → creates quotation → pays via MercadoPago → quotation auto-approved → inventory reduced
3. **AI Chatbot**: Customer asks natural language questions → Gemini processes with tool calling → executes catalog/inventory/cart operations → returns business-aware answers
4. **Admin NL2SQL**: Admin enters natural language query → Gemini converts to SQL → executes query → returns structured results

## Tech Stack

| Layer            | Technology                    |
| ---------------- | ----------------------------- |
| Language         | Python 3.11+                  |
| Framework        | FastAPI 0.135                 |
| ORM              | SQLModel + SQLAlchemy 2.0     |
| Database         | PostgreSQL 16                 |
| Auth             | JWT (PyJWT) + Argon2 (pwdlib) |
| AI               | Google Gemini 2.0             |
| Payments         | MercadoPago SDK 2.2           |
| Error Tracking   | Sentry                        |
| Containerization | Docker + Docker Compose       |

## API Endpoints

### Health

| Method | Endpoint  | Description               | Auth |
| ------ | --------- | ------------------------- | ---- |
| GET    | `/health` | Health check (DB session) | —    |

### Authentication

| Method | Endpoint | Description                         | Auth |
| ------ | -------- | ----------------------------------- | ---- |
| POST   | `/token` | Login → JWT token (form-urlencoded) | None |

### Users

| Method | Endpoint                  | Description       | Auth          |
| ------ | ------------------------- | ----------------- | ------------- |
| POST   | `/users`                  | Register new user | None          |
| GET    | `/users`                  | List all users    | `view_users`  |
| GET    | `/users/{user_id}`        | Get user by ID    | `view_users`  |
| PATCH  | `/users/{user_id}`        | Update user       | `update_user` |
| PATCH  | `/users/{user_id}/delete` | Soft-delete user  | `delete_user` |
| PATCH  | `/users/{user_id}/role`   | Change user role  | Admin         |

### Cart

| Method | Endpoint                | Description          | Auth        |
| ------ | ----------------------- | -------------------- | ----------- |
| GET    | `/cart`                 | View current cart    | Active user |
| POST   | `/cart/items`           | Add item to cart     | Active user |
| PATCH  | `/cart/items/{item_id}` | Update item quantity | Active user |
| DELETE | `/cart/items/{item_id}` | Remove item          | Active user |
| DELETE | `/cart`                 | Empty cart           | Active user |

### Inventory - Lotes

| Method | Endpoint           | Description                  | Auth                   |
| ------ | ------------------ | ---------------------------- | ---------------------- |
| POST   | `/lotes`           | Create batch/lot             | `gestionar_inventario` |
| GET    | `/lotes`           | List lots (`?estado=activo`) | `ver_inventario`       |
| GET    | `/lotes/{lote_id}` | Get lot by ID                | `ver_inventario`       |
| DELETE | `/lotes/{lote_id}` | Deactivate lot               | `gestionar_inventario` |
| GET    | `/movimientos`     | List inventory movements     | Active user            |

### Suppliers

| Method | Endpoint            | Description                 | Auth                   |
| ------ | ------------------- | --------------------------- | ---------------------- |
| GET    | `/proveedores/`     | List suppliers (`?activo=`) | `ver_inventario`       |
| GET    | `/proveedores/{id}` | Get supplier                | `ver_inventario`       |
| POST   | `/proveedores/`     | Create supplier             | `gestionar_inventario` |
| PATCH  | `/proveedores/{id}` | Update supplier             | `gestionar_inventario` |
| DELETE | `/proveedores/{id}` | Deactivate supplier         | `gestionar_inventario` |

### Wood Pieces

| Method | Endpoint       | Description                                             | Auth                   |
| ------ | -------------- | ------------------------------------------------------- | ---------------------- |
| POST   | `/piezas`      | Create piece (auto-calculates volume)                   | `gestionar_inventario` |
| GET    | `/piezas`      | List pieces (`?estado=&tipo_madera_id=&offset=&limit=`) | None                   |
| GET    | `/piezas/{id}` | Get piece by ID                                         | None                   |
| PATCH  | `/piezas/{id}` | Update piece                                            | `gestionar_inventario` |
| DELETE | `/piezas/{id}` | Deactivate piece                                        | `gestionar_inventario` |

### Wood Types

| Method | Endpoint           | Description         | Auth                   |
| ------ | ------------------ | ------------------- | ---------------------- |
| GET    | `/wood-types/`     | List all wood types | None                   |
| GET    | `/wood-types/{id}` | Get wood type       | None                   |
| POST   | `/wood-types/`     | Create wood type    | `gestionar_inventario` |
| PATCH  | `/wood-types/{id}` | Update wood type    | `gestionar_inventario` |
| DELETE | `/wood-types/{id}` | Delete wood type    | `gestionar_inventario` |

### Measurements

| Method | Endpoint        | Description        | Auth                   |
| ------ | --------------- | ------------------ | ---------------------- |
| GET    | `/medidas/`     | List measurements  | None                   |
| GET    | `/medidas/{id}` | Get measurement    | None                   |
| POST   | `/medidas/`     | Create measurement | `gestionar_inventario` |
| PATCH  | `/medidas/{id}` | Update measurement | `gestionar_inventario` |
| DELETE | `/medidas/{id}` | Delete measurement | `gestionar_inventario` |

### Categories

| Method | Endpoint           | Description     | Auth                   |
| ------ | ------------------ | --------------- | ---------------------- |
| GET    | `/categorias/`     | List categories | None                   |
| GET    | `/categorias/{id}` | Get category    | None                   |
| POST   | `/categorias/`     | Create category | `gestionar_inventario` |
| PATCH  | `/categorias/{id}` | Update category | `gestionar_inventario` |
| DELETE | `/categorias/{id}` | Delete category | `gestionar_inventario` |

### System Configuration (Admin only)

| Method | Endpoint              | Description      | Auth  |
| ------ | --------------------- | ---------------- | ----- |
| GET    | `/configuracion/`     | List all configs | Admin |
| GET    | `/configuracion/{id}` | Get config       | Admin |
| POST   | `/configuracion/`     | Create config    | Admin |
| PATCH  | `/configuracion/{id}` | Update config    | Admin |
| DELETE | `/configuracion/{id}` | Delete config    | Admin |

### Quotations

| Method | Endpoint             | Description                           | Auth               |
| ------ | -------------------- | ------------------------------------- | ------------------ |
| POST   | `/cotizaciones`      | Create quotation from cart            | None               |
| GET    | `/cotizaciones`      | List quotations                       | None               |
| GET    | `/cotizaciones/{id}` | Get quotation                         | None               |
| PATCH  | `/cotizaciones/{id}` | Update quotation (`?recalcular=true`) | None               |
| DELETE | `/cotizaciones/{id}` | Delete quotation                      | `delete_quotation` |

### Quotation Details

| Method | Endpoint                                 | Description          | Auth |
| ------ | ---------------------------------------- | -------------------- | ---- |
| POST   | `/cotizaciones/detalles`                 | Create detail line   | None |
| GET    | `/cotizaciones/detalles`                 | List all details     | None |
| GET    | `/cotizaciones/detalles/cotizacion/{id}` | Details by quotation | None |
| GET    | `/cotizaciones/detalles/{id}`            | Get detail           | None |
| PATCH  | `/cotizaciones/detalles/{id}`            | Update detail        | None |
| DELETE | `/cotizaciones/detalles/{id}`            | Delete detail        | None |

### Dashboard Metrics

| Method | Endpoint              | Description            | Auth                   |
| ------ | --------------------- | ---------------------- | ---------------------- |
| GET    | `/metricas/dashboard` | Full dashboard metrics | `gestionar_inventario` |

### Payments

| Method | Endpoint             | Description                 | Auth         |
| ------ | -------------------- | --------------------------- | ------------ |
| POST   | `/pagos/preferencia` | Create MercadoPago checkout | Active user  |
| POST   | `/pagos/webhook`     | MercadoPago IPN webhook     | MP signature |
| GET    | `/pagos`             | List all payments           | Admin/Staff  |
| GET    | `/pagos/{id}`        | Get payment status          | Active user  |

### AI Assistant

| Method | Endpoint                          | Description                         | Auth     |
| ------ | --------------------------------- | ----------------------------------- | -------- |
| POST   | `/assistant/chat`                 | Chat with AI (tool calling, images) | Optional |
| DELETE | `/assistant/session/{session_id}` | Clear session                       | None     |

### Legacy Chatbot (NL→SQL)

| Method | Endpoint                        | Description                  | Auth |
| ------ | ------------------------------- | ---------------------------- | ---- |
| POST   | `/chatbot/human_query`          | Natural language → SQL query | None |
| DELETE | `/chatbot/session/{session_id}` | Clear session                | None |

## Authentication & Authorization

### JWT Token Flow

```
Client                          API
  │                               │
  │  POST /token                  │
  │  (username + password)        │
  │──────────────────────────────►│
  │                               │  Verify password (Argon2)
  │                               │  Generate JWT token
  │◄──────────────────────────────│
  │  { access_token, token_type } │
  │                               │
  │  GET /protected-endpoint      │
  │  Authorization: Bearer <jwt>  │
  │──────────────────────────────►│
  │                               │  Decode JWT → user_id, role
  │                               │  Check permissions
  │◄──────────────────────────────│
  │  { data }                     │
```

### Roles & Permissions

| Role      | Permissions                                                                               |
| --------- | ----------------------------------------------------------------------------------------- |
| **admin** | Full access to all endpoints                                                              |
| **staff** | `ver_inventario`, `gestionar_inventario`, `view_users`, `update_user`, `delete_quotation` |
| **user**  | `create_user`, `view_users`                                                               |

### Login Example

```bash
curl -X POST http://localhost:8000/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=your_password"
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Using the Token

```bash
curl http://localhost:8000/piezas \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

### Token Details

- **Algorithm**: HS256 (configurable via `ALGORITHM` env var)
- **Expiration**: 60 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
- **Payload**: `{ sub: username, role: role_name, user_id: id, exp: timestamp }`

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 16 (or Docker)
- Google Gemini API key
- MercadoPago access token

### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd ANWOODBACKEND

# Configure environment variables
cp .env.example .env
# Edit .env with your credentials

# Start all services
docker-compose up --build
```

This starts:

- **API** on `http://localhost:8000`
- **PostgreSQL** on `localhost:5432`
- **pgAdmin** on `http://localhost:5050`

The API docs are available at `http://localhost:8000/docs`.

### Option 2: Local Development

```bash
# Clone the repository
git clone <repository-url>
cd ANWOODBACKEND

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your PostgreSQL connection and API keys

# For local PostgreSQL, update DATABASE_URL in .env:
# DATABASE_URL=postgresql://angwood_user:password@localhost:5432/angwood

# Initialize database and create admin user
python -m app.create_admin_user

# Start the development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Running Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Environment Variables

| Variable                      | Required | Description                                     |
| ----------------------------- | -------- | ----------------------------------------------- |
| `DATABASE_URL`                | Yes      | PostgreSQL connection string                    |
| `SECRET_KEY`                  | Yes      | JWT signing secret                              |
| `ALGORITHM`                   | Yes      | JWT algorithm (e.g., `HS256`)                   |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No       | Token lifetime (default: 30)                    |
| `SUPERUSER_USERNAME`          | Yes      | Initial admin username                          |
| `EMAIL`                       | Yes      | Initial admin email                             |
| `PASSWORD`                    | Yes      | Initial admin password                          |
| `POSTGRES_DB`                 | Yes      | PostgreSQL database name                        |
| `POSTGRES_USER`               | Yes      | PostgreSQL user                                 |
| `POSTGRES_PASSWORD`           | Yes      | PostgreSQL password                             |
| `GOOGLE_API_KEY`              | Yes      | Google API key (legacy chatbot)                 |
| `GEMINI_API_KEY`              | Yes      | Gemini API key (assistant)                      |
| `MP_ACCESS_TOKEN`             | Yes      | MercadoPago access token                        |
| `APP_URL`                     | No       | Frontend URL (default: `http://localhost:3000`) |
| `API_URL`                     | No       | Backend URL (default: `http://localhost:8000`)  |

## Interactive API Documentation

Once the server is running, access the auto-generated documentation:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Database Schema

The application uses 17 tables including: `user`, `role`, `permission`, `cart`, `itemcart`, `loteinventory`, `woodpiece`, `medida`, `tipo_madera`, `categoria`, `cotizacion`, `detalle_cotizacion`, `movimientoinventario`, `proveedor`, `proveedor_lote`, `configuracion`, and `pago`.

## Contributing

Contributions are welcome! Please read the following guidelines before submitting a pull request.

### Prerequisites

- Python 3.11+
- PostgreSQL 16 (or Docker)
- Google Gemini API key
- MercadoPago access token

For full setup instructions, see [Getting Started](#getting-started).

### Branching Strategy

This project follows a Git Flow–inspired workflow:

- **`main`** — Stable, production-ready code. Only merged from `develop` for releases.
- **`develop`** — Integration branch. All feature/fix branches target this branch.
- **`feature/*`** — New features. Branch off from `develop`.
  - Example: `feature/pagos-refund`
- **`fix/*`** — Bug fixes. Branch off from `develop`.
  - Example: `fix/cart-quantity-validation`
- **`chore/*`** — Maintenance, refactoring, documentation updates.
  - Example: `chore/update-dependencies`

### Submitting Changes

1. Fork the repository and clone your fork.
2. Create a new branch from `develop`:
   ```bash
   git checkout develop
   git checkout -b feature/your-feature-name
   ```
3. Make your changes following the code style conventions below.
4. Run the test suite to ensure nothing is broken:
   ```bash
   pip install -r requirements-dev.txt
   pytest
   ```
5. Commit your changes with a clear, conventional commit message (see below).
6. Push your branch and open a pull request targeting `develop`.

### Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
type(scope): short description

[optional body]

[optional footer]
```

**Types**: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `ci`

**Examples**:
- `feat(pagos): add refund endpoint`
- `fix(auth): correct token expiration validation`
- `docs(api): update quotation endpoint documentation`
- `test(cart): add edge case tests for empty cart`

### Code Style & Conventions

- **Python 3.11+** with full type hints on all functions and variables.
- **FastAPI** routers use dependency injection and `async` handlers.
- **SQLModel** for ORM models, **Pydantic** for request/response schemas.
- Use **relative imports** within the `app/` package (e.g., `from ..models import User`).
- No inline comments — let the code speak for itself.
- Follow the existing naming patterns: Spanish for domain entities (`pieza_madera`, `cotizacion`, `lote`), English for infrastructure (`auth`, `database`, `config`).

### Project Structure

```
app/
├── main.py                  # FastAPI app entry point
├── models.py                # SQLModel database models
├── schemas.py               # Pydantic request/response schemas
├── database.py              # DB session and engine
├── auth.py                  # JWT auth, RBAC, permissions
├── routers/                 # API route handlers (one file per domain)
├── services/                # Business logic layer
│   └── assistant_executor/  # AI assistant tool executors
└── openapi.py               # OpenAPI metadata
tests/                       # Pytest test suite
```

### Testing

All new features and bug fixes should include tests. Tests live in the `tests/` directory and use **pytest** with **pytest-cov** for coverage.

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage report
pytest --cov=app
```

When adding tests, follow the existing naming convention: `test_<module>.py` mirroring the module being tested.

### Pull Request Guidelines

- Give your PR a clear, descriptive title.
- Describe **what** changed and **why** in the PR description.
- Reference any related issues (e.g., `Closes #12`).
- Ensure all existing tests pass before submitting.
- Keep PRs focused — one feature or fix per PR when possible.
- A maintainer will review your PR and may request changes.
