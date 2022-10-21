from http.server import HTTPServer, SimpleHTTPRequestHandler
import socketserver
from threading import Thread
from functools import partial
from tempfile import NamedTemporaryFile
import shutil
import socket
import subprocess
from typing import Union

from DynAIkonTrap.server import html_generator
from DynAIkonTrap.settings import LoggerSettings, OutputSettings
from DynAIkonTrap.camera_to_disk import CameraToDisk
from DynAIkonTrap.camera import Camera
from DynAIkonTrap.logging import get_logger

logger = get_logger(__name__)

WEBSITE_PORT = 9999
SHELL_PORT = 4200


class Handler(SimpleHTTPRequestHandler):
    """A handler class which inherits from `http.server.SimpleHTTPRequestHandler`. The method, `do_GET()` is overwritten to intercept GET requests for `camera-fov.jpg`.
    """

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

class ObservationServer:
    """The observation server handles HTML generation, running the HTTP server and starting the Shellinabox daemon. """
    
    def __init__(self, output_settings : OutputSettings, logger_settings: LoggerSettings, read_image_from: Union[Camera, CameraToDisk]):
        """Initialises ObservationServer.

        Args:
            output_settings (OutputSettings): Needs output_settings to determine the output directory to serve
            logger_settings (LoggerSettings):  Needs logger_settings to determine the log file to serve
            read_image_from (Union[Camera, CameraToDisk]): Needs an object to read images from for FOV refresh
        """
        self._observation_dir = output_settings.path
        self._log_path = logger_settings.path
        self._website_port = WEBSITE_PORT
        self._shell_port = SHELL_PORT
        self.createHomePage()
        self.createFOVPage()
        self.createObservationsHTML()
        self.createShellPage()
        self._handler = partial(Handler, read_image_from)
        self._shellinabox_handler = ServiceHandler(shell_str=f"sudo shellinaboxd -p {self._shell_port} -t")
        self._usher = Thread(target=self.run, daemon=True)
        self._usher.start()


    def createFOVPage(self):
        """Calls html_generator to make the FOV page."""
        html_generator.make_fov_page()

    def createHomePage(self):
        """Calls the html_generator to make the main page."""
        html_generator.make_main_page(self._observation_dir, self._log_path)

    def createObservationsHTML(self):
        """Calls the html_generator to make the observations html."""
        html_generator.process_dir(self._observation_dir)
    
    def createShellPage(self):
        """Calls the html_generator to make the shell page."""
        html_generator.make_shell_page(self.get_ip(), self._shell_port)

    def run(self):
        """Runs the server if the OS allows it, otherwise, error message is written to the log."""
        try:
            socketserver.TCPServer.allow_reuse_address = True
            with socketserver.TCPServer(("", self._website_port), self._handler) as httpd:
                logger.info("Server started on port: {}".format(str(self._website_port)))
                httpd.serve_forever()
        except OSError as e:
            logger.error("Observation server start failed: {}".format(e))
            logger.info("Continuing without observation server.")

    def get_ip(self):
        """Simple method to get the IP address of this device. See: https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib"""
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

class ServiceHandler:
    """A class to handle running a service daemon on a separate thread using subprocess.call. Constructor takes a string, the command to be executed to start the daemon."""

    def __init__(self, shell_str: str):
        self._shell_str = shell_str
        self._service_manager = Thread(target=self.run_service, daemon=True)
        self._service_manager.start()

    def run_service(self):
        subprocess.call(self._shell_str, shell=True)

