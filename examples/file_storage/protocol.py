from netframe import Message

class PROTOCOL:
    NONE = 0
    ADD = 1
    DEL = 2
    GET = 3
    GET_RESP = 4
    LIST = 5
    LIST_RESP = 6
    ACK = 7

FILE_LEN_FIELD_SIZE = 4
FILE_NAME_FIELD_SIZE = 1

class fs_packet:
    def __init__(self, id):
        self.id = id

    def pack(self) -> Message:
        msg = Message()
        msg.hdr.id = self.id
        
        return msg

    def unpack(self, msg: Message):
        self.id = msg.hdr.id


class fs_file_op(fs_packet):
    def __init__(self, id):
        super().__init__(id)
        self.filename: str = ''

    def pack(self) -> Message:
        msg = super().pack()
        filenameBytes = self.filename.encode()
        msg.append(len(filenameBytes).to_bytes(FILE_NAME_FIELD_SIZE, 'little'))
        msg.append(filenameBytes)
        
        return msg

    def unpack(self, msg: Message):
        self.id = msg.hdr.id
        fileNameLen = int.from_bytes(msg.pop(FILE_NAME_FIELD_SIZE), 'little')
        self.filename = msg.pop(fileNameLen).decode()


class fs_file_transfer(fs_file_op):
    def __init__(self, id) -> None:
        super().__init__(id)
        self.file: bytes = b''

    def pack(self) -> Message:
        msg = super().pack()
        msg.append(len(self.file).to_bytes(FILE_LEN_FIELD_SIZE, 'little'))
        msg.append(self.file)

        return msg

    def unpack(self, msg: Message):
        super().unpack(msg)
        fileLen = int.from_bytes(msg.pop(FILE_LEN_FIELD_SIZE), 'little')
        self.file = msg.pop(fileLen)

        
class fs_add(fs_file_transfer):
    def __init__(self):
        super().__init__(id=PROTOCOL.ADD)


class fs_del(fs_file_op):
    def __init__(self):
        super().__init__(id=PROTOCOL.DEL)


class fs_get(fs_file_op):
    def __init__(self):
        super().__init__(id=PROTOCOL.GET)


class fs_get_resp(fs_file_transfer):
    def __init__(self):
        super().__init__(PROTOCOL.GET_RESP)

    def __repr__(self):
        return f'{self.filename}: {self.file.hex()}'


class fs_list(fs_packet):
    def __init__(self):
        super().__init__(id=PROTOCOL.LIST)


class fs_list_resp(fs_packet):
    FILE_COUNT_FIELD_SIZE = 2

    def __init__(self):
        super().__init__(id=PROTOCOL.LIST_RESP)
        self.filenameToSize: dict[str, int] = {}

    def pack(self):
        msg = super().pack()
        msg.append(len(self.filenameToSize).to_bytes(self.FILE_COUNT_FIELD_SIZE, 'little'))
        for filename, size in self.filenameToSize.items():
            filenameBytes = filename.encode()
            msg.append(len(filenameBytes).to_bytes(FILE_NAME_FIELD_SIZE, 'little'))
            msg.append(filenameBytes)
            msg.append(size.to_bytes(FILE_LEN_FIELD_SIZE, 'little'))

        return msg

    def unpack(self, msg: Message):
        super().unpack(msg)

        fileCount = int.from_bytes(msg.pop(self.FILE_COUNT_FIELD_SIZE), 'little')
        for _ in range(fileCount):
            filenameLen = int.from_bytes(msg.pop(FILE_NAME_FIELD_SIZE), 'little')
            filename = msg.pop(filenameLen).decode()
            size = int.from_bytes(msg.pop(FILE_LEN_FIELD_SIZE), 'little')
            
            self.filenameToSize[filename] = size

    def __repr__(self):
        ret = ''
        for name, size in self.filenameToSize.items():
            ret += f"{name}: {size}b\n"
        return ret

            
class fs_ack(fs_packet):
    RC_FIELD_SIZE = 1
    class RC:
        NONE = 0
        OK = 1
        FILE_EXISTS = 2
        FILE_NOT_FOUND = 3

    def __init__(self):
        super().__init__(id=PROTOCOL.ACK)
        self.rc = self.RC.NONE

    def pack(self) -> Message:
        msg = super().pack()
        msg.append(self.rc.to_bytes(self.RC_FIELD_SIZE, 'little'))

        return msg

    def unpack(self, msg: Message):
        super().unpack(msg)
        self.rc = int.from_bytes(msg.pop(self.RC_FIELD_SIZE), 'little')

    def __repr__(self):
        rcToMsg = {
            self.RC.OK:             "[+]OK",
            self.RC.FILE_EXISTS:    "[-]File with that name already exists",
            self.RC.FILE_NOT_FOUND: "[-]File not found",
        }
        return rcToMsg.get(self.rc, "[-]Unexpected return code")