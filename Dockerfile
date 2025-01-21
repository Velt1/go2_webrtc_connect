FROM python:3.8-slim

# Set working directory
WORKDIR /app/acuda_ac

# Update and install required packages
RUN apt-get update
RUN apt-get install python3 -y
RUN apt-get install python3-pip -y
RUN apt-get install portaudio19-dev -y
RUN apt-get install python3-venv -y
RUN apt-get install -y libgl1 libglib2.0-0
RUN apt-get install git -y

# RUN apt-get update && apt-get install -y \
#     python3 \
#     python3-pip \
#     python3-venv \
#     portaudio19-dev \
#     libgl1 \
#     libglib2.0-0 \
#     iproute2 \
#     iputils-ping \
#     dnsutils \
#     curl

RUN git clone --recurse-submodules https://github.com/Velt1/go2_webrtc_connect.git
# move ./go2_webrtc_connect/start.sh to /app/acuda_ac
RUN mv ./go2_webrtc_connect/start.sh ./start.sh
# Set up a Python virtual environment and install Python dependencies
RUN python3 -m venv /app/venv
RUN /app/venv/bin/pip install --upgrade pip
RUN /app/venv/bin/pip install -e ./go2_webrtc_connect
RUN /app/venv/bin/pip install requests wasmtime

# Make start.sh executable
RUN chmod +x ./start.sh

# Set environment variables
ENV PATH="/app/venv/bin:$PATH" 
USER root

# Run the start.sh script to activate the virtual environment and start Python
CMD ["bash", "./start.sh"]
# run forever with tail dev null command
# CMD ["tail", "-f", "/dev/null"]
