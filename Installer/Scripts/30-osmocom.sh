#!/bin/bash
set -e

git clone https://gitea.osmocom.org/sdr/gr-osmosdr.git
cd gr-osmosdr
mkdir build
cd build
cmake ..
make
sudo make install
sudo ldconfig
########## Verify ##########
hackrf_sweep -h #&& ls /usr/local/bin/osmocom_fft
""",True,'Hardware'))

# 8812au Driver
programs_ubuntu22_04.append(('8812au Driver (810.8 MB)',
"""# Still Broken, Needs Replacement Driver
sudo apt-get -y install dkms
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/aircrack-ng/rtl8812au/
cd ~/Installed_by_FISSURE/rtl8812au
sudo make dkms_install
""",True,'Hardware'))

# Zigbee Sniffer
programs_ubuntu22_04.append(('Zigbee Sniffer (10.1 MB)',
"""mkdir -p ~/Installed_by_FISSURE
cp -R """ + fissure_directory + """/Tools/OpenSniffer-0.1/ ~/Installed_by_FISSURE/
cd ~/Installed_by_FISSURE/OpenSniffer-0.1/
sudo python3 setup.py install
#sudo add-apt-repository -y ppa:rock-core/qt4  # PyQt4, doesn't work
#sudo apt-get update
wget http://archive.ubuntu.com/ubuntu/pool/universe/q/qt-assistant-compat/libqtassistantclient4_4.6.3-7build1_amd64.deb -O ~/Downloads/libqtassistantclient4_4.6.3-7build1_amd64.deb 
sudo apt-get install -y ~/Downloads/libqtassistantclient4_4.6.3-7build1_amd64.deb
wget http://archive.ubuntu.com/ubuntu/pool/universe/p/python-qt4/python-qt4_4.12.1+dfsg-2_amd64.deb -O ~/Downloads/python-qt4_4.12.1+dfsg-2_amd64.deb
sudo apt-get install -y ~/Downloads/python-qt4_4.12.1+dfsg-2_amd64.deb
wget http://archive.ubuntu.com/ubuntu/pool/universe/p/python-pyaudio/python-pyaudio_0.2.11-1build2_amd64.deb -O ~/Downloads/python-pyaudio_0.2.11-1build2_amd64.deb
sudo apt-get install -y ~/Downloads/python-pyaudio_0.2.11-1build2_amd64.deb
rm ~/Downloads/libqtassistantclient4_4.6.3-7build1_amd64.deb
rm ~/Downloads/python-qt4_4.12.1+dfsg-2_amd64.deb
rm ~/Downloads/python-pyaudio_0.2.11-1build2_amd64.deb
sudo apt-get install -y mlocate
""",True,'Hardware'))

# fl2k
programs_ubuntu22_04.append(('fl2k',
"""mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://gitea.osmocom.org/sdr/osmo-fl2k.git  # gets redirected: https://git.osmocom.org/osmo-fl2k.git
cd osmo-fl2k
mkdir build
cd build 
cmake ../ -DINSTALL_UDEV_RULES=ON
make -j 3
sudo make install
sudo ldconfig
sudo udevadm control -R
sudo udevadm trigger
########## Verify ##########
ls /usr/local/bin/fl2k_test
""",True,'Hardware'))

# Proxmark3
programs_ubuntu22_04.append(('Proxmark3 (3.1 GB)',
"""sudo apt-get install -y p7zip git build-essential libreadline8 libreadline-dev libusb-0.1-4 libusb-dev perl pkg-config wget libncurses5-dev gcc-arm-none-eabi libreadline-dev libpcsclite-dev gcc-arm-none-eabi
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/Proxmark/proxmark3.git
cd proxmark3
make clean && make all
########## Verify ##########
ls ~/Installed_by_FISSURE/proxmark3/client/proxmark3
""",True,'Hardware'))

# PlutoSDR
programs_ubuntu22_04.append(('PlutoSDR (194.4 MB)',
"""sudo apt-get install -y libglib2.0-dev libgtk2.0-dev libgtkdatabox-dev libmatio-dev libfftw3-dev libxml2 libxml2-dev bison flex libavahi-common-dev libavahi-client-dev libcurl4-openssl-dev libjansson-dev cmake libaio-dev libserialport-dev libcdk5-dev libusb-1.0-0-dev doxygen graphviz git libgmp-dev swig liborc-dev
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/pcercuei/libini.git
cd libini
mkdir build && cd build && cmake ../ && make && sudo make install
cd ~/Installed_by_FISSURE
git clone https://github.com/analogdevicesinc/libiio.git
cd libiio
mkdir build && cd build && cmake ../ && make && sudo make install
cd ~/Installed_by_FISSURE
git clone https://github.com/analogdevicesinc/libad9361-iio.git
cd libad9361-iio
cmake ./
make
sudo make install
#cd ~/Installed_by_FISSURE
#git clone https://github.com/analogdevicesinc/iio-oscilloscope.git  # IIO oscilloscope is broken. /usr/include/gtkdatabox_graph.h:100:38: error: unknown type name ‘GdkRGBA’; did you mean ‘GdkGC’?
#cd iio-oscilloscope
#git checkout origin/master
#mkdir build && cd build
#cmake ../ && make
#sudo make install
#cd ~/Installed_by_FISSURE
#git clone -b upgrade-3.8 https://github.com/analogdevicesinc/gr-iio.git  # No Github version for 3.10. Comes with GNU Radio 3.10.
#cd gr-iio
#cmake .
#make
#sudo make install
#cd ..
#sudo ldconfig
########## Verify ##########
ls /usr/lib/python*/*/gnuradio/iio
""",True,'Hardware'))

# qFlipper
programs_ubuntu22_04.append(('qFlipper',
"""mkdir -p ~/Installed_by_FISSURE/qFlipper
cd ~/Installed_by_FISSURE/qFlipper
wget -r -np -nd -A "qFlipper-x86_64-dev*.AppImage" https://update.flipperzero.one/builds/qFlipper/dev/
chmod +x qFlipper*
########## Verify ##########
ls ~/Installed_by_FISSURE/qFlipper/qFlipper*
""",True,'Hardware'))

# gr-acars-3.10ng
programs_ubuntu22_04.append(('gr-acars-3.10ng (7.1 MB)',
"""cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-acars-3.10ng/
sudo rm -Rf build
mkdir build
cd build
cmake ..
make
sudo make install
sudo ldconfig
########## Verify ##########
ls /usr/local/lib/python*/*/acars
""",True,'Out-of-Tree Modules'))

# gr-adsb
programs_ubuntu22_04.append(('gr-adsb (2.7 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-adsb/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-adsb"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-adsb/)" ]; 
then
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-adsb/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/gnuradio/adsb
""",True,'Out-of-Tree Modules'))

# gr-ainfosec
programs_ubuntu22_04.append(('gr-ainfosec (7.6 MB)',
"""cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-ainfosec/
sudo rm -Rf build
mkdir build
cd build
cmake ..
make
sudo make install
sudo ldconfig
########## Verify ##########
ls /usr/local/lib/python*/*/gnuradio/ainfosec
""",True,'Minimum Install'))

# gr-ais
programs_ubuntu22_04.append(('gr-ais (9.2 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-ais/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-ais"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-ais/)" ]; 
then
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-ais/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/gnuradio/ais
""",True,'Out-of-Tree Modules'))

# gr-aistx
programs_ubuntu22_04.append(('gr-aistx',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/ais/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/ais"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/ais/gr-aistx/)" ]; 
then
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/ais/gr-aistx/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/gnuradio/aistx
""",True,'Out-of-Tree Modules'))

# gr-bluetooth
programs_ubuntu22_04.append(('gr-bluetooth (34.7 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-bluetooth/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-bluetooth"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-bluetooth/)" ]; 
then
  mkdir -p ~/Installed_by_FISSURE
  cd ~/Installed_by_FISSURE
  rm -Rf libbtbb
  git clone https://github.com/greatscottgadgets/libbtbb -b master
  cd libbtbb
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-bluetooth/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/bin/btrx
""",False,'Out-of-Tree Modules'))

# gr-clapper_plus
programs_ubuntu22_04.append(('gr-clapper_plus (2.4 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-clapper_plus/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-clapper_plus"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-clapper_plus/)" ]; 
then
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-clapper_plus/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/gnuradio/clapper_plus
""",True,'Out-of-Tree Modules'))

# gr-dect2
programs_ubuntu22_04.append(('gr-dect2 (11.9 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-dect2/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-dect2"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-dect2/)" ]; 
then
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-dect2/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/gnuradio/dect2
""",True,'Out-of-Tree Modules'))

# gr-foo
programs_ubuntu22_04.append(('gr-foo (37.6 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-foo/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-foo"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-foo/)" ]; 
then
  sudo apt-get install -y libsndfile1-dev
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-foo/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/foo
""",True,'Out-of-Tree Modules'))

# gr-fuzzer
programs_ubuntu22_04.append(('gr-fuzzer (7.4 MB)',
"""cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-fuzzer/
sudo rm -Rf build
mkdir build
cd build
cmake ..
make
sudo make install
sudo ldconfig
########## Verify ##########
ls /usr/local/lib/python*/*/gnuradio/fuzzer
""",True,'Out-of-Tree Modules'))

# gr-garage_door
programs_ubuntu22_04.append(('gr-garage_door (2.4 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-garage_door/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-garage_door"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-garage_door/)" ]; 
then
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-garage_door/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/gnuradio/garage_door
""",True,'Out-of-Tree Modules'))

# gr-gsm
programs_ubuntu22_04.append(('gr-gsm (156.8 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-gsm/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-gsm"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-gsm/)" ]; 
then
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-gsm/
  sudo rm -Rf build
  sudo apt-get install -y gr-osmosdr
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
  # gr-gsm needs to be made twice for "import arfcn" block to work
  make 
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/gnuradio/gsm
""",True,'Out-of-Tree Modules'))

# gr-ieee802-11
programs_ubuntu22_04.append(('gr-ieee802-11 (37.9 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-ieee802-11/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-ieee802-11"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-ieee802-11/)" ]; 
then
  sudo apt-get install -y libsndfile1-dev
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-ieee802-11/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/ieee802_11
""",True,'Out-of-Tree Modules'))

# gr-ieee802-15-4
programs_ubuntu22_04.append(('gr-ieee802-15-4 (63.3 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-ieee802-15-4/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-ieee802-15-4"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-ieee802-15-4/)" ]; 
then
  sudo apt-get install -y libsndfile1-dev
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-ieee802-15-4/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
  grcc """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-ieee802-15-4/examples/ieee802_15_4_CSS_PHY.grc
  grcc """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-ieee802-15-4/examples/ieee802_15_4_OQPSK_PHY.grc
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/ieee802_15_4
""",True,'Out-of-Tree Modules'))

# gr-iridium
programs_ubuntu22_04.append(('gr-iridium (29.5 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-iridium/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-iridium"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-iridium/)" ]; 
then
  sudo apt-get install -y libsndfile1-dev
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-iridium/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/iridium
""",True,'Out-of-Tree Modules'))

# gr-j2497
programs_ubuntu22_04.append(('gr-j2497 (2.6 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-j2497/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-j2497"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-j2497/)" ]; 
then
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-j2497/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/gnuradio/j2497
""",True,'Out-of-Tree Modules'))

# gr-limesdr
programs_ubuntu22_04.append(('gr-limesdr (12.0 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-limesdr/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-limesdr"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-limesdr/)" ]; 
then
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-limesdr/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/gnuradio/limesdr
""",True,'Out-of-Tree Modules'))

# gr-mixalot
programs_ubuntu22_04.append(('gr-mixalot (19.1 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-mixalot/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-mixalot"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-mixalot/)" ]; 
then
  sudo apt-get install -y libitpp-dev
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-mixalot/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/gnuradio/mixalot
""",True,'Out-of-Tree Modules'))

# gr-nrsc5
programs_ubuntu22_04.append(('gr-nrsc5 (53.8 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-nrsc5/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-nrsc5"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-nrsc5/)" ]; 
then
  sudo apt-get install -y libsndfile1-dev
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-nrsc5/
  sudo rm -Rf build
  sudo apt install -y git build-essential cmake autoconf libtool libao-dev libfftw3-dev librtlsdr-dev libgsl-dev
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/nrsc5
""",True,'Out-of-Tree Modules'))

# gr-paint
programs_ubuntu22_04.append(('gr-paint (9.0 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-paint/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-paint"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-paint/)" ]; 
then
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-paint/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-paint/
  gcc tgatoluma.c -o tgatoluma
  chmod +x tgatoluma
  cp tgatoluma ~/.local/bin/
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/paint
""",True,'Out-of-Tree Modules'))

# gr-rds
programs_ubuntu22_04.append(('gr-rds (20.5 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-rds/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-rds"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-rds/)" ]; 
then
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-rds/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/rds
""",True,'Out-of-Tree Modules'))

# gr-sdrplay3
programs_ubuntu22_04.append(('gr-sdrplay3',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-sdrplay3/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-sdrplay3"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-sdrplay3/)" ];  # Requires SDRplay API before building: https://www.sdrplay.com/api
then
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-sdrplay3/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/*/sdrplay3
""",True,'Out-of-Tree Modules'))

# gr-tpms
programs_ubuntu22_04.append(('gr-tpms (11.8 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-tpms/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-tpms"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-tpms/)" ]; 
then
  sudo apt-get install -y libsndfile1-dev
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-tpms/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/gnuradio/tpms
""",True,'Out-of-Tree Modules'))

# gr-tpms_poore
programs_ubuntu22_04.append(('gr-tpms_poore (2.5 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-tpms_poore/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-tpms_poore"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-tpms_poore/)" ]; 
then
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-tpms_poore/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/gnuradio/tpms_poore
""",True,'Out-of-Tree Modules'))

# gr-X10
programs_ubuntu22_04.append(('gr-X10 (2.4 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-X10/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-X10"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-X10/)" ]; 
then
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-X10/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/gnuradio/X10
""",True,'Out-of-Tree Modules'))

# gr-zwave_poore
programs_ubuntu22_04.append(('gr-zwave_poore (2.5 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-zwave_poore/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-zwave_poore"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-zwave_poore/)" ]; 
then
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-zwave_poore/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/gnuradio/zwave_poore
""",True,'Out-of-Tree Modules'))

# QSpectrumAnalyzer
programs_ubuntu22_04.append(('QSpectrumAnalyzer (9.6 MB)',
"""#sudo add-apt-repository -y ppa:myriadrf/drivers
#sudo apt-get -y update
sudo apt-get install -y python3-pip python3-pyqt5 python3-numpy python3-scipy python3-soapysdr  # No package: soapysdr
sudo apt-get install -y soapysdr-module-rtlsdr soapysdr-module-airspy soapysdr-module-hackrf soapysdr-module-lms7
python3 -m pip install --user qspectrumanalyzer  # log in again, run without sudo
########## Verify ##########
ls ~/.local/bin/qspectrumanalyzer
""",True,'SDR'))

# GQRX
programs_ubuntu22_04.append(('GQRX (7.0 MB)',
"""sudo apt-get install -y libqt5svg5-dev  #sudo apt-get install -y gqrx-sdr
sudo apt-get install -y libpulse-dev
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE/
git clone https://github.com/gqrx-sdr/gqrx.git
cd  ~/Installed_by_FISSURE/gqrx
mkdir build
cd build
cmake ..
make
sudo make install
########## Verify ##########
ls /usr/local/bin/gqrx
""",True,'SDR'))

# Dump1090
programs_ubuntu22_04.append(('Dump1090 (3.4 MB)',
"""sudo apt-get install -y libusb-1.0-0-dev
sudo apt-get install -y librtlsdr-dev
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE/
git clone https://github.com/antirez/dump1090.git
cd ~/Installed_by_FISSURE/dump1090/
make
########## Verify ##########
~/Installed_by_FISSURE/dump1090/dump1090 --help
""",True,'Aircraft'))

# QtDesigner
programs_ubuntu22_04.append(('QtDesigner',
"""sudo apt-get install -y build-essential qtcreator qtbase5-dev qtchooser qt5-qmake qtbase5-dev-tools
########## Verify ##########
ls /usr/bin/designer
""",True,'Development'))

# Grip
programs_ubuntu22_04.append(('Grip (6.4 MB)',
"""sudo python3 -m pip install grip
########## Verify ##########
ls /usr/local/bin/grip
""",True,'Development'))

# Kismet
programs_ubuntu22_04.append(('Kismet (106.4 MB)',
git clone git://git.osmocom.org/osmo-ir77
cd osmo-ir77/codec/
sudo make
cp ir77_ambe_decode ~/Installed_by_FISSURE/iridium-toolkit/
########## Verify ##########
ls ~/Installed_by_FISSURE/osmo-ir77/codec/ir77_ambe_decode
""",True,'Satellite'))

# IridiumLive
programs_ubuntu22_04.append(('IridiumLive (97.2 MB)',
"""mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/microp11/iridiumlive.git
wget -P ~/Installed_by_FISSURE/ https://github.com/microp11/iridiumlive/releases/download/v1.2/linux-x64.zip
unzip -q linux-x64.zip
rm linux-x64.zip
cd linux-x64
sudo chmod +x IridiumLive
########## Verify ##########
ls ~/Installed_by_FISSURE/linux-x64/IridiumLive
""",True,'Satellite'))

# NETATTACK2 - Fix
programs_ubuntu22_04.append(('NETATTACK2',
"""#sudo pip install netifaces  # fix for python2
#sudo apt-get install -y python-scapy python-nmap python-nfqueue nmap  # this needs to be fixed, can it still run with python2?
sudo python2 -m pip install netifaces
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/chrizator/netattack2.git
sudo python2 -m pip install nmap
cd netattack2
git clone https://gitea.osmocom.org/sdr/gr-osmosdr.git
cd gr-osmosdr
mkdir build
cd build
cmake ..
make
sudo make install
sudo ldconfig
########## Verify ##########
hackrf_sweep -h #&& ls /usr/local/bin/osmocom_fft
""",True,'Hardware'))

# 8812au Driver
programs_ubuntu22_04_arm.append(('8812au Driver (810.8 MB)',
"""# Still Broken, Needs Replacement Driver
sudo apt-get -y install dkms
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/aircrack-ng/rtl8812au/
cd ~/Installed_by_FISSURE/rtl8812au
sudo make dkms_install
""",True,'Hardware'))

# Zigbee Sniffer
programs_ubuntu22_04_arm.append(('Zigbee Sniffer (10.1 MB)',
"""mkdir -p ~/Installed_by_FISSURE
cp -R """ + fissure_directory + """/Tools/OpenSniffer-0.1/ ~/Installed_by_FISSURE/
cd ~/Installed_by_FISSURE/OpenSniffer-0.1/
sudo python3 setup.py install
#sudo add-apt-repository -y ppa:rock-core/qt4  # PyQt4, doesn't work
#sudo apt-get update
wget http://archive.ubuntu.com/ubuntu/pool/universe/q/qt-assistant-compat/libqtassistantclient4_4.6.3-7build1_amd64.deb -O ~/Downloads/libqtassistantclient4_4.6.3-7build1_amd64.deb 
sudo apt-get install -y ~/Downloads/libqtassistantclient4_4.6.3-7build1_amd64.deb
wget http://archive.ubuntu.com/ubuntu/pool/universe/p/python-qt4/python-qt4_4.12.1+dfsg-2_amd64.deb -O ~/Downloads/python-qt4_4.12.1+dfsg-2_amd64.deb
sudo apt-get install -y ~/Downloads/python-qt4_4.12.1+dfsg-2_amd64.deb
wget http://archive.ubuntu.com/ubuntu/pool/universe/p/python-pyaudio/python-pyaudio_0.2.11-1build2_amd64.deb -O ~/Downloads/python-pyaudio_0.2.11-1build2_amd64.deb
sudo apt-get install -y ~/Downloads/python-pyaudio_0.2.11-1build2_amd64.deb
rm ~/Downloads/libqtassistantclient4_4.6.3-7build1_amd64.deb
rm ~/Downloads/python-qt4_4.12.1+dfsg-2_amd64.deb
rm ~/Downloads/python-pyaudio_0.2.11-1build2_amd64.deb
sudo apt-get install -y mlocate
""",True,'Hardware'))

# fl2k
programs_ubuntu22_04_arm.append(('fl2k',
"""mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://gitea.osmocom.org/sdr/osmo-fl2k.git  # gets redirected: https://git.osmocom.org/osmo-fl2k.git
cd osmo-fl2k
mkdir build
cd build 
cmake ../ -DINSTALL_UDEV_RULES=ON
make -j 3
sudo make install
sudo ldconfig
sudo udevadm control -R
sudo udevadm trigger
########## Verify ##########
ls /usr/local/bin/fl2k_test
""",True,'Hardware'))

# Proxmark3
programs_ubuntu22_04_arm.append(('Proxmark3 (3.1 GB)',
"""sudo apt-get install -y p7zip git build-essential libreadline8 libreadline-dev libusb-0.1-4 libusb-dev perl pkg-config wget libncurses5-dev gcc-arm-none-eabi libreadline-dev libpcsclite-dev gcc-arm-none-eabi
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/Proxmark/proxmark3.git
cd proxmark3
make clean && make all
########## Verify ##########
ls ~/Installed_by_FISSURE/proxmark3/client/proxmark3
""",True,'Hardware'))

# PlutoSDR
programs_ubuntu22_04_arm.append(('PlutoSDR (194.4 MB)',
"""sudo apt-get install -y libglib2.0-dev libgtk2.0-dev libgtkdatabox-dev libmatio-dev libfftw3-dev libxml2 libxml2-dev bison flex libavahi-common-dev libavahi-client-dev libcurl4-openssl-dev libjansson-dev cmake libaio-dev libserialport-dev libcdk5-dev libusb-1.0-0-dev doxygen graphviz git libgmp-dev swig liborc-dev
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/pcercuei/libini.git
cd libini
mkdir build && cd build && cmake ../ && make && sudo make install
cd ~/Installed_by_FISSURE
git clone https://github.com/analogdevicesinc/libiio.git
cd libiio
mkdir build && cd build && cmake ../ && make && sudo make install
cd ~/Installed_by_FISSURE
git clone https://github.com/analogdevicesinc/libad9361-iio.git
cd libad9361-iio
cmake ./
make
sudo make install
#cd ~/Installed_by_FISSURE
#git clone https://github.com/analogdevicesinc/iio-oscilloscope.git  # IIO oscilloscope is broken. /usr/include/gtkdatabox_graph.h:100:38: error: unknown type name ‘GdkRGBA’; did you mean ‘GdkGC’?
#cd iio-oscilloscope
#git checkout origin/master
#mkdir build && cd build
#cmake ../ && make
#sudo make install
#cd ~/Installed_by_FISSURE
#git clone -b upgrade-3.8 https://github.com/analogdevicesinc/gr-iio.git  # No Github version for 3.10. Comes with GNU Radio 3.10.
#cd gr-iio
#cmake .
#make
#sudo make install
#cd ..
#sudo ldconfig
########## Verify ##########
ls /usr/lib/python*/*/gnuradio/iio
""",True,'Hardware'))

# qFlipper
programs_ubuntu22_04_arm.append(('qFlipper',
"""mkdir -p ~/Installed_by_FISSURE/qFlipper
cd ~/Installed_by_FISSURE/qFlipper
wget -r -np -nd -A "qFlipper-x86_64-dev*.AppImage" https://update.flipperzero.one/builds/qFlipper/dev/
chmod +x qFlipper*
########## Verify ##########
ls ~/Installed_by_FISSURE/qFlipper/qFlipper*
""",True,'Hardware'))

# gr-acars-3.10ng
programs_ubuntu22_04_arm.append(('gr-acars-3.10ng (7.1 MB)',
"""cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-acars-3.10ng/
sudo rm -Rf build
mkdir build
cd build
cmake ..
make
sudo make install
sudo ldconfig
########## Verify ##########
ls /usr/local/lib/python*/*/acars
""",True,'Out-of-Tree Modules'))

# gr-adsb
programs_ubuntu22_04_arm.append(('gr-adsb (2.7 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-adsb/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-adsb"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-adsb/)" ]; 
then
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-adsb/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/gnuradio/adsb
""",True,'Out-of-Tree Modules'))

# gr-ainfosec
programs_ubuntu22_04_arm.append(('gr-ainfosec (7.6 MB)',
"""cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-ainfosec/
sudo rm -Rf build
mkdir build
cd build
cmake ..
make
sudo make install
sudo ldconfig
########## Verify ##########
ls /usr/local/lib/python*/*/gnuradio/ainfosec
""",True,'Minimum Install'))

# gr-ais
programs_ubuntu22_04_arm.append(('gr-ais (9.2 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-ais/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-ais"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-ais/)" ]; 
then
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-ais/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/gnuradio/ais
""",True,'Out-of-Tree Modules'))

# gr-aistx
programs_ubuntu22_04_arm.append(('gr-aistx',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/ais/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/ais"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/ais/gr-aistx/)" ]; 
then
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/ais/gr-aistx/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/gnuradio/aistx
""",True,'Out-of-Tree Modules'))

# gr-bluetooth
programs_ubuntu22_04_arm.append(('gr-bluetooth (34.7 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-bluetooth/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-bluetooth"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-bluetooth/)" ]; 
then
  mkdir -p ~/Installed_by_FISSURE
  cd ~/Installed_by_FISSURE
  rm -Rf libbtbb
  git clone https://github.com/greatscottgadgets/libbtbb -b master
  cd libbtbb
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-bluetooth/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/bin/btrx
""",False,'Out-of-Tree Modules'))

# gr-clapper_plus
programs_ubuntu22_04_arm.append(('gr-clapper_plus (2.4 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-clapper_plus/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-clapper_plus"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-clapper_plus/)" ]; 
then
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-clapper_plus/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/gnuradio/clapper_plus
""",True,'Out-of-Tree Modules'))

# gr-dect2
programs_ubuntu22_04_arm.append(('gr-dect2 (11.9 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-dect2/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-dect2"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-dect2/)" ]; 
then
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-dect2/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/gnuradio/dect2
""",True,'Out-of-Tree Modules'))

# gr-foo
programs_ubuntu22_04_arm.append(('gr-foo (37.6 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-foo/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-foo"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-foo/)" ]; 
then
  sudo apt-get install -y libsndfile1-dev
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-foo/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/foo
""",True,'Out-of-Tree Modules'))

# gr-fuzzer
programs_ubuntu22_04_arm.append(('gr-fuzzer (7.4 MB)',
"""cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-fuzzer/
sudo rm -Rf build
mkdir build
cd build
cmake ..
make
sudo make install
sudo ldconfig
########## Verify ##########
ls /usr/local/lib/python*/*/gnuradio/fuzzer
""",True,'Out-of-Tree Modules'))

# gr-garage_door
programs_ubuntu22_04_arm.append(('gr-garage_door (2.4 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-garage_door/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-garage_door"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-garage_door/)" ]; 
then
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-garage_door/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/gnuradio/garage_door
""",True,'Out-of-Tree Modules'))

# gr-gsm
programs_ubuntu22_04_arm.append(('gr-gsm (156.8 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-gsm/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-gsm"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-gsm/)" ]; 
then
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-gsm/
  sudo rm -Rf build
  sudo apt-get install -y gr-osmosdr
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
  # gr-gsm needs to be made twice for "import arfcn" block to work
  make 
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/gnuradio/gsm
""",True,'Out-of-Tree Modules'))

# gr-ieee802-11
programs_ubuntu22_04_arm.append(('gr-ieee802-11 (37.9 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-ieee802-11/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-ieee802-11"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-ieee802-11/)" ]; 
then
  sudo apt-get install -y libsndfile1-dev
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-ieee802-11/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/ieee802_11
""",True,'Out-of-Tree Modules'))

# gr-ieee802-15-4
programs_ubuntu22_04_arm.append(('gr-ieee802-15-4 (63.3 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-ieee802-15-4/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-ieee802-15-4"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-ieee802-15-4/)" ]; 
then
  sudo apt-get install -y libsndfile1-dev
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-ieee802-15-4/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
  grcc """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-ieee802-15-4/examples/ieee802_15_4_CSS_PHY.grc
  grcc """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-ieee802-15-4/examples/ieee802_15_4_OQPSK_PHY.grc
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/ieee802_15_4
""",True,'Out-of-Tree Modules'))

# gr-iridium
programs_ubuntu22_04_arm.append(('gr-iridium (29.5 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-iridium/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-iridium"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-iridium/)" ]; 
then
  sudo apt-get install -y libsndfile1-dev
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-iridium/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/iridium
""",True,'Out-of-Tree Modules'))

# gr-j2497
programs_ubuntu22_04_arm.append(('gr-j2497 (2.6 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-j2497/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-j2497"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-j2497/)" ]; 
then
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-j2497/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/gnuradio/j2497
""",True,'Out-of-Tree Modules'))

# gr-limesdr
programs_ubuntu22_04_arm.append(('gr-limesdr (12.0 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-limesdr/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-limesdr"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-limesdr/)" ]; 
then
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-limesdr/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/gnuradio/limesdr
""",True,'Out-of-Tree Modules'))

# gr-mixalot
programs_ubuntu22_04_arm.append(('gr-mixalot (19.1 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-mixalot/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-mixalot"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-mixalot/)" ]; 
then
  sudo apt-get install -y libitpp-dev
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-mixalot/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/gnuradio/mixalot
""",True,'Out-of-Tree Modules'))

# gr-nrsc5
programs_ubuntu22_04_arm.append(('gr-nrsc5 (53.8 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-nrsc5/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-nrsc5"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-nrsc5/)" ]; 
then
  sudo apt-get install -y libsndfile1-dev
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-nrsc5/
  sudo rm -Rf build
  sudo apt install -y git build-essential cmake autoconf libtool libao-dev libfftw3-dev librtlsdr-dev libgsl-dev
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/nrsc5
""",True,'Out-of-Tree Modules'))

# gr-paint
programs_ubuntu22_04_arm.append(('gr-paint (9.0 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-paint/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-paint"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-paint/)" ]; 
then
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-paint/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-paint/
  gcc tgatoluma.c -o tgatoluma
  chmod +x tgatoluma
  cp tgatoluma ~/.local/bin/
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/paint
""",True,'Out-of-Tree Modules'))

# gr-rds
programs_ubuntu22_04_arm.append(('gr-rds (20.5 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-rds/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-rds"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-rds/)" ]; 
then
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-rds/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/rds
""",True,'Out-of-Tree Modules'))

# gr-sdrplay3
programs_ubuntu22_04_arm.append(('gr-sdrplay3',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-sdrplay3/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-sdrplay3"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-sdrplay3/)" ];  # Requires SDRplay API before building: https://www.sdrplay.com/api
then
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-sdrplay3/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/*/sdrplay3
""",True,'Out-of-Tree Modules'))

# gr-tpms
programs_ubuntu22_04_arm.append(('gr-tpms (11.8 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-tpms/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-tpms"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-tpms/)" ]; 
then
  sudo apt-get install -y libsndfile1-dev
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-tpms/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/gnuradio/tpms
""",True,'Out-of-Tree Modules'))

# gr-tpms_poore
programs_ubuntu22_04_arm.append(('gr-tpms_poore (2.5 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-tpms_poore/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-tpms_poore"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-tpms_poore/)" ]; 
then
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-tpms_poore/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/gnuradio/tpms_poore
""",True,'Out-of-Tree Modules'))

# gr-X10
programs_ubuntu22_04_arm.append(('gr-X10 (2.4 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-X10/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-X10"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-X10/)" ]; 
then
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-X10/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/gnuradio/X10
""",True,'Out-of-Tree Modules'))

# gr-zwave_poore
programs_ubuntu22_04_arm.append(('gr-zwave_poore (2.5 MB)',
"""cd """ + fissure_directory + """
if [ ! -f "Custom_Blocks/maint-3.10/gr-zwave_poore/.git" ]; then
    git submodule update --init -- "Custom_Blocks/maint-3.10/gr-zwave_poore"
fi
if [ "$(ls -A """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-zwave_poore/)" ]; 
then
  cd """ + fissure_directory + """/Custom_Blocks/maint-3.10/gr-zwave_poore/
  sudo rm -Rf build
  mkdir build
  cd build
  cmake ..
  make
  sudo make install
  sudo ldconfig
else
  echo "Folder is empty. Execute 'git submodule update --init' from FISSURE directory."
fi
########## Verify ##########
ls /usr/local/lib/python*/*/gnuradio/zwave_poore
""",True,'Out-of-Tree Modules'))

# QSpectrumAnalyzer
programs_ubuntu22_04_arm.append(('QSpectrumAnalyzer (9.6 MB)',
"""#sudo add-apt-repository -y ppa:myriadrf/drivers
#sudo apt-get -y update
sudo apt-get install -y python3-pip python3-pyqt5 python3-numpy python3-scipy python3-soapysdr  # No package: soapysdr
sudo apt-get install -y soapysdr-module-rtlsdr soapysdr-module-airspy soapysdr-module-hackrf soapysdr-module-lms7
python3 -m pip install --user qspectrumanalyzer  # log in again, run without sudo
########## Verify ##########
ls ~/.local/bin/qspectrumanalyzer
""",True,'SDR'))

# GQRX
programs_ubuntu22_04_arm.append(('GQRX (7.0 MB)',
"""sudo apt-get install -y libqt5svg5-dev  #sudo apt-get install -y gqrx-sdr
sudo apt-get install -y libpulse-dev
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE/
git clone https://github.com/gqrx-sdr/gqrx.git
cd  ~/Installed_by_FISSURE/gqrx
mkdir build
cd build
cmake ..
make
sudo make install
########## Verify ##########
ls /usr/local/bin/gqrx
""",True,'SDR'))

# Dump1090
programs_ubuntu22_04_arm.append(('Dump1090 (3.4 MB)',
"""sudo apt-get install -y libusb-1.0-0-dev
sudo apt-get install -y librtlsdr-dev
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE/
git clone https://github.com/antirez/dump1090.git
cd ~/Installed_by_FISSURE/dump1090/
make
########## Verify ##########
~/Installed_by_FISSURE/dump1090/dump1090 --help
""",True,'Aircraft'))

# QtDesigner
programs_ubuntu22_04_arm.append(('QtDesigner',
"""sudo apt-get install -y build-essential qtcreator qtbase5-dev qtchooser qt5-qmake qtbase5-dev-tools
########## Verify ##########
ls /usr/bin/designer
""",True,'Development'))

# Grip
programs_ubuntu22_04_arm.append(('Grip (6.4 MB)',
"""sudo python3 -m pip install grip
########## Verify ##########
ls /usr/local/bin/grip
""",True,'Development'))

# Kismet
programs_ubuntu22_04_arm.append(('Kismet (106.4 MB)',
git clone git://git.osmocom.org/osmo-ir77
cd osmo-ir77/codec/
sudo make
cp ir77_ambe_decode ~/Installed_by_FISSURE/iridium-toolkit/
########## Verify ##########
ls ~/Installed_by_FISSURE/osmo-ir77/codec/ir77_ambe_decode
""",True,'Satellite'))

# IridiumLive
programs_ubuntu22_04_arm.append(('IridiumLive (97.2 MB)',
"""mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/microp11/iridiumlive.git
wget -P ~/Installed_by_FISSURE/ https://github.com/microp11/iridiumlive/releases/download/v1.2/linux-x64.zip
unzip -q linux-x64.zip
rm linux-x64.zip
cd linux-x64
sudo chmod +x IridiumLive
########## Verify ##########
ls ~/Installed_by_FISSURE/linux-x64/IridiumLive
""",True,'Satellite'))

# NETATTACK2 - Fix
programs_ubuntu22_04_arm.append(('NETATTACK2',
"""#sudo pip install netifaces  # fix for python2
#sudo apt-get install -y python-scapy python-nmap python-nfqueue nmap  # this needs to be fixed, can it still run with python2?
sudo python2 -m pip install netifaces
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/chrizator/netattack2.git
sudo python2 -m pip install nmap
cd netattack2
