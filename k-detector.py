#!/usr/bin/env python3
"""K-Memory Detector — Version autonome"""
import os, sys, json, subprocess, platform, shutil, re
from datetime import datetime, timezone

class KDetector:
    def __init__(self):
        self.env = {"timestamp": datetime.now(timezone.utc).isoformat(),"os":{},"llm":{},"agent":{},"tools":{},"storage":{},"host":{}}
    def detect_all(self):
        self.env["os"] = {"system":platform.system(),"release":platform.release(),"machine":platform.machine()}
        self.env["host"] = {"cpu_cores": os.cpu_count()}
        try:
            if os.name == 'posix':
                s = os.statvfs('/')
                self.env["storage"] = {"free_gb": round(s.f_frsize*s.f_bavail/(1024**3),1)}
        except: pass
        providers = {}
        for key, name in [("OPENAI_API_KEY","openai"),("ANTHROPIC_API_KEY","anthropic"),("DEEPSEEK_API_KEY","deepseek")]:
            if os.environ.get(key): providers[name] = {"detected":True}
        for env_file in [os.path.expanduser("~/.env"),os.path.expanduser("~/.hermes/.env"),".env"]:
            if os.path.exists(env_file):
                with open(env_file) as f: content = f.read()
                for key, name in [("OPENAI_API_KEY","openai"),("ANTHROPIC_API_KEY","anthropic"),("DEEPSEEK_API_KEY","deepseek")]:
                    if key in content and name not in providers: providers[name] = {"detected":True,"from_file":env_file}
        self.env["llm"]["providers"] = providers
        self.env["llm"]["count"] = len(providers)
        if shutil.which("ollama"): self.env["llm"]["ollama_local"] = True
        if shutil.which("nvidia-smi"):
            try: self.env["gpu"] = subprocess.run(["nvidia-smi","--query-gpu=name","--format=csv,noheader"],capture_output=True,text=True,timeout=5).stdout.strip()[:100]
            except: pass
        return self.env

if __name__ == "__main__":
    d = KDetector()
    env = d.detect_all()
    with open("k-memory-env.json","w") as f: json.dump(env,f,indent=2)
    print(f"Environnement: {env['os']['system']} | Providers: {env['llm']['count']} | Libre: {env.get('storage',{}).get('free_gb','?')} Go")
