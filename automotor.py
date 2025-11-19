import os
import re
import shutil
import hashlib
import zipfile
import time

# ==========================================
# CONFIGURAÇÕES
# ==========================================
NOME_REPO = "repository.streamxtv.matrix"
ARQUIVO_XML = os.path.join(NOME_REPO, "addon.xml")
# ==========================================

def ler_versao_addon():
    """ Lê apenas a versão do ADDON, ignorando o cabeçalho XML """
    if not os.path.exists(ARQUIVO_XML):
        print(f"❌ ERRO CRÍTICO: Arquivo não encontrado: {ARQUIVO_XML}")
        return None

    with open(ARQUIVO_XML, "r", encoding="utf-8") as f:
        conteudo = f.read()

    # Procura especificamente dentro da tag <addon ... version="...">
    padrao = re.compile(r'(<addon[^>]+version=")([^"]+)(")', re.DOTALL)
    match = padrao.search(conteudo)

    if match:
        return match.group(2)
    else:
        print("❌ ERRO: Não consegui ler a versão do Addon. O arquivo está corrompido?")
        return None

def corrigir_e_atualizar_xml(nova_versao):
    print(f"🔧 Processando arquivo XML...")

    with open(ARQUIVO_XML, "r", encoding="utf-8") as f:
        conteudo = f.read()

    # 1. CORREÇÃO DE SEGURANÇA: Força o cabeçalho XML para 1.0 (Padrão Mundial)
    # Se estiver <?xml version="2.5.5"... ele corrige para "1.0"
    # Isso evita que o Kodi rejeite o arquivo.
    if '<?xml' in conteudo:
        conteudo = re.sub(r'<\?xml[^>]+\?>', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>', conteudo, count=1)
        print("   -> Cabeçalho XML verificado/corrigido para 1.0.")

    # 2. ATUALIZAÇÃO DO ADDON: Troca a versão do addon pela nova
    padrao_addon = re.compile(r'(<addon[^>]+version=")([^"]+)(")', re.DOTALL)
    
    # Verifica se vai haver mudança
    match = padrao_addon.search(conteudo)
    if match and match.group(2) == nova_versao:
        print("⚠️  Atenção: A versão digitada é a mesma que já existe.")
    
    # Aplica a nova versão
    novo_conteudo = padrao_addon.sub(f'\\g<1>{nova_versao}\\g<3>', conteudo, count=1)

    # Salva o arquivo corrigido e atualizado
    with open(ARQUIVO_XML, "w", encoding="utf-8") as f:
        f.write(novo_conteudo)
    
    print(f"✅ XML Salvo! (Header: 1.0 | Addon: {nova_versao})")
    return True

def gerar_zips(versao):
    print(f"\n📦 Gerando arquivos ZIP (Versão {versao})...")
    
    # Remove Zips antigos da pasta para não duplicar
    for item in os.listdir(NOME_REPO):
        if item.endswith(".zip"):
            os.remove(os.path.join(NOME_REPO, item))

    zip_interno = os.path.join(NOME_REPO, f"{NOME_REPO}-{versao}.zip")
    zip_externo = f"{NOME_REPO}.zip"

    # Cria o ZIP
    with zipfile.ZipFile(zip_interno, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(NOME_REPO):
            for file in files:
                if file.endswith(".zip") or file.startswith("."): continue
                
                caminho_real = os.path.join(root, file)
                caminho_zip = os.path.join(NOME_REPO, file) # Garante estrutura correta
                zf.write(caminho_real, caminho_zip)
    
    print(f"✅ ZIP Interno criado: {zip_interno}")

    # Copia para raiz
    if os.path.exists(zip_externo): os.remove(zip_externo)
    shutil.copy(zip_interno, zip_externo)
    print(f"✅ ZIP Externo (Site) criado: {zip_externo}")

def gerar_lista_global():
    print("\n📝 Atualizando addons.xml e MD5 global...")
    
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
        
    print(f"✅ Lista Global atualizada ({count} addons).")

# --- EXECUÇÃO ---
if __name__ == "__main__":
    print("---------------------------------------")
    print("   AUTOMATOR STREAMXTV - MATRIX V5 (FIX)")
    print("---------------------------------------\n")

    versao_atual = ler_versao_addon()

    if versao_atual:
        print(f"🔎 Versão atual do ADDON: [ {versao_atual} ]")
        
        nova_versao = input("👉 Digite a NOVA versão (ex: 2.5.6): ").strip()

        if nova_versao:
            # 1. Corrige Header e Atualiza Versão
            corrigir_e_atualizar_xml(nova_versao)
            # 2. Gera Zips
            gerar_zips(nova_versao)
            # 3. Atualiza lista
            gerar_lista_global()
            
            print("\n🚀 TUDO PRONTO E CORRIGIDO! PODE SUBIR.")
        else:
            print("❌ Cancelado.")
    else:
        print("❌ Erro ao ler estrutura do arquivo.")
        
    input("\n[ENTER] para sair...")