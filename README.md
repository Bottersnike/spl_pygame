# Sound Level Meter using Python

## What _is_ this?
This is a simple script that is designed to run on a Raspberry Pi which will
take up to two inputs and monitor their volumes, giving visual feedback to the
operator with the aim of keeping volume consistant between different operators.

## How does it work?
The interface has been designed to be simple to use and uses large coloured
"pannels" to indicate if the current level is okay or not. A graph can also be
shown which helps to give an overview of whether the volume has been consistant.

## Is it configurable?
Absolutely! It has been themed to blend in with a Roland system, however it is
entirely customizable using the `config.py` file. This allows for the interface
to be entirely re-coloured as well as allowing for the thresholds, graph size,
interface padding and much more to be easilly changed. All of the things that
can be changed have a short description along with them making editing the file
a breeze. All colours are in the form `(RED, GREEEN, BLUE)` and an alpha channel
is (sadly) not supported.

## Sounds good. How do I get started?
At its simplest level, download this entire repository and then run `main.py`.
That said, there are a few dependencies required:

- Python 3.x
- Pygame
- numpy
- SciPy
- PyAudio

Once python has been installed, all of the other dependancies can be installed
using the command line tool `pip` by doing `python3 -m pip install --user pygame
numpy scipy pyaudio`.
This has been primerally been designed to run on a Raspberry Pi using a TFT
screen, and for that, there is a little more to do:

- First, setup a Raspberry Pi following the instructions
  [here](https://www.raspberrypi.org/learning/software-guide/quickstart/).
- The Pi likely loaded desktop when it started. If this was the case, press
  `Ctrl+Alt+F3`.
- Login with the username `pi` and the password `raspberry`.
- Issue the command `sudo apt install git`.
- Issue the command `wget https://bootstrap.pypa.io/get-pip.py`.
- Issue the command `sudo python3 get_pip.py`.
- Issue the command `sudo python3 -m pip install pygame numpy scipy pyaudio`.
- Issue the command `git clone https://github.com/Bottersnike/spl_pygame meter`.
- Use `sudo raspi-config` to set the `pi` user to automatically log in and
  enable SSH. **Make sure to enable SSH. This will be the only way to
  re-configure the Pi or install updates once you've finished.** If your Pi
  booted to the desktop, this is also the place to dissable that as we don't
  want it to do that.
- Issue the command `sudo reboot`.
- Finally, run `nano .bashrc` and add `cd meter && while true; do python3
  main.py; done` on a new line at the end.

This will make the RPi automatically log in and start the meter and should it
crash for any reason (although it shouldn't), it will start straight back up.
_(I don't have a fresh Pi to test this on, but it should work. If there are any
issues, with it, let me know and I'll ammend it.)_

Enabling SSH is important as once you have made it automatically login and start
the script, you can't stop it. To connect using SSH, use an Ethernet cable to
connect to your Pi then use a tool such as `nmap` to locate its IP address then
you can follow step 4
[here](https://www.raspberrypi.org/documentation/remote-access/ssh/README.md) to
gain access to it.

## Operational modes

### `A/W`
The button labled `A/W` will toggle A-weighting on the audio input being
received from the mic. This can be useful for getting a more accurate picture of
the audio level. It is not recommended to use this with `SPLIT` enabled.

### `SPEECH`
`SPEECH` mode will lower the thresholds to a second set defined in `config.py`.
This is useful as speech is almost always quieter than music and as such the
thresholds need to be lowered.

### `SPLIT`
`SPLIT` mode will seperate the audio at a frequecy defined in `config.py` (125Hz
by default) allowing bass to be analysed seperatly from trebble. When
A-weighting is enabled, a lot of the lower frequecy noise is remove and for this
reason the two are not recommended to be used together. This mode cannot be
enabled while a secondary input is being used (`LINE_IN` in `config.py`) as it
emulates a second input.

### `GRAPH`
When the `GRAPH` button is enabled, a graph will be displayed on the lower half
of the display showing the volume over a past amount of time that can be
configured in `config.py` (200 samples by default).
