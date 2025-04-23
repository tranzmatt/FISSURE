#!/bin/bash
set -e

apt-get update && \
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    build-essential \
    cmake \
    curl \
    debconf \
    debconf-utils \
    docker-compose-v2 \
    docker.io \
    does \
    dsniff \
    eog \
    expect \
    gedit \
    git \
    gnome-terminal \
    gpsd-clients \
    libcanberra-gtk-module \
    liborc-0.4-dev \
    libosmocore-dev \
    libpq-dev \
    ncurses-term \
    net-tools \
    p7zip-full \
    python-dev-is-python3 \
    python3-gi-cairo \
    python3-opencv
    python3-pip \
    python3-tk \
    python3-testresources \
    rtl-sdr \
    snapd \
    software-properties-common \
    tshark \
    ubuntu-standard \
    unzip \
    usbutils \
    wireshark \
    wireshark-dev \
    xdg-utils

snap install netron

add-apt-repository --y ppa:wireshark-dev/stable  # Latest Wireshark
apt-get update
echo "wireshark-common wireshark-common/install-setuid boolean true" | debconf-set-selections
apt-get install -y wireshark 
groupadd wireshark
usermod -a -G wireshark $USER
chgrp wireshark /usr/bin/dumpcap
chmod o-rx /usr/bin/dumpcap
setcap 'CAP_NET_RAW+eip CAP_NET_ADMIN+eip' /usr/bin/dumpcap
getcap /usr/bin/dumpcap
mkdir -p ~/.config/wireshark/plugins
cp -a """ + fissure_directory + """/Dissectors/. ~/.config/wireshark/plugins

# Set up Python virtual environment
python3 -m venv /opt/fissure_venv
source /opt/fissure_venv/bin/activate
pip install --upgrade pip
pip install \
    --upgrade \
    PyYAML==5.1 \
    This \
    aiohttp \
    bitarray \
    cmake \
    conflicts \
    crcmod \
    eventlet \
    geopy \
    gpsd-py3 \
    ipython \
    matplotlib \
    mgrs \
    msgpack \
    netaddr \
    opencv-python-headless \
    paho-mqtt \
    pandas \
    psutil \
    psycopg2 \
    pycrypto \
    pydotplus \
    pypcapfile \
    pyserial \
    pyshark \
    python-dotenv \
    pyyaml \
    pyzipper \
    pyzmq \
    qasync \
    scikit-learn==1.3.2 \
    seaborn \
    setuptools \
    sounddevice \
    tensorflow-cpu \
    version \
    virtualenv \
    watchdog \
    with \
    yellowbrick
