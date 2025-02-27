import os
import re
import socket

from netframe import Client, Message
from protocol import PROTOCOL, fs_add, fs_del, fs_get, fs_get_resp, fs_list, fs_list_resp, fs_ack


def req_add(client: Client, filename: str, size: int):
    req = fs_add()
    req.filename = filename
    req.file = os.urandom(size)
    client.send(req.pack())

    handle_resp(client.recv(), [PROTOCOL.ACK])


def req_get(client: Client, filename: str):
    req = fs_get()
    req.filename = filename
    client.send(req.pack())

    handle_resp(client.recv(), [PROTOCOL.GET_RESP, PROTOCOL.ACK])


def req_del(client: Client, filename: str):
    req = fs_del()
    req.filename = filename
    client.send(req.pack())

    handle_resp(client.recv(), [PROTOCOL.ACK])


def req_list(client: Client):
    pkt = fs_list()
    client.send(pkt.pack())

    handle_resp(client.recv(), [PROTOCOL.LIST_RESP])


def handle_resp(resp: Message, expected: list[int]):
    idToType = {
        PROTOCOL.ACK:       fs_ack,
        PROTOCOL.GET_RESP:  fs_get_resp,
        PROTOCOL.LIST_RESP: fs_list_resp,
    }

    if resp.hdr.id not in expected:
        print("[-]Unexpected response")
        return
    
    pkt = idToType[resp.hdr.id]()
    pkt.unpack(resp)
    print(pkt)


def is_valid_filename(filename: str):
    if not filename or len(filename) > 255 or \
        filename[0] == ' ' or filename[-1] in [' ', '.']:
        return False
    
    invalidChs = r'[\\/:*?"<>|\x00-\x1F]'
    if re.search(invalidChs, filename):
        return False
    
    return True


def main():
    client = Client()
    addr = socket.gethostbyname(socket.gethostname())
    client.connect(ip=addr, port=54314)

    while True:
        cmd = input("\nEnter:\n"
            "1 <name> <len> - to send random <len> bytes on server for storage in a file named <name>\n"
            "2 <name> - to download and display contents of the file <name>\n"
            "3 <name> - to delete file <name> from the server\n"
            "4 - to list all files stored on server with their respective sizes\n"
            "5 - to quit\n")
        
        args = cmd.split(' ')
        if not args[0].isdigit():
            print("[-]Invalid command, first arg must be a number")
            continue
        code = int(args[0])
        
        match code:
            case 1:
                if len(args) <= 2 or not is_valid_filename(args[1]) or not args[2].isdigit():
                    print("[-]Incorrect args")
                    continue
                req_add(client, args[1], int(args[2]))
            case 2:
                if len(args) <= 1 or not is_valid_filename(args[1]):
                    print("[-]Incorrect args")
                    continue
                req_get(client, args[1])
            case 3:
                if len(args) <= 1 or not is_valid_filename(args[1]):
                    print("[-]Incorrect args")
                    continue
                req_del(client, args[1])
            case 4:
                req_list(client)
            case 5:
                client.shutdown()
                break
            case _:
                print("[-]Unexpected command")


if __name__ == "__main__":
    main()