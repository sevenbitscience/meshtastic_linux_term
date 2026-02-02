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

Should split paging on lines. The terminal should break it's output in 40 cols,
so I should be good to just send up to 5 lines of text in one message (40*5 =
200, about as much text as I want to send in one message)
