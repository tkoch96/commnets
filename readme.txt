Transport Layer Protocol Design
Thomas Koch & Jerry Qiu
------------------

Our API feature a reliable transport protocol for the transmission of data.


File list
------------------
receiver.py
sender.py
channelsimulator.py
helper_funcs.py
utils.py
test.txt


Compilation Instruction
------------------
To set up the test environment, the user should intepret the source codes using Python 2.7.


Running the Example
----------------- 
To send the pre-defined "test.txt" using our codes, one would need to one terminal to run the sender, and another terminal to run the receiver.

In one terminal, the user should type "python receiver.py" to open the receiver.

In the other terminal, the user should type "python sender.py" to start send data in the channel.

The receiver will save this text to file_rec.txt, in which you can view the transmitted data.



Using the Code 
-----------------------------------------------
Our API can be implemented in your own projects. To use the protocol, import the JerrTom_send and JerrTom_receive classes and create instances like:

jts = JerrTom_send()
-----
jtr = JerrTom_receive()

To send data, obtain the data as a string of 1s and 0s. 
example: data = '0000101010000101'
First call, jtr.receive() and then call
jts.send(data).

Data transmission will ensue and (after transmission) the sender will have the data in the form of a string of 1's and 0's as an attribute.
It can be accesseed like jtr.data

