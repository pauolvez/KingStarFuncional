import subprocess
import os

def start_flaresolverr():
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'flaresolverr', 'flaresolverr.exe'))
    return subprocess.Popen([path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)