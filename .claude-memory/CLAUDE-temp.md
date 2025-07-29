# CinchDB Frontend Build Plan

## Overview
Build a clean, functional NextJS frontend for CinchDB focused on:
1. **Project State Display** - Show databases, branches, tenants, tables
2. **Interactive Querying** - Execute SQL queries with formatted results
3. **Basic Schema Management** - View and create tables/columns

## Design Principles
- **Start Simple** - MVP features only, no pre-optimization
- **Clean UI** - Minimal, functional design using Tailwind CSS
- **TypeScript SDK Integration** - Use our newly built SDK
- **Real-time Feedback** - Show loading states, errors clearly

## Core Features (MVP)

### 1. Authentication
- API key input form
- Store in localStorage
- Show connection status

### 2. Project Overview Dashboard
- Current database/branch/tenant display
- Quick stats (table count, tenant count)
- Switch database/branch/tenant dropdowns

### 3. Schema Explorer (Left Sidebar)
- Tree view of:
  - Databases
    - Branches  
      - Tables
        - Columns
  - Tenants (separate section)

### 4. Query Interface (Main Panel)
- SQL editor with syntax highlighting (react-codemirror)
- Execute button with loading state
- Results table with:
  - Column headers
  - Sortable data
  - Row count
  - Export to CSV

### 5. Table Management
- View table structure
- Create new table form
- Add column to existing table

## Tech Stack
- **Framework**: NextJS 14 with App Router
- **UI Library**: Tailwind CSS + shadcn/ui components
- **State Management**: React hooks + Context API (keep it simple)
- **SDK**: @cinchdb/client (our TypeScript SDK)
- **Code Editor**: @uiw/react-codemirror
- **Icons**: Lucide React

## Component Structure
```
app/
├── layout.tsx          # Root layout with providers
├── page.tsx            # Landing/connection page  
├── dashboard/
│   ├── layout.tsx      # Dashboard layout with sidebar
│   └── page.tsx        # Main query interface
├── components/
│   ├── auth/
│   │   └── api-key-form.tsx
│   ├── layout/
│   │   ├── sidebar.tsx
│   │   └── header.tsx
│   ├── query/
│   │   ├── query-editor.tsx
│   │   └── results-table.tsx
│   └── schema/
│       ├── schema-tree.tsx
│       └── create-table-form.tsx
└── lib/
    ├── cinchdb-context.tsx  # Client context provider
    └── utils.ts

```

## Implementation Order
1. Setup NextJS with TypeScript and Tailwind
2. Create authentication flow
3. Build layout with sidebar
4. Implement schema explorer
5. Add query interface
6. Add table creation
7. Polish and test

## UI Mockup (ASCII)
```
┌─────────────────────────────────────────────────────────────┐
│ CinchDB           [main/mydb/main ▼]         [Disconnect]   │
├─────────────────┬───────────────────────────────────────────┤
│ SCHEMA          │ Query Editor                               │
│                 │ ┌─────────────────────────────────────┐   │
│ ▼ mydb          │ │ SELECT * FROM users                 │   │
│   ▼ main        │ │ WHERE active = 1                    │   │
│     ▶ users     │ │ LIMIT 10;                           │   │
│     ▶ products  │ └─────────────────────────────────────┘   │
│                 │                                             │
│ TENANTS         │ [Execute] [Clear]                Export ▼  │
│ • main          │                                             │
│ • customer_a    │ Results (3 rows)                           │
│                 │ ┌─────┬────────┬───────────┬──────────┐   │
│                 │ │ id  │ name   │ email     │ active   │   │
│                 │ ├─────┼────────┼───────────┼──────────┤   │
│                 │ │ 1   │ Alice  │ alice@... │ 1        │   │
│                 │ │ 2   │ Bob    │ bob@...   │ 1        │   │
│                 │ │ 3   │ Carol  │ carol@... │ 1        │   │
│                 │ └─────┴────────┴───────────┴──────────┘   │
└─────────────────┴───────────────────────────────────────────┘
```

## State Management
```typescript
interface AppState {
  client: CinchDBClient | null;
  connected: boolean;
  currentDatabase: string;
  currentBranch: string;
  currentTenant: string;
  databases: Database[];
  branches: Branch[];
  tenants: Tenant[];
  tables: TableInfo[];
}
```

## Error Handling
- Toast notifications for errors
- Inline validation for forms
- Connection retry logic
- Clear error messages from API

## Future Enhancements (Not MVP)
- Visual query builder
- Branch merging UI
- Data editing
- Change history viewer
- Multi-tenant comparison
- Schema diff visualization