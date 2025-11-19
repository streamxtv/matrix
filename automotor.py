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
NOME_REPO = "repository.streamxtv.matrix"
ARQUIVO_XML = os.path.join(NOME_REPO, "addon.xml")

# CORES PARA O TERMINAL
class Cor:
    VERDE = '\033[92m'
    AMARELO = '\033[93m'
    VERMELHO = '\033[91m'
    AZUL = '\033[94m'
    NEGRITO = '\033[1m'
    RESET = '\033[0m'

def limpar_tela():
    os.system('cls' if os.name == 'nt' else 'clear')

def banner():
    print(Cor.VERDE + Cor.NEGRITO)
    print(r"""
  ____  _                              __   __ _______      __
 / ___|| |_ _ __ ___  __ _ _ __ ___    \ \ / /|_   _\ \    / /
 \___ \| __| '__/ _ \/ _` | '_ ` _ \    \ V /   | |  \ \  / / 
  ___) | |_| | |  __/ (_| | | | | | |   /   \   | |   \ \/ /  
 |____/ \__|_|  \___|\__,_|_| |_| |_|  /_/ \_\  |_|    \__/   
    """ + Cor.RESET)
    print(f"{Cor.AZUL}  :: AUTOMATOR MATRIX VERSION :: {Cor.RESET}\n")

def barra_progresso(texto, tempo=0.5):
    """Cria uma animação de barra de carregamento estilosa"""
    print(f"{Cor.AMARELO}➤ {texto}{Cor.RESET}")
    toolbar_width = 40
    sys.stdout.write("[%s]" % (" " * toolbar_width))
    sys.stdout.flush()
    sys.stdout.write("\b" * (toolbar_width+1))

    for i in range(toolbar_width):
        time.sleep(tempo/toolbar_width) # Ajusta velocidade
        sys.stdout.write("█")
        sys.stdout.flush()
    sys.stdout.write("]\n")

def ler_versao_addon():
    if not os.path.exists(ARQUIVO_XML):
        print(f"{Cor.VERMELHO}❌ ERRO CRÍTICO: Arquivo não encontrado: {ARQUIVO_XML}{Cor.RESET}")
        return None

    with open(ARQUIVO_XML, "r", encoding="utf-8") as f:
        conteudo = f.read()

    padrao = re.compile(r'(<addon[^>]+version=")([^"]+)(")', re.DOTALL)
    match = padrao.search(conteudo)

    if match:
        return match.group(2)
    else:
        print(f"{Cor.VERMELHO}❌ ERRO: Não consegui ler a versão do Addon.{Cor.RESET}")
        return None

def corrigir_e_atualizar_xml(nova_versao):
    barra_progresso("Analisando e corrigindo XML...")
    
    with open(ARQUIVO_XML, "r", encoding="utf-8") as f:
        conteudo = f.read()

    # Correção do Header 1.0
    if '<?xml' in conteudo:
        conteudo = re.sub(r'<\?xml[^>]+\?>', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>', conteudo, count=1)

    # Atualização da Versão
    padrao_addon = re.compile(r'(<addon[^>]+version=")([^"]+)(")', re.DOTALL)
    novo_conteudo = padrao_addon.sub(f'\\g<1>{nova_versao}\\g<3>', conteudo, count=1)

    with open(ARQUIVO_XML, "w", encoding="utf-8") as f:
        f.write(novo_conteudo)
    
    print(f"{Cor.VERDE}✅ XML Atualizado e Salvo!{Cor.RESET}")
    return True

def gerar_zips(versao):
    barra_progresso(f"Compactando arquivos para v{versao}...", tempo=1.0)
    
    # Remove antigos
    for item in os.listdir(NOME_REPO):
        if item.endswith(".zip"):
            os.remove(os.path.join(NOME_REPO, item))

    zip_interno = os.path.join(NOME_REPO, f"{NOME_REPO}-{versao}.zip")
    zip_externo = f"{NOME_REPO}.zip"

    with zipfile.ZipFile(zip_interno, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(NOME_REPO):
            for file in files:
                if file.endswith(".zip") or file.startswith("."): continue
                caminho_real = os.path.join(root, file)
                caminho_zip = os.path.join(NOME_REPO, file) 
                zf.write(caminho_real, caminho_zip)
    
    print(f"{Cor.VERDE}✅ ZIP Interno (Update) criado.{Cor.RESET}")

    if os.path.exists(zip_externo): os.remove(zip_externo)
    shutil.copy(zip_interno, zip_externo)
    print(f"{Cor.VERDE}✅ ZIP Externo (Site) criado.{Cor.RESET}")

def gerar_lista_global():
    barra_progresso("Gerando Hash MD5 e Lista Global...", tempo=0.8)
    
    if os.path.exists("addons.xml"): os.remove("addons.xml")
    if os.path.exists("addons.xml.md5"): os.remove("addons.xml.md5")

    xml_final = "<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n<addons>\n"
    count = 0
    
    for item in os.listdir("."):
        if os.path.isdir(item) and not item.startswith(".") and item != "zips":
            path_xml = os.path.join(item, "addon.xml")
            if os.path.exists(path_xml):
                try:
                    with open(path_xml, "r", encoding="utf-8") as f:
                        lines = f.read().splitlines()
                        for line in lines:
                            if "<?xml" in line: continue
                            xml_final += line.rstrip() + "\n"
                        xml_final += "\n"
                        count += 1
                except: pass

    xml_final += "</addons>\n"

    with open("addons.xml", "w", encoding="utf-8") as f:
        f.write(xml_final)
    
    md5 = hashlib.md5(xml_final.encode("utf-8")).hexdigest()
    with open("addons.xml.md5", "w", encoding="utf-8") as f:
        f.write(md5)
        
    print(f"{Cor.VERDE}✅ Lista Global compilada ({count} addons).{Cor.RESET}")

# --- MAIN ---
if __name__ == "__main__":
    limpar_tela()
    banner()

    versao_atual = ler_versao_addon()

    if versao_atual:
        print(f"📦 Versão Atual: {Cor.AMARELO}[ {versao_atual} ]{Cor.RESET}")
        print(f"{Cor.AZUL}" + "-" * 40 + f"{Cor.RESET}")
        
        nova_versao = input(f"{Cor.NEGRITO}👉 Digite a NOVA versão (ex: 2.5.7): {Cor.RESET}").strip()

        if nova_versao:
            if nova_versao == versao_atual:
                print(f"\n{Cor.AMARELO}⚠️  A versão é a mesma. Tem certeza?{Cor.RESET}")
                if input("   [Enter] para continuar ou [S] para sair: ").lower() == 's':
                    exit()
            
            print("\n")
            corrigir_e_atualizar_xml(nova_versao)
            gerar_zips(nova_versao)
            gerar_lista_global()
            
            print(f"\n{Cor.AZUL}" + "=" * 40 + f"{Cor.RESET}")
            print(f"{Cor.VERDE}{Cor.NEGRITO}🚀 SISTEMA ATUALIZADO COM SUCESSO!{Cor.RESET}")
            print(f"   Pronto para subir para o GitHub.")
            print(f"{Cor.AZUL}" + "=" * 40 + f"{Cor.RESET}")
        else:
            print(f"\n{Cor.VERMELHO}❌ Operação cancelada.{Cor.RESET}")
    
    input("\n[Pressione ENTER para fechar]")