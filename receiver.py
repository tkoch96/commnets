# Written by S. Mevawala, modified by D. Gitzel

import channelsimulator
import numpy as np, logging
from helper_funcs import *
import utils


class BogoReceiver(object):

    def __init__(self, inbound_port=50005, outbound_port=50006, timeout=10, debug_level=logging.DEBUG):
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
        
        #specificies locations of header fields in the header block
        self.size_of_sequence_number = 8
        self.index_of_sequence_number = 1
        self.size_of_checksum = 2
        self.index_of_checksum = self.index_of_sequence_number + self.size_of_sequence_number
        self.index_of_fin = self.index_of_checksum + self.size_of_checksum
        self.size_of_header = self.size_of_checksum + self.size_of_sequence_number + 1

        #data oriented things
        self.max_data_size_sender = 1024 - self.size_of_header #bytes
        self.size_rand_data = 500 #bytes - for checksumming the ack purposes
        self.size_data_type = 16 #number of bits constituting one element of data

        #connection - oriented things
        self.connection_active = False
        self.sequence_number = to_bin(0,num_bytes=self.size_of_sequence_number) #number of next packet it hopes to receive
        self.data = '' #store final bytes in string representing bits
        self.data_queue = {} #holds packets in the queue for re-ordering

    def initialize_sequence_number(self, sn):
        #begin connection, set the sequence number to the starting value
        self.starting_sequence_number = sn
        self.sequence_number = sn

    def store(self,data,sequence_number):
        #store data in the queue
        self.data_queue[sequence_number] = data

    def print_data(self):
        # assume data is numeric sequence of bytes
        print(self.data)

    def update_data(self):
        # we have received the next packet in the sequence, so we 
        # would like to update our pointer to the next packet we would like to receive
        # we may have received future packets which are waiting in the queue so we would like to push our 
        if self.data_queue == {}:
            #no future packets waiting
            self.sequence_number = to_bin(self.max_data_size_sender + int(self.sequence_number,2),num_bytes=self.size_of_sequence_number)
        else:
            #TODO: Maybe handle wrap-around of sequence numbers?
            seq_num_ints = [int(el,2) for el in self.data_queue.keys()]
            for sn in np.sort(seq_num_ints):
                if to_bin(sn,num_bytes=self.size_of_sequence_number) == self.sequence_number:
                    #this is the next packet we are waiting for so update the sequence number
                    self.sequence_number = to_bin(self.max_data_size_sender + int(self.sequence_number,2),num_bytes=self.size_of_sequence_number)
                    #add this data to the final data
                    self.data += self.data_queue[to_bin(sn, num_bytes=self.size_of_sequence_number)]
                    #remove this from the queue
                    del self.data_queue[to_bin(sn, num_bytes=self.size_of_sequence_number)]
        print("Updated next expected byte to: %d"%(int(self.sequence_number,2) - int(self.starting_sequence_number,2)))

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
            print("\n\nParsing packet.")
            
            #print("Packet: %s"%packet)
            #packet = packet[2:] #get rid of beginning nonsense
            header = packet[0:self.size_of_header*8] #grab header
            #print("Received header: %s"%header)
            data = packet[self.size_of_header*8:] #grab data
            sequence_number = header[0:self.size_of_sequence_number * 8]
            #print("Received sequence number: %s"%sequence_number)
            header_chksum = header[(self.index_of_checksum - 1) * 8: (self.index_of_checksum + self.size_of_checksum - 1) * 8]
            fin = header[(self.index_of_fin - 1) * 8: self.index_of_fin * 8]
            data_chksum = calculate_checksum(data)
            #create random data and checksum to send back to client
            sd = np.random.randint(0,2^8,size=(1,self.size_rand_data))[0]
            send_data = ''
            #print("random number being sent: %d"%send_data)
            for num in sd:
                send_data += to_bin(num, num_bytes=1)
            #print("Sending data back: %s"%send_data)
            send_checksum = calculate_checksum(send_data)

            if not (data_chksum == header_chksum):
                #send an ack for the next packet we hope to receive in the sequence
                #print("Data checksum: %s"%data_chksum)
                #print("Header checksum: %s"%header_chksum)
                print("Checksum invalid, next expected frame is %d."%(int(sequence_number,2) - int(self.starting_sequence_number,2)))

            else:
                
                if not self.connection_active:
                    #TODO make a hello sequence, during which they agree on the starting sequence number
                    self.connection_active = True
                    self.initialize_sequence_number(sequence_number)

                print("Checksum valid, received sequence_number: %d."%(int(sequence_number,2) - int(self.starting_sequence_number,2)))

                self.store(data,sequence_number) #store this data, with the corresponding sequence number
                if sequence_number == self.sequence_number:
                    # if this is the next packet in the sequence, update the current sequence number
                    self.update_data()

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
            self.simulator.u_send(send_packet)  # send packet

            # self.print_data()

if __name__ == "__main__":
    rcvr = JerrTom_recv()
    rcvr.receive()
