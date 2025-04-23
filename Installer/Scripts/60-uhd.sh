#!/bin/bash
set -e

"""mkdir -p ~/Installed_by_FISSURE  # Set MTU to 9000 and run uhd_image_loader command
cd ~/Installed_by_FISSURE
#wget https://codeload.github.com/EttusResearch/uhd/zip/release_003_010_003_000 -O uhd.zip
#unzip uhd.zip
#cd uhd-release_003_010_003_000/host/include
#sudo cp -Rv uhd/rfnoc /usr/share/uhd/
#rm -Rf ~/Installed_by_FISSURE/uhd-release_003_010_003_000
/usr/lib/uhd/utils/uhd_images_downloader.py
#"/usr/bin/uhd_image_loader" --args="type=x300,addr=192.168.40.2"  # Use your X310 IP
sudo sysctl -w net.core.wmem_max=24862979
""",True,'Hardware'))

# HackRF, gr-osmosdr
programs_ubuntu22_04.append(('HackRF, gr-osmosdr',
"""sudo apt-get install -y libusb-1.0-0-dev

# HackRF
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE/
wget https://github.com/greatscottgadgets/hackrf/releases/download/v2022.09.1/hackrf-2022.09.1.zip
unzip hackrf-2022.09.1.zip
rm hackrf-2022.09.1.zip
mkdir ~/Installed_by_FISSURE/hackrf-2022.09.1/host/build
cd ~/Installed_by_FISSURE/hackrf-2022.09.1/host/build
cmake ..
make
sudo make install
sudo ldconfig
sudo cp """ + fissure_directory + """/Tools/53-hackrf.rules /etc/udev/rules.d/53-hackrf.rules
sudo udevadm trigger --action=change
#sudo apt-get install -y hackrf

# gr-osmosdr
#sudo apt-get install gr-osmosdr
cd ~/Installed_by_FISSURE
#sudo apt install -y git cmake libuhd-dev uhd-host swig libgmp3-dev python3-pip python3-tk python3-pil 
#python3-pil.imagetk gnuradio
#Needs gr-foo and gr-ieee802-11
""",True,'V2V'))

"""sudo apt install -y git cmake libfftw3-dev libmbedtls-dev libboost-program-options-dev libconfig++-dev libsctp-dev libuhd-dev libpcsclite-dev pcsc-tools pcscd
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
"""#sudo apt-get install -y # boost.program-options, boost.crc, boost.circular-buffer, libfftw3, libuhd 3.9.5 or later
sudo apt-get install -y libuhd-dev
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/pvachon/zepassd.git
cd zepassd
make
########## Verify ##########
ls ~/Installed_by_FISSURE/zepassd/zepassd
""",True,'RFID'))

# iridium-toolkit
programs_ubuntu22_04.append(('iridium-toolkit (3.3 MB)',
"""#Python (2.7), NumPy (scipy), crcmod
sudo apt-get install -y mplayer
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/muccc/iridium-toolkit.git
"""sudo apt install -y libliquid-dev libbtbb-dev libuhd-dev
sudo apt-get install -y libhackrf-dev libbladerf-dev  # Separating in case there are conflicts with Hardware install
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/mikeryan/ice9-bluetooth-sniffer.git
cd ice9-bluetooth-sniffer
mkdir build
cd build
cmake ..
make
sudo make install
########## Verify ##########
ls ~/Installed_by_FISSURE/ice9-bluetooth-sniffer/build/ice9-bluetooth
""",True,'Bluetooth'))

# dump978
programs_ubuntu22_04.append(('dump978 (2.0 MB)',
"""mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/mutability/dump978.git
cd dump978
make
########## Verify ##########
ls ~/Installed_by_FISSURE/dump978/dump978
""",True,'Aircraft'))

# htop
programs_ubuntu22_04.append(('htop (782.4 kB)',
"""sudo apt-get install -y htop
########## Verify ##########
ls /usr/bin/htop
""",True,'Development'))

# OpenWebRX
programs_ubuntu22_04.append(('OpenWebRX (50.4 MB)',
"""wget -O - https://repo.openwebrx.de/debian/key.gpg.txt | sudo apt-key add
echo 'deb https://repo.openwebrx.de/ubuntu/ jammy main' | sudo tee /etc/apt/sources.list.d/openwebrx.list
sudo apt-get update
sudo apt-get install -y openwebrx
sudo systemctl stop openwebrx
sudo systemctl disable openwebrx  # Prevents starting on boot
########## Verify ##########
ls /usr/bin/openwebrx
""",True,'SDR'))

# CRC RevEng
programs_ubuntu22_04.append(('CRC RevEng (905.3 kB)',
"""mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
wget -T 10 https://sourceforge.net/projects/reveng/files/3.0.5/reveng-3.0.5.zip/download
unzip download
rm download
cd reveng-3.0.5
make
########## Verify ##########
ls ~/Installed_by_FISSURE/reveng-3.0.5/bin/i386-linux/reveng
""",True,'Data'))

# wl-color-picker
programs_ubuntu22_04.append(('wl-color-picker (643.1 kB)',
"""sudo apt-get install -y slurp grim wl-clipboard
cd ~/Installed_by_FISSURE
git clone https://github.com/jgmdev/wl-color-picker.git
########## Verify ##########
ls ~/Installed_by_FISSURE/wl-color-picker/wl-color-picker.sh
""",True,'Development'))

# GHex
programs_ubuntu22_04.append(('GHex',
"""sudo apt-get install -y ghex
########## Verify ##########
ls /usr/bin/ghex
""",True,'Data'))

# Archive Flow Graphs
programs_ubuntu22_04.append(('Archive Flow Graphs',
"""cd """ + fissure_directory + """/Flow\ Graph\ Library/maint-3.10/Archive\ Flow\ Graphs/
find . -name '*.grc' -exec grcc {} \;
""",True,'Compile Flow Graphs'))

# Fuzzing Flow Graphs
programs_ubuntu22_04.append(('Fuzzing Flow Graphs',
"""cd """ + fissure_directory + """/Flow\ Graph\ Library/maint-3.10/Fuzzing\ Flow\ Graphs/
find . -name '*.grc' -exec grcc {} \;
""",True,'Compile Flow Graphs'))

# Inspection Flow Graphs
programs_ubuntu22_04.append(('Inspection Flow Graphs',
"""cd """ + fissure_directory + """/Flow\ Graph\ Library/maint-3.10/Inspection\ Flow\ Graphs/
find . -name '*.grc' -exec grcc {} \;
""",True,'Compile Flow Graphs'))

# IQ Flow Graphs
programs_ubuntu22_04.append(('IQ Flow Graphs',
"""cd """ + fissure_directory + """/Flow\ Graph\ Library/maint-3.10/IQ\ Flow\ Graphs/
find . -name '*.grc' -exec grcc {} \;
""",True,'Compile Flow Graphs'))

# PD Flow Graphs
programs_ubuntu22_04.append(('PD Flow Graphs',
"""cd """ + fissure_directory + """/Flow\ Graph\ Library/maint-3.10/PD\ Flow\ Graphs/
find . -name '*.grc' -exec grcc {} \;
""",True,'Compile Flow Graphs'))

# Single-Stage Flow Graphs
programs_ubuntu22_04.append(('Single-Stage Flow Graphs',
"""cd """ + fissure_directory + """/Flow\ Graph\ Library/maint-3.10/Single-Stage\ Flow\ Graphs/
find . -name '*.grc' -exec grcc {} \;
""",True,'Compile Flow Graphs'))

# Sniffer Flow Graphs
programs_ubuntu22_04.append(('Sniffer Flow Graphs',
"""cd """ + fissure_directory + """/Flow\ Graph\ Library/maint-3.10/Sniffer\ Flow\ Graphs/
find . -name '*.grc' -exec grcc {} \;
""",True,'Compile Flow Graphs'))

# Standalone Flow Graphs
programs_ubuntu22_04.append(('Standalone Flow Graphs',
"""cd """ + fissure_directory + """/Flow\ Graph\ Library/maint-3.10/Standalone\ Flow\ Graphs/
find . -name '*.grc' -exec grcc {} \;
""",True,'Compile Flow Graphs'))

# TSI Flow Graphs
programs_ubuntu22_04.append(('TSI Flow Graphs',
"""cd """ + fissure_directory + """/Flow\ Graph\ Library/maint-3.10/TSI\ Flow\ Graphs/
find . -name '*.grc' -exec grcc {} \;
""",True,'Compile Flow Graphs'))

# Trigger Flow Graphs
programs_ubuntu22_04.append(('Trigger Flow Graphs',
"""cd """ + fissure_directory + """/Flow\ Graph\ Library/maint-3.10/Triggers/
find . -name '*.grc' -exec grcc {} \;
""",True,'Compile Flow Graphs'))

# pyais
programs_ubuntu22_04.append(('pyais',
"""sudo python3 -m pip install pyais
########## Verify ##########
ls /usr/local/lib/python3*/dist-packages/pyais
""",True,'AIS'))

# HAMRS
programs_ubuntu22_04.append(('HAMRS (105.8 MB)',
"""mkdir -p ~/Installed_by_FISSURE/HAMRS
cd ~/Installed_by_FISSURE/HAMRS
wget https://hamrs-releases.s3.us-east-2.amazonaws.com/1.0.6/hamrs-1.0.6-linux-x86_64.AppImage
sudo chmod +x hamrs*
########## Verify ##########
ls ~/Installed_by_FISSURE/HAMRS/hamrs*
""",True,'Ham Radio'))

# Binwalk
programs_ubuntu22_04.append(('Binwalk',
"""sudo apt-get install -y python3-binwalk binwalk
########## Verify ##########
ls /usr/bin/binwalk
""",False,'Data'))

# Read the Docs
programs_ubuntu22_04.append(('Read the Docs',
"""sudo python3 -m pip install sphinx
sudo python3 -m pip install sphinx_rtd_theme
########## Verify ##########
sudo python3 -m pip show sphinx_rtd_theme
""",True,'Development'))

# IQEngine
programs_ubuntu22_04.append(('IQEngine',
"""if command -v docker > /dev/null 2>&1; then
  echo "Docker is installed."
else
  echo "Docker is not installed."
  sudo apt-get install -y docker.io
  #sudo systemctl start docker
  #sudo systemctl enable docker
  sudo usermod -aG docker ${USER}  # Reboot computer to use docker commands without sudo
  #newgrp docker
fi
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/IQEngine/IQEngine.git
cd ~/Installed_by_FISSURE/IQEngine
cp example.env .env
docker run --env-file .env -v '""" + fissure_directory + """/IQ Recordings':/tmp/myrecordings -p 3001:3000 --pull=always -d ghcr.io/iqengine/iqengine:pre
sudo apt-get install -y uhd-host
sudo apt-get install -y gnuradio-dev

# Configure GNU Radio
(gnuradio-companion &) && sleep 5 && killall gnuradio-companion
/bin/echo -e "[grc]\nlocal_blocks_path=""" + fissure_directory + """/Custom_Blocks\nxterm_executable=/usr/bin/gnome-terminal" > ~/.gnuradio/config.conf
sudo cp /usr/lib/uhd/utils/uhd-usrp.rules /etc/udev/rules.d/  # For B205 mini
sudo udevadm control --reload-rules
sudo udevadm trigger
sudo mkdir /usr/share/uhd
sudo chmod -R 777 /usr/share/uhd
uhd_images_downloader

# Find OOT Modules
printf "\\n%s\\n" "export PYTHONPATH=/usr/local/lib/python3.8/site-packages:/usr/local/lib/python3/dist-packages:/usr/lib/python3/site-packages:$PYTHONPATH" >> ~/.bashrc
printf "\\n%s\\n" "export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH" >> ~/.bashrc
printf "\\n%s\\n" "export PYTHONPATH=/usr/local/lib/python3/dist-packages:/usr/lib/python3/site-packages:$PYTHONPATH" >> ~/.profile  # For GRC without terminal
printf "\\n%s\\n" "export LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH" >> ~/.profile  # For GRC without terminal
. ~/.bashrc
sudo apt-get install -y libzmq3-dev swig cmake
sudo sh -c "/bin/echo -e '/usr/local/lib' >> /etc/ld.so.conf"
sudo ldconfig
########## Verify ##########
gnuradio-companion --help
""",True,"Minimum Install"))

# Scapy
programs_ubuntu22_04_arm.append(('Scapy (80.1 MB)',
"""sudo apt-get install -y python3-scapy
#sudo python3 -m pip install scapy  # Causes errors
sudo python2 -m pip install scapy==2.4.5
sudo sed -i 's/tostring/tobytes/g' /usr/local/lib/python3.10/dist-packages/scapy/arch/linux.py
########## Verify ##########
python2 -c "import scapy" && python3 -c "import scapy"
""",True,"Minimum Install"))

# Wireshark
programs_ubuntu22_04_arm.append(('Wireshark (49.9 MB)',
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
programs_ubuntu22_04_arm.append(('PostgreSQL Database',
"""sudo python3 -m pip install python-dotenv
sudo apt-get install -y libpq-dev
sudo python3 -m pip install psycopg2
sudo apt-get install -y docker.io docker-compose-v2
sudo usermod -aG docker ${USER}  # Reboot computer to use docker commands without sudo
"""mkdir -p ~/Installed_by_FISSURE  # Set MTU to 9000 and run uhd_image_loader command
cd ~/Installed_by_FISSURE
#wget https://codeload.github.com/EttusResearch/uhd/zip/release_003_010_003_000 -O uhd.zip
#unzip uhd.zip
#cd uhd-release_003_010_003_000/host/include
#sudo cp -Rv uhd/rfnoc /usr/share/uhd/
#rm -Rf ~/Installed_by_FISSURE/uhd-release_003_010_003_000
/usr/lib/uhd/utils/uhd_images_downloader.py
#"/usr/bin/uhd_image_loader" --args="type=x300,addr=192.168.40.2"  # Use your X310 IP
sudo sysctl -w net.core.wmem_max=24862979
""",True,'Hardware'))

# HackRF, gr-osmosdr
programs_ubuntu22_04_arm.append(('HackRF, gr-osmosdr',
"""sudo apt-get install -y libusb-1.0-0-dev

# HackRF
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE/
wget https://github.com/greatscottgadgets/hackrf/releases/download/v2022.09.1/hackrf-2022.09.1.zip
unzip hackrf-2022.09.1.zip
rm hackrf-2022.09.1.zip
mkdir ~/Installed_by_FISSURE/hackrf-2022.09.1/host/build
cd ~/Installed_by_FISSURE/hackrf-2022.09.1/host/build
cmake ..
make
sudo make install
sudo ldconfig
sudo cp """ + fissure_directory + """/Tools/53-hackrf.rules /etc/udev/rules.d/53-hackrf.rules
sudo udevadm trigger --action=change
#sudo apt-get install -y hackrf

# gr-osmosdr
#sudo apt-get install gr-osmosdr
cd ~/Installed_by_FISSURE
#sudo apt install -y git cmake libuhd-dev uhd-host swig libgmp3-dev python3-pip python3-tk python3-pil 
#python3-pil.imagetk gnuradio
#Needs gr-foo and gr-ieee802-11
""",True,'V2V'))

"""sudo apt install -y git cmake libfftw3-dev libmbedtls-dev libboost-program-options-dev libconfig++-dev libsctp-dev libuhd-dev libpcsclite-dev pcsc-tools pcscd
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
"""#sudo apt-get install -y # boost.program-options, boost.crc, boost.circular-buffer, libfftw3, libuhd 3.9.5 or later
sudo apt-get install -y libuhd-dev
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/pvachon/zepassd.git
cd zepassd
make
########## Verify ##########
ls ~/Installed_by_FISSURE/zepassd/zepassd
""",True,'RFID'))

# iridium-toolkit
programs_ubuntu22_04_arm.append(('iridium-toolkit (3.3 MB)',
"""#Python (2.7), NumPy (scipy), crcmod
sudo apt-get install -y mplayer
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/muccc/iridium-toolkit.git
"""sudo apt install -y libliquid-dev libbtbb-dev libuhd-dev
sudo apt-get install -y libhackrf-dev libbladerf-dev  # Separating in case there are conflicts with Hardware install
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/mikeryan/ice9-bluetooth-sniffer.git
cd ice9-bluetooth-sniffer
mkdir build
cd build
cmake ..
make
sudo make install
########## Verify ##########
ls ~/Installed_by_FISSURE/ice9-bluetooth-sniffer/build/ice9-bluetooth
""",True,'Bluetooth'))

# dump978
programs_ubuntu22_04_arm.append(('dump978 (2.0 MB)',
"""mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/mutability/dump978.git
cd dump978
make
########## Verify ##########
ls ~/Installed_by_FISSURE/dump978/dump978
""",True,'Aircraft'))

# htop
programs_ubuntu22_04_arm.append(('htop (782.4 kB)',
"""sudo apt-get install -y htop
########## Verify ##########
ls /usr/bin/htop
""",True,'Development'))

# OpenWebRX
programs_ubuntu22_04_arm.append(('OpenWebRX (50.4 MB)',
"""wget -O - https://repo.openwebrx.de/debian/key.gpg.txt | sudo apt-key add
echo 'deb https://repo.openwebrx.de/ubuntu/ jammy main' | sudo tee /etc/apt/sources.list.d/openwebrx.list
sudo apt-get update
sudo apt-get install -y openwebrx
sudo systemctl stop openwebrx
sudo systemctl disable openwebrx  # Prevents starting on boot
########## Verify ##########
ls /usr/bin/openwebrx
""",True,'SDR'))

# CRC RevEng
programs_ubuntu22_04_arm.append(('CRC RevEng (905.3 kB)',
"""mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
wget -T 10 https://sourceforge.net/projects/reveng/files/3.0.5/reveng-3.0.5.zip/download
unzip download
rm download
cd reveng-3.0.5
make
########## Verify ##########
ls ~/Installed_by_FISSURE/reveng-3.0.5/bin/i386-linux/reveng
""",True,'Data'))

# wl-color-picker
programs_ubuntu22_04_arm.append(('wl-color-picker (643.1 kB)',
"""sudo apt-get install -y slurp grim wl-clipboard
cd ~/Installed_by_FISSURE
git clone https://github.com/jgmdev/wl-color-picker.git
########## Verify ##########
ls ~/Installed_by_FISSURE/wl-color-picker/wl-color-picker.sh
""",True,'Development'))

# GHex
programs_ubuntu22_04_arm.append(('GHex',
"""sudo apt-get install -y ghex
########## Verify ##########
ls /usr/bin/ghex
""",True,'Data'))

# Archive Flow Graphs
programs_ubuntu22_04_arm.append(('Archive Flow Graphs',
"""cd """ + fissure_directory + """/Flow\ Graph\ Library/maint-3.10/Archive\ Flow\ Graphs/
find . -name '*.grc' -exec grcc {} \;
""",True,'Compile Flow Graphs'))

# Fuzzing Flow Graphs
programs_ubuntu22_04_arm.append(('Fuzzing Flow Graphs',
"""cd """ + fissure_directory + """/Flow\ Graph\ Library/maint-3.10/Fuzzing\ Flow\ Graphs/
find . -name '*.grc' -exec grcc {} \;
""",True,'Compile Flow Graphs'))

# Inspection Flow Graphs
programs_ubuntu22_04_arm.append(('Inspection Flow Graphs',
"""cd """ + fissure_directory + """/Flow\ Graph\ Library/maint-3.10/Inspection\ Flow\ Graphs/
find . -name '*.grc' -exec grcc {} \;
""",True,'Compile Flow Graphs'))

# IQ Flow Graphs
programs_ubuntu22_04_arm.append(('IQ Flow Graphs',
"""cd """ + fissure_directory + """/Flow\ Graph\ Library/maint-3.10/IQ\ Flow\ Graphs/
find . -name '*.grc' -exec grcc {} \;
""",True,'Compile Flow Graphs'))

# PD Flow Graphs
programs_ubuntu22_04_arm.append(('PD Flow Graphs',
"""cd """ + fissure_directory + """/Flow\ Graph\ Library/maint-3.10/PD\ Flow\ Graphs/
find . -name '*.grc' -exec grcc {} \;
""",True,'Compile Flow Graphs'))

# Single-Stage Flow Graphs
programs_ubuntu22_04_arm.append(('Single-Stage Flow Graphs',
"""cd """ + fissure_directory + """/Flow\ Graph\ Library/maint-3.10/Single-Stage\ Flow\ Graphs/
find . -name '*.grc' -exec grcc {} \;
""",True,'Compile Flow Graphs'))

# Sniffer Flow Graphs
programs_ubuntu22_04_arm.append(('Sniffer Flow Graphs',
"""cd """ + fissure_directory + """/Flow\ Graph\ Library/maint-3.10/Sniffer\ Flow\ Graphs/
find . -name '*.grc' -exec grcc {} \;
""",True,'Compile Flow Graphs'))

# Standalone Flow Graphs
programs_ubuntu22_04_arm.append(('Standalone Flow Graphs',
"""cd """ + fissure_directory + """/Flow\ Graph\ Library/maint-3.10/Standalone\ Flow\ Graphs/
find . -name '*.grc' -exec grcc {} \;
""",True,'Compile Flow Graphs'))

# TSI Flow Graphs
programs_ubuntu22_04_arm.append(('TSI Flow Graphs',
"""cd """ + fissure_directory + """/Flow\ Graph\ Library/maint-3.10/TSI\ Flow\ Graphs/
find . -name '*.grc' -exec grcc {} \;
""",True,'Compile Flow Graphs'))

# Trigger Flow Graphs
programs_ubuntu22_04_arm.append(('Trigger Flow Graphs',
"""cd """ + fissure_directory + """/Flow\ Graph\ Library/maint-3.10/Triggers/
find . -name '*.grc' -exec grcc {} \;
""",True,'Compile Flow Graphs'))

# pyais
programs_ubuntu22_04_arm.append(('pyais',
"""sudo python3 -m pip install pyais
########## Verify ##########
ls /usr/local/lib/python3*/dist-packages/pyais
""",True,'AIS'))

# HAMRS
programs_ubuntu22_04_arm.append(('HAMRS (105.8 MB)',
"""mkdir -p ~/Installed_by_FISSURE/HAMRS
cd ~/Installed_by_FISSURE/HAMRS
wget https://hamrs-releases.s3.us-east-2.amazonaws.com/1.0.6/hamrs-1.0.6-linux-x86_64.AppImage
sudo chmod +x hamrs*
########## Verify ##########
ls ~/Installed_by_FISSURE/HAMRS/hamrs*
""",True,'Ham Radio'))

# Binwalk
programs_ubuntu22_04_arm.append(('Binwalk',
"""sudo apt-get install -y python3-binwalk binwalk
########## Verify ##########
ls /usr/bin/binwalk
""",True,'Data'))

# Read the Docs
programs_ubuntu22_04_arm.append(('Read the Docs',
"""sudo python3 -m pip install sphinx
sudo python3 -m pip install sphinx_rtd_theme
########## Verify ##########
sudo python3 -m pip show sphinx_rtd_theme
""",True,'Development'))

# IQEngine
programs_ubuntu22_04_arm.append(('IQEngine',
"""if command -v docker > /dev/null 2>&1; then
  echo "Docker is installed."
else
  echo "Docker is not installed."
  sudo apt-get install -y docker.io
  #sudo systemctl start docker
  #sudo systemctl enable docker
  sudo usermod -aG docker ${USER}  # Reboot computer to use docker commands without sudo
  #newgrp docker
fi
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/IQEngine/IQEngine.git
cd ~/Installed_by_FISSURE/IQEngine
cp example.env .env
docker run --env-file .env -v '""" + fissure_directory + """/IQ Recordings':/tmp/myrecordings -p 3001:3000 --pull=always -d ghcr.io/iqengine/iqengine:pre
