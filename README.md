# phonehomey

Detect if you are home or away, and trigger automation. 

phonehomey is a Python 3 project that will track if you are at home or away, and then run arbitrary scripts as you come and go. It does this by monitoring the presence of your mobile phone's MAC address on your home network. phonehomey will run 'home' and 'away' actions for each phone in the config file as they are determined to be one or the other. It will also run 'all_home' and 'all_away' actions when it's determined that all phones are home or away.

# Setup

1. Download all Python 3 required libraries and install them into a venv folder. To do this, just `cd` into this directory and type: `make`

2. Open the `config.yml` file and read the comments at the top for info regarding how to use the config file. You will need your iPhone's wifi MAC address, and a [prowlapp](https://www.prowlapp.com/) API key. Note that you can copy `config.yml` to `config_local.yml` if you wish. phonehomey will look for `config_local.yml` first. Note that `*_local*` is in the `.gitignore` file to prevent accidental commits with personal info.

3. Use [run_action.py](scripts/run_action.py) as a starting framework to write your Python automation scripts. All scripts must go in the scritps folder. You can use the same script for all actions by parsing variables that are passed in, or have unique scripts for each thing. If you don't want an action to run any automation, just use an empty script file.

# Usage

With the config file complete, run phonehomey.py from its virtual environment (shown with the optional verbose mode):

`./venv/bin/python phonehomey.py -v`

Verbose mode outputs all debug to standard out (in addition to the log file if DEBUG level is set in the config file).

# Requirements

* Python 3
* Mac OS X or linux
* [prowlapp](https://www.prowlapp.com/) $3 on iOS
* iOS only until code for a push notification api/app is added for android

# Limitations

* Arrival detection is very timely. However, departure detection time will be equal to the push notification timeout (default 15 min), meaning the phone needs to be gone for that timeout before it's determined to be away.
* The host running phonehomey must be on the same naetwork (layer 2) as the phones (wifi, or ethernet plugged into the same wifi router)

# License

[MIT](LICENSE.md)
