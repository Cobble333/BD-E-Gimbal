from serial import Serial

class GimbalController:
    def __init__(self, port, address, baudrate=9600):
        self.port = port
        self.address = address
        self.baudrate = baudrate

    def _send(self, cmd1, cmd2, data1, data2):
        packet = bytearray(7)
        packet[0] = 0xFF
        packet[1] = self.address
        packet[2] = cmd1
        packet[3] = cmd2
        packet[4] = data1
        packet[5] = data2
        packet[6] = sum(packet[1:6]) % 256
        with Serial(self.port, self.baudrate, timeout=1) as ser:
            ser.write(packet)

    def pan_left(self, speed):  self._send(0x00, 0x04, speed, 0x00)
    def pan_right(self, speed): self._send(0x00, 0x02, speed, 0x00)
    def tilt_up(self, speed):   self._send(0x00, 0x08, 0x00, speed)
    def tilt_down(self, speed): self._send(0x00, 0x10, 0x00, speed)
    def stop(self):             self._send(0x00, 0x00, 0x00, 0x00)
