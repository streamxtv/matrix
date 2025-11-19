import os
import re
import shutil
import hashlib
import zipfile
import time
import sys

# ==========================================
# CONFIGURAÇÕES
# ==========================================
NOME_REPO_PRINCIPAL = "repository.streamxtv.matrix"
# ==========================================

# CORES
class Cor:
    VERDE = '\033[92m'
    AMARELO = '\033[93m'
    VERMELHO = '\033[91m'
    AZUL = '\033[94m'
    CIANO = '\033[96m'
    RESET = '\033[0m'

def limpar_tela():
    os.system('cls' if os.name == 'nt' else 'clear')

def banner():
    print(Cor.VERDE)
    print(r"""
  ____  _                              __   __ _______      __
 / ___|| |_ _ __ ___  __ _ _ __ ___    \ \ / /|_   _\ \    / /
 \___ \| __| '__/ _ \/ _` | '_ ` _ \    \ V /   | |  \ \  / / 
  ___) | |_| | |  __/ (_| | | | | | |   /   \   | |   \ \/ /  
 |____/ \__|_|  \___|\__,_|_| |_| |_|  /_/ \_\  |_|    \__/   
    """ + Cor.RESET)
    print(f"{Cor.CIANO}      :: GOD MODE V7 - GERENCIADOR TOTAL :: {Cor.RESET}\n")

def ler_xml_addon(pasta):
    """Lê o ID e a VERSÃO de qualquer addon.xml"""
    caminho = os.path.join(pasta, "addon.xml")
    if not os.path.exists(caminho): return None, None

    with open(caminho, "r", encoding="utf-8") as f:
        conteudo = f.read()

    # Pega ID e Versão
    match_id = re.search(r'<addon[^>]+id="([^"]+)"', conteudo)
    match_ver = re.search(r'<addon[^>]+version="([^"]+)"', conteudo)

    if match_id and match_ver:
        return match_id.group(1), match_ver.group(1)
    return None, None

def zipar_addon(pasta, id_addon, versao):
    """Cria o ZIP de qualquer addon na estrutura correta"""
    nome_zip = f"{id_addon}-{versao}.zip"
    caminho_zip = os.path.join(pasta, nome_zip)
    
    # Se o ZIP já existe, não precisa refazer (ganha tempo), a menos que seja o Repo principal
    if os.path.exists(caminho_zip) and pasta != NOME_REPO_PRINCIPAL:
        print(f"   📦 {id_addon} v{versao} já está zipado. Pulando...")
        return

    print(f"   ⚙️  Compactando: {Cor.AMARELO}{id_addon} v{versao}{Cor.RESET}...")
    
    with zipfile.ZipFile(caminho_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(pasta):
            for file in files:
                if file.endswith(".zip") or file.startswith("."): continue
                caminho_abs = os.path.join(root, file)
                # Cria estrutura pasta/arquivo dentro do zip
                caminho_rel = os.path.relpath(caminho_abs, start=os.path.dirname(pasta))
                zf.write(caminho_abs, caminho_rel)

def atualizar_repo_principal():
    """Lógica exclusiva para atualizar a versão do Repo Principal"""
    print(f"\n{Cor.AZUL}>>> VERIFICANDO REPOSITÓRIO PRINCIPAL <<<{Cor.RESET}")
    id_repo, ver_atual = ler_xml_addon(NOME_REPO_PRINCIPAL)
    
    if not id_repo:
        print("❌ Erro no Repo Principal.")
        return

    print(f"📂 Repositório: {id_repo}")
    print(f"🔢 Versão Atual: {Cor.AMARELO}{ver_atual}{Cor.RESET}")
    
    nova = input(f"👉 Digite nova versão (ou ENTER para manter {ver_atual}): ").strip()
    
    if nova and nova != ver_atual:
        # Atualiza XML
        xml_file = os.path.join(NOME_REPO_PRINCIPAL, "addon.xml")
        with open(xml_file, "r", encoding="utf-8") as f: content = f.read()
        
        # Corrige Header se precisar
        if '<?xml' in content:
            content = re.sub(r'<\?xml[^>]+\?>', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>', content, count=1)
            
        # Troca versão
        content = re.sub(f'version="{ver_atual}"', f'version="{nova}"', content, count=1)
        
        with open(xml_file, "w", encoding="utf-8") as f: f.write(content)
        print(f"✅ Versão alterada para {nova}")
        
        # Remove zip antigo do repo
        for f in os.listdir(NOME_REPO_PRINCIPAL):
            if f.endswith(".zip"): os.remove(os.path.join(NOME_REPO_PRINCIPAL, f))
            
        # O zip novo será criado no loop geral abaixo
        
        # Atualiza o zip da raiz (site)
        zip_interno = os.path.join(NOME_REPO_PRINCIPAL, f"{NOME_REPO_PRINCIPAL}-{nova}.zip")
        # Vamos esperar o loop geral criar o zip primeiro, depois copiamos no final
    else:
        print("   Mantendo versão atual.")

def processar_tudo():
    print(f"\n{Cor.AZUL}>>> PROCESSANDO TODOS OS ADDONS <<<{Cor.RESET}")
    
    xml_global = "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n<addons>\n"
    count = 0
    
    # Varre todas as pastas
    for item in os.listdir("."):
        if os.path.isdir(item) and not item.startswith(".") and item != "zips":
            # É uma pasta. Tem addon.xml?
            id_addon, versao = ler_xml_addon(item)
            
            if id_addon and versao:
                # É um addon válido!
                zipar_addon(item, id_addon, versao)
                
                # Adiciona ao XML Global
                path_xml = os.path.join(item, "addon.xml")
                with open(path_xml, "r", encoding="utf-8") as f:
                    lines = f.read().splitlines()
                    for line in lines:
                        if "<?xml" in line: continue
                        xml_global += line.rstrip() + "\n"
                    xml_global += "\n"
                count += 1
    
    xml_global += "</addons>\n"
    
    # Salva XML e MD5
    with open("addons.xml", "w", encoding="utf-8") as f: f.write(xml_global)
    md5 = hashlib.md5(xml_global.encode("utf-8")).hexdigest()
    with open("addons.xml.md5", "w", encoding="utf-8") as f: f.write(md5)
    
    # Atualiza o ZIP da Raiz (Para o Site) se o repo tiver sido atualizado
    id_repo, ver_repo = ler_xml_addon(NOME_REPO_PRINCIPAL)
    zip_repo_interno = os.path.join(NOME_REPO_PRINCIPAL, f"{NOME_REPO_PRINCIPAL}-{ver_repo}.zip")
    zip_repo_raiz = f"{NOME_REPO_PRINCIPAL}.zip"
    
    if os.path.exists(zip_repo_interno):
        if os.path.exists(zip_repo_raiz): os.remove(zip_repo_raiz)
        shutil.copy(zip_repo_interno, zip_repo_raiz)
        print(f"\n✅ ZIP do Site (Raiz) atualizado para v{ver_repo}")

    print(f"\n{Cor.VERDE}✨ SUCESSO! {count} Addons processados e listados.{Cor.RESET}")

# --- MAIN ---
if __name__ == "__main__":
    limpar_tela()
    banner()
    
    # 1. Pergunta se quer atualizar o Repo Principal
    atualizar_repo_principal()
    
    # 2. Varre tudo, zipa tudo e gera a lista
    processar_tudo()
    
    print(f"\n{Cor.AZUL}========================================{Cor.RESET}")
    print(f"   PODE SUBIR TUDO PRO GITHUB!")
    print(f"{Cor.AZUL}========================================{Cor.RESET}")
    input("\n[ENTER] para sair...")