import requests
import re
import time
import json
import argparse
from bs4 import BeautifulSoup, Comment
from urllib.parse import urlparse, urljoin
from collections import deque

HEADERS = {
    "User-Agent": "ReconCLI/1.0"
}

REGEX = {
    "EMAIL": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
    "TELEFONE": r"\(?\d{2}\)?\s?9?\d{4}-?\d{4}",
    "ENDPOINT": r"(\/api\/[a-zA-Z0-9_\/-]+)",
    "JWT": r"eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+",
    "API_KEY": r"(?i)(api_key|apikey|token)['\"]?\s*[:=]\s*['\"][a-zA-Z0-9_-]{16,}"
}

def crawler(args):
    alvo = args.url
    dominio = urlparse(alvo).netloc
    fila = deque([(alvo, 0)])
    visitados = set()

    resultado = {
        "target": alvo,
        "emails": set(),
        "telefones": set(),
        "endpoints": set(),
        "tokens": set(),
        "comentarios": set(),
        "subdominios": set(),
        "urls_visitadas": 0
    }

    while fila:
        url, depth = fila.popleft()

        if url in visitados or depth > args.depth:
            continue

        visitados.add(url)

        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if "text/html" not in r.headers.get("Content-Type", ""):
                continue

            print(f"[+] {url}")
            soup = BeautifulSoup(r.text, "html.parser")
            texto = soup.get_text(" ")

            # Regex scan
            for nome, rgx in REGEX.items():
                for achado in re.findall(rgx, texto):
                    if nome == "EMAIL":
                        resultado["emails"].add(achado)
                    elif nome == "TELEFONE":
                        resultado["telefones"].add(achado)
                    elif nome == "ENDPOINT":
                        resultado["endpoints"].add(achado)
                    else:
                        resultado["tokens"].add(str(achado))

            # Comentários HTML
            for c in soup.find_all(string=lambda t: isinstance(t, Comment)):
                if len(c.strip()) > 5:
                    resultado["comentarios"].add(c.strip())

            # Links
            for tag in soup.find_all(["a", "script"], src=True) + soup.find_all("a", href=True):
                link = tag.get("href") or tag.get("src")
                url_full = urljoin(url, link)
                parsed = urlparse(url_full)

                if not parsed.scheme.startswith("http"):
                    continue

                if parsed.netloc.endswith(dominio) and parsed.netloc != dominio:
                    resultado["subdominios"].add(parsed.netloc)

                if dominio in parsed.netloc:
                    fila.append((url_full, depth + 1))

            time.sleep(args.delay)

        except Exception as e:
            if not args.silent:
                print(f"[!] Erro: {e}")

    resultado["urls_visitadas"] = len(visitados)

    salvar_output(resultado, args.output)

def salvar_output(resultado, arquivo):
    serializavel = {k: list(v) if isinstance(v, set) else v for k, v in resultado.items()}
    with open(arquivo, "w") as f:
        json.dump(serializavel, f, indent=2)

    print(f"\n[✓] Resultado salvo em: {arquivo}")

def main():
    parser = argparse.ArgumentParser(description="Recon CLI - Web Recon Tool")
    parser.add_argument("-u", "--url", required=True, help="URL alvo")
    parser.add_argument("-d", "--depth", type=int, default=2, help="Profundidade do crawler")
    parser.add_argument("--delay", type=int, default=1, help="Delay entre requisições")
    parser.add_argument("--silent", action="store_true", help="Modo silencioso")
    parser.add_argument("-o", "--output", default="output/resultado.json", help="Arquivo de saída")

    args = parser.parse_args()
    crawler(args)

if __name__ == "__main__":
    main()
