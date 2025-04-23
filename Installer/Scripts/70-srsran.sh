#!/bin/bash
set -e

# srsRAN_4G/srsRAN/srsLTE
programs_ubuntu22_04.append(('srsRAN_4G',
"""sudo apt-get install -y build-essential cmake net-tools libfftw3-dev libmbedtls-dev libboost-program-options-dev libconfig++-dev libsctp-dev gcc-11 g++-11
sudo apt-get install -y libboost-system-dev libboost-test-dev libboost-thread-dev libqwt-qt5-dev qtbase5-dev  # srsGUI
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/srsLTE/srsGUI.git
cd srsGUI
mkdir build
cd build
export CC=$(which gcc-11)
export CXX=$(which g++-11)
cmake ..
make
sudo make install
cd ~/Installed_by_FISSURE
git clone https://github.com/srsRAN/srsRAN_4G.git
cp """ + fissure_directory + """/Tools/IMSI-Catcher_4G/cell_search.c ~/Installed_by_FISSURE/srsRAN_4G/lib/examples/  # IMSI-Catcher 4G
cd srsRAN_4G/
mkdir build
cd build
cmake ..
make
sudo make install
sudo ldconfig
sudo srsran_install_configs.sh user  # user or service, not username
cd ../..
mkdir -p ~/.config/srsran
sudo cp -f """ + fissure_directory + """/Tools/srsRAN_configs/* ~/.config/srsran/
sudo chown -R $USER:$USER ~/.config/srsran     # IMSI-Catcher 4G
sudo apt-get install -y fortune cowsay lolcat  # IMSI-Catcher 4G
# cd srsRAN/srsepc
# interface=$(route | awk '/default/ {print $0}' | awk 'END {print $(NF)}')
# sudo ./srsepc_if_masq.sh "$interface"
# gnome-terminal --tab --title="srsEPC" -- /bin/sh -c 'sudo srsepc; $SHELL' 
# gnome-terminal --tab --title="srsENB" -- /bin/sh -c 'sudo srsenb; $SHELL'
########## Verify ##########
srsenb --help
""",True,'LTE'))

# FALCON - FIX (needs older soapysdr version?)
programs_ubuntu22_04.append(('FALCON',
"""sudo apt-get install -y build-essential git cmake libfftw3-dev libmbedtls-dev libboost-program-options-dev libconfig++-dev libsctp-dev  # For srsLTE
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
sudo apt-get install -y libglib2.0-dev libudev-dev libcurl4-gnutls-dev libboost-all-dev qtdeclarative5-dev libqt5charts5-dev  # FALCON
git clone https://github.com/falkenber9/falcon.git
cd falcon
mkdir build
cd build
cmake -DFORCE_SUBPROJECT_SRSLTE=ON -DCMAKE_INSTALL_PREFIX=/usr ../
make
sudo make install
#sudo xargs rm < install_manifest.txt  # uninstall
#make clean
########## Verify ##########
ls /usr/bin/FalconGUI
""",False,'LTE'))

# LTE-ciphercheck - Fix
programs_ubuntu22_04.append(('LTE-ciphercheck',
git clone https://github.com/mrlnc/LTE-ciphercheck  # No 22.04 version yet.
cd LTE-ciphercheck
mkdir build 
cd build
cmake ..
make srsue
sudo ldconfig
cp """ + fissure_directory + """/Tools/LTE-ciphercheck/ciphercheck.conf ../srsue/ciphercheck.conf 
""",False,'LTE'))

# Aircrack-ng
programs_ubuntu22_04.append(('Aircrack-ng (20.4 MB)',
"""sudo apt-get install -y aircrack-ng
########## Verify ##########
aircrack-ng --help
""",True,'802.11'))

# Geany
programs_ubuntu22_04.append(('Geany (16.4 MB)',
"""sudo apt-get install -y geany
########## Verify ##########
geany --help
""",False,'Development'))

# Arduino IDE
programs_ubuntu22_04.append(('Arduino IDE (630.3 MB)',
"""wget -P ~/Installed_by_FISSURE/ https://downloads.arduino.cc/arduino-1.8.15-linux64.tar.xz
cd ~/Installed_by_FISSURE
tar -xf arduino-1.8.15-linux64.tar.xz
rm arduino-1.8.15-linux64.tar.xz
cd arduino-1.8.15/
sudo ./install.sh
cp -R """ + fissure_directory + """/Tools/Esp8266_listen_trigger/ ~/Installed_by_FISSURE/
########## Verify ##########
arduino --version
""",True,'Development'))

# Minicom
programs_ubuntu22_04.append(('Minicom (2.1 MB)',
"""sudo apt-get install -y minicom
########## Verify ##########
ls /usr/bin/minicom
""",True,'Hardware'))

# PuTTY
programs_ubuntu22_04.append(('PuTTY (6.4 MB)',
"""sudo apt-get install -y putty
########## Verify ##########
putty --help
""",True,'Hardware'))

# openHAB - FIX
programs_ubuntu22_04.append(('openHAB (616.9 MB)',
"""sudo apt-get -yq install gnupg curl
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 0xB1998361219BD9C9
cd ~/Downloads
curl -O https://cdn.azul.com/zulu/bin/zulu-repo_1.0.0-2_all.deb
sudo apt-get install ./zulu-repo_1.0.0-2_all.deb
sudo apt-get update
sudo apt-get install -y zulu11-jdk
rm zulu-repo_1.0.0-2_all.deb
wget -qO - 'https://openhab.jfrog.io/artifactory/api/gpg/key/public' | sudo apt-key add -
sudo apt-get install -y apt-transport-https
echo 'deb https://openhab.jfrog.io/artifactory/openhab-linuxpkg stable main' | sudo tee /etc/apt/sources.list.d/openhab.list
sudo apt-get update 
sudo apt-get install -y openhab
########## Verify ##########
ls /usr/bin/openhab-cli
""",True,'Z-Wave'))

# rtl-zwave
programs_ubuntu22_04.append(('rtl-zwave (106.5 kB)',
"""mkdir -p ~/Installed_by_FISSURE
sudo apt-get install -y libpcap-dev
cp -R """ + fissure_directory + """/Tools/rtl-zwave-master ~/Installed_by_FISSURE/
cd ~/Installed_by_FISSURE/rtl-zwave-master
make
########## Verify ##########
ls ~/Installed_by_FISSURE/rtl-zwave-master/rtl_zwave
""",True,'Z-Wave'))

# waving-z
programs_ubuntu22_04.append(('waving-z (2.3 MB)',
"""mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE/
git clone https://github.com/baol/waving-z.git
cd ~/Installed_by_FISSURE/waving-z
mkdir build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build .
########## Verify ##########
ls ~/Installed_by_FISSURE/waving-z/build/wave-in
""",True,'Z-Wave'))

# baudline
programs_ubuntu22_04.append(('baudline (4.9 MB)',
"""mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
wget -P ~/Installed_by_FISSURE/ https://www.baudline.com/baudline_1.08_linux_x86_64.tar.gz  # They removed this file. We are not allowed to distribute source.
tar -xf baudline_1.08_linux_x86_64.tar.gz
rm baudline_1.08_linux_x86_64.tar.gz
########## Verify ##########
~/Installed_by_FISSURE/baudline_1.08_linux_x86_64/baudline --help
""",False,'SDR'))

# Universal Radio Hacker
programs_ubuntu22_04.append(('Universal Radio Hacker (129.2 MB)',
"""sudo python3 -m pip install cython
sudo python3 -m pip install urh
########## Verify ##########
urh --version
""",True,'SDR'))

# Inspectrum
programs_ubuntu22_04.append(('Inspectrum (1.8 MB)',
"""sudo apt-get install -y inspectrum
########## Verify ##########
inspectrum --help
""",True,'SDR'))

# OpenCPN
programs_ubuntu22_04.append(('OpenCPN (209.3 MB)',
"""sudo add-apt-repository -y ppa:opencpn/opencpn
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys C865EB40  # FIX
sudo apt-get update
sudo apt-get install -y opencpn
########## Verify ##########
ls /usr/bin/opencpn
""",True,'AIS'))

# Kalibrate
programs_ubuntu22_04.append(('Kalibrate (2.1 MB)',
"""mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/steve-m/kalibrate-rtl.git
cd kalibrate-rtl
./bootstrap && CXXFLAGS='-W -Wall -O3' ./configure && make
########## Verify ##########
ls ~/Installed_by_FISSURE/kalibrate-rtl/src/kal
""",True,'GSM'))

# retrogram-rtlsdr
programs_ubuntu22_04.append(('retrogram-rtlsdr (1.7 MB)',
"""mkdir -p ~/Installed_by_FISSURE
sudo apt-get install -y librtlsdr-dev libncurses5-dev libboost-program-options-dev
cp -R """ + fissure_directory + """/Tools/retrogram-rtlsdr-master ~/Installed_by_FISSURE/
cd ~/Installed_by_FISSURE/retrogram-rtlsdr-master
make
########## Verify ##########
ls ~/Installed_by_FISSURE/retrogram-rtlsdr-master/retrogram-rtlsdr
""",True,'SDR'))

# RTLSDR-Airband
programs_ubuntu22_04.append(('RTLSDR-Airband (7.0 MB)',
"""sudo apt-get install -y build-essential cmake pkg-config libmp3lame-dev libshout3-dev libconfig++-dev libfftw3-dev libpulse-dev
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/szpajder/RTLSDR-Airband.git
cd RTLSDR-Airband
mkdir build
cd build
cmake ../
make
sudo make install
########## Verify ##########
rtl_airband -h
""",True,'SDR'))

# Spektrum
programs_ubuntu22_04.append(('Spektrum (241.9 MB)',
"""echo 'blacklist dvb_usb_rtl28xxu' | sudo tee /etc/modprobe.d/rtl-sdr.conf  # Restart computer to use RTL device
echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2838", GROUP="adm", MODE="0666"' | sudo tee /etc/udev/rules.d/20.rtlsdr.rules
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
wget -P ~/Installed_by_FISSURE/ https://github.com/pavels/spektrum/releases/download/2.1.0/spektrum-linux64.tar.gz
tar -xf spektrum-linux64.tar.gz
rm spektrum-linux64.tar.gz
########## Verify ##########
ls ~/Installed_by_FISSURE/spektrum/spektrum
""",True,'SDR'))

# SDRTrunk
programs_ubuntu22_04.append(('SDRTrunk (106.9 MB)',
"""#sudo apt-get -yq install gnupg curl  # Java (if needed)
#sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 0xB1998361219BD9C9
#cd ~/Downloads
#curl -O https://cdn.azul.com/zulu/bin/zulu-repo_1.0.0-2_all.deb
#sudo apt-get install ./zulu-repo_1.0.0-2_all.deb
#sudo apt-get update
#sudo apt-get install -y zulu11-jdk
#rm zulu-repo_1.0.0-2_all.deb
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
wget -P ~/Installed_by_FISSURE/ https://github.com/DSheirer/sdrtrunk/releases/download/v0.5.0-alpha.6/sdr-trunk-linux-x86_64-v0.5.0-alpha6.zip
unzip -q sdr-trunk-linux-x86_64-v0.5.0-alpha6.zip
rm sdr-trunk-linux-x86_64-v0.5.0-alpha6.zip
########## Verify ##########
ls ~/Installed_by_FISSURE/sdr-trunk-linux-x86_64-v0.5.0-alpha6/bin/sdr-trunk
""",True,'Trunked Radio'))

# Audacity
programs_ubuntu22_04.append(('Audacity (38.8 MB)',
"""sudo apt-get install -y audacity
########## Verify ##########
audacity --version
""",True,'Audio'))

# Sound eXchange
programs_ubuntu22_04.append(('Sound eXchange (2.3 MB)',
"""sudo apt-get install -y sox
########## Verify ##########
sox --version
""",True,'Audio'))

# LAME
programs_ubuntu22_04.append(('LAME (286.8 kB)',
"""sudo apt-get install -y lame
########## Verify ##########
lame --version
""",True,'Audio'))

# mpv
programs_ubuntu22_04.append(('mpv (174.7 MB)',
"""sudo apt-get install -y mpv
########## Verify ##########
mpv --version
""",True,'Audio'))

# FFmpeg
programs_ubuntu22_04.append(('FFmpeg (114.7 kB)',
"""sudo apt-get install -y ffmpeg 
########## Verify ##########
ffmpeg --help
""",True,'Audio'))

# MPlayer
programs_ubuntu22_04.append(('MPlayer (10.4 MB)',
"""sudo apt-get install -y mplayer
########## Verify ##########
ls /usr/bin/mplayer
""",True,'Audio'))

# VLC
programs_ubuntu22_04.append(('VLC (402.1 MB)',
"""sudo apt-get install -y vlc
########## Verify ##########
vlc --help
""",True,'Video'))

# Simple Screen Recorder
programs_ubuntu22_04.append(('Simple Screen Recorder (5.6 MB)',
"""sudo apt-get install -y simplescreenrecorder
########## Verify ##########
simplescreenrecorder --help
""",False,'Video'))

# radiosonde_auto_rx
programs_ubuntu22_04.append(('radiosonde_auto_rx (82.4 MB)',
"""sudo apt-get install -y python3 python3-numpy python3-setuptools python3-crcmod python3-requests python3-dateutil python3-pip python3-flask sox git build-essential libtool cmake usbutils libusb-1.0-0-dev rng-tools libsamplerate-dev libatlas3-base libgfortran5
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/projecthorus/radiosonde_auto_rx.git
cd radiosonde_auto_rx/auto_rx
./build.sh
cp station.cfg.example station.cfg
sudo python3 -m pip install -r requirements.txt
########## Verify ##########
ls ~/Installed_by_FISSURE/radiosonde_auto_rx/auto_rx/auto_rx.py
""",True,'Radiosonde'))

# SdrGlut
programs_ubuntu22_04.append(('SdrGlut',
"""sudo apt-get install -y build-essential libwxgtk3.2-dev libglew-dev libusb-dev libsoapysdr-dev libopenal-dev libliquid-dev freeglut3-dev libalut-dev libsndfile1-dev librtaudio-dev libhdf4-dev libfftw3-dev
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone --depth=1 https://github.com/righthalfplane/SdrGlut.git
cd SdrGlut
make -f makefileUbuntu -j 8
cd iqSDR
make -f makefileUbuntuOLD -j 8
########## Verify ##########
ls ~/Installed_by_FISSURE/SdrGlut/sdrglut.x
""",True,'SDR'))

# rehex
programs_ubuntu22_04.append(('rehex (197.1 MB)',
"""sudo apt-get install -y build-essential git libwxgtk3.0-gtk3-dev libjansson-dev libcapstone-dev liblua5.3-dev lua5.3 lua5.2 libunistring-dev libgtk-3-dev lua-busted libbotan-2-dev
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/solemnwarning/rehex.git
cd rehex
sudo git config --global --add safe.directory """ + os.path.expanduser('~') + """/Installed_by_FISSURE/rehex
yes | sudo cpan Template
sudo make install
########## Verify ##########
ls /usr/local/bin/rehex 
""",True,'Data'))

# ZEPASSD
programs_ubuntu22_04.append(('ZEPASSD (11.6 MB)',
wget http://archive.ubuntu.com/ubuntu/pool/universe/libn/libnetfilter-queue/libnetfilter-queue1_1.0.2-2_amd64.deb
sudo dpkg -i libnetfilter-queue1_1.0.2-2_amd64.deb
wget http://archive.ubuntu.com/ubuntu/pool/universe/n/nfqueue-bindings/python-nfqueue_0.6-1build2_amd64.deb
sudo dpkg -i python-nfqueue_0.6-1build2_amd64.deb 
""",False,'802.11'))

# Wifite
programs_ubuntu22_04.append(('Wifite (797.5 MB)',
"""echo "macchanger macchanger/automatically_run boolean false" | sudo debconf-set-selections
# python, iwconfig, ifconfig, Aircrack-ng, tshark, reaver, bully, coWPAtty, pyrit, hashcat, hcxdumptool, hcxpcaptool
sudo apt-get install -y build-essential libpcap-dev aircrack-ng pixiewps libssl-dev hashcat libcurl4-openssl-dev pkg-config macchanger python-is-python3
sudo python3 -m pip install psycopg2-binary #scapy (python3 scapy with pip causes errors)
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/derv82/wifite2.git
git clone https://github.com/t6x/reaver-wps-fork-t6x
cd reaver-wps-fork-t6x/src
./configure
make
sudo make install
cd ~/Installed_by_FISSURE
git clone https://github.com/aanarchyy/bully
cd bully/src
make
sudo make install
cd ~/Installed_by_FISSURE
wget http://www.willhackforsushi.com/code/cowpatty/4.6/cowpatty-4.6.tgz
tar zxfv cowpatty-4.6.tgz
rm cowpatty-4.6.tgz
cd cowpatty-4.6
make
sudo cp cowpatty /usr/bin
cd ~/Installed_by_FISSURE
mkdir Pyrit-v0.5.0
cd Pyrit-v0.5.0
wget https://github.com/JPaulMora/Pyrit/releases/download/v0.5.0/Pyrit-v0.5.0.zip
unzip -q Pyrit-v0.5.0.zip
rm Pyrit-v0.5.0.zip
sudo apt-get install -y python2-dev
python2 setup.py clean
python2 setup.py build
sudo python2 setup.py install
cd ~/Installed_by_FISSURE
git clone https://github.com/ZerBea/hcxdumptool.git
cd hcxdumptool
make
sudo make install
cd ~/Installed_by_FISSURE
git clone https://github.com/ZerBea/hcxtools.git
cd hcxtools
make
sudo make install
sudo ln -s /usr/bin/hcxpcapngtool /usr/bin/hcxpcaptool
#sudo apt-get install -y tshark
""",False,'802.11'))

# rtl_433
programs_ubuntu22_04.append(('rtl_433 (27.8 MB)',
"""#sudo apt-get install -y rtl-433
sudo apt-get install -y libtool libusb-1.0-0-dev librtlsdr-dev rtl-sdr build-essential cmake pkg-config
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/merbanan/rtl_433.git
cd rtl_433/
mkdir build
cd build
cmake ..
make
sudo make install
########## Verify ##########
rtl_433 -help
""",True,'433 MHz'))

# RouterSploit
programs_ubuntu22_04.append(('RouterSploit (369.3 MB)',
"""sudo apt-get install -y python3-pip libglib2.0-dev rustc
sudo python3 -m pip install setuptools-rust
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://www.github.com/threat9/routersploit
cd routersploit
python3 -m pip install setuptools
python3 -m pip install -r requirements.txt
python3 -m pip install bluepy
########## Verify ##########
~/Installed_by_FISSURE/routersploit/rsf.py --help
""",True,'802.11'))

# Metasploit
programs_ubuntu22_04.append(('Metasploit (1.1 GB)',
"""mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
mkdir metasploit
cd metasploit
curl https://raw.githubusercontent.com/rapid7/metasploit-omnibus/master/config/templates/metasploit-framework-wrappers/msfupdate.erb > msfinstall && chmod 755 msfinstall && ./msfinstall
########## Verify ##########
ls /usr/bin/msfconsole
""",True,'802.11'))

# monitor_rtl433
programs_ubuntu22_04.append(('monitor_rtl433 (54.6 MB)',
"""mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/mcbridejc/monitor_rtl433.git
cd monitor_rtl433
sudo python3 -m pip install . --force-reinstall --ignore-installed
sudo python3 -m pip install python-dateutil
sudo python3 -m pip install flask_table
########## Verify ##########
ls /usr/local/bin/monitor_rtl433
""",True,'433 MHz'))

# scan-ssid
programs_ubuntu22_04.append(('scan-ssid (585.8 kB)',
"""mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
sudo apt-get install -y iw
git clone https://github.com/Resethel/scan-ssid.git
cd scan-ssid
sudo cp scan-ssid /usr/local/bin
sudo chmod 755 /usr/local/bin/scan-ssid  # can't be in monitor mode, managed only
########## Verify ##########
scan-ssid --help
""",True,'802.11'))

# minimodem
programs_ubuntu22_04.append(('minimodem (217.1 kB)',
"""sudo apt-get install -y minimodem
########## Verify ##########
minimodem --version
""",True,'Audio'))

# WSJT-X
programs_ubuntu22_04.append(('WSJT-X (35.2 MB)',
"""sudo apt-get install -y wsjtx
########## Verify ##########
ls /usr/bin/wsjtx
""",True,'Ham Radio'))

# Google Earth Pro
programs_ubuntu22_04.append(('Google Earth Pro (314.6 MB)',
"""mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
wget https://dl.google.com/dl/earth/client/current/google-earth-pro-stable_current_amd64.deb
sudo dpkg -i google-earth-pro-stable_current_amd64.deb
########## Verify ##########
ls /usr/bin/google-earth-pro
""",True,'Mapping'))

# gr-air-modes
programs_ubuntu22_04.append(('gr-air-modes (1.3 MB)',
"""sudo apt-get install -y gr-air-modes
sudo sed -i 's/numpy.float)/numpy.float32)/g' /usr/lib/python3/dist-packages/air_modes/mlat.py  # Deprecated numpy type: np.float->np.float32 or np.float64
########## Verify ##########
modes_rx --help
""",True,'Aircraft'))

# ESP8266 Deauther v2
programs_ubuntu22_04.append(('ESP8266 Deauther v2 (6.6 MB)',
"""mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
wget https://github.com/SpacehuhnTech/esp8266_deauther/archive/v2.zip
unzip -q v2.zip
rm v2.zip
""",True,'802.11'))

# Viking
programs_ubuntu22_04.append(('Viking (531.5 MB)',
"""mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone git://git.code.sf.net/p/viking/code viking
sudo apt install -y gtk-doc-tools docbook-xsl yelp-tools libpng-dev libgtk-3-dev libicu-dev libjson-glib-dev intltool
sudo apt-get install -y libcurl4-gnutls-dev libglib2.0-dev-bin
sudo apt-get install -y libsqlite3-dev nettle-dev libmapnik-dev libgeoclue-2-dev libgexiv2-dev libgps-dev libmagic-dev libbz2-dev libzip-dev liboauth-dev
sudo apt-get install -y autopoint libnova-dev
cd viking
./autogen.sh
./configure
make
sudo make install
########## Verify ##########
viking --help
""",True,'Mapping'))

# PyGPSClient
programs_ubuntu22_04.append(('PyGPSClient (27.3 MB)',
"""sudo apt install -y python3-pip python3-tk python3-pil python3-pil.imagetk
sudo apt remove -y python3-cryptography
sudo python3 -m pip install --upgrade PyGPSClient
########## Verify ##########
ls /usr/local/bin/pygpsclient
""",True,'GPS'))

# Gpredict
programs_ubuntu22_04.append(('Gpredict (17.6 MB)',
"""sudo apt-get install -y gpredict
########## Verify ##########
gpredict --help
""",True,'GPS'))

# FoxtrotGPS
programs_ubuntu22_04.append(('FoxtrotGPS (2.8 MB)',
"""sudo apt-get install -y foxtrotgps
########## Verify ##########
foxtrotgps --help
""",True,'GPS'))

# multimon-ng
programs_ubuntu22_04.append(('multimon-ng (13.6 MB)',
"""sudo apt-get install -y libpulse-dev
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/EliasOenal/multimonNG.git
cd multimonNG
mkdir build
cd build
qmake ../multimon-ng.pro
make
sudo make install
########## Verify ##########
ls /usr/local/bin/multimon-ng
""",True,'POCSAG'))

# Xastir
programs_ubuntu22_04.append(('Xastir (53.3 MB)',
"""echo 'xastir xastir/setuid boolean true' | sudo debconf-set-selections
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y xastir
########## Verify ##########
sudo xastir -V
""",True,'Ham Radio'))

# LTE-Cell-Scanner
programs_ubuntu22_04.append(('LTE-Cell-Scanner (168.1 MB)',
"""sudo apt-get install -y cmake libncurses5-dev liblapack-dev libblas-dev libboost-thread-dev libboost-system-dev libitpp-dev librtlsdr-dev libfftw3-dev
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/JiaoXianjun/LTE-Cell-Scanner.git
cd LTE-Cell-Scanner
mkdir build
cd build
cmake ..
make 
sudo make install
########## Verify ##########
ls /usr/local/bin/CellSearch
""",True,'LTE'))

# btscanner
programs_ubuntu22_04.append(('btscanner (1.3 MB)',
"""sudo apt-get install -y btscanner
########## Verify ##########
btscanner --help
""",True,'Bluetooth'))

# hcidump
programs_ubuntu22_04.append(('hcidump (1.1 MB)',
"""sudo apt-get install -y bluez-hcidump
########## Verify ##########
hcidump --help
""",True,'Bluetooth'))

# GraphicsMagick
programs_ubuntu22_04.append(('GraphicsMagick (6.0 MB)',
"""sudo apt-get install -y graphicsmagick-imagemagick-compat
########## Verify ##########
gm -help
""",True,'SDR'))

# Spectrum Painter
programs_ubuntu22_04.append(('Spectrum Painter (13.8 MB)',
"""sudo python3 -m pip install numpy imageio 
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/polygon/spectrum_painter.git
#cd spectrum_painter/
#pip3 install --user -e .  # call with "python3 -m spectrum_painter.img2iqstream"
""",True,'SDR'))

# nrsc5 and nrsc5-gui
programs_ubuntu22_04.append(('nrsc5 (116.2 MB)',
"""sudo apt install -y git build-essential cmake autoconf libtool libao-dev libfftw3-dev librtlsdr-dev libgsl-dev python3-pyaudio
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/theori-io/nrsc5.git
cd nrsc5
mkdir build
cd build
cmake ..
make
sudo make install
sudo ldconfig
# nrsc5-gui
python3 -m pip install --upgrade Pillow
python3 -m pip install pyaudio
sudo apt-get install -y python-gobject
cd ~/Installed_by_FISSURE
git clone https://github.com/cmnybo/nrsc5-gui.git
########## Verify ##########
nrsc5 -v
""",True,'HD Radio'))

# HAM2MON
programs_ubuntu22_04.append(('HAM2MON (901.1 kB)',
"""mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/bkerler/ham2mon.git
cp -f """ + fissure_directory + """/Tools/ham2mon/cursesgui.py ~/Installed_by_FISSURE/ham2mon/apps/
""",True,'Ham Radio'))

# Anki
programs_ubuntu22_04.append(('Anki (223.5 MB)',
"""sudo apt-get install -y anki
########## Verify ##########
anki -h
""",True,'Ham Radio'))

# Bless
programs_ubuntu22_04.append(('Bless (4.00 kB)',
"""sudo apt-get install -y snapd
sudo snap install bless-unofficial
########## Verify ##########
snap list bless-unofficial
""",True,'Data'))

# trackerjacker - Fix (needs newer scapy version, something else (netattack2?) resets it, some pieces don't work while running it)
programs_ubuntu22_04.append(('trackerjacker',
"""sudo ln -s -f /usr/lib/x86_64-linux-gnu/libc.a /usr/lib/x86_64-linux-gnu/liblibc.a  # Python3.9 missing file
sudo sed -i 's/tostring/tobytes/g' /usr/local/lib/python3.10/dist-packages/scapy/arch/linux.py
sudo python3 -m pip install trackerjacker
########## Verify ##########
sudo trackerjacker --help
""",True,'802.11'))

# airgeddon
programs_ubuntu22_04.append(('airgeddon (222.1 MB)',
"""sudo apt-get install -y crunch mdk3 hostapd lighttpd ruby-dev xterm isc-dhcp-server ettercap-text-only john
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone --depth 1 https://github.com/v1s1t0r1sh3r3/airgeddon.git
#asleap
mkdir asleap
cd asleap
wget http://http.kali.org/pool/main/a/asleap/asleap_2.3~git20201128.254acab-0kali1_amd64.deb
sudo dpkg -i asleap_2.3~git20201128.254acab-0kali1_amd64.deb
#bettercap
sudo apt-get install -y build-essential libpcap-dev net-tools 
cd ~/Installed_by_FISSURE
mkdir bettercap
cd bettercap
wget https://github.com/bettercap/bettercap/releases/download/v2.31.1/bettercap_linux_amd64_v2.31.1.zip
unzip -q bettercap_linux_amd64_v2.31.1.zip
rm bettercap_linux_amd64_v2.31.1.zip
sudo cp bettercap /usr/bin/
#mdk4
sudo apt-get install -y libnl-genl-3-dev
cd ~/Installed_by_FISSURE
git clone https://github.com/aircrack-ng/mdk4
cd mdk4
make
sudo make install
""",True,'802.11'))

# Hydra
programs_ubuntu22_04.append(('Hydra (13.3 MB)',
"""sudo apt-get install -y hydra
########## Verify ##########
ls /usr/bin/hydra
""",True,'SSH'))

# Enscribe
programs_ubuntu22_04.append(('Enscribe (90.1 MB)',
"""sudo apt-get install -y enscribe
########## Verify ##########
ls /usr/bin/enscribe
""",True,'Audio'))

# ESP32 Bluetooth Classic Sniffer
programs_ubuntu22_04.append(('ESP32 BT Classic Sniffer (400.0 MB)',
"""# Now contains errors caused by newer wireshark versions. Not supporting this until it is fixed.
mkdir -p ~/Installed_by_FISSURE  # Requires Wireshark 3.4 by default, modifying it for 3.6.5, 4.0.3, 4.2.5
cd ~/Installed_by_FISSURE
git clone https://github.com/Matheus-Garbelini/esp32_bluetooth_classic_sniffer
cd esp32_bluetooth_classic_sniffer
#rm ./dissectors/config.h  # Produces errors if missing
sed -i 's/VERSION "3.4.0"/VERSION "4.2.5"/g' ./dissectors/config.h
sed -i 's/VERSION_MAJOR 3/VERSION_MAJOR 4/g' ./dissectors/config.h
sed -i 's/VERSION_MINOR 4/VERSION_MINOR 2/g' ./dissectors/config.h
sed -i 's/VERSION_MICRO 0/VERSION_MICRO 5/g' ./dissectors/config.h
sed -i 's/PLUGIN_PATH_ID "3.4"/PLUGIN_PATH_ID "4.2"/g' ./dissectors/config.h
sed -i 's/Bluetooth Link Manager Protocol/ESP32 Bluetooth Link Manager Protocol/g' ./dissectors/packet-btbrlmp.c
sed -i 's/btlmp/esp32_btlmp/g' ./dissectors/packet-btbrlmp.c
sed -i 's/3.4/4.2/g' ./dissectors/build.sh
sudo ./requirements.sh
./build.sh
sudo cp dissectors/h4bcm.so /usr/lib/x86_64-linux-gnu/wireshark/plugins/4.2/epan/  # Placing it where "sudo Wireshark" dissectors are located
rm ~/.local/lib/wireshark/plugins/4.2/epan/h4bcm.so  # To avoid "plugin 'h4bcm.so' was found in multiple directories" warning
########## Verify ##########
ls /usr/lib/x86_64-linux-gnu/wireshark/plugins/4.2/epan/h4bcm.so
""",False,'Bluetooth'))

# SigDigger
programs_ubuntu22_04.append(('SigDigger (48.00 kB)',
"""sudo apt-get install -y libsndfile1-dev libfftw3-dev qmake6 soapysdr-tools libsoapysdr-dev fuse
mkdir -p ~/Installed_by_FISSURE/SigDigger
cd ~/Installed_by_FISSURE/SigDigger
wget https://github.com/BatchDrake/SigDigger/releases/download/v0.3.0/SigDigger-0.3.0-x86_64-full.AppImage  # Needs newer version of QMake. Above 5.12.8, 5.14?
chmod a+x SigDigger-0.3.0-x86_64-full.AppImage
########## Verify ##########
ls ~/Installed_by_FISSURE/SigDigger/SigDigger-0.3.0-x86_64-full.AppImage
""",True,'SDR'))

# QSSTV
programs_ubuntu22_04.append(('QSSTV (2.8 MB)',
"""sudo apt-get install -y qsstv
########## Verify ##########
ls /usr/bin/qsstv
""",True,'Ham Radio'))

# m17-cxx-demod
programs_ubuntu22_04.append(('m17-cxx-demod (21.8 MB)',
"""sudo apt-get install -y libcodec2-dev libboost-dev libgtest-dev
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://bitbucket.org/blaze-lib/blaze.git
sudo mkdir -p /usr/local/include/blaze
sudo cp -r blaze/blaze /usr/local/include/
cd ~/Installed_by_FISSURE
git clone https://github.com/mobilinkd/m17-cxx-demod.git
cd m17-cxx-demod/
mkdir build
cd build
cmake ..
make
sudo make install
########## Verify ##########
ls /usr/local/bin/m17-demod
""",True,'M17'))

# Fldigi
programs_ubuntu22_04.append(('Fldigi (15.1 MB)',
"""sudo apt-get install -y fldigi
########## Verify ##########
ls /usr/bin/fldigi
""",True,'Ham Radio'))

# pyFDA
programs_ubuntu22_04.append(('pyFDA (11.7 MB)',
"""sudo python3 -m pip install pyfda --use-pep517  # Has PEP issues with Python 3.10
########## Verify ##########
pyfdax -h
""",True,'Filters'))

# Bootable USB
programs_ubuntu22_04.append(('Bootable USB (107.4 MB)',
"""sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 382003C2C8B7B4AB813E915B14E4942973C62A1B
sudo add-apt-repository -y "deb http://ppa.launchpad.net/nemh/systemback/ubuntu xenial main"
sudo apt update
sudo apt install -y systemback
sudo add-apt-repository -y ppa:mkusb/ppa
sudo apt-get update
sudo apt-get install -y mkusb usb-pack-efi mkusb-plug guidus
########## Verify ##########
ls /usr/bin/systemback && ls /usr/bin/guidus
""",True,'Development'))

# Dire Wolf
programs_ubuntu22_04.append(('Dire Wolf (207.8 MB)',
"""sudo apt-get -y install git gcc g++ make cmake libasound2-dev libudev-dev
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://www.github.com/wb2osz/direwolf
cd direwolf
git checkout dev
mkdir build && cd build
cmake ..
make -j4
sudo make install
make install-conf
########## Verify ##########
ls /usr/local/bin/direwolf
""",True,'Ham Radio'))

# Meld
programs_ubuntu22_04.append(('Meld (9.4 MB)',
"""sudo apt-get -y install meld
########## Verify ##########
ls /usr/bin/meld
""",True,'Data'))

# nwdiag
programs_ubuntu22_04.append(('nwdiag (30.3 MB)',
"""sudo python3 -m pip install nwdiag
########## Verify ##########
packetdiag -h
""",True,'Data'))

# HamClock
programs_ubuntu22_04.append(('HamClock (41.2 MB)',
"""mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
wget https://www.clearskyinstitute.com/ham/HamClock/ESPHamClock.zip
unzip -q ESPHamClock.zip
rm ESPHamClock.zip
cd ESPHamClock
make install hamclock-1600x960
sudo make install hamclock-1600x960
########## Verify ##########
ls /usr/local/bin/hamclock
""",True,'Ham Radio'))

# ICE9 Bluetooth Sniffer
programs_ubuntu22_04.append(('ICE9 Bluetooth Sniffer (10.4 MB)',
docker stop $(docker ps -q --filter ancestor=ghcr.io/iqengine/iqengine:pre)
########## Verify ##########
sudo docker run hello-world
""",True,'Data'))

# TAK Server
programs_ubuntu22_04.append(('TAK Server',
"""# Create TAK.gov account and download TAKSERVER-DOCKER-#.#-RELEASE-##.ZIP from https://tak.gov/products/tak-server
# Place ZIP file in ~/Installed_by_FISSURE folder and then run this installer item!

if command -v docker > /dev/null 2>&1; then
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

# Unzip and move into the extracted directory
unzip takserver-docker-*.zip
if [ -n "$(find . -maxdepth 1 -type d -name 'takserver-docker-*' -print -quit)" ]; then
    cd takserver-docker-*/

    # Ensure CoreConfig.xml exists
    [ ! -f tak/CoreConfig.xml ] && cp tak/CoreConfig.example.xml tak/CoreConfig.xml

    # Set database password
    sed -i 's/password=""/password="atakatak"/' tak/CoreConfig.xml

    # Build and start the database
    sudo docker build -t takserver-db:"$(cat tak/version.txt)" -f docker/Dockerfile.takserver-db .
    sudo docker network create takserver-"$(cat tak/version.txt)"

    # Set executable permissions for necessary scripts
    chmod +x tak/db-utils/configureInDocker.sh
    chmod +x tak/certs/makeRootCa.sh
    chmod +x tak/certs/makeCert.sh

    sudo docker run -d \
      -v $(pwd)/tak:/opt/tak:z \
      -p 5432:5432 \
      --network takserver-"$(cat tak/version.txt)" \
      --network-alias tak-database \
      --name takserver-db-"$(cat tak/version.txt)" \
      takserver-db:"$(cat tak/version.txt)"

    # Wait for the database to be fully ready
    echo "Waiting for PostgreSQL to be ready..."
    until sudo docker exec takserver-db-"$(cat tak/version.txt)" psql -U martiuser -d cot -c "SELECT 1;" &>/dev/null; do
        sleep 3
        echo "Waiting for database..."
    done
    echo "Database is ready!"

    # Build and start TAK Server
    sudo docker build -t takserver:"$(cat tak/version.txt)" -f docker/Dockerfile.takserver .
    sudo docker run -d \
      -v $(pwd)/tak:/opt/tak:z \
      -p 8089:8089 -p 8443:8443 -p 8444:8444 -p 8446:8446 -p 9000:9000 -p 9001:9001 \
      --network takserver-"$(cat tak/version.txt)" \
      --name takserver-"$(cat tak/version.txt)" \
      takserver:"$(cat tak/version.txt)"

    # Modify certificate metadata
    sed -i 's/^STATE=.*/STATE="test_state"/' tak/certs/cert-metadata.sh
    sed -i 's/^CITY=.*/CITY="test_city"/' tak/certs/cert-metadata.sh
    sed -i 's/^ORGANIZATIONAL_UNIT=.*/ORGANIZATIONAL_UNIT="test_organization"/' tak/certs/cert-metadata.sh
    sed -i 's/^ORGANIZATION=.*/ORGANIZATION="test_org"/' tak/certs/cert-metadata.sh

    # Generate Root CA
    sudo docker exec takserver-"$(cat tak/version.txt)" bash -c "cd /opt/tak/certs && ./makeRootCa.sh"

    # Ensure CA certificate exists before continuing
    sudo docker exec takserver-"$(cat tak/version.txt)" bash -c "test -f /opt/tak/certs/files/ca.pem || (echo 'CA generation failed!' && exit 1)"

    # Generate Certificates
    sudo docker exec takserver-"$(cat tak/version.txt)" bash -c "cd /opt/tak/certs && ./makeCert.sh server takserver"
    sudo docker exec takserver-"$(cat tak/version.txt)" bash -c "cd /opt/tak/certs && ./makeCert.sh client admin"
    sudo docker exec takserver-"$(cat tak/version.txt)" bash -c "cd /opt/tak/certs && ./makeCert.sh client webadmin"

    # Ensure directories have correct permissions
    sudo find ~/Installed_by_FISSURE/takserver-docker-*/tak/certs/files/ -type d -exec chmod 755 {} +
      
    sudo openssl rsa -in "$(find ~/Installed_by_FISSURE/takserver-docker-*/tak/certs/files/ -name 'takserver.key' | head -n 1)" \
        -out "$(find ~/Installed_by_FISSURE/takserver-docker-*/tak/certs/files/ -type d | head -n 1)/takserver.key.unencrypted" \
        -passin pass:"atakatak"

    sudo mv "$(ls -d ~/Installed_by_FISSURE/takserver-docker-*/tak/certs/files | head -n 1)/takserver.key.unencrypted" \
      "$(ls -d ~/Installed_by_FISSURE/takserver-docker-*/tak/certs/files | head -n 1)/takserver.key"

    # Set ownership for all certificate-related files to the current user
    sudo find ~/Installed_by_FISSURE/takserver-docker-*/tak/certs/files/ -type f -exec chown $USER:$USER {} +
    sudo find ~/Installed_by_FISSURE/takserver-docker-*/tak/certs/files/ -type d -exec chown $USER:$USER {} +

    # Set proper permissions for private keys
    sudo find ~/Installed_by_FISSURE/takserver-docker-*/tak/certs/files/ -type f -name "*.key" -exec chmod 644 {} +

    # Set correct permissions for other certificate files
    sudo find ~/Installed_by_FISSURE/takserver-docker-*/tak/certs/files/ -type f -not -name "*.key" -exec chmod 644 {} +

    # Restart TAK Server to apply changes
    sudo docker restart takserver-"$(cat tak/version.txt)"

    # Copy takserver.key and takserver.pem to FISSURE Config Files
    cd """ + fissure_directory + """
    PYTHONPATH=""" + fissure_directory + """ python3 fissure/utils/tak_yaml_key_insert.py \
    "$(find ~/Installed_by_FISSURE/takserver-docker-*/tak/certs/files/ -name 'takserver.key' | head -n 1)" \
    "$(find ~/Installed_by_FISSURE/takserver-docker-*/tak/certs/files/ -name 'takserver.pem' | head -n 1)" \
    "$(find ~/Installed_by_FISSURE/takserver-docker-*/tak/certs/files/ -name 'webadmin.p12' | head -n 1)" \
    "$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' takserver-5.3-RELEASE-24)"

    # Import webadmin.p12:

    # Google Chrome/Edge
    # Open chrome://settings/certificates in your browser.
    # Go to the "Your certificates" tab.
    # Click "Import".
    # Select /home/cups-pk-helper/webadmin.p12.
    # Enter the password (default: atakatak, unless changed).
    # Complete the import and restart your browser.

    # Mozilla Firefox
    # Open about:preferences#privacy in the Firefox address bar.
    # Scroll down to Certificates and click "View Certificates".
    # Go to the "Your Certificates" tab.
    # Click "Import".
    # Select /home/cups-pk-helper/webadmin.p12 and enter the password (atakatak).
    # Restart Firefox.

    # To Remove TAK:
    # docker ps -a | grep takserver
    # docker rm -f $(docker ps -aq --filter "name=takserver")
    # docker rm -f $(docker ps -aq --filter "name=takserver-db")
    # docker ps -a
    # docker images | grep takserver
    # docker rmi -f $(docker images -q takserver)
    # docker rmi -f $(docker images -q takserver-db)
    # docker images
    # docker network ls | grep takserver
    # docker network rm $(docker network ls --filter "name=takserver" -q)
    # sudo rm -rf ~/Installed_by_FISSURE/takserver-docker-*/

    echo ""
    echo "TAK Server setup complete! Import webadmin.p12 certificate via browser. Access WebTAK at https://localhost:8443"
    echo ""
else
    echo "TAK Server zip extraction failed or extracted folder not found. Exiting."
fi

########## Verify ##########
ls "$(find ~/Installed_by_FISSURE/takserver-docker-*/tak/certs/files/ -name 'webadmin.p12' | head -n 1)"

# fissure Commands 
programs_ubuntu22_04_arm.append(('fissure Commands',
f"""mkdir -p ~/.local/bin
if grep -Fq "~/.local/bin" ~/.bashrc
then
  echo "~/.local/bin is already in ~/.bashrc"
else
  printf "\\n%s\\n" "export PATH=~/.local/bin:$PATH" >> ~/.bashrc
fi

# Create fissure command
/bin/echo -e "export PYTHONPATH=$PYTHONPATH:{fissure_directory} \ncd {fissure_directory} \npython3 {fissure_directory}/fissure/Dashboard/__main__.py" > ~/.local/bin/fissure
sudo chmod +x ~/.local/bin/fissure

# Create fissure-sensor-node command
/bin/echo -e "export PYTHONPATH=$PYTHONPATH:{fissure_directory} \ncd {fissure_directory} \npython3 {fissure_directory}/fissure/Sensor_Node/SensorNode.py" > ~/.local/bin/fissure-sensor-node
sudo chmod +x ~/.local/bin/fissure-sensor-node

# Create desktop entry for FISSURE
echo "[Desktop Entry]\\nStartupWMClass=__main__.py\\nName=FISSURE\\nTerminal=false\\nType=Application\nCategories=Qt;Science;DataVisualization;Electricity;HamRadio;" > {fissure_directory}/Installer/fissure.desktop
echo "Exec=/home/$USER/.local/bin/fissure" >> {fissure_directory}/Installer/fissure.desktop
echo "Icon={fissure_directory}/docs/Icons/logo_f.png" >> {fissure_directory}/Installer/fissure.desktop
sudo cp {fissure_directory}/Installer/fissure.desktop /usr/share/applications/

# Reload bashrc to update PATH
. ~/.bashrc

########## Verify ##########
ls ~/.local/bin/fissure ~/.local/bin/fissure-sensor-node
""", True, 'Minimum Install'))

# Password Prompt Exceptions
programs_ubuntu22_04_arm.append(('Password Prompt Exceptions',
f"""# Replace placeholder in the template file directly into a temporary file
sed "s/__USERNAME__/$(whoami)/g" "{fissure_directory}/Installer/password_prompt_exceptions.txt" > /tmp/password_prompt_exceptions

# Validate the temporary sudoers file
echo "Validating sudoers file..."
if visudo -c -f /tmp/password_prompt_exceptions; then
    echo "Validation successful. Installing sudoers file..."
    sudo mv /tmp/password_prompt_exceptions /etc/sudoers.d/fissure
    sudo chown root:root /etc/sudoers.d/fissure
    sudo chmod 440 /etc/sudoers.d/fissure
    echo "No Password Prompts Setup completed successfully!"
else
    echo "Validation failed! Not installing the sudoers file to avoid system issues."
    rm /tmp/password_prompt_exceptions
fi
########## Verify ##########
ls -l /etc/sudoers.d/fissure
""", True, 'Minimum Install'))

# GNU Radio
programs_ubuntu22_04_arm.append(('GNU Radio (1.3 GB)',
"""sudo add-apt-repository -y ppa:gnuradio/gnuradio-releases
sudo apt-get update
sudo apt-get install -y gnuradio  # =3.10.5.1-0~gnuradio~jammy-2  # Check for changes here: https://launchpad.net/~gnuradio/+archive/ubuntu/gnuradio-releases
# srsRAN_4G/srsRAN/srsLTE
programs_ubuntu22_04_arm.append(('srsRAN_4G',
"""sudo apt-get install -y build-essential cmake net-tools libfftw3-dev libmbedtls-dev libboost-program-options-dev libconfig++-dev libsctp-dev gcc-11 g++-11
sudo apt-get install -y libboost-system-dev libboost-test-dev libboost-thread-dev libqwt-qt5-dev qtbase5-dev  # srsGUI
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/srsLTE/srsGUI.git
cd srsGUI
mkdir build
cd build
export CC=$(which gcc-11)
export CXX=$(which g++-11)
cmake ..
make
sudo make install
cd ~/Installed_by_FISSURE
git clone https://github.com/srsRAN/srsRAN_4G.git
cp """ + fissure_directory + """/Tools/IMSI-Catcher_4G/cell_search.c ~/Installed_by_FISSURE/srsRAN_4G/lib/examples/  # IMSI-Catcher 4G
cd srsRAN_4G/
mkdir build
cd build
cmake ..
make
sudo make install
sudo ldconfig
sudo srsran_install_configs.sh user  # user or service, not username
cd ../..
mkdir -p ~/.config/srsran
sudo cp -f """ + fissure_directory + """/Tools/srsRAN_configs/* ~/.config/srsran/
sudo chown -R $USER:$USER ~/.config/srsran     # IMSI-Catcher 4G
sudo apt-get install -y fortune cowsay lolcat  # IMSI-Catcher 4G
# cd srsRAN/srsepc
# interface=$(route | awk '/default/ {print $0}' | awk 'END {print $(NF)}')
# sudo ./srsepc_if_masq.sh "$interface"
# gnome-terminal --tab --title="srsEPC" -- /bin/sh -c 'sudo srsepc; $SHELL' 
# gnome-terminal --tab --title="srsENB" -- /bin/sh -c 'sudo srsenb; $SHELL'
########## Verify ##########
srsenb --help
""",True,'LTE'))

# FALCON - FIX (needs older soapysdr version?)
programs_ubuntu22_04_arm.append(('FALCON',
"""sudo apt-get install -y build-essential git cmake libfftw3-dev libmbedtls-dev libboost-program-options-dev libconfig++-dev libsctp-dev  # For srsLTE
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
sudo apt-get install -y libglib2.0-dev libudev-dev libcurl4-gnutls-dev libboost-all-dev qtdeclarative5-dev libqt5charts5-dev  # FALCON
git clone https://github.com/falkenber9/falcon.git
cd falcon
mkdir build
cd build
cmake -DFORCE_SUBPROJECT_SRSLTE=ON -DCMAKE_INSTALL_PREFIX=/usr ../
make
sudo make install
#sudo xargs rm < install_manifest.txt  # uninstall
#make clean
########## Verify ##########
ls /usr/bin/FalconGUI
""",False,'LTE'))

# LTE-ciphercheck - Fix
programs_ubuntu22_04_arm.append(('LTE-ciphercheck',
git clone https://github.com/mrlnc/LTE-ciphercheck  # No 22.04 version yet.
cd LTE-ciphercheck
mkdir build 
cd build
cmake ..
make srsue
sudo ldconfig
cp """ + fissure_directory + """/Tools/LTE-ciphercheck/ciphercheck.conf ../srsue/ciphercheck.conf 
""",False,'LTE'))

# Aircrack-ng
programs_ubuntu22_04_arm.append(('Aircrack-ng (20.4 MB)',
"""sudo apt-get install -y aircrack-ng
########## Verify ##########
aircrack-ng --help
""",True,'802.11'))

# Geany
programs_ubuntu22_04_arm.append(('Geany (16.4 MB)',
"""sudo apt-get install -y geany
########## Verify ##########
geany --help
""",True,'Development'))

# Arduino IDE
programs_ubuntu22_04_arm.append(('Arduino IDE (630.3 MB)',
"""wget -P ~/Installed_by_FISSURE/ https://downloads.arduino.cc/arduino-1.8.15-linux64.tar.xz
cd ~/Installed_by_FISSURE
tar -xf arduino-1.8.15-linux64.tar.xz
rm arduino-1.8.15-linux64.tar.xz
cd arduino-1.8.15/
sudo ./install.sh
cp -R """ + fissure_directory + """/Tools/Esp8266_listen_trigger/ ~/Installed_by_FISSURE/
########## Verify ##########
arduino --version
""",True,'Development'))

# Minicom
programs_ubuntu22_04_arm.append(('Minicom (2.1 MB)',
"""sudo apt-get install -y minicom
########## Verify ##########
ls /usr/bin/minicom
""",True,'Hardware'))

# PuTTY
programs_ubuntu22_04_arm.append(('PuTTY (6.4 MB)',
"""sudo apt-get install -y putty
########## Verify ##########
putty --help
""",True,'Hardware'))

# openHAB - FIX
programs_ubuntu22_04_arm.append(('openHAB (616.9 MB)',
"""sudo apt-get -yq install gnupg curl
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 0xB1998361219BD9C9
cd ~/Downloads
curl -O https://cdn.azul.com/zulu/bin/zulu-repo_1.0.0-2_all.deb
sudo apt-get install ./zulu-repo_1.0.0-2_all.deb
sudo apt-get update
sudo apt-get install -y zulu11-jdk
rm zulu-repo_1.0.0-2_all.deb
wget -qO - 'https://openhab.jfrog.io/artifactory/api/gpg/key/public' | sudo apt-key add -
sudo apt-get install -y apt-transport-https
echo 'deb https://openhab.jfrog.io/artifactory/openhab-linuxpkg stable main' | sudo tee /etc/apt/sources.list.d/openhab.list
sudo apt-get update 
sudo apt-get install -y openhab
########## Verify ##########
ls /usr/bin/openhab-cli
""",True,'Z-Wave'))

# rtl-zwave
programs_ubuntu22_04_arm.append(('rtl-zwave (106.5 kB)',
"""mkdir -p ~/Installed_by_FISSURE
sudo apt-get install -y libpcap-dev
cp -R """ + fissure_directory + """/Tools/rtl-zwave-master ~/Installed_by_FISSURE/
cd ~/Installed_by_FISSURE/rtl-zwave-master
make
########## Verify ##########
ls ~/Installed_by_FISSURE/rtl-zwave-master/rtl_zwave
""",True,'Z-Wave'))

# waving-z
programs_ubuntu22_04_arm.append(('waving-z (2.3 MB)',
"""mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE/
git clone https://github.com/baol/waving-z.git
cd ~/Installed_by_FISSURE/waving-z
mkdir build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build .
########## Verify ##########
ls ~/Installed_by_FISSURE/waving-z/build/wave-in
""",True,'Z-Wave'))

# baudline
programs_ubuntu22_04_arm.append(('baudline (4.9 MB)',
"""mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
wget -P ~/Installed_by_FISSURE/ https://www.baudline.com/baudline_1.08_linux_x86_64.tar.gz  # They removed this file. We are not allowed to distribute source.
tar -xf baudline_1.08_linux_x86_64.tar.gz
rm baudline_1.08_linux_x86_64.tar.gz
########## Verify ##########
~/Installed_by_FISSURE/baudline_1.08_linux_x86_64/baudline --help
""",False,'SDR'))

# Universal Radio Hacker
programs_ubuntu22_04_arm.append(('Universal Radio Hacker (129.2 MB)',
"""sudo python3 -m pip install cython
sudo python3 -m pip install urh
########## Verify ##########
urh --version
""",True,'SDR'))

# Inspectrum
programs_ubuntu22_04_arm.append(('Inspectrum (1.8 MB)',
"""sudo apt-get install -y inspectrum
########## Verify ##########
inspectrum --help
""",True,'SDR'))

# OpenCPN
programs_ubuntu22_04_arm.append(('OpenCPN (209.3 MB)',
"""sudo add-apt-repository -y ppa:opencpn/opencpn
sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys C865EB40  # FIX
sudo apt-get update
sudo apt-get install -y opencpn
########## Verify ##########
ls /usr/bin/opencpn
""",True,'AIS'))

# Kalibrate
programs_ubuntu22_04_arm.append(('Kalibrate (2.1 MB)',
"""mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/steve-m/kalibrate-rtl.git
cd kalibrate-rtl
./bootstrap && CXXFLAGS='-W -Wall -O3' ./configure && make
########## Verify ##########
ls ~/Installed_by_FISSURE/kalibrate-rtl/src/kal
""",True,'GSM'))

# retrogram-rtlsdr
programs_ubuntu22_04_arm.append(('retrogram-rtlsdr (1.7 MB)',
"""mkdir -p ~/Installed_by_FISSURE
sudo apt-get install -y librtlsdr-dev libncurses5-dev libboost-program-options-dev
cp -R """ + fissure_directory + """/Tools/retrogram-rtlsdr-master ~/Installed_by_FISSURE/
cd ~/Installed_by_FISSURE/retrogram-rtlsdr-master
make
########## Verify ##########
ls ~/Installed_by_FISSURE/retrogram-rtlsdr-master/retrogram-rtlsdr
""",True,'SDR'))

# RTLSDR-Airband
programs_ubuntu22_04_arm.append(('RTLSDR-Airband (7.0 MB)',
"""sudo apt-get install -y build-essential cmake pkg-config libmp3lame-dev libshout3-dev libconfig++-dev libfftw3-dev libpulse-dev
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/szpajder/RTLSDR-Airband.git
cd RTLSDR-Airband
mkdir build
cd build
cmake ../
make
sudo make install
########## Verify ##########
rtl_airband -h
""",True,'SDR'))

# Spektrum
programs_ubuntu22_04_arm.append(('Spektrum (241.9 MB)',
"""echo 'blacklist dvb_usb_rtl28xxu' | sudo tee /etc/modprobe.d/rtl-sdr.conf  # Restart computer to use RTL device
echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2838", GROUP="adm", MODE="0666"' | sudo tee /etc/udev/rules.d/20.rtlsdr.rules
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
wget -P ~/Installed_by_FISSURE/ https://github.com/pavels/spektrum/releases/download/2.1.0/spektrum-linux64.tar.gz
tar -xf spektrum-linux64.tar.gz
rm spektrum-linux64.tar.gz
########## Verify ##########
ls ~/Installed_by_FISSURE/spektrum/spektrum
""",True,'SDR'))

# SDRTrunk
programs_ubuntu22_04_arm.append(('SDRTrunk (106.9 MB)',
"""#sudo apt-get -yq install gnupg curl  # Java (if needed)
#sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 0xB1998361219BD9C9
#cd ~/Downloads
#curl -O https://cdn.azul.com/zulu/bin/zulu-repo_1.0.0-2_all.deb
#sudo apt-get install ./zulu-repo_1.0.0-2_all.deb
#sudo apt-get update
#sudo apt-get install -y zulu11-jdk
#rm zulu-repo_1.0.0-2_all.deb
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
wget -P ~/Installed_by_FISSURE/ https://github.com/DSheirer/sdrtrunk/releases/download/v0.5.0-alpha.6/sdr-trunk-linux-x86_64-v0.5.0-alpha6.zip
unzip -q sdr-trunk-linux-x86_64-v0.5.0-alpha6.zip
rm sdr-trunk-linux-x86_64-v0.5.0-alpha6.zip
########## Verify ##########
ls ~/Installed_by_FISSURE/sdr-trunk-linux-x86_64-v0.5.0-alpha6/bin/sdr-trunk
""",True,'Trunked Radio'))

# Audacity
programs_ubuntu22_04_arm.append(('Audacity (38.8 MB)',
"""sudo apt-get install -y audacity
########## Verify ##########
audacity --version
""",True,'Audio'))

# Sound eXchange
programs_ubuntu22_04_arm.append(('Sound eXchange (2.3 MB)',
"""sudo apt-get install -y sox
########## Verify ##########
sox --version
""",True,'Audio'))

# LAME
programs_ubuntu22_04_arm.append(('LAME (286.8 kB)',
"""sudo apt-get install -y lame
########## Verify ##########
lame --version
""",True,'Audio'))

# mpv
programs_ubuntu22_04_arm.append(('mpv (174.7 MB)',
"""sudo apt-get install -y mpv
########## Verify ##########
mpv --version
""",True,'Audio'))

# FFmpeg
programs_ubuntu22_04_arm.append(('FFmpeg (114.7 kB)',
"""sudo apt-get install -y ffmpeg 
########## Verify ##########
ffmpeg --help
""",True,'Audio'))

# MPlayer
programs_ubuntu22_04_arm.append(('MPlayer (10.4 MB)',
"""sudo apt-get install -y mplayer
########## Verify ##########
ls /usr/bin/mplayer
""",True,'Audio'))

# VLC
programs_ubuntu22_04_arm.append(('VLC (402.1 MB)',
"""sudo apt-get install -y vlc
########## Verify ##########
vlc --help
""",True,'Video'))

# Simple Screen Recorder
programs_ubuntu22_04_arm.append(('Simple Screen Recorder (5.6 MB)',
"""sudo apt-get install -y simplescreenrecorder
########## Verify ##########
simplescreenrecorder --help
""",False,'Video'))

# radiosonde_auto_rx
programs_ubuntu22_04_arm.append(('radiosonde_auto_rx (82.4 MB)',
"""sudo apt-get install -y python3 python3-numpy python3-setuptools python3-crcmod python3-requests python3-dateutil python3-pip python3-flask sox git build-essential libtool cmake usbutils libusb-1.0-0-dev rng-tools libsamplerate-dev libatlas3-base libgfortran5
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/projecthorus/radiosonde_auto_rx.git
cd radiosonde_auto_rx/auto_rx
./build.sh
cp station.cfg.example station.cfg
sudo python3 -m pip install -r requirements.txt
########## Verify ##########
ls ~/Installed_by_FISSURE/radiosonde_auto_rx/auto_rx/auto_rx.py
""",True,'Radiosonde'))

# SdrGlut
programs_ubuntu22_04_arm.append(('SdrGlut',
"""sudo apt-get install -y build-essential libwxgtk3.2-dev libglew-dev libusb-dev libsoapysdr-dev libopenal-dev libliquid-dev freeglut3-dev libalut-dev libsndfile1-dev librtaudio-dev libhdf4-dev libfftw3-dev
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone --depth=1 https://github.com/righthalfplane/SdrGlut.git
cd SdrGlut
make -f makefileUbuntu -j 8
cd iqSDR
make -f makefileUbuntuOLD -j 8
########## Verify ##########
ls ~/Installed_by_FISSURE/SdrGlut/sdrglut.x
""",True,'SDR'))

# rehex
programs_ubuntu22_04_arm.append(('rehex (197.1 MB)',
"""sudo apt-get install -y build-essential git libwxgtk3.0-gtk3-dev libjansson-dev libcapstone-dev liblua5.3-dev lua5.3 lua5.2 libunistring-dev libgtk-3-dev lua-busted libbotan-2-dev
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/solemnwarning/rehex.git
cd rehex
sudo git config --global --add safe.directory """ + os.path.expanduser('~') + """/Installed_by_FISSURE/rehex
yes | sudo cpan Template
sudo make install
########## Verify ##########
ls /usr/local/bin/rehex 
""",True,'Data'))

# ZEPASSD
programs_ubuntu22_04_arm.append(('ZEPASSD (11.6 MB)',
wget http://archive.ubuntu.com/ubuntu/pool/universe/libn/libnetfilter-queue/libnetfilter-queue1_1.0.2-2_amd64.deb
sudo dpkg -i libnetfilter-queue1_1.0.2-2_amd64.deb
wget http://archive.ubuntu.com/ubuntu/pool/universe/n/nfqueue-bindings/python-nfqueue_0.6-1build2_amd64.deb
sudo dpkg -i python-nfqueue_0.6-1build2_amd64.deb 
""",False,'802.11'))

# Wifite
programs_ubuntu22_04_arm.append(('Wifite (797.5 MB)',
"""echo "macchanger macchanger/automatically_run boolean false" | sudo debconf-set-selections
# python, iwconfig, ifconfig, Aircrack-ng, tshark, reaver, bully, coWPAtty, pyrit, hashcat, hcxdumptool, hcxpcaptool
sudo apt-get install -y build-essential libpcap-dev aircrack-ng pixiewps libssl-dev hashcat libcurl4-openssl-dev pkg-config macchanger python-is-python3
sudo python3 -m pip install psycopg2-binary #scapy (python3 scapy with pip causes errors)
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/derv82/wifite2.git
git clone https://github.com/t6x/reaver-wps-fork-t6x
cd reaver-wps-fork-t6x/src
./configure
make
sudo make install
cd ~/Installed_by_FISSURE
git clone https://github.com/aanarchyy/bully
cd bully/src
make
sudo make install
cd ~/Installed_by_FISSURE
wget http://www.willhackforsushi.com/code/cowpatty/4.6/cowpatty-4.6.tgz
tar zxfv cowpatty-4.6.tgz
rm cowpatty-4.6.tgz
cd cowpatty-4.6
make
sudo cp cowpatty /usr/bin
cd ~/Installed_by_FISSURE
mkdir Pyrit-v0.5.0
cd Pyrit-v0.5.0
wget https://github.com/JPaulMora/Pyrit/releases/download/v0.5.0/Pyrit-v0.5.0.zip
unzip -q Pyrit-v0.5.0.zip
rm Pyrit-v0.5.0.zip
sudo apt-get install -y python2-dev
python2 setup.py clean
python2 setup.py build
sudo python2 setup.py install
cd ~/Installed_by_FISSURE
git clone https://github.com/ZerBea/hcxdumptool.git
cd hcxdumptool
make
sudo make install
cd ~/Installed_by_FISSURE
git clone https://github.com/ZerBea/hcxtools.git
cd hcxtools
make
sudo make install
sudo ln -s /usr/bin/hcxpcapngtool /usr/bin/hcxpcaptool
#sudo apt-get install -y tshark
""",True,'802.11'))

# rtl_433
programs_ubuntu22_04_arm.append(('rtl_433 (27.8 MB)',
"""#sudo apt-get install -y rtl-433
sudo apt-get install -y libtool libusb-1.0-0-dev librtlsdr-dev rtl-sdr build-essential cmake pkg-config
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/merbanan/rtl_433.git
cd rtl_433/
mkdir build
cd build
cmake ..
make
sudo make install
########## Verify ##########
rtl_433 -help
""",True,'433 MHz'))

# RouterSploit
programs_ubuntu22_04_arm.append(('RouterSploit (369.3 MB)',
"""sudo apt-get install -y python3-pip libglib2.0-dev rustc
sudo python3 -m pip install setuptools-rust
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://www.github.com/threat9/routersploit
cd routersploit
python3 -m pip install setuptools
python3 -m pip install -r requirements.txt
python3 -m pip install bluepy
########## Verify ##########
~/Installed_by_FISSURE/routersploit/rsf.py --help
""",True,'802.11'))

# Metasploit
programs_ubuntu22_04_arm.append(('Metasploit (1.1 GB)',
"""mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
mkdir metasploit
cd metasploit
curl https://raw.githubusercontent.com/rapid7/metasploit-omnibus/master/config/templates/metasploit-framework-wrappers/msfupdate.erb > msfinstall && chmod 755 msfinstall && ./msfinstall
########## Verify ##########
ls /usr/bin/msfconsole
""",True,'802.11'))

# monitor_rtl433
programs_ubuntu22_04_arm.append(('monitor_rtl433 (54.6 MB)',
"""mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/mcbridejc/monitor_rtl433.git
cd monitor_rtl433
sudo python3 -m pip install . --force-reinstall --ignore-installed
sudo python3 -m pip install python-dateutil
sudo python3 -m pip install flask_table
########## Verify ##########
ls /usr/local/bin/monitor_rtl433
""",True,'433 MHz'))

# scan-ssid
programs_ubuntu22_04_arm.append(('scan-ssid (585.8 kB)',
"""mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
sudo apt-get install -y iw
git clone https://github.com/Resethel/scan-ssid.git
cd scan-ssid
sudo cp scan-ssid /usr/local/bin
sudo chmod 755 /usr/local/bin/scan-ssid  # can't be in monitor mode, managed only
########## Verify ##########
scan-ssid --help
""",True,'802.11'))

# minimodem
programs_ubuntu22_04_arm.append(('minimodem (217.1 kB)',
"""sudo apt-get install -y minimodem
########## Verify ##########
minimodem --version
""",True,'Audio'))

# WSJT-X
programs_ubuntu22_04_arm.append(('WSJT-X (35.2 MB)',
"""sudo apt-get install -y wsjtx
########## Verify ##########
ls /usr/bin/wsjtx
""",True,'Ham Radio'))

# Google Earth Pro
programs_ubuntu22_04_arm.append(('Google Earth Pro (314.6 MB)',
"""mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
wget https://dl.google.com/dl/earth/client/current/google-earth-pro-stable_current_amd64.deb
sudo dpkg -i google-earth-pro-stable_current_amd64.deb
########## Verify ##########
ls /usr/bin/google-earth-pro
""",True,'Mapping'))

# gr-air-modes
programs_ubuntu22_04_arm.append(('gr-air-modes (1.3 MB)',
"""sudo apt-get install -y gr-air-modes
sudo sed -i 's/numpy.float)/numpy.float32)/g' /usr/lib/python3/dist-packages/air_modes/mlat.py  # Deprecated numpy type: np.float->np.float32 or np.float64
########## Verify ##########
modes_rx --help
""",True,'Aircraft'))

# ESP8266 Deauther v2
programs_ubuntu22_04_arm.append(('ESP8266 Deauther v2 (6.6 MB)',
"""mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
wget https://github.com/SpacehuhnTech/esp8266_deauther/archive/v2.zip
unzip -q v2.zip
rm v2.zip
""",True,'802.11'))

# Viking
programs_ubuntu22_04_arm.append(('Viking (531.5 MB)',
"""mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone git://git.code.sf.net/p/viking/code viking
sudo apt install -y gtk-doc-tools docbook-xsl yelp-tools libpng-dev libgtk-3-dev libicu-dev libjson-glib-dev intltool
sudo apt-get install -y libcurl4-gnutls-dev libglib2.0-dev-bin
sudo apt-get install -y libsqlite3-dev nettle-dev libmapnik-dev libgeoclue-2-dev libgexiv2-dev libgps-dev libmagic-dev libbz2-dev libzip-dev liboauth-dev
sudo apt-get install -y autopoint libnova-dev
cd viking
./autogen.sh
./configure
make
sudo make install
########## Verify ##########
viking --help
""",True,'Mapping'))

# PyGPSClient
programs_ubuntu22_04_arm.append(('PyGPSClient (27.3 MB)',
"""sudo apt install -y python3-pip python3-tk python3-pil python3-pil.imagetk
sudo apt remove -y python3-cryptography
sudo python3 -m pip install --upgrade PyGPSClient
########## Verify ##########
ls /usr/local/bin/pygpsclient
""",True,'GPS'))

# Gpredict
programs_ubuntu22_04_arm.append(('Gpredict (17.6 MB)',
"""sudo apt-get install -y gpredict
########## Verify ##########
gpredict --help
""",True,'GPS'))

# FoxtrotGPS
programs_ubuntu22_04_arm.append(('FoxtrotGPS (2.8 MB)',
"""sudo apt-get install -y foxtrotgps
########## Verify ##########
foxtrotgps --help
""",True,'GPS'))

# multimon-ng
programs_ubuntu22_04_arm.append(('multimon-ng (13.6 MB)',
"""sudo apt-get install -y libpulse-dev
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/EliasOenal/multimonNG.git
cd multimonNG
mkdir build
cd build
qmake ../multimon-ng.pro
make
sudo make install
########## Verify ##########
ls /usr/local/bin/multimon-ng
""",True,'POCSAG'))

# Xastir
programs_ubuntu22_04_arm.append(('Xastir (53.3 MB)',
"""echo 'xastir xastir/setuid boolean true' | sudo debconf-set-selections
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y xastir
########## Verify ##########
sudo xastir -V
""",True,'Ham Radio'))

# LTE-Cell-Scanner
programs_ubuntu22_04_arm.append(('LTE-Cell-Scanner (168.1 MB)',
"""sudo apt-get install -y cmake libncurses5-dev liblapack-dev libblas-dev libboost-thread-dev libboost-system-dev libitpp-dev librtlsdr-dev libfftw3-dev
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/JiaoXianjun/LTE-Cell-Scanner.git
cd LTE-Cell-Scanner
mkdir build
cd build
cmake ..
make 
sudo make install
########## Verify ##########
ls /usr/local/bin/CellSearch
""",True,'LTE'))

# btscanner
programs_ubuntu22_04_arm.append(('btscanner (1.3 MB)',
"""sudo apt-get install -y btscanner
########## Verify ##########
btscanner --help
""",True,'Bluetooth'))

# hcidump
programs_ubuntu22_04_arm.append(('hcidump (1.1 MB)',
"""sudo apt-get install -y bluez-hcidump
########## Verify ##########
hcidump --help
""",True,'Bluetooth'))

# GraphicsMagick
programs_ubuntu22_04_arm.append(('GraphicsMagick (6.0 MB)',
"""sudo apt-get install -y graphicsmagick-imagemagick-compat
########## Verify ##########
gm -help
""",True,'SDR'))

# Spectrum Painter
programs_ubuntu22_04_arm.append(('Spectrum Painter (13.8 MB)',
"""sudo python3 -m pip install numpy imageio 
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/polygon/spectrum_painter.git
#cd spectrum_painter/
#pip3 install --user -e .  # call with "python3 -m spectrum_painter.img2iqstream"
""",True,'SDR'))

# nrsc5 and nrsc5-gui
programs_ubuntu22_04_arm.append(('nrsc5 (116.2 MB)',
"""sudo apt install -y git build-essential cmake autoconf libtool libao-dev libfftw3-dev librtlsdr-dev libgsl-dev python3-pyaudio
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/theori-io/nrsc5.git
cd nrsc5
mkdir build
cd build
cmake ..
make
sudo make install
sudo ldconfig
# nrsc5-gui
python3 -m pip install --upgrade Pillow
python3 -m pip install pyaudio
sudo apt-get install -y python-gobject
cd ~/Installed_by_FISSURE
git clone https://github.com/cmnybo/nrsc5-gui.git
########## Verify ##########
nrsc5 -v
""",True,'HD Radio'))

# HAM2MON
programs_ubuntu22_04_arm.append(('HAM2MON (901.1 kB)',
"""mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/bkerler/ham2mon.git
cp -f """ + fissure_directory + """/Tools/ham2mon/cursesgui.py ~/Installed_by_FISSURE/ham2mon/apps/
""",True,'Ham Radio'))

# Anki
programs_ubuntu22_04_arm.append(('Anki (223.5 MB)',
"""sudo apt-get install -y anki
########## Verify ##########
anki -h
""",True,'Ham Radio'))

# Bless
programs_ubuntu22_04_arm.append(('Bless (4.00 kB)',
"""sudo apt-get install -y snapd
sudo snap install bless-unofficial
########## Verify ##########
snap list bless-unofficial
""",True,'Data'))

# trackerjacker - Fix (needs newer scapy version, something else (netattack2?) resets it, some pieces don't work while running it)
programs_ubuntu22_04_arm.append(('trackerjacker',
"""sudo ln -s -f /usr/lib/x86_64-linux-gnu/libc.a /usr/lib/x86_64-linux-gnu/liblibc.a  # Python3.9 missing file
sudo sed -i 's/tostring/tobytes/g' /usr/local/lib/python3.10/dist-packages/scapy/arch/linux.py
sudo python3 -m pip install trackerjacker
########## Verify ##########
sudo trackerjacker --help
""",True,'802.11'))

# airgeddon
programs_ubuntu22_04_arm.append(('airgeddon (222.1 MB)',
"""sudo apt-get install -y crunch mdk3 hostapd lighttpd ruby-dev xterm isc-dhcp-server ettercap-text-only john
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone --depth 1 https://github.com/v1s1t0r1sh3r3/airgeddon.git
#asleap
mkdir asleap
cd asleap
wget http://http.kali.org/pool/main/a/asleap/asleap_2.3~git20201128.254acab-0kali1_amd64.deb
sudo dpkg -i asleap_2.3~git20201128.254acab-0kali1_amd64.deb
#bettercap
sudo apt-get install -y build-essential libpcap-dev net-tools 
cd ~/Installed_by_FISSURE
mkdir bettercap
cd bettercap
wget https://github.com/bettercap/bettercap/releases/download/v2.31.1/bettercap_linux_amd64_v2.31.1.zip
unzip -q bettercap_linux_amd64_v2.31.1.zip
rm bettercap_linux_amd64_v2.31.1.zip
sudo cp bettercap /usr/bin/
#mdk4
sudo apt-get install -y libnl-genl-3-dev
cd ~/Installed_by_FISSURE
git clone https://github.com/aircrack-ng/mdk4
cd mdk4
make
sudo make install
""",True,'802.11'))

# Hydra
programs_ubuntu22_04_arm.append(('Hydra (13.3 MB)',
"""sudo apt-get install -y hydra
########## Verify ##########
ls /usr/bin/hydra
""",True,'SSH'))

# Enscribe
programs_ubuntu22_04_arm.append(('Enscribe (90.1 MB)',
"""sudo apt-get install -y enscribe
########## Verify ##########
ls /usr/bin/enscribe
""",True,'Audio'))

# ESP32 Bluetooth Classic Sniffer
programs_ubuntu22_04_arm.append(('ESP32 BT Classic Sniffer (400.0 MB)',
"""# Now contains errors caused by newer wireshark versions. Not supporting this until it is fixed.
mkdir -p ~/Installed_by_FISSURE  # Requires Wireshark 3.4 by default, modifying it for 3.6.5, 4.0.3, 4.2.5
cd ~/Installed_by_FISSURE
git clone https://github.com/Matheus-Garbelini/esp32_bluetooth_classic_sniffer
cd esp32_bluetooth_classic_sniffer
#rm ./dissectors/config.h  # Produces errors if missing
sed -i 's/VERSION "3.4.0"/VERSION "4.2.5"/g' ./dissectors/config.h
sed -i 's/VERSION_MAJOR 3/VERSION_MAJOR 4/g' ./dissectors/config.h
sed -i 's/VERSION_MINOR 4/VERSION_MINOR 2/g' ./dissectors/config.h
sed -i 's/VERSION_MICRO 0/VERSION_MICRO 5/g' ./dissectors/config.h
sed -i 's/PLUGIN_PATH_ID "3.4"/PLUGIN_PATH_ID "4.2"/g' ./dissectors/config.h
sed -i 's/Bluetooth Link Manager Protocol/ESP32 Bluetooth Link Manager Protocol/g' ./dissectors/packet-btbrlmp.c
sed -i 's/btlmp/esp32_btlmp/g' ./dissectors/packet-btbrlmp.c
sed -i 's/3.4/4.2/g' ./dissectors/build.sh
sudo ./requirements.sh
./build.sh
sudo cp dissectors/h4bcm.so /usr/lib/x86_64-linux-gnu/wireshark/plugins/4.2/epan/  # Placing it where "sudo Wireshark" dissectors are located
rm ~/.local/lib/wireshark/plugins/4.2/epan/h4bcm.so  # To avoid "plugin 'h4bcm.so' was found in multiple directories" warning
########## Verify ##########
ls /usr/lib/x86_64-linux-gnu/wireshark/plugins/4.2/epan/h4bcm.so
""",False,'Bluetooth'))

# SigDigger
programs_ubuntu22_04_arm.append(('SigDigger (48.00 kB)',
"""sudo apt-get install -y libsndfile1-dev libfftw3-dev qmake6 soapysdr-tools libsoapysdr-dev fuse
mkdir -p ~/Installed_by_FISSURE/SigDigger
cd ~/Installed_by_FISSURE/SigDigger
wget https://github.com/BatchDrake/SigDigger/releases/download/v0.3.0/SigDigger-0.3.0-x86_64-full.AppImage  # Needs newer version of QMake. Above 5.12.8, 5.14?
chmod a+x SigDigger-0.3.0-x86_64-full.AppImage
########## Verify ##########
ls ~/Installed_by_FISSURE/SigDigger/SigDigger-0.3.0-x86_64-full.AppImage
""",True,'SDR'))

# QSSTV
programs_ubuntu22_04_arm.append(('QSSTV (2.8 MB)',
"""sudo apt-get install -y qsstv
########## Verify ##########
ls /usr/bin/qsstv
""",True,'Ham Radio'))

# m17-cxx-demod
programs_ubuntu22_04_arm.append(('m17-cxx-demod (21.8 MB)',
"""sudo apt-get install -y libcodec2-dev libboost-dev libgtest-dev
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://bitbucket.org/blaze-lib/blaze.git
sudo mkdir -p /usr/local/include/blaze
sudo cp -r blaze/blaze /usr/local/include/
cd ~/Installed_by_FISSURE
git clone https://github.com/mobilinkd/m17-cxx-demod.git
cd m17-cxx-demod/
mkdir build
cd build
cmake ..
make
sudo make install
########## Verify ##########
ls /usr/local/bin/m17-demod
""",True,'M17'))

# Fldigi
programs_ubuntu22_04_arm.append(('Fldigi (15.1 MB)',
"""sudo apt-get install -y fldigi
########## Verify ##########
ls /usr/bin/fldigi
""",True,'Ham Radio'))

# pyFDA
programs_ubuntu22_04_arm.append(('pyFDA (11.7 MB)',
"""sudo python3 -m pip install pyfda --use-pep517  # Has PEP issues with Python 3.10
########## Verify ##########
pyfdax -h
""",True,'Filters'))

# Bootable USB
programs_ubuntu22_04_arm.append(('Bootable USB (107.4 MB)',
"""sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 382003C2C8B7B4AB813E915B14E4942973C62A1B
sudo add-apt-repository -y "deb http://ppa.launchpad.net/nemh/systemback/ubuntu xenial main"
sudo apt update
sudo apt install -y systemback
sudo add-apt-repository -y ppa:mkusb/ppa
sudo apt-get update
sudo apt-get install -y mkusb usb-pack-efi mkusb-plug guidus
########## Verify ##########
ls /usr/bin/systemback && ls /usr/bin/guidus
""",True,'Development'))

# Dire Wolf
programs_ubuntu22_04_arm.append(('Dire Wolf (207.8 MB)',
"""sudo apt-get -y install git gcc g++ make cmake libasound2-dev libudev-dev
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://www.github.com/wb2osz/direwolf
cd direwolf
git checkout dev
mkdir build && cd build
cmake ..
make -j4
sudo make install
make install-conf
########## Verify ##########
ls /usr/local/bin/direwolf
""",True,'Ham Radio'))

# Meld
programs_ubuntu22_04_arm.append(('Meld (9.4 MB)',
"""sudo apt-get -y install meld
########## Verify ##########
ls /usr/bin/meld
""",True,'Data'))

# nwdiag
programs_ubuntu22_04_arm.append(('nwdiag (30.3 MB)',
"""sudo python3 -m pip install nwdiag
########## Verify ##########
packetdiag -h
""",True,'Data'))

# HamClock
programs_ubuntu22_04_arm.append(('HamClock (41.2 MB)',
"""mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
wget https://www.clearskyinstitute.com/ham/HamClock/ESPHamClock.zip
unzip -q ESPHamClock.zip
rm ESPHamClock.zip
cd ESPHamClock
make install hamclock-1600x960
sudo make install hamclock-1600x960
########## Verify ##########
ls /usr/local/bin/hamclock
""",True,'Ham Radio'))

# ICE9 Bluetooth Sniffer
programs_ubuntu22_04_arm.append(('ICE9 Bluetooth Sniffer (10.4 MB)',
docker stop $(docker ps -q --filter ancestor=ghcr.io/iqengine/iqengine:pre)
########## Verify ##########
sudo docker run hello-world
""",True,'Data'))

# TAK Server
programs_ubuntu22_04_arm.append(('TAK Server',
"""# Create TAK.gov account and download TAKSERVER-DOCKER-#.#-RELEASE-##.ZIP from https://tak.gov/products/tak-server
# Place ZIP file in ~/Installed_by_FISSURE folder and then run this installer item!

if command -v docker > /dev/null 2>&1; then
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

# Unzip and move into the extracted directory
unzip takserver-docker-*.zip
if [ -n "$(find . -maxdepth 1 -type d -name 'takserver-docker-*' -print -quit)" ]; then
    cd takserver-docker-*/

    # Ensure CoreConfig.xml exists
    [ ! -f tak/CoreConfig.xml ] && cp tak/CoreConfig.example.xml tak/CoreConfig.xml

    # Set database password
    sed -i 's/password=""/password="atakatak"/' tak/CoreConfig.xml

    # Build and start the database
    sudo docker build -t takserver-db:"$(cat tak/version.txt)" -f docker/Dockerfile.takserver-db .
    sudo docker network create takserver-"$(cat tak/version.txt)"

    # Set executable permissions for necessary scripts
    chmod +x tak/db-utils/configureInDocker.sh
    chmod +x tak/certs/makeRootCa.sh
    chmod +x tak/certs/makeCert.sh

    sudo docker run -d \
      -v $(pwd)/tak:/opt/tak:z \
      -p 5432:5432 \
      --network takserver-"$(cat tak/version.txt)" \
      --network-alias tak-database \
      --name takserver-db-"$(cat tak/version.txt)" \
      takserver-db:"$(cat tak/version.txt)"

    # Wait for the database to be fully ready
    echo "Waiting for PostgreSQL to be ready..."
    until sudo docker exec takserver-db-"$(cat tak/version.txt)" psql -U martiuser -d cot -c "SELECT 1;" &>/dev/null; do
        sleep 3
        echo "Waiting for database..."
    done
    echo "Database is ready!"

    # Build and start TAK Server
    sudo docker build -t takserver:"$(cat tak/version.txt)" -f docker/Dockerfile.takserver .
    sudo docker run -d \
      -v $(pwd)/tak:/opt/tak:z \
      -p 8089:8089 -p 8443:8443 -p 8444:8444 -p 8446:8446 -p 9000:9000 -p 9001:9001 \
      --network takserver-"$(cat tak/version.txt)" \
      --name takserver-"$(cat tak/version.txt)" \
      takserver:"$(cat tak/version.txt)"

    # Modify certificate metadata
    sed -i 's/^STATE=.*/STATE="test_state"/' tak/certs/cert-metadata.sh
    sed -i 's/^CITY=.*/CITY="test_city"/' tak/certs/cert-metadata.sh
    sed -i 's/^ORGANIZATIONAL_UNIT=.*/ORGANIZATIONAL_UNIT="test_organization"/' tak/certs/cert-metadata.sh
    sed -i 's/^ORGANIZATION=.*/ORGANIZATION="test_org"/' tak/certs/cert-metadata.sh

    # Generate Root CA
    sudo docker exec takserver-"$(cat tak/version.txt)" bash -c "cd /opt/tak/certs && ./makeRootCa.sh"

    # Ensure CA certificate exists before continuing
    sudo docker exec takserver-"$(cat tak/version.txt)" bash -c "test -f /opt/tak/certs/files/ca.pem || (echo 'CA generation failed!' && exit 1)"

    # Generate Certificates
    sudo docker exec takserver-"$(cat tak/version.txt)" bash -c "cd /opt/tak/certs && ./makeCert.sh server takserver"
    sudo docker exec takserver-"$(cat tak/version.txt)" bash -c "cd /opt/tak/certs && ./makeCert.sh client admin"
    sudo docker exec takserver-"$(cat tak/version.txt)" bash -c "cd /opt/tak/certs && ./makeCert.sh client webadmin"

    # Ensure directories have correct permissions
    sudo find ~/Installed_by_FISSURE/takserver-docker-*/tak/certs/files/ -type d -exec chmod 755 {} +
      
    sudo openssl rsa -in "$(find ~/Installed_by_FISSURE/takserver-docker-*/tak/certs/files/ -name 'takserver.key' | head -n 1)" \
        -out "$(find ~/Installed_by_FISSURE/takserver-docker-*/tak/certs/files/ -type d | head -n 1)/takserver.key.unencrypted" \
        -passin pass:"atakatak"

    sudo mv "$(ls -d ~/Installed_by_FISSURE/takserver-docker-*/tak/certs/files | head -n 1)/takserver.key.unencrypted" \
      "$(ls -d ~/Installed_by_FISSURE/takserver-docker-*/tak/certs/files | head -n 1)/takserver.key"

    # Set ownership for all certificate-related files to the current user
    sudo find ~/Installed_by_FISSURE/takserver-docker-*/tak/certs/files/ -type f -exec chown $USER:$USER {} +
    sudo find ~/Installed_by_FISSURE/takserver-docker-*/tak/certs/files/ -type d -exec chown $USER:$USER {} +

    # Set proper permissions for private keys
    sudo find ~/Installed_by_FISSURE/takserver-docker-*/tak/certs/files/ -type f -name "*.key" -exec chmod 644 {} +

    # Set correct permissions for other certificate files
    sudo find ~/Installed_by_FISSURE/takserver-docker-*/tak/certs/files/ -type f -not -name "*.key" -exec chmod 644 {} +

    # Restart TAK Server to apply changes
    sudo docker restart takserver-"$(cat tak/version.txt)"

    # Copy takserver.key and takserver.pem to FISSURE Config Files
    cd """ + fissure_directory + """
    PYTHONPATH=""" + fissure_directory + """ python3 fissure/utils/tak_yaml_key_insert.py \
    "$(find ~/Installed_by_FISSURE/takserver-docker-*/tak/certs/files/ -name 'takserver.key' | head -n 1)" \
    "$(find ~/Installed_by_FISSURE/takserver-docker-*/tak/certs/files/ -name 'takserver.pem' | head -n 1)" \
    "$(find ~/Installed_by_FISSURE/takserver-docker-*/tak/certs/files/ -name 'webadmin.p12' | head -n 1)" \
    "$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' takserver-5.3-RELEASE-24)"

    # Import webadmin.p12:

    # Google Chrome/Edge
    # Open chrome://settings/certificates in your browser.
    # Go to the "Your certificates" tab.
    # Click "Import".
    # Select /home/cups-pk-helper/webadmin.p12.
    # Enter the password (default: atakatak, unless changed).
    # Complete the import and restart your browser.

    # Mozilla Firefox
    # Open about:preferences#privacy in the Firefox address bar.
    # Scroll down to Certificates and click "View Certificates".
    # Go to the "Your Certificates" tab.
    # Click "Import".
    # Select /home/cups-pk-helper/webadmin.p12 and enter the password (atakatak).
    # Restart Firefox.

    # To Remove TAK:
    # docker ps -a | grep takserver
    # docker rm -f $(docker ps -aq --filter "name=takserver")
    # docker rm -f $(docker ps -aq --filter "name=takserver-db")
    # docker ps -a
    # docker images | grep takserver
    # docker rmi -f $(docker images -q takserver)
    # docker rmi -f $(docker images -q takserver-db)
    # docker images
    # docker network ls | grep takserver
    # docker network rm $(docker network ls --filter "name=takserver" -q)
    # sudo rm -rf ~/Installed_by_FISSURE/takserver-docker-*/

    echo ""
    echo "TAK Server setup complete! Import webadmin.p12 certificate via browser. Access WebTAK at https://localhost:8443"
    echo ""
else
    echo "TAK Server zip extraction failed or extracted folder not found. Exiting."
fi

########## Verify ##########
ls "$(find ~/Installed_by_FISSURE/takserver-docker-*/tak/certs/files/ -name 'webadmin.p12' | head -n 1)"
""",False,'Mapping'))

""",False,'Mapping'))
