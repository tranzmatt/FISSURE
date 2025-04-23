#!/bin/bash
set -e

apt-get update && \
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    # \
    #python-software-properties \
    ./python-scipy_0.19.1-2ubuntu1_amd64.deb \
    FIX? \
    Python3 \
    Yes \
    build-essential \
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
    python-setuptools \
    python-tk \
    python3-gi-cairo \
    python3-pip \
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
#!/bin/bash
set -e


programs_ubuntu22_04_arm = []

# Misc. Dependencies
programs_ubuntu22_04_arm.append(('Misc. Dependencies (1.4 GB)',
"""apt-get -y update
apt-get -y install cmake
curl https://bootstrap.pypa.io./pip/2.7/get-pip.py | python2  # Installs pip 20.3.4
wget http://archive.ubuntu.com/ubuntu/pool/universe/p/python-scipy/python-scipy_0.19.1-2ubuntu1_amd64.deb
rm python-scipy_0.19.1-2ubuntu1_amd64.deb
add-apt-repository -y ppa:git-core/ppa
apt-get -y update
add-apt-repository --y ppa:wireshark-dev/stable  # Latest Wireshark
apt-get update
echo "wireshark-common wireshark-common/install-setuid boolean true" | debconf-set-selections
snap install netron
python3 -m pip uninstall opencv-python
. ~/.bashrc
""",True,"Minimum Install"))


# Wireshark
programs_ubuntu22_04.append(('Wireshark (49.9 MB)',
"""add-apt-repository --y ppa:wireshark-dev/stable  # Gets installed with Misc. Dependencies (tshark), ESP32 Bluetooth Classic Sniffer
apt-get update
groupadd wireshark
usermod -a -G wireshark $USER
chgrp wireshark /usr/bin/dumpcap
chmod o-rx /usr/bin/dumpcap
setcap 'CAP_NET_RAW+eip CAP_NET_ADMIN+eip' /usr/bin/dumpcap
getcap /usr/bin/dumpcap
mkdir -p ~/.config/wireshark/plugins
cp -a """ + fissure_directory + """/Dissectors/. ~/.config/wireshark/plugins
########## Verify ##########
wireshark --help
""",True,"Minimum Install"))

# PostgreSQL Database 
programs_ubuntu22_04.append(('PostgreSQL Database',
usermod -aG docker ${USER}  # Reboot computer to use docker commands without sudo

# Set up Python virtual environment
python3 -m venv /opt/fissure_venv
source /opt/fissure_venv/bin/activate
pip install --upgrade pip
pip install \
    # \
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
