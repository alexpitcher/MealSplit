
  # MealSplit Web App

  This is a code bundle for MealSplit Web App. The original project is available at https://www.figma.com/design/xgln7KEU4V3N00e3dkRbjO/MealSplit-Web-App.

  ## Running the code

  Option A: via Docker Compose (recommended)

  - From the repository root:
    ```bash
    docker compose up web app postgres redis
    ```
  - Frontend: http://localhost:5173
  - API: http://localhost:8000 (CORS allows http://localhost:5173)

  Option B: locally with Node

  - Install dependencies:
    ```bash
    npm install
    ```
  - Start dev server:
    ```bash
    npm run dev -- --host 0.0.0.0 --port 5173
    ```
  - The frontend expects the API at `http://localhost:8000/api/v1`.
  
