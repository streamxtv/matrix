# --- START OF FILE script.webfilebrowser/resources/lib/httpserver.py ---

# -*- coding: utf-8 -*-

# --- INÍCIO DA MODIFICAÇÃO ---
import sys
import os
import xbmc
import xbmcaddon

# Adiciona a pasta 'lib' da raiz ao caminho de busca do Python
try:
    # Kodi 19+ (Matrix)
    addon_path = xbmcaddon.Addon().getAddonInfo('path')
except AttributeError:
    # Kodi 18- (Leia)
    addon_path = xbmc.translatePath(xbmcaddon.Addon().getAddonInfo('path'))

lib_path = os.path.join(addon_path, 'lib')
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)
# --- FIM DA MODIFICAÇÃO ---

import logging
import io
import zipfile
import xbmcvfs
import mimetypes
from urllib.parse import unquote

# Importa as bibliotecas Flask
try:
    from flask import Flask, Response, render_template_string, abort, request
    WERKZEUG_AVAILABLE = True
except ImportError:
    logging.critical("Flask não encontrado. Certifique-se de que 'script.module.flask' está instalado e declarado no addon.xml.")
    WERKZEUG_AVAILABLE = False
    Flask = lambda name: type('FakeFlask', (), {'route': lambda *a, **kw: lambda f: f})

# --- CONFIGURAÇÃO DA APLICAÇÃO FLASK ---

BASE_PATH = 'special://home/'
app = Flask('webfilebrowser')

# Função para juntar caminhos virtuais do Kodi
def kodi_path_join(base, part):
    return f"{base.rstrip('/')}/{part.strip('/')}"

# Função para servir arquivos usando xbmcvfs
def serve_file_from_kodi(path, subpath):
    if path.lower().endswith('.log'):
        log_filename = path.split('/')[-1]
        return render_template_string(get_webtail_template(), log_path=subpath, log_filename=log_filename)
    
    try:
        f = xbmcvfs.File(path, 'rb')
        file_content = f.readBytes()
        f.close()
        
        filename = path.split('/')[-1]
        mimetype, _ = mimetypes.guess_type(filename)
        if mimetype is None:
            mimetype = 'application/octet-stream'

        return Response(
            file_content,
            mimetype=mimetype,
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )
    except Exception as e:
        logging.error(f"Erro ao servir o arquivo '{path}': {e}")
        return abort(500, "Não foi possível ler o arquivo")

# Função para caminhar pelos diretórios usando xbmcvfs
def walk_kodi(top):
    try:
        dirs, files = xbmcvfs.listdir(top)
        yield top, dirs, files
        for name in dirs:
            new_path = kodi_path_join(top, name)
            yield from walk_kodi(new_path)
    except Exception as e:
        logging.error(f"Erro ao listar diretório '{top}': {e}")

# ---- ROTAS PARA O LOG VIEWER E NAVEGADOR ----

@app.route('/api/tail/<path:subpath>')
def api_tail_log(subpath):
    try:
        offset = int(request.args.get('offset', 0))
        full_path = kodi_path_join(BASE_PATH, subpath)

        if not xbmcvfs.exists(full_path):
            return Response("Arquivo de log não encontrado.", status=404)
        
        stat = xbmcvfs.Stat(full_path)
        total_size = stat.st_size()

        content = b''
        if total_size > offset:
            f = xbmcvfs.File(full_path, 'rb')
            f.seek(offset)
            content = f.readBytes()
            f.close()

        resp = Response(content, mimetype='text/plain')
        resp.headers['X-Seek-Offset'] = str(total_size)
        return resp

    except Exception as e:
        logging.error(f"Erro na API de tail para '{subpath}': {e}")
        return Response(f"Erro no servidor: {e}", status=500)

@app.route('/favicon.ico')
def favicon():
    return Response(status=204)

@app.route('/', defaults={'subpath': ''})
@app.route('/<path:subpath>')
def browse(subpath):
    try:
        unquoted_subpath = unquote(subpath).strip('/')
        full_path = kodi_path_join(BASE_PATH, unquoted_subpath) if unquoted_subpath else BASE_PATH

        is_directory = xbmcvfs.exists(full_path.rstrip('/') + '/')

        if not is_directory and not xbmcvfs.exists(full_path):
             logging.error(f"Caminho não encontrado pelo xbmcvfs: {full_path}")
             return abort(404, "Arquivo ou Pasta não encontrada")

        if is_directory:
            if request.args.get('zip') == 'true':
                return serve_directory_as_zip(full_path, unquoted_subpath)

            path_with_slash = full_path.rstrip('/') + '/'
            dirs, files = xbmcvfs.listdir(path_with_slash)
            items_list = []
            current_path_part = unquoted_subpath.strip('/')

            for name in sorted(dirs, key=str.lower):
                items_list.append({ 'name': name, 'is_dir': True, 'href': f"/{current_path_part + '/' if current_path_part else ''}{name}" })
            
            for name in sorted(files, key=str.lower):
                file_href = f"/{current_path_part + '/' if current_path_part else ''}{name}"
                items_list.append({ 'name': name, 'is_dir': False, 'href': file_href })
            
            parent_path = '/'.join(unquoted_subpath.split('/')[:-1]) if unquoted_subpath else None
            breadcrumb_parts = unquoted_subpath.split('/') if unquoted_subpath else []

            return render_template_string(
                get_html_template(), items=items_list, current_folder=unquoted_subpath.split('/')[-1] or 'Kodi Home',
                breadcrumb_parts=breadcrumb_parts, parent_path=parent_path
            )
        else:
            return serve_file_from_kodi(full_path, unquoted_subpath)

    except Exception as e:
        logging.error(f"Erro ao processar o caminho '{subpath}': {e}", exc_info=True)
        return abort(500, "Erro Interno do Servidor")

def serve_directory_as_zip(path, relative_path):
    zip_buffer = io.BytesIO()
    folder_name = relative_path.split('/')[-1] or 'Kodi_Home'
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        base_zip_path = path.rstrip('/') + '/'
        for root, _, files in walk_kodi(path):
            for file in files:
                file_path = kodi_path_join(root, file)
                archive_name = file_path.replace(base_zip_path, '', 1)
                f = xbmcvfs.File(file_path, 'rb')
                zipf.writestr(archive_name, f.readBytes())
                f.close()
    zip_buffer.seek(0)
    return Response(
        zip_buffer.getvalue(), mimetype='application/zip',
        headers={'Content-Disposition': f'attachment; filename="{folder_name}.zip"'}
    )

# ---- TEMPLATES HTML ----

def get_webtail_template():
    # TEMPLATE COM BOTÃO DE PAUSA/PLAY
    return """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monitorando: {{ log_filename }}</title>
    <link rel="icon" href="data:,">
    <style>
        body { background-color: #121212; color: #e0e0e0; font-family: 'Courier New', monospace; margin: 0; }
        #header { display: flex; align-items: center; justify-content: space-between; background-color: #1e1e1e; padding: 10px 20px; border-bottom: 2px solid #03dac6; font-size: 1.2em; position: fixed; top: 0; left: 0; right: 0; z-index: 10; }
        #log-container { position: absolute; top: 55px; bottom: 0; left: 0; right: 0; overflow: auto; white-space: pre-wrap; padding: 10px; word-wrap: break-word; }
        /* Estilo do botão de pausa */
        #pauseBtn { background-color: #03dac6; color: #000; border: none; padding: 5px 10px; font-size: 0.8em; cursor: pointer; border-radius: 4px; }
        #pauseBtn.paused { background-color: #bb86fc; }
    </style>
</head>
<body>
    <div id="header">
        <span>Monitorando: <strong>{{ log_filename }}</strong></span>
        <button id="pauseBtn">Pausar</button>
    </div>
    <pre id="log-container"></pre>

    <script type="text/javascript">
        let offset = 0;
        let polling = null;
        let isPaused = false; // <<< NOVO: Variável de estado
        const logContainer = document.getElementById('log-container');
        const pauseBtn = document.getElementById('pauseBtn'); // <<< NOVO: Referência do botão
        const apiUrl = `/api/tail/{{ log_path }}`;

        const append = function (text) {
            if (text) {
                const scrollDown = logContainer.scrollHeight - logContainer.scrollTop - logContainer.clientHeight < 5;
                logContainer.textContent += text;
                if (scrollDown) {
                    logContainer.scrollTop = logContainer.scrollHeight;
                }
            }
        };

        const request = function (uri, callback) {
            const xhr = new XMLHttpRequest();
            xhr.open('GET', uri, true);
            xhr.onreadystatechange = function () {
                if (xhr.readyState === 4 && xhr.status === 200) {
                    const newOffset = xhr.getResponseHeader('X-Seek-Offset');
                    if (newOffset) {
                        offset = parseInt(newOffset, 10);
                    }
                    callback(xhr.responseText);
                }
            };
            xhr.send(null);
        };

        const tail = function () {
            if (isPaused) return; // <<< NOVO: Não faz nada se estiver pausado
            request(apiUrl + '?offset=' + offset, append);
        };

        const startPolling = function () {
            if (isPaused) return; // <<< NOVO
            tail();
            if (polling == null) {
                polling = window.setInterval(tail, 2500);
            }
        };

        const stopPolling = function () {
            if (polling != null) {
                window.clearInterval(polling);
                polling = null;
            }
        };

        // <<< NOVO: Lógica do botão de pausa
        pauseBtn.addEventListener('click', function() {
            isPaused = !isPaused;
            if (isPaused) {
                stopPolling();
                pauseBtn.textContent = 'Continuar';
                pauseBtn.classList.add('paused');
            } else {
                startPolling();
                pauseBtn.textContent = 'Pausar';
                pauseBtn.classList.remove('paused');
            }
        });

        window.onload = startPolling;
        window.onfocus = startPolling;
        window.onblur = stopPolling;
    </script>
</body>
</html>
"""

def get_html_template():
    # O TEMPLATE "Glassmorphism" PARA O NAVEGADOR DE ARQUIVOS
    return """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KODI MANAGER - {{ current_folder }}</title>
    <link rel="icon" href="data:,">
    <style>
        :root {
            --primary-text: #e0e0e0; --secondary-text: #a0a0a0;
            --accent-color: #03dac6; --primary-color: #bb86fc;
        }
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap');
        
        body { 
            font-family: 'Inter', sans-serif; 
            background: #000;
            color: var(--primary-text); 
            margin: 0; padding: 2em; min-height: 100vh; box-sizing: border-box;
            background-image: radial-gradient(circle at 1px 1px, rgba(255,255,255,0.1) 1px, transparent 0);
            background-size: 25px 25px;
        }
        .page-title { text-align: center; margin-bottom: 2em; }
        .page-title h1 {
            font-size: 3.5em; font-weight: 700; margin: 0;
            background: linear-gradient(45deg, var(--accent-color), var(--primary-color));
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            background-clip: text; text-fill-color: transparent;
        }
        .page-title p { font-size: 1.2em; color: var(--secondary-text); margin-top: 0.5em; }
        .container { 
            max-width: 1000px; margin: auto;
            background: rgba(25, 25, 25, 0.5);
            backdrop-filter: blur(15px); -webkit-backdrop-filter: blur(15px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px; box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37); padding: 2em;
        }
        .header {
            display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between;
            gap: 1.5em; border-bottom: 1px solid rgba(255, 255, 255, 0.1); 
            padding-bottom: 1.5em; margin-bottom: 1.5em;
        }
        .header-left { flex-grow: 1; }
        h2 { font-weight: 700; font-size: 2em; margin: 0; word-break: break-word; color: #fff; }
        .breadcrumb { font-size: 0.9em; color: var(--secondary-text); margin-top: 0.5em; word-break: break-all; }
        .breadcrumb a { color: var(--secondary-text); text-decoration: none; transition: color 0.2s; }
        .breadcrumb a:hover { color: var(--primary-color); }
        .download-btn { 
            display: inline-flex; align-items: center; gap: 0.5em; padding: 12px 22px; 
            background: linear-gradient(45deg, var(--accent-color), var(--primary-color));
            color: #000; border-radius: 8px; font-weight: 500;
            transition: transform 0.2s, box-shadow 0.2s; text-decoration: none; border: none;
        }
        .download-btn:hover { transform: translateY(-2px); box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3); }
        .download-btn svg { width: 1.2em; height: 1.2em; }
        .file-list { list-style-type: none; padding: 0; margin: 0; }
        .file-item a {
            display: flex; align-items: center; padding: 14px 10px; border-radius: 8px;
            text-decoration: none; color: var(--primary-text); transition: background-color 0.2s;
            font-size: 1.1em; font-weight: 500; gap: 1em;
        }
        .file-item:not(:last-child) { border-bottom: 1px solid rgba(255, 255, 255, 0.05); }
        .file-item a:hover { background-color: rgba(255, 255, 255, 0.1); }
        .icon { flex-shrink: 0; width: 1.5em; height: 1.5em; color: var(--secondary-text); }
        .file-name { word-break: break-all; }
        .file-item a .tag {
            margin-left: auto; color: #000; background: var(--accent-color);
            padding: 4px 10px; border-radius: 5px; font-size: 0.8em; font-weight: 700;
        }
    </style>
</head>
<body>
    <div class="page-title">
        <h1>KODI MANAGER</h1>
        <p>Seu navegador de arquivos pessoal</p>
    </div>
    <div class="container">
        <div class="header">
            <div class="header-left">
                <h2>{{ current_folder }}</h2>
                <div class="breadcrumb">
                    <a href="/">Home</a>
                    {% for part in breadcrumb_parts %}/ <a href="/{{ '/'.join(breadcrumb_parts[:loop.index]) }}">{{ part }}</a>{% endfor %}
                </div>
            </div>
            <a href="?zip=true" class="download-btn">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor"><path d="M10.75 2.75a.75.75 0 0 0-1.5 0v8.614L6.295 8.235a.75.75 0 1 0-1.09 1.03l4.25 4.5a.75.75 0 0 0 1.09 0l4.25-4.5a.75.75 0 0 0-1.09-1.03l-2.955 3.129V2.75Z" /><path d="M3.5 12.75a.75.75 0 0 0-1.5 0v2.5A2.75 2.75 0 0 0 4.75 18h10.5A2.75 2.75 0 0 0 18 15.25v-2.5a.75.75 0 0 0-1.5 0v2.5c0 .69-.56 1.25-1.25 1.25H4.75c-.69 0-1.25-.56-1.25-1.25v-2.5Z" /></svg>
                Baixar .ZIP
            </a>
        </div>
        <ul class="file-list">
            {% if parent_path is not none %}
            <li class="file-item">
                <a href="/{{ parent_path if parent_path != '.' else '' }}">
                    <svg class="icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M12.79 5.23a.75.75 0 0 1-.02 1.06L8.832 10l3.938 3.71a.75.75 0 1 1-1.04 1.08l-4.5-4.25a.75.75 0 0 1 0-1.08l4.5-4.25a.75.75 0 0 1 1.06.02Z" clip-rule="evenodd" /></svg>
                    <span class="file-name">.. (Pasta Anterior)</span>
                </a>
            </li>
            {% endif %}
            {% for item in items %}
            <li class="file-item">
                <a href="{{ item.href }}">
                    {% if item.is_dir %}
                    <svg class="icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor"><path d="M3.75 3A1.75 1.75 0 0 0 2 4.75v10.5c0 .966.784 1.75 1.75 1.75h12.5A1.75 1.75 0 0 0 18 15.25V8.75A1.75 1.75 0 0 0 16.25 7H8.83c-.387 0-.768-.158-1.04-.439L6.43 5.44A1.75 1.75 0 0 0 5.181 5H3.75Z" /></svg>
                    {% else %}
                    <svg class="icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4 2a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H4Zm11.5 2.75a.75.75 0 0 0-1.5 0V6h-1.5a.75.75 0 0 0 0 1.5H14v1.5a.75.75 0 0 0 1.5 0V7.5h1.5a.75.75 0 0 0 0-1.5H15.5V4.25Z" clip-rule="evenodd" /></svg>
                    {% endif %}
                    <span class="file-name">{{ item.name }}</span>
                    {% if item.name.lower().endswith('.log') %}<span class="tag">Visualizar</span>{% endif %}
                </a>
            </li>
            {% endfor %}
        </ul>
    </div>
</body>
</html>
"""
# --- END OF FILE script.webfilebrowser/resources/lib/httpserver.py ---