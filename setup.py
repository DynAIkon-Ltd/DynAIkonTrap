from setuptools import setup
from setuptools import find_packages


def get_platform():
    try:
        with open("/sys/firmware/devicetree/base/model", "r") as f:
            model = " ".join(f.readline().strip().split()[:3])
    except Exception:
        model = ""

    return model

if get_platform() == "Raspberry Pi Zero":
    tflite_dependency = 'tflite_runtime @ https://dynaikon.com/resources/tflite_runtime-2.7.0-cp37-cp37m-linux_armv6l.whl'
else:
    tflite_dependency = 'tflite_runtime @ https://github.com/google-coral/pycoral/releases/download/v2.0.0/tflite_runtime-2.5.0.post1-cp37-cp37m-linux_armv7l.whl'

with open("DynAIkonTrap/VERSION", "r") as f:
    version = f.read()

with open("README.md") as f:
    readme = f.read()

setup(
    name='DynAIkonTrap',
    version=version,
    author="DynAikon LTD",
    author_email="rrueger@dynaikon.com",
    description="Dynaikon's camera trapping software",
    long_description=readme,
    long_description_content_type="text/markdown",
    url = "https://gitlab.dynaikon.com/dynaikontrap/dynaikontrap",
    project_urls={
        "Tracker": "https://gitlab.dynaikon.com/dynaikontrap/dynaikontrap/-/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    packages=find_packages(where="."),
    install_requires=[
        'picamera==1.13',
        'pyserial==3.4',
        'requests==2.24.0',
        'urllib3==1.25.9',
        'opencv-python-headless==4.4.0.44',
        'scipy',
        'Pillow==8.4.0',
        tflite_dependency,
    ],
    entry_points={
        'console_scripts': ['dynaikontrap=DynAIkonTrap.__main__:main']
    },
    package_data={
        "": [
            'VERSION',
            'filtering/yolo_animal_detector.cfg',
            'filtering/yolo_animal_detector.weights',
            'filtering/yolo_animal_detector.weights',
            'filtering/models/ssdlite_mobilenet_v2_animal_human/model.tflite',
            'filtering/models/ssdlite_mobilenet_v2_animal_only/model.tflite',
            'filtering/models/ssdlite_mobilenet_v2_animal_only/model2.tflite',
            ]
    }
)
