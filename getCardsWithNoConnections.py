#!/usr/bin/python

import paramiko
import sys
import subprocess
from getpass import getpass

# Gets a list of the servers that we want to read from
'''
    James enter the correct file location for all of the servers here. 
'''
def getServers():
    try:
        response = requests.get("http://nmf.int.westgroup.com/switchmap/6500-ios/index.html")
        soup = BeautifulSoup(response.text, 'lxml')
        return [li.a.text.split()[0] for li in soup.findAll('li')]
    except:
        print("Could not get servers from URL, please check that the site is up and has not been moved")
        exit(1)
# Takes as input string representation of output. 
# Gets a list of the cards that have no connections
def getCardsWithNoConnections(output):
    portConnected = {}
    output = output.strip().split('\n')[1:]
    for line in output:
        line = line.split()
        card = line[0].split('/')[0][2]
        status = line[-5]  # Second field is sometimes missing. Negative indexing solves this
        if card not in portConnected or portConnected[card] == "notconnect" or (portConnected[card] == "disabled" and portConnected[card] != "notconnect"):
            portConnected[card] = status
    
    return {k:v for (k,v) in portConnected.items() if v != "connected"}

def main():
    gbsuiteUser = input("Enter gbsuite User: ")
    gbsuitePass = getpass("Enter gbsuite Password:")

    # Create ssh connection to gbsuite as jump server
    vm = paramiko.SSHClient()
    vm.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        vm.connect('gbsuite-tr1.int.thomsonreuters.com', username=gbsuiteUser, password=gbsuitePass)
    except:
        print("Failed to connect to gbsuite")
        vm.close()
        exit(1)
    
    switchUser = input("Enter network switch user: ")
    switchPass = getpass("Enter network switch user password: ")
    outFile = open("cardsWithNoConnections.txt", "w")
    servers = getServers()

    try:
        for server in servers:
            # create transport for gbsuite to our network switches
            vmtransport = vm.get_transport()
            local_addr = ('gbsuite-tr1.int.thomsonreuters.com', 22)
            dest_addr = (server, 22)
            vmchannel = vmtransport.open_channel("direct-tcpip", dest_addr, local_addr)

            # Create ssh connection between gbsuite and network switch
            jhost = paramiko.SSHClient()
            jhost.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                jhost.connect(server, username=switchUser, password=switchPass, sock=vmchannel)
            except:
                raise Exception("Could not connect to " + server)
                

            # gets output from the command sh int status:
            stdin, stdout, stderr = jhost.exec_command("sh int status") 

            # stdout is a stream. This map converts it to a string. We also remove the first
            # we start the string at where the string Port is found to skip a security warning from the terminal
            output = "".join(map(chr, stdout.read()))
            output = output[output.find("Port"):]
            print(output)
            badCards = getCardsWithNoConnections(output)
            for card in badCards: 
                if badCards[card] == disabled:
                    server + " Line Card " + card + " HAS DISABLED\n"
                else:
                    outFile.write(server + " Line Card " + card + "\n")
                outFile.write(out)
            jhost.close()
    except Exception as error:
        print('Caught this error: ' + repr(error))
    finally:
        jhost.close()
        vm.close()
        outFile.close()

if __name__ == "__main__":
    main()