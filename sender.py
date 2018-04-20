# Written by S. Mevawala, modified by D. Gitzel

import socket
import channelsimulator
import numpy as np, struct

from helper_funcs import *

class BogoSender(object):

    def __init__(self):
        #super(self, BogoSender).__init__()
        self.simulator = channelsimulator.ChannelSimulator(True)  # False for receiver
        self.simulator.sndr_setup(1)
        self.simulator.rcvr_setup(1)

    def send(self):
        while True:
            try:
                self.simulator.u_send(bin(2344))  # send data
                ack = self.simulator.u_receive()  # receive ACK
                print ack
                break
            except socket.timeout:
                pass


class JerrTom_send(BogoSender):
    def __init__(self):
        super(JerrTom_send,self).__init__()

    def check_my_checksum(self, packet, checksum):
        # checks to see if checksum is a valid checksum for packet
        total = 0
        for char in packet:
            total += struct.unpack('B', char)[0]
        return total + checksum == 256

    def send(self, data='1000010100100111'):
        # send data to host using simulator
        np.random.seed(4)

        #create header for packet
        sequence_number = np.random.randint(0,256) #1 byte
        checksum = calculate_checksum(data) #1 byte
        fin = to_bin(0,num_bytes = 1) #fin byte

        print("Checksum: %s"%str(checksum))
        #create header
        header = to_bin(sequence_number) + str(checksum) + fin
        #change data to binary
        payload = data

        #concatenate pieces of the packet
        packet = '0b' + header + payload
        print("Header: %s"%header)
        print("Payload: %s"%payload)
        while True:
            try:
                self.simulator.u_send(packet)
                ack = self.simulator.u_receive()  # receive ACK
                print("Ack: %s"%ack)
                break
            except socket.timeout:
                pass

if __name__ == "__main__":
    sndr = JerrTom_send()
    sndr.send()

