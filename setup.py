from setuptools import setup, find_packages

setup(
    name='go2-webrtc-connect',
    version='1.0.0',
    author='m.fritsche',
    author_email='m.fritsche@security-robotics.de',
    packages=find_packages(),
    install_requires=[
        'aiortc',
        'pycryptodome',
        'opencv-python',
        'sounddevice',
        'pyaudio'
    ],
)
