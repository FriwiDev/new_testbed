class MacUtil(object):

    def __init__(self):
        self.next_mac = 0x815

    # Method from distrinet util.py
    def _colon_hex(self, val: int, bytecount: int) -> str:
        """Generate colon-hex string.
           val: input as unsigned int
           bytecount: number of bytes to convert
           returns: chStr colon-hex string"""
        pieces = []
        for i in range(bytecount - 1, -1, -1):
            piece = ((0xff << (i * 8)) & val) >> (i * 8)
            pieces.append('%02x' % piece)
        ch_str = ':'.join(pieces)
        return ch_str

    # Method from distrinet util.py
    def _mac_colon_hex(self, mac: int) -> str:
        """Generate MAC colon-hex string from unsigned int.
           mac: MAC address as unsigned int
           returns: macStr MAC colon-hex string"""
        return self._colon_hex(mac, 6)

    def generate_new_mac(self) -> str:
        ret = self._mac_colon_hex(self.next_mac)
        self.next_mac += 1
        return ret
