#!/bin/bash
set -e


programs_ubuntu22_04_arm = []

# Misc. Dependencies
programs_ubuntu22_04_arm.append(('Misc. Dependencies (1.4 GB)',
"""sudo apt-get -y update
sudo apt-get install -y ubuntu-standard
sudo apt-get install -y eog
sudo apt-get -y install cmake
sudo apt-get install -y python-setuptools python-dev-is-python3 build-essential
sudo apt-get install -y curl
curl https://bootstrap.pypa.io./pip/2.7/get-pip.py | sudo python2  # Installs pip 20.3.4
sudo apt-get install -y python3-pip
sudo python3 -m pip install cmake --upgrade
sudo apt install -y python3-testresources
sudo python3 -m pip install --upgrade setuptools
sudo python3 -m pip install --upgrade virtualenv
#sudo python3 -m pip install matplotlib  # This version conflicts with yellowbrick
sudo python3 -m pip install PyYAML==5.1
sudo python3 -m pip install pyyaml
wget http://archive.ubuntu.com/ubuntu/pool/universe/p/python-scipy/python-scipy_0.19.1-2ubuntu1_amd64.deb
sudo apt-get install -y ./python-scipy_0.19.1-2ubuntu1_amd64.deb  # FIX?
rm python-scipy_0.19.1-2ubuntu1_amd64.deb
sudo apt-get install -y gedit
sudo apt-get install -y software-properties-common #python-software-properties # does Python3
sudo add-apt-repository -y ppa:git-core/ppa
sudo apt-get -y update
sudo apt-get install -y git 
sudo apt-get install -y libcanberra-gtk-module
sudo python3 -m pip install bitarray
sudo apt install net-tools
sudo python3 -m pip install crcmod
sudo python3 -m pip install pycrypto
sudo apt-get install -y python-tk
sudo python3 -m pip install pyzmq
sudo apt-get install -y libosmocore-dev
sudo apt-get install -y liborc-0.4-dev
sudo apt-get install -y expect
sudo add-apt-repository --y ppa:wireshark-dev/stable  # Latest Wireshark
sudo apt-get update
sudo python3 -m pip install pyshark
sudo apt install -y debconf
echo "wireshark-common wireshark-common/install-setuid boolean true" | sudo debconf-set-selections
sudo DEBIAN_FRONTEND=noninteractive apt install -y tshark
sudo python3 -m pip install pypcapfile
sudo python2 -m pip install pypcapfile
sudo python2 -m pip install netaddr
sudo python3 -m pip install psutil
sudo python3 -m pip install pyserial
sudo apt-get install -y gpsd-clients python3-gi-cairo
sudo python3 -m pip install pandas
sudo apt-get install -y dsniff
sudo apt-get install -y ncurses-term
sudo python3 -m pip install yellowbrick
sudo python3 -m pip install seaborn
sudo apt-get install -y gnome-terminal
sudo apt-get install -y rtl-sdr
sudo python3 -m pip install gpsd-py3
sudo python3 -m pip install geopy
sudo python3 -m pip install sounddevice
sudo python3 -m pip install qasync
sudo python3 -m pip install pydotplus
sudo python3 -m pip install tensorflow-cpu
sudo apt-get install -y snapd
sudo snap install netron
sudo python3 -m pip install ipython
sudo python3 -m pip install scikit-learn==1.3.2
sudo python3 -m pip uninstall opencv-python
sudo python3 -m pip install opencv-python-headless
sudo python3 -m pip install pyzipper
sudo apt-get install -y unzip
sudo apt-get install -y usbutils
sudo python3 -m pip install mgrs
sudo apt-get install -y debconf-utils
sudo apt-get install -y xdg-utils
sudo apt-get install -y p7zip-full
sudo python3 -m pip install watchdog
sudo python3 -m pip install aiohttp
sudo python3 -m pip install paho-mqtt
sudo python3 -m pip install msgpack
sudo python3 -m pip install eventlet
. ~/.bashrc
""",True,"Minimum Install"))


# Wireshark
programs_ubuntu22_04.append(('Wireshark (49.9 MB)',
"""sudo add-apt-repository --y ppa:wireshark-dev/stable  # Gets installed with Misc. Dependencies (tshark), ESP32 Bluetooth Classic Sniffer
sudo apt-get update
sudo apt install -y wireshark wireshark-dev  # Yes
sudo groupadd wireshark
sudo usermod -a -G wireshark $USER
sudo chgrp wireshark /usr/bin/dumpcap
sudo chmod o-rx /usr/bin/dumpcap
sudo setcap 'CAP_NET_RAW+eip CAP_NET_ADMIN+eip' /usr/bin/dumpcap
sudo getcap /usr/bin/dumpcap
mkdir -p ~/.config/wireshark/plugins
cp -a """ + fissure_directory + """/Dissectors/. ~/.config/wireshark/plugins
########## Verify ##########
wireshark --help
""",True,"Minimum Install"))

# PostgreSQL Database 
programs_ubuntu22_04.append(('PostgreSQL Database',
"""sudo python3 -m pip install python-dotenv
sudo apt-get install -y libpq-dev
sudo python3 -m pip install psycopg2
sudo apt-get install -y docker.io docker-compose-v2
sudo usermod -aG docker ${USER}  # Reboot computer to use docker commands without sudo
