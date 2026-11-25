import os, site, subprocess, sys

BASE = "/home/container"
TMP = os.path.join(BASE, "tmp")
os.makedirs(TMP, exist_ok=True)
os.environ["TMPDIR"] = TMP

ver = f"python{sys.version_info.major}.{sys.version_info.minor}"
site_pkgs = os.path.join(BASE, ".local", "lib", ver, "site-packages")
if os.path.isdir(site_pkgs):
    site.addsitedir(site_pkgs)

try:
    from streamlit.web import cli as stcli
except ImportError:
    env = dict(os.environ, TMPDIR=TMP)
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "--prefix", ".local",
         "streamlit==1.46.0", "duckdb==1.3.1", "pandas==2.3.0"],
        env=env, cwd=BASE,
    )
    if os.path.isdir(site_pkgs):
        site.addsitedir(site_pkgs)
    from streamlit.web import cli as stcli

port = os.environ.get("SERVER_PORT", "8080")
sys.argv = [
    "streamlit", "run", "main.py",
    "--server.port", str(port),
    "--server.address", "0.0.0.0",
    "--server.headless", "true",
]
sys.exit(stcli.main())

