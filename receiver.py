# Written by S. Mevawala, modified by D. Gitzel

import channelsimulator
import numpy as np, logging
from helper_funcs import *
import utils


class BogoReceiver(object):

    def __init__(self, inbound_port=50005, outbound_port=50006, timeout=10, debug_level=logging.INFO):
        self.logger = utils.Logger(self.__class__.__name__, debug_level)

        self.inbound_port = inbound_port
        self.outbound_port = outbound_port
        self.simulator = channelsimulator.ChannelSimulator(inbound_port=inbound_port, outbound_port=outbound_port,
                                                           debug_level=debug_level)
        self.simulator.rcvr_setup(timeout)
        self.simulator.sndr_setup(timeout)

    def receive(self):
        while True:
            print self.simulator.u_receive()  # receive data
            self.simulator.u_send(bin(123))  # send ACK


class JerrTom_recv(BogoReceiver):
    def __init__(self):
        super(JerrTom_recv,self).__init__()
        self.size_of_header = 10 #bytes
        #specificies locations of header fields in the header block
        self.size_of_sequence_number = 8
        self.index_of_sequence_number = 1
        self.index_of_checksum = 9
        self.index_of_fin = 10

        #data oriented things
        self.size_rand_data = 5 #bytes - for checksumming the ack purposes
        self.size_data_type = 16 #number of bits constituting one element of data

        #connection - oriented things
        self.connection_active = False
        self.sequence_number = 0 #number of next packet it hopes to receive
        self.data = '' #store final bytes in string form for file transfers
        self.data_queue = [] #holds packets in the queue for re-ordering
        self.max_data_queue_size = 1024 #bytes

    def store(self,data,sequence_number):
        #TODO need to make this more complicated
        #print("Storing data for later: %s"%data)
        self.data += data

    def print_data(self):
        # assume data is numeric sequence of bytes
        print(self.data)

    def receive(self):
        while True:
            packet = self.simulator.u_receive()
            if packet is None:
                print("Packet not received.")
                return
            packet = [to_bin(bite,num_bytes = 1) for bite in packet]
            p = ''
            for bite in packet:
                p += bite
            packet = p
            
            #print("Packet: %s"%packet)
            #packet = packet[2:] #get rid of beginning nonsense
            header = packet[0:self.size_of_header*8] #grab header
            #print("Received header: %s"%header)
            data = packet[self.size_of_header*8:] #grab data
            sequence_number = header[0:self.size_of_sequence_number * 8]
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
                #problem with the packet - drop it
                #TODO: don't drop it?
                print("Data checksum: %s"%data_chksum)
                print("Header checksum: %s"%header_chksum)

                self.sequence_number = sequence_number #still waiting for this packet
                print("Checksum invalid.")

            else:
                print("Checksum valid.")
                self.sequence_number = int(sequence_number,2) + len(data) / 8
                self.sequence_number = to_bin(self.sequence_number, num_bytes = self.size_of_sequence_number)
                self.store(data,sequence_number)

            fin_ack = to_bin(0,num_bytes=1)
            if fin == to_bin(1, num_bytes = 1): 
                #if the fin byte is checked, end the connection
                print("Acknowledging desire to close connection.")
                fin_ack = to_bin(1,num_bytes=1)

            send_seq_num = self.sequence_number

            #form packet
            send_header = send_seq_num + send_checksum + fin_ack
            send_packet = to_seq_of_ints(send_header + send_data)
            send_packet = bytearray(send_packet)
            print("Sending packet back...")
            print(len(send_packet))
            self.simulator.u_send(send_packet)  # send packet

            # self.print_data()

if __name__ == "__main__":
    rcvr = JerrTom_recv()
    rcvr.receive()
