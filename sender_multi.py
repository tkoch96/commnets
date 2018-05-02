# Written by S. Mevawala, modified by D. Gitzel

import socket
import channelsimulator
import time
import numpy as np, struct
import utils, logging, threading

from helper_funcs import *

class BogoSender(object):

    def __init__(self, inbound_port=50006, outbound_port=50005, timeout=.1, debug_level=logging.DEBUG):
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


class RapidSender(threading.Thread):
    def __init__(self, jts):
        super(RapidSender,self).__init__()
        self.jts = jts

    def run(self):
        while not self.jts.end_program:
            if self.jts.allowed_to_send():
                self.jts.send_packet(self.jts.curr_sent) #send packet to receiver
            time.sleep(.001)

class RapidRetriever(threading.Thread):
    def __init__(self,jts):
        super(RapidRetriever, self).__init__()
        self.jts = jts

    def run(self):
        while not self.jts.end_program:
            try:
                response = self.jts.simulator.u_receive() #get a response
                self.jts.handle_response(response) #process this response
            except socket.timeout:
                self.jts.handle_timeout()

            if self.jts.check_if_done():
                #check to see if we have any more data to transmit
                self.jts.send_fin = True
            time.sleep(.001)


class JerrTom_send(BogoSender):
    def __init__(self):
        super(JerrTom_send,self).__init__()
        self.print_stuff = True
        #specificies locations of header fields in the header block
        self.size_of_sequence_number = 8
        self.index_of_sequence_number = 1
        self.size_of_checksum = 2
        self.index_of_checksum = self.index_of_sequence_number + self.size_of_sequence_number
        self.index_of_fin_ack = self.index_of_checksum + self.size_of_checksum
        self.size_of_header = self.size_of_checksum + self.size_of_sequence_number + 1

        self.max_data_size = 1024 - self.size_of_header #bytes
        self.max_un_acked = 10 #size of window (in packet size units)

        #connection oriented things
        self.start_sequence_number = 0 #offset accounting for random starting sequence number
        self.curr_wind = 0 #receiver has acked up to this byte
        self.curr_sent = 0 #sent up to but not including this byte
        self.data = None #data to send to the host
        self.sequence_number = 0
        self.send_fin = False
        self.end_program = False


        #thread oriented things
        #anything that accesses variables that could be both read and written by the threads at the same time should be locked
        self.lock = threading.Lock()

    def allowed_to_send(self):
        size_packet = self.max_data_size - self.size_of_header
        self.lock.acquire()
        try:
            num_packs_un_acked = (int(self.curr_sent,2) - int(self.curr_wind,2)) / size_packet
        finally:
            self.lock.release()
        return num_packs_un_acked <= self.max_un_acked

    def check_if_done(self):
        # checks to see if our current window is at the length of the data
        byte_num = int(self.curr_wind,2) - int(self.start_sequence_number,2) #curr_wind is read and written by the same thread, no lock needed
        if self.print_stuff:
            print("Current window: %d"%byte_num)
        return byte_num >= len(self.data) / 8

    def get_data(self,seq_num):
        #retrieve data from the cache with sequence number seq_num
        byte_number = int(seq_num,2) - int(self.start_sequence_number,2)
        #either get the maximum amount, or whatever we have left to transmit
        len_data_packet = np.minimum(self.max_data_size * 8, len(self.data[byte_number * 8:]))
        data = self.data[byte_number * 8:byte_number * 8 + len_data_packet]
        #print("Len data packet: %d"%len_data_packet)
        #print("Len data: %d"%len(data))
        return data

    def send_packet(self, seq_num, fin_bit = None):
        #send the packet whose sequence number starts with seq_num
        if self.print_stuff:
            print("Sending packet to host")
        if fin_bit is None:
             fin_bit = int(self.send_fin)
        data = self.get_data(seq_num)
        checksum = calculate_checksum(data)
        #print("Sending checksum: %s"%checksum)
        fin = to_bin(fin_bit, num_bytes = 1)

        header = seq_num + checksum + fin
        if self.print_stuff:
            print("Sending packet with sequence number: %d."%(int(seq_num,2) - int(self.start_sequence_number,2)))
        #print("Sending header: %s"%header)
        packet = to_seq_of_ints(header + data) #convert this string data to ints
        packet = bytearray(packet) #make it a bytearray for transmission
        
        #update the current sent pointer
        #curr sent is read and written by same thread, don't need lock
        self.curr_sent = to_bin(int(seq_num,2) + len(data) / 8,num_bytes = self.size_of_sequence_number)
        
        self.simulator.u_send(packet)

    def handle_response(self, packet):
        ## Packet parsing
        if self.print_stuff:
            print("\n\nParsing packet...")
        packet = [to_bin(bite,num_bytes = 1) for bite in packet]
        p = ''
        for bite in packet:
            p += bite
        packet = p
        header = packet[0:self.size_of_header*8] #grab header
        data = packet[self.size_of_header*8:] #grab data
        sequence_number = header[0:self.size_of_sequence_number * 8]
        header_chksum = header[(self.index_of_checksum - 1) * 8: (self.index_of_checksum + self.size_of_checksum - 1) * 8]
        fin_ack = header[(self.index_of_fin_ack - 1) * 8: self.index_of_fin_ack * 8]

        # calculate checksum of data enclosed in the packet
        data_chksum = calculate_checksum(data)

        if (data_chksum == header_chksum):
            if self.print_stuff:
                print("Checksum valid.")
            #host successfully received a packet, record the sequence number
            if int(fin_ack) == 1:
                #if we opted to close the connection, cool
                if self.print_stuff:
                    print("Connection closed! Data transfer complete.")
                self.end_program = True
            #receiver is expecting packet with sequence_number next, so its received up
            #to sequence_number bytes
            self.curr_wind = sequence_number

    def handle_timeout(self):
        #re-send the oldest packet we are waiting for, and reset all values to oldest packet
        

        #assuming a burst error, probably assume all packets got lost
        #we would rather resend packets we have already acked than wait for more and more timeouts
        #may cause duplicate packets, but its relatively simple for receiver to handle this

        #curr wind is the ack for the next packet we hoped to receive, subtract a packet length to get the packet we would
        #like to resend

        #size_data_packet = self.max_data_size - self.size_of_header
        if self.print_stuff:
            print("Handling timeout, resending sequence starting at: %d."%(int(self.curr_wind,2) - int(self.start_sequence_number,2)))
        seq_to_send = self.curr_wind#to_bin(int(self.curr_wind,2) - size_data_packet, num_bytes=self.size_of_sequence_number)

        self.send_packet(seq_to_send)

    def send(self, data='1000010100100111'):
        #send the data specified by data to the receiver using u_send
        #if the data size is greater than the MTU, it will use more than one transmission
        self.data = data

        #create header for packet
        sequence_number = np.random.randint(0,np.power(2,3*self.size_of_sequence_number) / 2)
        self.start_sequence_number = to_bin(sequence_number,num_bytes=self.size_of_sequence_number)
        self.curr_wind = to_bin(int(self.start_sequence_number,2) + self.max_data_size,num_bytes=self.size_of_sequence_number)
        self.curr_sent = self.start_sequence_number

        threads = []
        rs = RapidSender(self)
        rr = RapidRetriever(self)
        threads.append(rs)
        threads.append(rr)
        rs.start() #sent packets
        rr.start() #look for responses

        for t in threads:
            t.join()

if __name__ == "__main__":
    sndr = JerrTom_send()
    data = open("test.txt","rb").read()
    s = len(data)
    file_data = ''
    for byte in data:
        file_data += to_bin(ord(byte), num_bytes = 1)
    print("Read data")
    time.sleep(5)
    t = time.time()
    sndr.send(file_data)

    print("Throughput: %.3f bytes / sec"%(s/(time.time() - t)))