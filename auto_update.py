# -*- coding: utf-8 -*-
import os
import re
import shutil
import hashlib
import zipfile
import sys

# ==========================================
# CONFIGURAÇÕES DO PROJETO
# ==========================================
NOME_REPO_PRINCIPAL = "repository.streamxtv.matrix"
PASTA_ZIPS = "zips"
CODINOME_KODI = "matrix" 
# ==========================================

CAMINHO_FINAL = os.path.join(PASTA_ZIPS, CODINOME_KODI)

class Cor:
    VERDE = '\033[92m'
    AMARELO = '\033[93m'
    VERMELHO = '\033[91m'
    AZUL = '\033[94m'
    CIANO = '\033[96m'
    RESET = '\033[0m'

def limpar_tela():
    os.system('cls' if os.name == 'nt' else 'clear')

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', s)]

def banner():
    print(Cor.VERDE)
    print(r"""
  _____  ______ _____   ____  
 |  __ \|  ____|  __ \ / __ \ 
 | |__) | |__  | |__) | |  | |
 |  _  /|  __| |  ___/| |  | |
 | | \ \| |____| |    | |__| |
 |_|  \_\______|_|     \____/ 
    """ + Cor.RESET)
    
    print(f"{Cor.CIANO}      :: SISTEMA DE GESTÃO AUTOMATIZADA :: {Cor.RESET}")
    print(f"{Cor.AMARELO}          Desenvolvido por bl4444ck {Cor.RESET}\n")

def encontrar_arquivo_ignorando_cx(pasta, nome_arquivo):
    if not os.path.exists(pasta): return None
    for f in os.listdir(pasta):
        if f.lower() == nome_arquivo.lower():
            return os.path.join(pasta, f)
    return None

def ler_xml_do_arquivo(caminho_arquivo):
    if not os.path.exists(caminho_arquivo): return None, None, None
    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        conteudo = f.read()
    match_id = re.search(r'<addon[^>]+id=["\']([^"\']+)["\']', conteudo)
    match_ver = re.search(r'<addon[^>]+version=["\']([^"\']+)["\']', conteudo)
    if match_id and match_ver:
        return match_id.group(1), match_ver.group(1), conteudo
    return None, None, None

def ler_xml_de_zip(caminho_zip):
    try:
        with zipfile.ZipFile(caminho_zip, 'r') as z:
            arquivos = z.namelist()
            xml_files = [f for f in arquivos if f.endswith('addon.xml') and '/' in f]
            if not xml_files: return None
            with z.open(xml_files[0]) as f:
                return f.read().decode('utf-8')
    except:
        return None

def corrigir_xml_do_repo_para_matrix(pasta_repo, id_repo):
    xml_file = os.path.join(pasta_repo, "addon.xml")
    if not os.path.exists(xml_file): return

    with open(xml_file, "r", encoding="utf-8") as f: content = f.read()
    mudou = False
    
    # Ajusta datadir para .../zips/matrix/
    regex_datadir = r'(<datadir zip="true">)(.*?)(</datadir>)'
    match = re.search(regex_datadir, content)
    if match:
        url_atual = match.group(2)
        if not url_atual.rstrip('/').endswith(CODINOME_KODI):
            nova_url = url_atual.rstrip('/') + f"/{CODINOME_KODI}/"
            content = content.replace(url_atual, nova_url)
            mudou = True
            print(f"    🔧 Corrigindo 'datadir' para /{CODINOME_KODI}/")

    # Ajusta info/checksum para .../zips/matrix/addons.xml
    regex_info = r'(<(info|checksum).*?>)(.*?)(</(info|checksum)>)'
    for match in re.finditer(regex_info, content):
        url_atual = match.group(3)
        if f"/{CODINOME_KODI}/addons.xml" not in url_atual:
            partes = url_atual.rsplit('/', 1)
            if len(partes) == 2:
                nova_url = f"{partes[0]}/{CODINOME_KODI}/{partes[1]}"
                content = content.replace(url_atual, nova_url)
                mudou = True
                print(f"    🔧 Corrigindo '{match.group(2)}' para pasta /{CODINOME_KODI}/")

    if mudou:
        with open(xml_file, "w", encoding="utf-8") as f: f.write(content)

def atualizar_versao_xml(pasta, id_addon, versao_atual):
    print(f"\n{Cor.AZUL}>>> DETECTADO:{Cor.RESET} {id_addon}")
    if id_addon == NOME_REPO_PRINCIPAL:
        corrigir_xml_do_repo_para_matrix(pasta, id_addon)

    print(f"    Versão no arquivo: {Cor.AMARELO}{versao_atual}{Cor.RESET}")
    
    # Apenas espera o ENTER.
    input(f"    {Cor.VERDE}[ENTER] para confirmar e processar...{Cor.RESET}")
    
    return versao_atual

def zipar_addon(pasta_origem, id_addon, versao):
    destino_dir = os.path.join(CAMINHO_FINAL, id_addon)
    if not os.path.exists(destino_dir): os.makedirs(destino_dir)

    nome_zip = f"{id_addon}-{versao}.zip"
    caminho_zip = os.path.join(destino_dir, nome_zip)
    
    # --- FAXINA DE ZIPS ANTIGOS ---
    # Antes de criar o novo, apaga qualquer zip que tenha nome diferente
    for arquivo in os.listdir(destino_dir):
        if arquivo.endswith(".zip") and arquivo != nome_zip:
            try:
                os.remove(os.path.join(destino_dir, arquivo))
                print(f"    🗑️  ZIP antigo removido: {Cor.VERMELHO}{arquivo}{Cor.RESET}")
            except:
                pass
    # ------------------------------

    for asset in ['icon.png', 'fanart.jpg', 'addon.xml']:
        if asset.endswith('xml'):
            src = os.path.join(pasta_origem, asset)
            if os.path.exists(src): shutil.copy(src, os.path.join(destino_dir, asset))
        else:
            arquivo_real = encontrar_arquivo_ignorando_cx(pasta_origem, asset)
            if arquivo_real:
                shutil.copy(arquivo_real, os.path.join(destino_dir, asset))

    if os.path.exists(caminho_zip): os.remove(caminho_zip)
    print(f"    📦 ZIP criado em: {Cor.AMARELO}{PASTA_ZIPS}/{CODINOME_KODI}/{id_addon}/{nome_zip}{Cor.RESET}")
    
    exclude_dirs = ['.git', '.github', PASTA_ZIPS, '__pycache__', '.idea']
    with zipfile.ZipFile(caminho_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(pasta_origem):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for file in files:
                if file.endswith(".zip") or file.endswith(".pyc") or file.startswith("."): continue
                abs_p = os.path.join(root, file)
                rel_p = os.path.relpath(abs_p, start=os.path.dirname(pasta_origem))
                zf.write(abs_p, rel_p)

def processar_tudo():
    if not os.path.exists(CAMINHO_FINAL): os.makedirs(CAMINHO_FINAL)
    
    catalogo_addons = {}
    pastas_raiz_processadas = []
    versao_repo_atualizada = None

    # 1. Processa Raiz
    print(f"🔍 Verificando pastas na raiz...")
    for item in os.listdir("."):
        if os.path.isdir(item) and not item.startswith(".") and item != PASTA_ZIPS:
            id_addon, versao, _ = ler_xml_do_arquivo(os.path.join(item, "addon.xml"))
            if id_addon:
                versao_final = atualizar_versao_xml(item, id_addon, versao)
                if id_addon == NOME_REPO_PRINCIPAL: versao_repo_atualizada = versao_final
                zipar_addon(item, id_addon, versao_final)
                _, _, xml_atualizado = ler_xml_do_arquivo(os.path.join(item, "addon.xml"))
                catalogo_addons[id_addon] = xml_atualizado
                pastas_raiz_processadas.append(item)

    # 2. Processa Zips Antigos
    print(f"\n🔍 Recuperando addons antigos em '{CAMINHO_FINAL}'...")
    if os.path.exists(CAMINHO_FINAL):
        for id_pasta in os.listdir(CAMINHO_FINAL):
            caminho_pasta_zip = os.path.join(CAMINHO_FINAL, id_pasta)
            if os.path.isdir(caminho_pasta_zip) and id_pasta not in catalogo_addons:
                xml_solto = os.path.join(caminho_pasta_zip, "addon.xml")
                if os.path.exists(xml_solto):
                    _, _, conteudo = ler_xml_do_arquivo(xml_solto)
                    if conteudo:
                        catalogo_addons[id_pasta] = conteudo
                        print(f"   Recuperado (XML): {Cor.VERDE}{id_pasta}{Cor.RESET}")
                        if id_pasta == NOME_REPO_PRINCIPAL:
                            mv = re.search(r'version=["\']([^"\']+)["\']', conteudo)
                            if mv: versao_repo_atualizada = mv.group(1)
                        continue
                
                zips = [f for f in os.listdir(caminho_pasta_zip) if f.endswith(".zip")]
                if zips:
                    zips.sort(key=natural_sort_key)
                    conteudo_zip = ler_xml_de_zip(os.path.join(caminho_pasta_zip, zips[-1]))
                    if conteudo_zip:
                        catalogo_addons[id_pasta] = conteudo_zip
                        print(f"   Recuperado (ZIP): {Cor.VERDE}{id_pasta}{Cor.RESET}")
                        if id_pasta == NOME_REPO_PRINCIPAL:
                            mv = re.search(r'version=["\']([^"\']+)["\']', conteudo_zip)
                            if mv: versao_repo_atualizada = mv.group(1)

    # 3. Gera XML Master
    xml_master = "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n<addons>\n"
    for _, conteudo in catalogo_addons.items():
        lines = conteudo.splitlines()
        for line in lines:
            if "<?xml" in line: continue
            xml_master += line.rstrip() + "\n"
        xml_master += "\n"
    xml_master += "</addons>\n"

    # Grava em zips/matrix/
    with open(os.path.join(CAMINHO_FINAL, "addons.xml"), "w", encoding="utf-8") as f: f.write(xml_master)
    md5 = hashlib.md5(xml_master.encode("utf-8")).hexdigest()
    with open(os.path.join(CAMINHO_FINAL, "addons.xml.md5"), "w", encoding="utf-8") as f: f.write(md5)
    print(f"\n✅ 'addons.xml' gerado em: {CAMINHO_FINAL} (Matrix)")

    # Grava NA RAIZ TAMBÉM
    with open("addons.xml", "w", encoding="utf-8") as f: f.write(xml_master)
    with open("addons.xml.md5", "w", encoding="utf-8") as f: f.write(md5)
    print(f"✅ 'addons.xml' gerado na RAIZ (Compatibilidade)")

    # 4. Atualiza ZIP na Raiz
    if versao_repo_atualizada:
        path_repo_zip = os.path.join(CAMINHO_FINAL, NOME_REPO_PRINCIPAL, f"{NOME_REPO_PRINCIPAL}-{versao_repo_atualizada}.zip")
        if os.path.exists(path_repo_zip):
            shutil.copy(path_repo_zip, f"{NOME_REPO_PRINCIPAL}.zip")
            print(f"✅ Instalador '{NOME_REPO_PRINCIPAL}.zip' atualizado na raiz.")

    # 5. Faxina
    if pastas_raiz_processadas:
        print(f"\n{Cor.VERMELHO}" + "="*50)
        print(f"⚠️  FASE DE LIMPEZA DA RAIZ ⚠️")
        print("="*50 + f"{Cor.RESET}")
        print(f"Pastas processadas: {pastas_raiz_processadas}")
        resp = input(f"\n{Cor.AMARELO}>> Apagar pastas da raiz? (S/N): {Cor.RESET}").lower()
        if resp == 's':
            for p in pastas_raiz_processadas:
                try: shutil.rmtree(p); print(f"🗑️  Apagado: {p}")
                except: pass
            print(f"\n{Cor.VERDE}✨ RAIZ LIMPA!{Cor.RESET}")
        else:
            print(f"\n🚫 Pastas mantidas.")

if __name__ == "__main__":
    limpar_tela()
    banner()
    processar_tudo()
    print(f"\n{Cor.AZUL}" + "="*50)
    print(f"   PODE SUBIR TUDO PRO GITHUB! 🚀")
    print("="*50 + f"{Cor.RESET}")
    input("\n[ENTER] para sair...")