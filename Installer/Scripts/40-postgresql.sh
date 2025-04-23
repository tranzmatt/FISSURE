#!/bin/bash
set -e

sudo apt install -y postgresql-client
cd '""" + fissure_directory + """'
cp example.env .env
bash -c '
    set -o allexport
    source .env
    set +o allexport
    export PGPASSWORD=$POSTGRES_PASSWORD
    sudo docker compose up -d
    until pg_isready -U $POSTGRES_USER -h $POSTGRES_HOST -p $POSTGRES_EXTERNAL_PORT; do
        echo "Waiting for PostgreSQL to be ready..."
        sleep 2
    done
    pg_restore -U $POSTGRES_USER -d $POSTGRES_DB -h $POSTGRES_HOST -p $POSTGRES_EXTERNAL_PORT -v db/fissure_db_dump.sql
'
########## Verify ##########
bash -c '
    set -o allexport
    source .env
    set +o allexport
    export PGPASSWORD=$POSTGRES_PASSWORD
    sudo docker compose up -d
    psql -U $POSTGRES_USER -d $POSTGRES_DB -h $POSTGRES_HOST -p $POSTGRES_EXTERNAL_PORT -c "SELECT COUNT(*) FROM pg_tables;"
'
""",True,'Minimum Install'))

# Meshtastic
programs_ubuntu22_04.append(('Meshtastic',
"""sudo apt-get install -y python3-serial
sudo apt-get install -y python3-protobuf
sudo apt-get install -y python3-pyserial
sudo python3 -m pip install meshtastic
sudo usermod -aG dialout $USER  # log out & in/reboot
sudo usermod -aG tty $USER
echo 'SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", MODE="0666"' | sudo tee /etc/udev/rules.d/99-meshtastic.rules
sudo udevadm control --reload-rules
sudo udevadm trigger
########## Verify ##########
python3 -c "import meshtastic"
""",True,'Minimum Install'))

# Network Certificates 
programs_ubuntu22_04.append(('Network Certificates',
"""cd '""" + fissure_directory + """'
export PYTHONPATH='""" + fissure_directory + """':$PYTHONPATH
python3 ./fissure/generate_certificates.py
########## Verify ##########
ls '""" + fissure_directory + """/certificates'
""",True,'Minimum Install'))

# LimeSDR
programs_ubuntu22_04.append(('LimeSDR (288.7 MB)',
"""#sudo add-apt-repository -y ppa:myriadrf/drivers  # doesn't work
#sudo apt-get update
sudo apt-get install -y limesuite liblimesuite-dev limesuite-udev  # No limesuite-images on 22.04
sudo apt-get install -y soapysdr-tools soapysdr-module-lms7
sudo apt-get install -y libboost-all-dev swig
########## Verify ##########
ls /usr/bin/LimeSuiteGUI
""",True,'Hardware'))

# BladeRF
programs_ubuntu22_04.append(('BladeRF (23.1 MB)',
"""sudo apt-get install -y libusb-1.0-0-dev libusb-1.0-0 build-essential cmake libncurses5-dev libtecla1 pkg-config git wget  # no package: libtecla1-dev       
sudo apt-get install -y bladerf
sudo apt-get install -y bladerf-fpga-hostedx115
sudo apt-get install -y bladerf-fpga-hostedx40
sudo apt-get install -y bladerf-fpga-hostedxa4
sudo apt-get install -y bladerf-fpga-hostedxa9
########## Verify ##########
bladeRF-cli --help
""",True,'Hardware'))

# USRP X300 Series - FIX
programs_ubuntu22_04.append(('USRP X300 Series (499.7 kB)',
sudo apt install -y postgresql-client
cd '""" + fissure_directory + """'
cp example.env .env
bash -c '
    set -o allexport
    source .env
    set +o allexport
    export PGPASSWORD=$POSTGRES_PASSWORD
    sudo docker compose up -d
    until pg_isready -U $POSTGRES_USER -h $POSTGRES_HOST -p $POSTGRES_EXTERNAL_PORT; do
        echo "Waiting for PostgreSQL to be ready..."
        sleep 2
    done
    pg_restore -U $POSTGRES_USER -d $POSTGRES_DB -h $POSTGRES_HOST -p $POSTGRES_EXTERNAL_PORT -v db/fissure_db_dump.sql
'
########## Verify ##########
bash -c '
    set -o allexport
    source .env
    set +o allexport
    export PGPASSWORD=$POSTGRES_PASSWORD
    sudo docker compose up -d
    psql -U $POSTGRES_USER -d $POSTGRES_DB -h $POSTGRES_HOST -p $POSTGRES_EXTERNAL_PORT -c "SELECT COUNT(*) FROM pg_tables;"
'
""",True,'Minimum Install'))

# Meshtastic
programs_ubuntu22_04_arm.append(('Meshtastic',
"""sudo apt-get install -y python3-serial
sudo apt-get install -y python3-protobuf
sudo apt-get install -y python3-pyserial
sudo python3 -m pip install meshtastic
sudo usermod -aG dialout $USER  # log out & in/reboot
sudo usermod -aG tty $USER
echo 'SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", MODE="0666"' | sudo tee /etc/udev/rules.d/99-meshtastic.rules
sudo udevadm control --reload-rules
sudo udevadm trigger
########## Verify ##########
python3 -c "import meshtastic"
""",True,'Minimum Install'))

# Network Certificates 
programs_ubuntu22_04_arm.append(('Network Certificates',
"""cd '""" + fissure_directory + """'
export PYTHONPATH='""" + fissure_directory + """':$PYTHONPATH
python3 ./fissure/generate_certificates.py
########## Verify ##########
ls '""" + fissure_directory + """/certificates'
""",True,'Minimum Install'))

# LimeSDR
programs_ubuntu22_04_arm.append(('LimeSDR (288.7 MB)',
"""#sudo add-apt-repository -y ppa:myriadrf/drivers  # doesn't work
#sudo apt-get update
sudo apt-get install -y limesuite liblimesuite-dev limesuite-udev  # No limesuite-images on 22.04
sudo apt-get install -y soapysdr-tools soapysdr-module-lms7
sudo apt-get install -y libboost-all-dev swig
########## Verify ##########
ls /usr/bin/LimeSuiteGUI
""",True,'Hardware'))

# BladeRF
programs_ubuntu22_04_arm.append(('BladeRF (23.1 MB)',
"""sudo apt-get install -y libusb-1.0-0-dev libusb-1.0-0 build-essential cmake libncurses5-dev libtecla1 pkg-config git wget  # no package: libtecla1-dev       
sudo apt-get install -y bladerf
sudo apt-get install -y bladerf-fpga-hostedx115
sudo apt-get install -y bladerf-fpga-hostedx40
sudo apt-get install -y bladerf-fpga-hostedxa4
sudo apt-get install -y bladerf-fpga-hostedxa9
########## Verify ##########
bladeRF-cli --help
""",True,'Hardware'))

# USRP X300 Series - FIX
programs_ubuntu22_04_arm.append(('USRP X300 Series (499.7 kB)',
