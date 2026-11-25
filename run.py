import os, sys
from streamlit.web import cli as stcli

port = os.environ.get("SERVER_PORT", "8080")
sys.argv = [
    "streamlit", "run", "main.py",
    "--server.port", str(port),
    "--server.address", "0.0.0.0",
    "--server.headless", "true",
]
sys.exit(stcli.main())
