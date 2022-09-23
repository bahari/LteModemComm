#############################################################################################################
# File:        ltemodem.py
# Description: Initiate and monitor 4G LTE modem
#              ----------------------------------------------------------------------------------------------
# Notes      : Major, Minor and Revision notes:
#              ----------------------------------------------------------------------------------------------
#              Major    - Software major number will counting up each time there is a major changes on the 
#                         software features. Minor number will reset to '0' and revision number will reset
#                         to '1' (on each major changes). Initially major number will be set to '1'
#              Minor    - Software minor number will counting up each time there is a minor changes on the
#                         software. Revision number will reset to '1' (on each minor changes).
#              Revision - Software revision number will counting up each time there is a bug fixing on the
#                         on the current major and minor number.
#              ----------------------------------------------------------------------------------------------
#              Current Features & Bug Fixing Information
#              ----------------------------------------------------------------------------------------------
#              0001     - Initiate 4G LTE modem by using wwan0 interface and qmcli command.
#              0002     - Custom 4G LTE modem network management and handling to cater Quectel EC25 mini
#                         PCIe uncertain behaviour.
#              0003     - Monitoring 4G LTE modem network periodically, gracefully shutdown the modem if 
#                         necessary and initiate back the modem connection upon network failure detection.
#              0004     - Handling popen extreme blocking when try to initiate 4G LTE modem using qmcli
#                         command. This features will be implemented via a qmicli command response thread 
#                         monitoring that will kill blocking qmicli command when timeout occurs.
#              0005     - Add a delay for 1 minute before initiate 4G network connectivity once the machine
#                         boot up.
#              0006     - Handling 4G LTE modem PCIE card initialization sequence.
#              0007     - Includes 2 mode 4G LTE modem initialization, 01-Using qmi-network CLI
#                         02-qmicli method.
#              0008     - Add enable OS raw IP mode setting (not persistent) inside 4G LTE modem initialization
#                         sequence.
#              0009     - Add necessary commenting.
#
#              ----------------------------------------------------------------------------------------------
# Author : Ahmad Bahari Nizam B. Abu Bakar.
#
# Version: 1.0.1
# Version: 1.0.2 - Add feature item [0008,0009]
#
# Date   : 06/02/2020 (INITIAL RELEASE DATE)
#          UPDATED - 08/07/2022 - 1.0.2
#
#############################################################################################################

import os, re, sys, time
import thread
import logging
import logging.handlers
import subprocess

# Global variable declaration
backLogger         = False    # Macro for logger
qmcliTimeOut       = False    # qmicli command timeout flag 
lteModemStat       = False    # 4G LTE modem connection status flag
machineBoot        = False    # machine boot status flag, to identified the machine has reboot or not
restart4gModem     = False    # Restart 4G connection flag
startSys           = False    # Start 4G LTE modem process sequence flag
quectelOpt         = False    # Option to used quectel daemon
pingAttempt        = 0        # 4G network ping process attempt counter
cmdTimeOutCnt      = 0        # qmicli command timeout counter
startSysCnt        = 0        # Delay counter before start 4G LTE modem process sequence
publicIpAddr       = '183.171.147.229' # 4G M2M public IP address

# Check for macro arguments
if (len(sys.argv) > 1):
    for x in sys.argv:
        # Optional macro if we want to enable text file log
        if x == "LOGGER":
            backLogger = True
        elif x == "QUECTOPT":
            quectelOpt = True

# Check for ltemodem.log existense, if its empty for sure the machine are previously booting up or shutdown
tempData = os.listdir('/tmp')

# Go through the resulted data
for files in tempData:
    if 'ltemodem.log' in tempData:
        machineBoot = False
        break
    # Machine are previously booting up or shutdown
    else:
        machineBoot = True

# Setup log file 
if backLogger == True:
    path = os.path.dirname(os.path.abspath(__file__))
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logfile = logging.handlers.TimedRotatingFileHandler('/tmp/ltemodem.log', when="midnight", backupCount=3)
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
    logfile.setFormatter(formatter)
    logger.addHandler(logfile)

# Doing string manipulations
def mid(s, offset, amount):
    return s[offset-1:offset+amount-1]

# Thread to check qmcli command time out
def commandTimeOut (threadname, delay):
    global backLogger
    global qmcliTimeOut
    global cmdTimeOutCnt
    global startSysCnt
    global startSys
    
    # Thread loop
    while True:
        # Loop every 1 sec based on the thread delay setting
        time.sleep(delay)

        # Start delay counter before start 4G LTE modem process sequence
        if startSys == False:
            startSysCnt += 1
            # Reach 1 minute, set the 4G LTE modem process sequence flag
            if startSysCnt == 60:
                startSys = True
                startSysCnt = 0
                
        # Increment command timeout counter
        cmdTimeOutCnt += 1
        # Check the command timeout flag
        if cmdTimeOutCnt == 5:
            cmdTimeOutCnt = 0
            # After 5 sec, time out flag still not clear, terminate qmicli command
            if qmcliTimeOut == True:
                out = subprocess.Popen(["ps aux | grep -v grep | grep qmicli"], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                stdout,stderr = out.communicate()

                # NO error after command execution
                # Response: root      2098  0.0  0.0 200912  5284 pts/0    Sl+  04:42   0:00 qmicli -d /dev/cdc-wdm0 --dms-get-operating-mode
                if stderr == None:
                    foundDig = False
                    pidNo = ''
                    respLen = len(stdout)
                    for a in range(0, (respLen + 1)):
                        oneChar = mid(stdout, a, 1)
                        # Check PID digit
                        if oneChar.isdigit():
                            foundDig = True
                            pidNo += oneChar
                        elif foundDig == True and oneChar == ' ':
                            break

                    # Start KILL the stuck qmicli command
                    if foundDig == True and pidNo != '':
                        tempCmd = 'kill -9 ' + pidNo
                        out = subprocess.Popen([tempCmd], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                        stdout,stderr = out.communicate()

                        # NO error after command execution
                        if stderr == None:
                            # Clear back qmicli tmeout flag
                            qmcliTimeOut = False
                            
                            # Write to logger
                            if backLogger == True:
                                logger.info("DEBUG_QMCLITO: KILL qmicli command SUCCESSFUL")
                            # Print statement
                            else:
                                print "DEBUG_QMCLITO: KILL qmicli command SUCCESSFUL"

            # No qmicli command stuck events occur
            else:
                # Write to logger
                if backLogger == True:
                    logger.info("DEBUG_QMCLITO: NO qmicli command stuck")
                # Print statement
                else:
                    print "DEBUG_QMCLITO: NO qmicli command stuck"
    
# Script entry point
def main():
    global backLogger
    global lteModemStat
    global pingAttempt
    global machineBoot
    global qmcliTimeOut
    global restart4gModem
    global startSys
    global quectelOpt
    global publicIpAddr

    # Only start this thread when using qmicli method
    if quectelOpt == False:
        # Create thread to get battery status 
        try:
            thread.start_new_thread(commandTimeOut, ("[commandTimeOut]", 1 ))
        except:
            # Write to logger
            if backLogger == True:
                logger.info("THREAD_ERROR: Unable to start [commandTimeOut] thread")
            # Print statement
            else:
                print "THREAD_ERROR: Unable to start [commandTimeOut] thread"
            
    # Forever loop
    while True:
        # loop every 1s only
        time.sleep(1)

        # After 1 minute, start 4G LTE modem process sequence
        if startSys == True or quectelOpt == True:
            # The machine are previously booting up or shutdown
            # Run the first initialization of 4G LTE modem
            if machineBoot == True:
                # Check for the network option method
                # Using qmi-network CLI
                if quectelOpt == True:
                    # START the 4G modem
                    #out = subprocess.Popen(['qmi-network', '/dev/cdc-wdm1', 'start'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                    out = subprocess.Popen(['qmi-network', '/dev/cdc-wdm0', 'start'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                    stdout,stderr = out.communicate()
                    
                    # NO error after command execution
                    if stderr == None:
                        # Network successfully started
                        if 'Network started successfully' in stdout:
                            # Write to logger
                            if backLogger == True:
                                logger.info("DEBUG_4G: START 4G modem (qmi-network) SUCCESSFUL")
                            # Print statement
                            else:
                                print "DEBUG_4G: START 4G modem (qmi-network) SUCCESSFUL"

                            # Wait before execute another command
                            time.sleep(1)

                            # Enable wwan0 interface
                            # Command: ifconfig wwan0 up
                            # Reply: NA 
                            out = subprocess.Popen(['ifconfig', 'wwan0', 'up'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                            stdout,stderr = out.communicate() 
                            
                            # NO error after command execution
                            if stderr == None:
                                # Write to logger
                                if backLogger == True:
                                    logger.info("DEBUG_4G: Bringing UP interface wwan0 SUCCESSFUL")
                                # Print statement
                                else:
                                    print "DEBUG_4G: Bringing UP interface wwan0 SUCCESSFUL"

                                # Wait before execute another command
                                time.sleep(1)

                                # Finally, configure the IP address and the default route with udhcpc
                                # Command: udhcpc -i wwan0
                                # Reply:
                                # udhcpc: sending discover
                                # udhcpc: sending select for 183.171.144.62
                                # udhcpc: lease of 183.171.144.62 obtained, lease time 7200
                                out = subprocess.Popen(['udhcpc', '-i', 'wwan0'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                                stdout,stderr = out.communicate()

                                # NO error after command execution
                                if stderr == None:
                                    publicIpAddr += ' obtained'
                                    # 4G LTE modem initialization with network provider completed
                                    if publicIpAddr in stdout:
                                        # Set flag to indicate 4G LTE modem first initialization completed
                                        machineBoot = False
                                        
                                        # Write to logger
                                        if backLogger == True:
                                            logger.info("DEBUG_4G: Obtained public IP address SUCCESSFUL")
                                        # Print statement
                                        else:
                                            print "DEBUG_4G: Obtained public IP address SUCCESSFUL"
                    
                        # Network failed to start
                        else:
                            # Write to logger
                            if backLogger == True:
                                logger.info("DEBUG_4G: START 4G modem (qmi-network) FAILED!, retry on the next cycle...")
                            # Print statement
                            else:
                                print "DEBUG_4G: START 4G modem (qmi-network) FAILED!, retry on the next cycle..."       

                    # Error during command execution
                    else:
                        # Write to logger
                        if backLogger == True:
                            logger.info("DEBUG_4G: START 4G modem (qmi-network) FAILED!, retry on the next cycle...")
                        # Print statement
                        else:
                            print "DEBUG_4G: START 4G modem (qmi-network) FAILED!, retry on the next cycle..."
                        
                # Using qmicli method
                else:
                    # Enable OS raw IP mode setting (not persistent)
                    out = subprocess.Popen(['echo', 'Y', '>', '/sys/class/net/wwan0/qmi/raw_ip'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                    stdout,stderr = out.communicate()
                    # NO error after command execution
                    if stderr == None:
                        # Write to logger
                        if backLogger == True:
                            logger.info("DEBUG_4G: Enable RAW IP mode setting SUCCESSFUL")
                        # Print statement
                        else:
                            print "DEBUG_4G: Enable RAW IP mode setting SUCCESSFUL"

                    # Wait before execute another command
                    time.sleep(1)
                    
                    # Enable wwan0 interface
                    # Command: ifconfig wwan0 up
                    # Reply: NA 
                    out = subprocess.Popen(['ifconfig', 'wwan0', 'up'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                    stdout,stderr = out.communicate()    

                    # NO error after command execution
                    if stderr == None:
                        # Write to logger
                        if backLogger == True:
                            logger.info("DEBUG_4G: Bringing UP interface wwan0 SUCCESSFUL")
                        # Print statement
                        else:
                            print "DEBUG_4G: Bringing UP interface wwan0 SUCCESSFUL"

                        # Wait before execute another command
                        time.sleep(1)

                        # Set qmicli tmeout flag for checking purposes
                        qmcliTimeOut = True
                        
                        # Check current 4G LTE modem status first
                        # Command: qmicli -d /dev/cdc-wdm0 --dms-get-operating-mode
                        # Reply:
                        # [/dev/cdc-wdm0] Operating mode retrieved:
                        # Mode: 'online' or 'offline'
                        # HW restricted: 'no'
                        out = subprocess.Popen(['qmicli', '-d', '/dev/cdc-wdm0', '--dms-get-operating-mode'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                        stdout,stderr = out.communicate()

                        # NO error after command execution
                        if stderr == None:
                            # Response OK
                            if 'online' in stdout:
                                # Write to logger
                                if backLogger == True:
                                    logger.info("DEBUG_4G: Get 4G modem operating mode SUCCESSFUL")
                                # Print statement
                                else:
                                    print "DEBUG_4G: Get 4G modem operating mode SUCCESSFUL"
                                
                                # Clear back qmicli tmeout flag
                                qmcliTimeOut = False

                                # Wait before execute another command
                                time.sleep(1)

                                # Set qmicli tmeout flag for checking purposes
                                qmcliTimeOut = True
                        
                                # Register the network with APN name
                                # Command: qmicli -p -d /dev/cdc-wdm0 --device-open-net='net-raw-ip|net-no-qos-header' --wds-start-network="apn='celcom3g',username=' ',password=' ',ip-type=4" --client-no-release-cid
                                # Reply;
                                # [/dev/cdc-wdm0] Network started
                                # Packet data handle: '2264423824'
                                # [/dev/cdc-wdm0] Client ID not released:
                                # Service: 'wds'
                                # CID: '20'
                                out = subprocess.Popen(['qmicli', '-p', '-d', '/dev/cdc-wdm0', "--device-open-net=net-raw-ip|net-no-qos-header", \
                                                        '--wds-start-network=', "apn='celcom3g',username=' ',password=' ',ip-type=4", \
                                                        '--client-no-release-cid'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                                stdout,stderr = out.communicate()

                                # NO error after command execution
                                if stderr == None:
                                    if 'Network started' in stdout:
                                        if 'CID' in stdout:
                                            # Write to logger
                                            if backLogger == True:
                                                logger.info("DEBUG_4G: 4G network registration SUCCESSFUL")
                                            # Print statement
                                            else:
                                                print "DEBUG_4G: 4G network registration SUCCESSFUL"
                                    
                                            # Clear back qmicli tmeout flag
                                            qmcliTimeOut = False

                                            # Wait before execute another command
                                            time.sleep(1)

                                            # Finally, configure the IP address and the default route with udhcpc
                                            # Command: udhcpc -i wwan0
                                            # Reply:
                                            # udhcpc: sending discover
                                            # udhcpc: sending select for 183.171.144.62
                                            # udhcpc: lease of 183.171.144.62 obtained, lease time 7200
                                            out = subprocess.Popen(['udhcpc', '-i', 'wwan0'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                                            stdout,stderr = out.communicate()

                                            # NO error after command execution
                                            if stderr == None:
                                                # 4G LTE modem initialization with network provider completed
                                                #if '183.171.212.223 obtained' in stdout:
                                                if '183.171.147.229 obtained' in stdout:
                                                    # Set flag to indicate 4G LTE modem first initialization completed
                                                    machineBoot = False
                                                    
                                                    # Write to logger
                                                    if backLogger == True:
                                                        logger.info("DEBUG_4G: Obtained public IP address SUCCESSFUL")
                                                    # Print statement
                                                    else:
                                                        print "DEBUG_4G: Obtained public IP address SUCCESSFUL"

                                    # Previously APN registration already successful
                                    elif 'PolicyMismatch' in stdout:
                                        # Write to logger
                                        if backLogger == True:
                                            logger.info("DEBUG_4G: 4G network registration SUCCESSFUL")
                                        # Print statement
                                        else:
                                            print "DEBUG_4G: 4G network registration SUCCESSFUL"

                                        # Clear back qmicli tmeout flag
                                        qmcliTimeOut = False

                                        # Wait before execute another command
                                        time.sleep(1)

                                        # Finally, configure the IP address and the default route with udhcpc
                                        # Command: udhcpc -i wwan0
                                        # Reply:
                                        # udhcpc: sending discover
                                        # udhcpc: sending select for 183.171.144.62
                                        # udhcpc: lease of 183.171.144.62 obtained, lease time 7200
                                        out = subprocess.Popen(['udhcpc', '-i', 'wwan0'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                                        stdout,stderr = out.communicate()

                                        # NO error after command execution
                                        if stderr == None:
                                            # 4G LTE modem initialization with network provider completed
                                            #if '183.171.212.223 obtained' in stdout:
                                            if '183.171.147.229 obtained' in stdout:
                                                # Set flag to indicate 4G LTE modem first initialization completed
                                                machineBoot = False
                                                
                                                # Write to logger
                                                if backLogger == True:
                                                    logger.info("DEBUG_4G: Obtained public IP address SUCCESSFUL")
                                                # Print statement
                                                else:
                                                    print "DEBUG_4G: Obtained public IP address SUCCESSFUL"

                                # Operation failed
                                else:
                                    # Write to logger
                                    if backLogger == True:
                                        logger.info("DEBUG_4G: Command execution FAILED during 4G network registration")
                                    # Print statement
                                    else:
                                        print "DEBUG_4G: Command execution FAILED during 4G network registration"    
                                            
                            # Response ERROR
                            elif 'error:' in stdout:
                                # Clear back qmicli tmeout flag
                                qmcliTimeOut = False

                                # Write to logger
                                if backLogger == True:
                                    logger.info("DEBUG_4G: Initiate 4G LTE modem for the first time FAILED!, retry....")
                                # Print statement
                                else:
                                    print "DEBUG_4G: Initiate 4G LTE modem for the first time FAILED!, retry...."

                        # Error during command executiom
                        else:
                            # Clear back qmicli tmeout flag
                            qmcliTimeOut = False
                                
                            # Write to logger
                            if backLogger == True:
                                logger.info("DEBUG_4G: Initiate 4G LTE modem for the first time FAILED!, retry....")
                            # Print statement
                            else:
                                print "DEBUG_4G: Initiate 4G LTE modem for the first time FAILED!, retry...."    

            # Previously 4G modem already started, start monitor the network
            else:
                # Normal 4G modem status check
                if restart4gModem == False:
                    # Start PING google.com
                    out = subprocess.Popen(['ping', '-c', '1', '8.8.8.8'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                    stdout,stderr = out.communicate()

                    # NO error after command execution
                    if stderr == None:
                        # 4G network OK
                        if '1 received' in stdout:
                            pingAttempt = 0
                            lteModemStat = True
                            
                            # Write to logger
                            if backLogger == True:
                                logger.info("DEBUG_4G: 4G network OK")
                            # Print statement
                            else:
                                print "DEBUG_4G: 4G network OK"

                        # 4G network FAILED!
                        elif '0 received' or 'failure' in stdout:
                            # Increment attempt to check 4G network by pinging process
                            pingAttempt += 1

                            # After  checking 5 times, still 4G network failed, start initiate 4G LTE modem:
                            if pingAttempt == 5:
                                pingAttempt = 0

                                # Write to logger
                                if backLogger == True:
                                    logger.info("DEBUG_4G: PING google.com FAILED!, Initiate restart process for 4G LTE modem...")
                                # Print statement
                                else:
                                    print "DEBUG_4G: PING google.com FAILED!, Initiate restart process for 4G LTE modem..."
                                    
                                # Wait before execute another command
                                time.sleep(1)

                                # Using qmi-network CLI
                                if quectelOpt == True:
                                    # STOP the 4G modem
                                    #out = subprocess.Popen(['qmi-network', '/dev/cdc-wdm1', 'stop'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                                    out = subprocess.Popen(['qmi-network', '/dev/cdc-wdm0', 'stop'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                                    stdout,stderr = out.communicate()
                                    
                                    # NO error after command execution
                                    if stderr == None:
                                        # Network successfully started
                                        if 'Network stopped successfully' in stdout:
                                            # Write to logger
                                            if backLogger == True:
                                                logger.info("DEBUG_4G: STOP 4G modem (qmi-network) SUCCESSFUL")
                                            # Print statement
                                            else:
                                                print "DEBUG_4G: STOP 4G modem (qmi-network) SUCCESSFUL"

                                            # Wait before execute another command
                                            time.sleep(1)

                                            # Disable wwan0 interface
                                            # Command: ifconfig wwan0 down
                                            # Reply: NA 
                                            out = subprocess.Popen(['ifconfig', 'wwan0', 'down'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                                            stdout,stderr = out.communicate() 
                                            
                                            # NO error after command execution
                                            if stderr == None:
                                                # Write to logger
                                                if backLogger == True:
                                                    logger.info("DEBUG_4G: Bringing DOWN interface wwan0 SUCCESSFUL")
                                                # Print statement
                                                else:
                                                    print "DEBUG_4G: Bringing DOWN interface wwan0 SUCCESSFUL"
                                            
						# Set flag to restart 4G LTE modem on the next cycle
						restart4gModem = True
												
						# Error during command executiom
					    else:
						# Write to logger
                                                if backLogger == True:
                                                    logger.info("DEBUG_4G: Bringing DOWN interface wwan0 FAILED!")
                                                # Print statement
                                                else:
                                                    print "DEBUG_4G: Bringing DOWN interface wwan0 FAILED!"

                                        # Network failed to start
                                        else:
                                            # Write to logger
                                            if backLogger == True:
                                                logger.info("DEBUG_4G: STOP 4G modem (qmi-network) FAILED!, retry on the next cycle...")
                                            # Print statement
                                            else:
                                                print "DEBUG_4G: STOP 4G modem (qmi-network) FAILED!, retry on the next cycle..."

                                    # Error during command executiom
                                    else:
                                        # Write to logger
                                        if backLogger == True:
                                            logger.info("DEBUG_4G: STOP 4G modem (qmi-network) FAILED!, retry on the next cycle...")
                                        # Print statement
                                        else:
                                            print "DEBUG_4G: STOP 4G modem (qmi-network) FAILED!, retry on the next cycle..."
                                                    
                                # Using qmicli method
                                else:
                                    # Set qmicli tmeout flag for checking purposes
                                    qmcliTimeOut = True

                                    # STOP 4G LTE modem
                                    out = subprocess.Popen(['qmicli', '-d', '/dev/cdc-wdm0', '--device-open-sync', '--dms-get-operating-mode'], \
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                                    stdout,stderr = out.communicate()

                                    # NO error after command execution
                                    if stderr == None:
                                        if 'HW restricted:' in stdout:
                                            # Write to logger
                                            if backLogger == True:
                                                logger.info("DEBUG_4G: STOP 4G LTE modem SUCCESSFUL")
                                            # Print statement
                                            else:
                                                print "DEBUG_4G: STOP 4G LTE modem SUCCESSFUL"

                                            # Clear back qmicli tmeout flag
                                            qmcliTimeOut = False
                                        
                                            # Wait before execute another command
                                            time.sleep(1)

                                            # Bring wwan0 interface DOWN
                                            out = subprocess.Popen(['ifconfig', 'wwan0', 'down'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                                            stdout,stderr = out.communicate()

                                            # NO error after command execution
                                            if stderr == None:
                                                # Write to logger
                                                if backLogger == True:
                                                    logger.info("DEBUG_4G: Bringing DOWN wwan0 SUCCESSFUL")
                                                # Print statement
                                                else:
                                                    print "DEBUG_4G: Bringing DOWN wwan0 SUCCESSFUL"
                                                
                                                # Wait before execute another command
                                                time.sleep(1)

                                                # KILL udhcpc instances
                                                out = subprocess.Popen(['killall', 'udhcpc'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                                                stdout,stderr = out.communicate()

                                                # NO error after command execution
                                                if stderr == None:
                                                    # Write to logger
                                                    if backLogger == True:
                                                        logger.info("DEBUG_4G: KILL  udhcpc SUCCESSFUL")
                                                        logger.info("DEBUG_4G: Initiate 4G LTE modem on the next cycle...")
                                                    # Print statement
                                                    else:
                                                        print "DEBUG_4G: KILL  udhcpc SUCCESSFUL"
                                                        print "DEBUG_4G: Initiate 4G LTE modem on the next cycle..."

                                                    # Set flag to restart 4G LTE modem on the next cycle
                                                    restart4gModem = True

                                        # Operation failed
                                        else:
                                            # Write to logger
                                            if backLogger == True:
                                                logger.info("DEBUG_4G: STOP 4G LTE modem FAILED!")
                                            # Print statement
                                            else:
                                                print "DEBUG_4G: STOP 4G LTE modem FAILED!"

                                    # Operation failed
                                    else:
                                        # Write to logger
                                        if backLogger == True:
                                            logger.info("DEBUG_4G: Command execution to STOP 4G LTE modem FAILED!")
                                        # Print statement
                                        else:
                                            print "DEBUG_4G: Command execution to STOP 4G LTE modem FAILED!"

                # Restart 4G LTE modem
                else:
                    # Using qmi-network CLI
                    if quectelOpt == True:
                        # START the 4G modem
                        #out = subprocess.Popen(['qmi-network', '/dev/cdc-wdm1', 'start'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                        out = subprocess.Popen(['qmi-network', '/dev/cdc-wdm0', 'start'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                        stdout,stderr = out.communicate()
                        
                        # NO error after command execution
                        if stderr == None:
                            # Network successfully started
                            if 'Network started successfully' in stdout:
                                # Write to logger
                                if backLogger == True:
                                    logger.info("DEBUG_4G: START 4G modem (qmi-network) SUCCESSFUL")
                                # Print statement
                                else:
                                    print "DEBUG_4G: START 4G modem (qmi-network) SUCCESSFUL"

                                # Wait before execute another command
                                time.sleep(1)

                                # Enable wwan0 interface
                                # Command: ifconfig wwan0 up
                                # Reply: NA 
                                out = subprocess.Popen(['ifconfig', 'wwan0', 'up'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                                stdout,stderr = out.communicate() 
                                
                                # NO error after command execution
                                if stderr == None:
                                    # Write to logger
                                    if backLogger == True:
                                        logger.info("DEBUG_4G: Bringing UP interface wwan0 SUCCESSFUL")
                                    # Print statement
                                    else:
                                        print "DEBUG_4G: Bringing UP interface wwan0 SUCCESSFUL"

                                    # Wait before execute another command
                                    time.sleep(1)

                                    # Finally, configure the IP address and the default route with udhcpc
                                    # Command: udhcpc -i wwan0
                                    # Reply:
                                    # udhcpc: sending discover
                                    # udhcpc: sending select for 183.171.144.62
                                    # udhcpc: lease of 183.171.144.62 obtained, lease time 7200
                                    out = subprocess.Popen(['udhcpc', '-i', 'wwan0'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                                    stdout,stderr = out.communicate()

                                    # NO error after command execution
                                    if stderr == None:
                                        publicIpAddr += ' obtained'
                                        # 4G LTE modem initialization with network provider completed
                                        if publicIpAddr in stdout:
                                            # Clear flag to restart 4G LTE modem on the next cycle
                                            restart4gModem = False
                                            
                                            # Write to logger
                                            if backLogger == True:
                                                logger.info("DEBUG_4G: Obtained public IP address SUCCESSFUL")
                                            # Print statement
                                            else:
                                                print "DEBUG_4G: Obtained public IP address SUCCESSFUL"
                        
                            # Network failed to start
                            else:
                                # Write to logger
                                if backLogger == True:
                                    logger.info("DEBUG_4G: START 4G modem (qmi-network) FAILED!, retry on the next cycle...")
                                # Print statement
                                else:
                                    print "DEBUG_4G: START 4G modem (qmi-network) FAILED!, retry on the next cycle..."    

                                # Retry checking the network connectivity

                        # Error during command executiom
                        else:
                            # Write to logger
                            if backLogger == True:
                                logger.info("DEBUG_4G: START 4G modem (qmi-network) FAILED!, retry on the next cycle...")
                            # Print statement
                            else:
                                print "DEBUG_4G: START 4G modem (qmi-network) FAILED!, retry on the next cycle..."
                                
                            # Retry checking the network connectivity
                                
                    # Using qmicli method
                    else:
                        # Enable OS raw IP mode setting (not persistent)
                        out = subprocess.Popen(['echo', 'Y', '>', '/sys/class/net/wwan0/qmi/raw_ip'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                        stdout,stderr = out.communicate()
                        # NO error after command execution
                        if stderr == None:
                            # Write to logger
                            if backLogger == True:
                                logger.info("DEBUG_4G: Enable RAW IP mode setting SUCCESSFUL")
                            # Print statement
                            else:
                                print "DEBUG_4G: Enable RAW IP mode setting SUCCESSFUL"

                        # Wait before execute another command
                        time.sleep(1)
                        
                        # Set qmicli tmeout flag for checking purposes
                        qmcliTimeOut = True

                        out = subprocess.Popen(['qmicli', '-d', '/dev/cdc-wdm0', "--dms-set-operating-mode=online"], \
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                        stdout,stderr = out.communicate()

                        # NO error after command execution
                        if stderr == None:
                            if 'successfully' in stdout:
                                # Write to logger
                                if backLogger == True:
                                    logger.info("DEBUG_4G: Set modem operating mode SUCCESSFUL")
                                # Print statement
                                else:
                                    print "DEBUG_4G: Set modem operating mode SUCCESSFUL"

                                # Clear back qmicli tmeout flag
                                qmcliTimeOut = False

                                # Enable wwan0 interface
                                # Command: ifconfig wwan0 up
                                # Reply: NA 
                                out = subprocess.Popen(['ifconfig', 'wwan0', 'up'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                                stdout,stderr = out.communicate()    

                                # NO error after command execution
                                if stderr == None:
                                    # Write to logger
                                    if backLogger == True:
                                        logger.info("DEBUG_4G: Bringing UP interface wwan0 SUCCESSFUL")
                                    # Print statement
                                    else:
                                        print "DEBUG_4G: Bringing UP interface wwan0 SUCCESSFUL"

                                    # Wait before execute another command
                                    time.sleep(1)

                                    # Set qmicli tmeout flag for checking purposes
                                    qmcliTimeOut = True

                                    # Register the network with APN name
                                    # Command: qmicli -p -d /dev/cdc-wdm0 --device-open-net='net-raw-ip|net-no-qos-header' --wds-start-network="apn='celcom3g',username=' ',password=' ',ip-type=4" --client-no-release-cid
                                    # Reply;
                                    # [/dev/cdc-wdm0] Network started
                                    # Packet data handle: '2264423824'
                                    # [/dev/cdc-wdm0] Client ID not released:
                                    # Service: 'wds'
                                    # CID: '20'
                                    out = subprocess.Popen(['qmicli', '-p', '-d', '/dev/cdc-wdm0', "--device-open-net=net-raw-ip|net-no-qos-header", \
                                                            '--wds-start-network=', "apn='celcom3g',username=' ',password=' ',ip-type=4", \
                                                            '--client-no-release-cid'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                                    stdout,stderr = out.communicate()

                                    # NO error after command execution
                                    if stderr == None:
                                        if 'Network started' in stdout:
                                            if 'CID' in stdout:    
                                                # Write to logger
                                                if backLogger == True:
                                                    logger.info("DEBUG_4G: 4G network registration SUCCESSFUL")
                                                # Print statement
                                                else:
                                                    print "DEBUG_4G: 4G network registration SUCCESSFUL"
                                        
                                                # Clear back qmicli tmeout flag
                                                qmcliTimeOut = False

                                                # Wait before execute another command
                                                time.sleep(1)

                                                # Finally, configure the IP address and the default route with udhcpc
                                                # Command: udhcpc -i wwan0
                                                # Reply:
                                                # udhcpc: sending discover
                                                # udhcpc: sending select for 183.171.144.62
                                                # udhcpc: lease of 183.171.144.62 obtained, lease time 7200
                                                out = subprocess.Popen(['udhcpc', '-i', 'wwan0'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                                                stdout,stderr = out.communicate()

                                                # NO error after command execution
                                                if stderr == None:
                                                    # 4G LTE modem initialization with network provider completed
                                                    #if '183.171.212.223 obtained' in stdout:
                                                    if '183.171.147.229 obtained' in stdout:
                                                        # Clear flag to restart 4G LTE modem on the next cycle
                                                        restart4gModem = False
                                                        
                                                        # Write to logger
                                                        if backLogger == True:
                                                            logger.info("DEBUG_4G: Obtained public IP address SUCCESSFUL")
                                                        # Print statement
                                                        else:
                                                            print "DEBUG_4G: Obtained public IP address SUCCESSFUL"
                                        # Previously APN registration already successful
                                        elif 'PolicyMismatch' in stdout:
                                            # Write to logger
                                            if backLogger == True:
                                                logger.info("DEBUG_4G: 4G network registration SUCCESSFUL")
                                            # Print statement
                                            else:
                                                print "DEBUG_4G: 4G network registration SUCCESSFUL"

                                            # Clear back qmicli tmeout flag
                                            qmcliTimeOut = False

                                            # Wait before execute another command
                                            time.sleep(1)

                                            # Finally, configure the IP address and the default route with udhcpc
                                            # Command: udhcpc -i wwan0
                                            # Reply:
                                            # udhcpc: sending discover
                                            # udhcpc: sending select for 183.171.144.62
                                            # udhcpc: lease of 183.171.144.62 obtained, lease time 7200
                                            out = subprocess.Popen(['udhcpc', '-i', 'wwan0'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                                            stdout,stderr = out.communicate()

                                            # NO error after command execution
                                            if stderr == None:
                                                # 4G LTE modem initialization with network provider completed
                                                #if '183.171.212.223 obtained' in stdout:
                                                if '183.171.147.229 obtained' in stdout:
                                                    # Clear flag to restart 4G LTE modem on the next cycle
                                                    restart4gModem = False
                                                    
                                                    # Write to logger
                                                    if backLogger == True:
                                                        logger.info("DEBUG_4G: Obtained public IP address SUCCESSFUL")
                                                    # Print statement
                                                    else:
                                                        print "DEBUG_4G: Obtained public IP address SUCCESSFUL"            
                                                
                                    # Operation failed
                                    else:
                                        # Write to logger
                                        if backLogger == True:
                                            logger.info("DEBUG_4G: Command execution FAILED during 4G network registration")
                                        # Print statement
                                        else:
                                            print "DEBUG_4G: Command execution FAILED during 4G network registration"     
                                        
                            # Operation failed
                            else:
                                # Write to logger
                                if backLogger == True:
                                    logger.info("DEBUG_4G: Set modem operating mode FAILED!")
                                # Print statement
                                else:
                                    print "DEBUG_4G: Set modem operating mode FAILED!"
                                    
                        # Operation failed
                        else:
                            # Write to logger
                            if backLogger == True:
                                logger.info("DEBUG_4G: Command execution to STOP 4G LTE modem FAILED!")
                            # Print statement
                            else:
                                print "DEBUG_4G: Command execution to STOP 4G LTE modem FAILED!"    
                        
if __name__ == "__main__":
    main()


