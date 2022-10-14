from http.server import HTTPServer, SimpleHTTPRequestHandler
import socketserver
from threading import Thread
from functools import partial
from tempfile import NamedTemporaryFile
from time import sleep
from DynAIkonTrap.server import html_generator
from DynAIkonTrap.settings import LoggerSettings, OutputSettings
from DynAIkonTrap.camera_to_disk import CameraToDisk
from argparse import ArgumentParser
import shutil


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
            #for now, load a basic jpg
            print("taking still...")
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
        self._port = 9999
        self.createHomePage()
        self.createFOVPage()
        self.createObservationsHTML()
        self._camera = read_image_from
        self._handler = partial(Handler, read_image_from)
        self._usher = Thread(target=self.run, daemon=True)
        self._usher.start()

    def cameraCaptureCallback(self):
        self._camera.capture_still('test.jpg')

    def createFOVPage(self):
        html_generator.make_fov_page()

    def createHomePage(self):
        html_generator.make_main_page(self._observation_dir, self._log_path)

    def createObservationsHTML(self):
        html_generator.process_dir(self._observation_dir)

    def run(self):
        with socketserver.TCPServer(("", self._port), self._handler) as httpd:
            print("Server started at localhost:" + str(self._port))
            httpd.serve_forever()
        



