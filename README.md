# Meshtastic Linux Terminal

[ WIP ]

Provide remote control access to a Linux machine using Meshtastic radios.

## Setup Instructions

Install the meshtastic python interface with

```
pip3 install --upgrade "meshtastic[cli]"
```

Further install instructions for meshtastic found
[here](https://meshtastic.org/docs/software/python/cli/installation/)


# TODOs

Currently it just runs commands using subprocess, but it would probably be
better if it offered a connection to an actual virtual terminal, perhaps like
what [pty](https://docs.python.org/3/library/pty.html) offers.
