#!/bin/bash
set -e

"""wget -O - https://www.kismetwireless.net/repos/kismet-release.gpg.key | sudo apt-key add -
echo 'deb https://www.kismetwireless.net/repos/apt/release/jammy jammy main' | sudo tee /etc/apt/sources.list.d/kismet.list
sudo cp /etc/apt/trusted.gpg /etc/apt/trusted.gpg.d  # Removes "sudo apt update" warnings
sudo apt update
echo "kismet kismet/install-setuid boolean false" | sudo debconf-set-selections
echo "kismet kismet/install-user string kismet" | sudo debconf-set-selections
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y kismet
""",True,'802.11'))

# UDP Replay
programs_ubuntu22_04.append(('UDP Replay (1.1 MB)',
"""sudo apt-get install -y libpcap-dev
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/rigtorp/udpreplay.git
cd ~/Installed_by_FISSURE/udpreplay
mkdir build
cd build
cmake ..
make
sudo make install
########## Verify ##########
ls /usr/local/bin/udpreplay
""",True,'802.11'))

# V2Verifier
programs_ubuntu22_04.append(('V2Verifier (3.8 MB)',
"""sudo apt-get install -y libgmp3-dev python3-tk python3-pil.imagetk
sudo python3 -m pip install fastecdsa
sudo python3 -m pip install -U pyyaml
"""wget -O - https://www.kismetwireless.net/repos/kismet-release.gpg.key | sudo apt-key add -
echo 'deb https://www.kismetwireless.net/repos/apt/release/jammy jammy main' | sudo tee /etc/apt/sources.list.d/kismet.list
sudo cp /etc/apt/trusted.gpg /etc/apt/trusted.gpg.d  # Removes "sudo apt update" warnings
sudo apt update
echo "kismet kismet/install-setuid boolean false" | sudo debconf-set-selections
echo "kismet kismet/install-user string kismet" | sudo debconf-set-selections
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y kismet
""",True,'802.11'))

# UDP Replay
programs_ubuntu22_04_arm.append(('UDP Replay (1.1 MB)',
"""sudo apt-get install -y libpcap-dev
mkdir -p ~/Installed_by_FISSURE
cd ~/Installed_by_FISSURE
git clone https://github.com/rigtorp/udpreplay.git
cd ~/Installed_by_FISSURE/udpreplay
mkdir build
cd build
cmake ..
make
sudo make install
########## Verify ##########
ls /usr/local/bin/udpreplay
""",True,'802.11'))

# V2Verifier
programs_ubuntu22_04_arm.append(('V2Verifier (3.8 MB)',
"""sudo apt-get install -y libgmp3-dev python3-tk python3-pil.imagetk
sudo python3 -m pip install fastecdsa
sudo python3 -m pip install -U pyyaml
