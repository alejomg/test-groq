# Test Groq

This project is a Python-based application built using the FastAPI web framework and Uvicorn for ASGI. Main purpose is testing Groq capabilities. 

## After Cloning

You need to do a couple of tasks in order to locally run or develop the application.

### Set up the Virtual Environment

> Python 3.12.x should be already installed in the OS

This project uses UV for virtual environment and dependency management.

1. Install UV, if already installed skip.

**macOS / Linux:**
```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**
```powershell
powershell -Command "irm https://astral.sh/uv/install.ps1 | iex"
```

2. Change to the `application directory`
```bash
  cd /path/to/test-groq
```

3. Create and activate the virtual environment with dependencies
```bash
  uv sync --dev
```

After these steps, you should have all dependencies needed to develop and locally run test-groq.

> Notice: From now on, you should always install new dependencies using `uv add [PACKAGE_NAME]` and for development dependencies use `uv add --dev [PACKAGE_NAME]`. The *uv.lock* and *pyproject.toml* files will be automatically updated.
 
4. Create a `.env` file and update it with your actual environment variables
```bash
  cp .env.sample .env
```

### Running the Application

This application is using Uvicorn ASGI as Web server.
 
1. Change to the `application directory`
```bash
  cd /path/to/test-groq
```

2. Start the application using UV:
```bash
  uv run uvicorn app.main:app --reload
```

Now the application should be accessible at `http://localhost:8000`. The Swagger UI (web interface) can be accessed at `http://localhost:8000/docs`.