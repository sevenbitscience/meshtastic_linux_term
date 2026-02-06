"""
Joey Milausnic
February 2026

Client that uses the data mode to act like a real terminal connection.

Server must be running with the `-x` flag to work with this, otherwise messages
sent with this program will be ingnored.
"""

import meshtastic
import meshtastic.serial_interface
from pubsub import pub
import selectors
import sys

# The channel that commands are sent over
COMMAND_CHANNEL=1
# Time to wait between sending messages, in seconds
MESSAGE_DELAY=5

# The maximum number of characters to send in one message
MAX_MESSAGE_CHARS=220

class MeshTerminal:
    def __init__(self, devicePath, secureChannelId):
        # Save the parameters this was called with
        self.secureChannelId = secureChannelId

        # Subscribe to whenever a message is recieved
        self.gotMessage = pub.subscribe(self.onReceive, "meshtastic.receive")
        print("[MESH_TERM] Attempting to connect to the radio...")
        # Connect to the radio
        try:
            if devicePath != "":
                self.interface = meshtastic.serial_interface.SerialInterface(devPath=devicePath)
            else:
                self.interface = meshtastic.serial_interface.SerialInterface()
            print(f"[MESH_TERM] Connected to [{self.interface.getShortName()}] {self.interface.getLongName()}")
        except Exception as e:
            print(f"[MESH_TERM] Failed to connect to meshtastic device: {e}")
            sys.exit(1)
    
    """
    Send out data from the terminal
    """
    def sendData(self):
        dataToBeSent = sys.stdin.readline()
        out = self.interface.sendData(dataToBeSent.encode("utf-8"), channelIndex=self.secureChannelId, portNum=357)

    """
    When a packet is received on the trusted channel, print the output to the 
    screen.
    """
    def onReceive(self, packet, interface):
        try:
            msg_type = packet['decoded']['portnum']
            channel = packet['channel'] 
            # Match messages on the right channel and app ID
            if channel == self.secureChannelId and msg_type == 357:
                sys.stdout.write(packet['decoded']['payload'].decode("utf-8"))
                sys.stdout.flush()
        except KeyError:
            pass

    def disconnect(self):
            self.interface.close()
            print("[MESH_TERM] Goodbye.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.disconnect()

def printHelp():
    print(
"""      Mesh Terminal (Client)
=========== OPTIONS ===========
-h --help         Show this help
   --show-devices Shows the connected meshtastic devices
-d --device       Specify a device by path on the system
-c --channel      Select which meshtastic channel to be used for secure communications
"""
)

if __name__ == "__main__":
    devicePath = ""
    channelId = COMMAND_CHANNEL
    # Parse args
    i = 0
    while i < len(sys.argv):
        if sys.argv[i] == "--show-devices":
            print(f"Found: {meshtastic.util.findPorts()}")
            sys.exit(0)
        elif sys.argv[i] == "--device" or sys.argv[i] == "-d":
            i += 1
            try:
                devicePath = str(sys.argv[i])
            except IndexError:
                print(f"[ERROR] Expected a device path, got nothing")
                sys.exit(1)
        elif sys.argv[i] == "--channel" or sys.argv[i] == "-c":
            i += 1
            try:
                channelId = int(sys.argv[i])
            except IndexError:
                print(f"[ERROR] Expected a channel id integer, got nothing") 
                sys.exit(1)
            except ValueError:
                print(f"[ERROR] Expected an integer channel id, got {sys.argv[i]}") 
                sys.exit(1)
        i += 1

    mesh_term = MeshTerminal(devicePath, channelId)

    sel = selectors.DefaultSelector()
    sel.register(sys.stdin, selectors.EVENT_READ)
    
    while True:
        try:
            for key, mask in sel.select(timeout=1):
                print("Got some data")
                mesh_term.sendData()
        except KeyboardInterrupt:
            print("Keyboard interrupt recieved, stopping.")
            mesh_term.disconnect()
            break
