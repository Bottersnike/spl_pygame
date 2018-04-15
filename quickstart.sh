#!/bin/bash
if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi

curl https://bootstrap.pypa.io/get-pip.py | python3
python3 -m pip install -r requirements.txt
echo "cd meter && while true; do python3 main.py; done" >> ~/.bashrc

echo "----------"
echo "Installation has finished. raspi-config will now open."
echo "Please enable SSH and Auto-Login for the `pi` user."
read -p "Press return to continue.. "

raspi-config

echo "You should now be fully configured. Please take this time to edit"
echo "config.py before running `sudo reboot` as this machine is now setup"
echo "to run the meter as soon as it boots."
