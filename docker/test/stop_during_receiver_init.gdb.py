"""AArch64 debugger fixture: stop at the observed native initialization seam."""
import os
import signal

import gdb


class StopDuringReceiverInitialization(gdb.Breakpoint):
    def __init__(self):
        super().__init__('notifyLogMessageListener', internal=True)
        self.injected = False

    def stop(self):
        if self.injected:
            return False
        # GCC/libstdc++ AArch64 ABI: arg x1 is std::string const&;
        # its first two words are data pointer and size. No inferior calls.
        string_address = int(gdb.parse_and_eval('$x1'))
        inferior = gdb.selected_inferior()
        layout = bytes(inferior.read_memory(string_address, 16))
        address = int.from_bytes(layout[:8], 'little')
        length = int.from_bytes(layout[8:], 'little')
        expected = b'sick_scansegment_xd initializing...'
        if length != len(expected):
            return False
        if bytes(inferior.read_memory(address, length)) != expected:
            return False
        self.injected = True
        gdb.write('INJECT STOP BEFORE UDP RECEIVER INITIALIZATION\n')
        # Fix the race timing: the real pre-shutdown callback sets this flag.
        # Also deliver SIGINT so native context shutdown and joins really run.
        gdb.execute('set {unsigned char}&s_shutdownSignalReceived = 1')
        os.kill(inferior.pid, signal.SIGINT)
        return False


StopDuringReceiverInitialization()
