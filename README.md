# Ignition Enterprise

An Enterprise-grade Autonomous Multi-Agent AI Code Review Platform built on Next.js 15 App Router.

## Architecture

Ignition uses a powerful multi-agent workflow (LangGraph) backed by a FastAPI service to autonomously review pull requests, detect architectural regressions, and generate auto-fixes.

The Frontend is built using:
- **Framework**: Next.js 15 (App Router, Server Components by default)
- **Styling**: Tailwind CSS v4, `shadcn/ui` based components
- **Animations**: Framer Motion
- **Charts**: Recharts
- **Icons**: Lucide React
- **Data Fetching**: Native `fetch` with robust error interception
- **Real-time Data**: HTML5 `EventSource` (Server-Sent Events)

## Project Structure

- `app/`: Next.js 15 App Router pages.
  - `dashboard/`: Main overview, recent reviews.
  - `reviews/`: Full review list and detailed timeline view.
  - `hitl/`: Human-in-the-Loop queue for critical approval.
  - `ledger/`: Historical metrics and Recharts ACS trends.
- `components/`: Modular, typed React components (Client & Server).
- `hooks/`: Custom React hooks (`use-toast`, `use-review-stream`).
- `lib/`: Utilities, Types, and the core API Client singleton.

## API & SSE Integration

The frontend uses an enterprise `ApiClient` located in `lib/api-client.ts`. It wraps the native fetch API to provide strict TypeScript models and unified error handling for the Python backend.

Real-time execution of the LangGraph AI is achieved using Server-Sent Events (SSE) located in `hooks/use-review-stream.ts`. It listens for discrete agent progression events (`agent.started`, `agent.completed`, etc.) and automatically reconnects upon failure.

## Development

```bash
# Install dependencies
npm install

# Start the development server
npm run dev
```

Navigate to `http://localhost:3000` to view the application.

## Production Build

```bash
# Typecheck and build the production bundle
npm run build

# Start the optimized production server
npm run start
```
