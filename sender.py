# Written by S. Mevawala, modified by D. Gitzel

import socket
import channelsimulator
import time
import numpy as np, struct
import utils, logging

from helper_funcs import *

class BogoSender(object):

    def __init__(self, inbound_port=50006, outbound_port=50005, timeout=10, debug_level=logging.INFO):
        self.logger = utils.Logger(self.__class__.__name__, debug_level)

        self.inbound_port = inbound_port
        self.outbound_port = outbound_port
        self.simulator = channelsimulator.ChannelSimulator(inbound_port=inbound_port, outbound_port=outbound_port,
                                                           debug_level=debug_level)
        self.simulator.sndr_setup(timeout)
        self.simulator.rcvr_setup(timeout)


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
        self.size_of_header = 10 #bytes
        #specificies locations of header fields in the header block (in bytes)
        self.size_of_sequence_number = 8 #bytes
        self.index_of_sequence_number = 1
        self.index_of_checksum = 9
        self.index_of_fin_ack = 10

        self.max_data_size = 1024 - self.size_of_header #bytes

        #connection oriented things
        self.start_sequence_number = 0 #offset accounting for random starting sequence number
        self.curr_wind = 0 #receiver has acked up to this byte
        self.curr_sent = 0 #sent up to but not including this byte
        self.queued_acks = [] # holds acks about future packets
        self.data = None #data to send to the host
        self.sequence_number = 0
        self.send_fin = False

    def check_if_done(self):
        # checks to see if our current window is at the length of the data
        byte_num = int(self.curr_wind,2) - int(self.start_sequence_number,2)
        return byte_num == len(self.data) / 8

    def get_data(self,seq_num):
        #retrieve data from the cache with sequence number seq_num
        byte_number = int(seq_num,2) - int(self.start_sequence_number,2)
        #either get the maximum amount, or whatever we have left to transmit
        len_data_packet = np.minimum(self.max_data_size * 8, len(self.data[byte_number * 8:]))
        data = self.data[byte_number * 8:byte_number * 8 + len_data_packet]
        print("Byte number: %d"%byte_number)
        #print("Len data packet: %d"%len_data_packet)
        #print("Len data: %d"%len(data))
        return data

    def send_packet(self, seq_num, fin_bit = None):
        #send the packet whose sequence number starts with seq_num
        print("Sending packet to host")
        if fin_bit is None:
             fin_bit = int(self.send_fin)
        data = self.get_data(seq_num)
        checksum = calculate_checksum(data)
        fin = to_bin(fin_bit, num_bytes = 1)

        header = seq_num + checksum + fin
        #print("Sending header: %s"%header)
        packet = to_seq_of_ints(header + data) #convert this string data to ints
        packet = bytearray(packet) #make it a bytearray for transmission
        self.curr_sent = to_bin(int(seq_num,2) + len(data) / 8,num_bytes = self.size_of_sequence_number)
        self.simulator.u_send(packet)

    def handle_response(self, packet):
        ## Packet parsing
        print("Parsing packet...")
        packet = [to_bin(bite,num_bytes = 1) for bite in packet]
        p = ''
        for bite in packet:
            p += bite
        packet = p
        header = packet[0:self.size_of_header*8] #grab header
        data = packet[self.size_of_header*8:] #grab data
        sequence_number = header[0:self.size_of_sequence_number * 8]
        header_chksum = header[(self.index_of_checksum - 1) * 8: self.index_of_checksum * 8]
        fin_ack = header[(self.index_of_fin_ack - 1) * 8: self.index_of_fin_ack * 8]

        # calculate checksum of data enclosed in the packet
        data_chksum = calculate_checksum(data)

        if not (data_chksum == header_chksum):
            #TODO: probably ignore cases like this, instead go with timeouts
            #going with timeouts will prevent duplicate data
            print("Checksum invalid")
            return

        else:
            #host successfully received a packet, record the sequence number
            if int(fin_ack) == 1:
                #if we opted to close the connection, cool
                print("Connection closed! Data transfer complete.")
                exit(0)
            #receiver is expecting packet with sequence_number next, so its received up
            #to sequence_number bytes
            self.update_curr_wind(sequence_number)

    def update_curr_wind(self, sequence_number):
        # try to update our current window with the sequence number sent by the host
        # this may not succeed, due to out of order processing of packets
        #print("Sequence number: %d"%int(sequence_number,2))
        #print("Current window: %d"%int(self.curr_wind,2))
        #print("Difference: %d"%(int(sequence_number,2) - int(self.curr_wind,2)))
        #exit(0)
        if sequence_number == self.curr_wind:
            # this is the oldest packet we are waiting for - update the current window
            self.curr_wind = to_bin(self.max_data_size + int(self.curr_wind,2), num_bytes=self.size_of_sequence_number)
            if int(self.curr_wind,2) - int(self.start_sequence_number,2) > len(self.data) / 8:
                #we are expecting the end of the sequence
                self.curr_wind = to_bin(len(self.data) / 8 + int(self.start_sequence_number,2),num_bytes=self.size_of_sequence_number)

            tmp_acks = [int(ack) for ack in self.queued_acks]
            for ack in np.sort(tmp_acks):
                # TODO: check for wrap-around on these numbers...
                # wrapped-around sequence numbers will be assessed first (and always be wrong)
                if str(ack) != self.curr_wind:
                    return
                self.curr_wind = to_bin(self.max_data_size + int(self.curr_wind,2), num_bytes=self.size_of_sequence_number)
                #TODO: remove things from the tmp acks list
        else:
            # the oldest packet we are waiting for has not yet arrived
            # add this to a list of queued acks
            self.queued_acks.append(sequence_number)

    def send(self, data='1000010100100111'):
        #send the data specified by data to the receiver using u_send
        #if the data size is greater than the MTU, it will use more than one transmission
        self.data = data

        #create header for packet
        sequence_number = np.random.randint(0,np.power(2,3*self.size_of_sequence_number))
        self.start_sequence_number = to_bin(sequence_number,num_bytes=self.size_of_sequence_number)
        self.curr_wind = to_bin(int(self.start_sequence_number,2) + self.max_data_size,num_bytes=self.size_of_sequence_number)
        self.curr_sent = self.start_sequence_number
        while True:
            try:
                #TODO: check to see if we are past our current data-sending limit
                self.send_packet(self.curr_sent) #send packet to receiver
                response = self.simulator.u_receive() #get a response
                self.handle_response(response) #process this response
                if self.check_if_done():
                    #check to see if we have any more data to transmit
                    self.send_fin = True
                #time.sleep(.3)
            except socket.timeout:
                #TODO: not pass and maybe not do timeouts like this anyway
                pass

if __name__ == "__main__":
    #np.random.seed(4)
    bytes_to_send = 10240
    random_data = ''
    for _ in range(bytes_to_send):
        random_data += to_bin(np.random.randint(0,256), num_bytes = 1)
    sndr = JerrTom_send()
    sndr.send(random_data)

