import meshtastic
import meshtastic.serial_interface
from pubsub import pub
import subprocess
import time
import pty
import selectors
import os
import sys
import fcntl
import termios
import struct

# The channel that commands are sent over
COMMAND_CHANNEL=1
# Time to wait between sending messages, in seconds
MESSAGE_DELAY=5

# The maximum number of characters to send in one message
MAX_MESSAGE_CHARS=220


class MeshTerminal:
    def __init__(self):
        # Subscribe to whenever a message is recieved
        self.gotMessage = pub.subscribe(self.onReceive, "meshtastic.receive")
        print("[MESH_TERM] Attempting to connect to the radio...")
        # Connect to the radio
        try:
            self.interface = meshtastic.serial_interface.SerialInterface()
            print(f"[MESH_TERM] Connected to [{self.interface.getShortName()}] {self.interface.getLongName()}")
        except Exception as e:
            print(f"[MESH_TERM] Failed to connect to meshtastic device: {e}")
            sys.exit(1)

        # Now initiallize the virtual terminal
        print("[MESH_TERM] Connecting to virtual terminal session...")

        # Get the current terminal setup and set it up for max-dumb (there are no 
        # colors, formatting or anything fancy over meshtastic, so we just want 
        # plain text output
        my_env = os.environ.copy()
        my_env["TERM"] = "dumb"
        my_env["PAGER"] = "cat"
        my_env["EDITOR"] = "cat"
        my_env["COLUMNS"] = "40"
        my_env["ROWS"] = "5"
        my_env["PS1"] = "\\u:\\w\\$ "

        # Create a pty terminal
        self.master_fd, self.slave_fd = pty.openpty()
        
        # Set the size of the terminal (40 x 5 should be alright)
        size_struct = struct.pack('HHHH', 24, 40, 0, 0)
        fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, size_struct)

        # Disable echo in the terminal
        attrs = termios.tcgetattr(self.slave_fd)
        attrs[3] = attrs[3] & ~termios.ECHO
        termios.tcsetattr(self.slave_fd, termios.TCSANOW, attrs)

        # Start up bash on the terminal
        self.my_pty = subprocess.Popen(['/bin/bash', '--norc', '-i'], 
                                  stdin=self.slave_fd,
                                  stdout=self.slave_fd,
                                  stderr=self.slave_fd,
                                  env=my_env,
                                  close_fds=True)

    def disconnect(self):
            self.interface.close()
            os.close(self.master_fd)
            os.close(self.slave_fd)
            print("[MESH_TERM] Goodbye.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.disconnect()


    """
    When a packet is received from the radio, check if it is in the encrypted 
    channel and then run the command within it.
    """
    def onReceive(self, packet, interface):
        #print(f"Got: {packet}")
        try:
            msg_type = packet['decoded']['portnum']
            channel = packet['channel'] 
            # Match text messages on the right channel
            if channel == COMMAND_CHANNEL and msg_type == 'TEXT_MESSAGE_APP':
                message_txt = packet['decoded']['payload'].decode()

                print(f"[MESH_TERM][MESSAGE LISTENER] Got a message on the authorized channel!\n{message_txt}")
                
                # Run the command that we got sent
                os.write(self.master_fd, (message_txt + "\n").encode())
                print('='*80)
        except KeyError:
            pass

    """
    Listen for text on the terminal and send it over the secure channel
    """
    def sendTtyFeedback(self):
        data = os.read(self.master_fd, 2048).decode("utf-8")
        if data:
            print(f"[MESH_TERM][SEND_TTY] Got data: {data}")
            chunks = self.chunk_data_on_lines(data, MAX_MESSAGE_CHARS)
            for msg in chunks:
                msg = msg.removesuffix('\r\n')
                print("[MESH_TERM][SEND_TTY] Sending a chunk...")
                print(msg,end='')
                self.interface.sendText(msg, wantAck=True, channelIndex=COMMAND_CHANNEL)
                if msg[-1] != '\n': print('')
                time.sleep(MESSAGE_DELAY)
            print('='*80)

    def split_by_length(self, text, length):
        return [text[i:i+length] for i in range(0, len(text), length)]

    def chunk_data_on_lines(self, text, max_chunk_size):
        #print("[MESH_TERM][CHUNKER] Starting chunker...")
        out = [""] 
        for line in text.splitlines(keepends=True):
            if len(out[-1]) + len(line) > max_chunk_size-1:
                #print(f"[MESH_TERM][CHUNKER] LINE IS TOO MUCH: \"{line.strip('\r\n')}\"")
                out.append(line.strip(''))
            else:
                #print(f"[MESH_TERM][CHUNKER] LINE IS GOOD \"{line.strip('\r\n')}\"")
                out[-1] += line
        #print(f"[MESH_TERM][CHUNKER] DONE: {out}")
        return out

if __name__ == "__main__":

    mesh_term = MeshTerminal()
    
    sel = selectors.DefaultSelector()
    sel.register(mesh_term.master_fd, selectors.EVENT_READ)

    while True:
        try:
            events = sel.select(timeout=1)
            for key, mask in events:
                if key.fd == mesh_term.master_fd:
                    mesh_term.sendTtyFeedback()
            time.sleep(1)
        except KeyboardInterrupt:
            print("Keyboard interrupt recieved, stopping.")
            mesh_term.disconnect()
            break
