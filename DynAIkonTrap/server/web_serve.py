from http.server import HTTPServer, SimpleHTTPRequestHandler
import socketserver
from threading import Thread
from functools import partial
from tempfile import NamedTemporaryFile
from DynAIkonTrap.server import html_generator
from DynAIkonTrap.settings import LoggerSettings, OutputSettings
from DynAIkonTrap.camera_to_disk import CameraToDisk
import shutil
import socket


class Handler(SimpleHTTPRequestHandler):

    def __init__(self, callback, *args, **kwargs):
        self.cameraCallback = callback
        super().__init__(*args, **kwargs)


    def do_GET(self):
        #this code execute when a GET request happens on the camera fov image
        if self.path.find("camera-fov.jpg") != -1:
            self.send_response(200)
            self.send_header('Content-type', 'image/jpeg')
            self.end_headers()
            tmp = NamedTemporaryFile(suffix='.jpg')
            self.cameraCallback.capture_still(tmp.name)
            shutil.copyfileobj(tmp, self.wfile)
        return super().do_GET()

class ModifiedHTTPServer(HTTPServer):
    def __init__(self, read_image_from: CameraToDisk, *args, **kwargs):
        self._camera = read_image_from
        super().__init__(*args, **kwargs)


class ObservationServer:

    def __init__(self, output_settings : OutputSettings, logger_settings: LoggerSettings, read_image_from: CameraToDisk):
        self._observation_dir = output_settings.path
        self._log_path = logger_settings.path
        self._website_port = 9999
        self._shell_port = 4200
        self.createHomePage()
        self.createFOVPage()
        self.createObservationsHTML()
        self.createShellPage()
        self._handler = partial(Handler, read_image_from)
        self._usher = Thread(target=self.run, daemon=True)
        self._usher.start()


    def createFOVPage(self):
        html_generator.make_fov_page()

    def createHomePage(self):
        html_generator.make_main_page(self._observation_dir, self._log_path)

    def createObservationsHTML(self):
        html_generator.process_dir(self._observation_dir)
    
    def createShellPage(self):
        html_generator.make_shell_page(self.get_ip(), self._shell_port)

    def run(self):
        with socketserver.TCPServer(("", self._website_port), self._handler) as httpd:
            print("Server started at localhost:" + str(self._website_port))
            httpd.serve_forever()
        
    def get_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP




