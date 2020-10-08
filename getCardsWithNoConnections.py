#!/usr/bin/python

import paramiko
import sys
import subprocess
import requests
from bs4 import BeautifulSoup
from getpass import getpass

# Gets a list of the servers that we want to read from by a get request
def getServers():
    try:
        response = requests.get("http://nmf.int.westgroup.com/switchmap/6500-ios/index.html")
        soup = BeautifulSoup(response.text, 'lxml')
        return [li.a.text.split('.')[0] for li in soup.findAll('li')]
    except:
        print("Could not get servers from URL, please check that the site is up and has not been moved")
        exit(1)

# Takes as input string representation of output. 
# Gets a list of the cards that have no connections
def getCardsWithNoConnections(output):
    output = output[output.find("Port"):]
    portConnected = {}
    output = output.strip().split('\n')[1:]
    for line in output:
        line = line.split()
        card = line[0].split('/')[0][2]
        status = line[-5]  # Second field is sometimes missing. Negative indexing solves this
        if card not in portConnected or portConnected[card] == "notconnect" or (portConnected[card] == "disabled" and portConnected[card] != "notconnect"):
            portConnected[card] = status
    return {k:v for (k,v) in portConnected.items() if v != "connected"}

# Takes ssh client, username and password, and connects the client to gbsuite
# returns 1 on error, 0 on success
def connectToJump(vm, user, pw):
    vm.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        vm.connect('gbsuite-tr1.int.thomsonreuters.com', username=user, password=pw)
        return 0
    except Exception as e:
        print("Failed to connect to gbsuite")
        print("Error: ", e)
        return 1

# Takes new ssh client, gbsuite client, servername, user, and password
# Connects this new client to the server we want to get in to 
def connectToSwitch(jhost, vm, server, user, pw):
    # Create ssh connection between gbsuite and network switch
    jhost.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    # create transport for gbsuite to our network switches
    vmtransport = vm.get_transport()
    local_addr = ('gbsuite-tr1.int.thomsonreuters.com', 22)
    dest_addr = (server, 22)
    vmchannel = vmtransport.open_channel("direct-tcpip", dest_addr, local_addr)
    try:
        jhost.connect(server, username=user, password=pw, sock=vmchannel)
        return 0
    except Exception as e:
        print("Error connecting to ", server)
        print("Error: ", e)
        return 1       

def main():
    vm = paramiko.SSHClient()
    jhost = paramiko.SSHClient()
    outFile = open("openCards.txt", "w")
    gbsuiteUser = input("Enter gbsuite User: ")
    gbsuitePass = getpass("Enter gbsuite Password:")
    if connectToJump(vm, gbsuiteUser, gbsuitePass) == 1:
        vm.close()
        exit(1)
    # Create ssh connection to gbsuite as jump server
    switchUser = input("Enter network switch user: ")
    switchPass = getpass("Enter network switch user password: ")
    for server in getServers():
        print("Now testing:", server)
        if connectToSwitch(jhost, vm, server, switchUser, switchPass) == 1:
            outFile.write("Failed at server: ", server)
            break
        # gets output from the command sh int status:
        stdin, stdout, stderr = jhost.exec_command("sh int status")
        # stdout is a stream. This map converts it to a string. We also remove the first
        # we start the string at where the string Port is found to skip a security warning from the terminal
        output = "".join(map(chr, stdout.read()))
        badCards = getCardsWithNoConnections(output)
        for card in badCards: 
            if badCards[card] == "disabled": outFile.write(server + " Line Card " + card + " HAS DISABLED\n")
            else: outFile.write(server + " Line Card " + card + "\n")
        jhost.close()

    jhost.close()
    vm.close()
    outFile.close()

if __name__ == "__main__":
    main()