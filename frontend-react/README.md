# AI Meeting Minutes Assistant Frontend

This is the maintained frontend codebase for the project.

## Stack

- React
- Vite
- Plain CSS
- Fetch-based API integration

## Run Locally

```bash
cd frontend-react
npm install
npm run dev
```

Then open the Vite dev server URL shown in the terminal, typically:

- `http://localhost:5173`

## Environment

Copy `.env.example` to `.env` if you want to override the backend URL:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Project Structure

- `src/components/`: visual building blocks
- `src/hooks/`: stateful workflow logic
- `src/services/`: backend API access
- `src/utils.js`: shared formatting helpers

## Notes

- The old `frontend/` directory is deprecated and should not be used for ongoing development.
- Backend APIs are expected to be available from the FastAPI service in `backend/`.
