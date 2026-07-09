# ULTRON Database Documentation

ULTRON uses a local-first SQLite engine to persist data. The database file is located at `ultron_memory.db` in the project root directory.

---

## 1. Database Schema Overview

```
 ┌─────────────────────────────────────────────────────────────┐
 │                       ultron_memory.db                      │
 └──────────────────────────────┬──────────────────────────────┘
                                │
         ┌──────────────────────┼──────────────────────┐
         ▼                      ▼                      ▼
   ┌───────────┐          ┌───────────┐          ┌───────────┐
   │preference │          │permission │          │project    │
   └───────────┘          └───────────┘          └───────────┘
         │                      │                      │
         └───────────┬──────────┴──────────┬───────────┘
                     ▼                     ▼
               ┌───────────┐         ┌───────────┐
               │conversation│         │session    │
               └───────────┘         └───────────┘
```

---

## 2. Table Definitions

### Table: `preference`
Stores system configuration overrides and operator profile data.
- **SQL DDL**:
  ```sql
  CREATE TABLE IF NOT EXISTS preference (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT UNIQUE NOT NULL,
      content TEXT,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  ```
- **Fields**:
  - `title`: Unique key identifying the setting (e.g. `display_name`, `first_launch_done`).
  - `content`: Text content or JSON-encoded payload.

### Table: `permission`
Manages hardware resources authorized status.
- **SQL DDL**:
  ```sql
  CREATE TABLE IF NOT EXISTS permission (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      resource TEXT UNIQUE NOT NULL,
      status TEXT CHECK(status IN ('allowed', 'denied')) NOT NULL,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  ```
- **Fields**:
  - `resource`: Hardware type (e.g. `microphone`, `speaker`, `camera`).
  - `status`: Allowed or denied.

### Table: `project`
Tracks developers' active workspace configurations.
- **SQL DDL**:
  ```sql
  CREATE TABLE IF NOT EXISTS project (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT UNIQUE NOT NULL,
      content TEXT,
      tags TEXT,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  ```
- **Fields**:
  - `title`: Name of the workspace (e.g. `ROWDY`).
  - `content`: JSON-encoded workspace settings (e.g. `directory`, `status`, `priority_task`).

### Table: `conversation`
Stores dialog history turns.
- **SQL DDL**:
  ```sql
  CREATE TABLE IF NOT EXISTS conversation (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      content TEXT NOT NULL,
      tags TEXT,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );
  ```
- **Fields**:
  - `title`: Description of the turn (e.g. `Interaction: open calculator`).
  - `content`: Dialogue exchange (e.g. `Query: ... \nResponse: ...`).

---

## 3. SQLite Integrity Constraints
- Every domain table contains `created_at` and `updated_at` timestamps for sync auditing.
- Table updates trigger database locks on write. The codebase serializes database access points to prevent locking issues.
- Database backups can be created simply by copying the `ultron_memory.db` file.
