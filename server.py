import meshtastic
import meshtastic.serial_interface
from pubsub import pub
import subprocess
import time
import textwrap

# The channel that commands are sent over
COMMAND_CHANNEL=1
# Time to wait between sending messages, in seconds
MESSAGE_DELAY=5

# The maximum number of characters to send in one message
MAX_MESSAGE_CHARS=220

def split_by_length(text, length):
    return [text[i:i+length] for i in range(0, len(text), length)]

"""
Runs a shell command and returns the output
"""
def run_command(command):
    result = subprocess.run(
            command,
            capture_output=True,
            text = True
            )
    #print(f"Recieved command {' '.join(command)}, got stdout={result.stdout}, stderr={result.stderr}")
    return (result.stdout, result.stderr)

def onReceive(packet, interface):
    #print(f"Got: {packet}")
    try:
        msg_type = packet['decoded']['portnum']
        channel = packet['channel'] 
        # Match text messages on the right channel
        if channel == COMMAND_CHANNEL and msg_type == 'TEXT_MESSAGE_APP':
            message_txt = packet['decoded']['payload'].decode()

            print(f"{'='*80}\nGot a message on interesting channel!\n{message_txt}")
            
            # Run the command that we got sent
            try:
                out, err = run_command(message_txt.split(' '))
            except FileNotFoundError:
                interface.sendText("Command not found", channelIndex=COMMAND_CHANNEL)
                print(f"Command was not found\n{'='*80}")
                return

            # We got some output, lets send it back on the shared channel
            msg_full = out if not err == b'' else out + "\nGot error:" + err
            print(f"Command returned:\n") #{msg_full}\n{'='*80}")
            chunks = split_by_length(msg_full, MAX_MESSAGE_CHARS)
            for msg in chunks:
                print(msg,end='')
                interface.sendText(msg, wantAck=True, channelIndex=COMMAND_CHANNEL)
                time.sleep(MESSAGE_DELAY)
            print('='*80)
    except KeyError:
        pass

if __name__ == "__main__":
    # Subscribe to whenever a message is recieved
    gotMessage = pub.subscribe(onReceive, "meshtastic.receive")
    
    print("Attempting to connect to the radio")
    # Connect to the radio
    interface = meshtastic.serial_interface.SerialInterface()
    print("Connected!")
    
    while True:
        try: time.sleep(10)
        except KeyboardInterrupt:
            print("Keyboard interrupt recieved, stopping.")
            interface.close()
            break
