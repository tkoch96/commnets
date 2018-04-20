# Written by S. Mevawala, modified by D. Gitzel

import channelsimulator
import numpy as np
from helper_funcs import *


class BogoReceiver(object):

    def __init__(self):
        #super(self, BogoReceiver).__init__()
        self.simulator = channelsimulator.ChannelSimulator(False)  # False for receiver
        self.simulator.rcvr_setup()
        self.simulator.sndr_setup()

    def receive(self):
        while True:
            print self.simulator.u_receive()  # receive data
            self.simulator.u_send(bin(123))  # send ACK


class JerrTom_recv(BogoReceiver):
    def __init__(self):
        super(JerrTom_recv,self).__init__()
        self.size_of_header = 3 #bytes
        #specificies locations of header fields in the header block
        self.index_of_sequence_number = 1
        self.index_of_checksum = 2
        self.index_of_fin = 3

        #data oriented things
        self.size_rand_data = 5 #bytes - for checksumming the ack purposes
        self.size_data_type = 16 #number of bits constituting one element of data

        #connection - oriented things
        self.connection_active = False
        self.sequence_number = 0 #number of next packet it hopes to receive
        self.data = ''

    def store(self,data,sequence_number):
        #TODO need to make this more complicated
        print("Storing data for later: %s"%data)
        self.data += data

    def print_data(self):
        # assume data is numeric sequence of bytes
        print(self.data)


    # def undo_binary(self,data):
    #     #takes in a binary value and returns integer string 
    #     num_samps = len(data) / self.size_data_type
    #     ret = ''
    #     for i in range(num_samps):
    #         this_samp = self.data[i * 8: (i+1) * 8]
    #         this_samp_int = 0
    #         for j,char in enumerate(this_samp):
    #             if char is '1':
    #                 this_samp_int += 2^j
    #         if ret != ''
    #             ret += '-' #spacer
    #         ret += str(this_samp_int)
    #     return ret

    def receive(self):
        while True:
            packet = self.simulator.u_receive()  # receive packet
            #print("Packet: %s"%packet)
            packet = packet[2:] #get rid of beginning nonsense
            header = packet[0:self.size_of_header*8] #grab header
            data = packet[self.size_of_header*8:] #grab data
            sequence_number = header[0:self.index_of_sequence_number * 8]
            #print("Received sequence number: %s"%sequence_number)
            header_chksum = header[(self.index_of_checksum - 1) * 8: self.index_of_checksum * 8]
            fin = header[(self.index_of_fin - 1) * 8: self.index_of_fin * 8]
            data_chksum = calculate_checksum(data)
            #create random data and checksum to send back to client
            send_data = np.random.randint(0,np.power(2,3 * self.size_rand_data))
            #print("random number being sent: %d"%send_data)
            send_data = to_bin(send_data, self.size_rand_data)
            #print("Sending data back: %s"%send_data)
            send_checksum = calculate_checksum(send_data)

            if not (data_chksum == header_chksum):
                #problem with the packet, send an ACK for the next packet we want to receive
                print("Checksum invalid")
                start_seq_num = to_bin(self.sequence_number)

            else:
                print("Checksum valid")    
                if not self.connection_active:
                    #start the connection
                    self.connection_active = True  
                    self.sequence_number = int(sequence_number) + 1
                    self.store(data,sequence_number)
                else:
                    self.sequence_number = int(sequence_number) + 1
                    self.store(data,sequence_number)

            if fin == to_bin(1): #if the fin byte is checked, end the connection
                # TODO make a fin ack
                self.connection_active = False
                self.start_seq_num = 0

            send_seq_num = str(self.sequence_number)
            send_seq_num = pad_binary_str(send_seq_num)

            #form packet
            send_header = send_seq_num + send_checksum
            send_packet = '0b' + send_header + send_data  
            print("Sending checksum: %s"%send_checksum)
            print("Next expected packet: %d"%self.sequence_number)
            print("Sending packet back: %s"%send_packet)

            self.simulator.u_send(send_packet)  # send packet

            # self.print_data()

if __name__ == "__main__":
    rcvr = JerrTom_recv()
    rcvr.receive()
