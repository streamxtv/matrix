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
import threading
from resources.lib import utils

# Importa o 'app' do nosso httpserver e o 'make_server' do werkzeug
try:
    from resources.lib.httpserver import app
    from werkzeug.serving import make_server
    WERKZEUG_AVAILABLE = True
except ImportError:
    logging.critical("Werkzeug não encontrado. O servidor web não pode ser iniciado.")
    WERKZEUG_AVAILABLE = False


class Monitor(xbmc.Monitor):
    def __init__(self):
        super(Monitor, self).__init__()
        self._http_server_runner = None
        self._lock = threading.Lock()

    def start(self):
        logging.debug("Monitor de serviço iniciado.")
        self.onSettingsChanged()

    def stop(self):
        with self._lock:
            self._stop_http_server_runner()
        logging.debug("Monitor de serviço parado.")

    def _start_http_server_runner(self, port):
        if not WERKZEUG_AVAILABLE:
            return
        if self._http_server_runner is None:
            logging.debug(f"Iniciando thread do servidor HTTP na porta {port}")
            self._http_server_runner = HTTPServerRunner(port)
            self._http_server_runner.start()

    def _stop_http_server_runner(self):
        if self._http_server_runner is not None:
            logging.debug("Parando thread do servidor HTTP.")
            self._http_server_runner.stop()
            self._http_server_runner.join()
            self._http_server_runner = None

    def onSettingsChanged(self):
        with self._lock:
            run_http_server = utils.get_boolean_setting("http_server")
            
            if run_http_server:
                http_port = utils.get_int_setting("port")
                
                # Se o servidor já está rodando e a porta mudou, reinicia
                if self._http_server_runner and self._http_server_runner.get_port() != http_port:
                    logging.info(f"Porta alterada para {http_port}. Reiniciando servidor.")
                    self._stop_http_server_runner()
                    self._start_http_server_runner(http_port)
                # Se não está rodando, inicia
                elif not self._http_server_runner:
                    self._start_http_server_runner(http_port)
            else:
                self._stop_http_server_runner()


class HTTPServerRunner(threading.Thread):
    def __init__(self, port):
        super(HTTPServerRunner, self).__init__()
        self._port = port
        # Usamos o servidor do Werkzeug, que é feito para rodar aplicações WSGI como o Flask
        # '0.0.0.0' faz o servidor ser acessível por outros dispositivos na sua rede
        self._server = make_server("0.0.0.0", self._port, app, threaded=True)

    def run(self):
        try:
            logging.info(f"Servidor Flask iniciado em http://{xbmc.getIPAddress()}:{self._port}")
            # serve_forever() é um loop bloqueante, por isso rodamos em uma thread
            self._server.serve_forever()
            logging.info("Servidor HTTP finalizado.")
        except Exception as e:
            logging.error(f"Falha ao iniciar o servidor HTTP na porta {self._port}: {e}")

    def stop(self):
        if self._server is not None:
            logging.info("Desligando o servidor HTTP...")
            # O servidor do Werkzeug tem um método shutdown() para parar o loop
            self._server.shutdown()
            self._server = None
            
    def get_port(self):
        return self._port


def run(start_delay=5):
    monitor = Monitor()
    if monitor.waitForAbort(start_delay):
        return
    monitor.start()
    monitor.waitForAbort()
    monitor.stop()