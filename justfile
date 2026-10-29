# Comment out if not Windows
set shell := ["powershell.exe", "-NoLogo", "-Command"]

# Run app
run:
    uv run uvicorn app.main:app --reload --port 8000

# Run UI
run-ui:
    uv run chainlit run ui_chainlit/app.py -w --port 8081

color:
    color 0A
    @echo Texto verde

color2:
    color 0A
    @echo Texto verde