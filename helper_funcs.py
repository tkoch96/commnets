from struct import unpack

def to_bin(data, num_bytes = None):
	raw_bin = "{0:b}".format(data)
    #prepend data with zeros, to constitute an integer number of bytes
	if num_bytes is None:
		num_to_pad =  8 - (len(raw_bin) % 8)
	else:
		num_to_pad = 8  * num_bytes - len(raw_bin)
	return num_to_pad * "0" + raw_bin

def calculate_checksum(packet):
	# assume packet is an integer number of bytes
	total = '0'
	num_bytes = len(packet) / 8
	for i in range(num_bytes):
		this_byte = packet[i * 8: (i+1) * 8]
		total = bin(int(total,2) + int(this_byte,2))[2:]
	chksum = bin(256 - int(total,2) % 256)[2:] 
	if len(chksum) % 8 != 0:
		chksum = '0' * (8 - len(chksum)) + chksum 
	return chksum

def pad_binary_str(str_to_pad):
	#pad this string to be an integer number of bits
	ret = '0' * (8 - len(str_to_pad)) + str_to_pad
	return ret