from consolemenu import ConsoleMenu
from consolemenu.items import FunctionItem, SubmenuItem, CommandItem
import yaml
import time
import serial
import sys
import struct
import datetime


from ft8 import FT8Send
from ft4 import FT4Send

#FT8 encoder
ft8_encoder = FT8Send()
ft4_encoder = FT4Send()

#Read configuration file
configs_file = open('transceiver_config.yml', 'r')
configs = yaml.safe_load(configs_file)

#Serial port for arduino
serial_port = configs['serial_port']
baudrate    = configs['baudrate']
try:
    puerto = serial.Serial(serial_port, baudrate, timeout=0.5)
except Exception as err:
    print(err)    
    print ("\nNo se puede abrir puerto: " + serial_port + "\n")
    exit(1)

#Global variables
callsign = configs['callsign']
grid = configs['grid']
current_msg = ''
rx_callsign = ''
mode = 'FT8'

def encode_ft8(msg):
    try:
        a77 = ft8_encoder.pack(msg, 1)
        symbols = ft8_encoder.make_symbols(a77)
    except Exception as err:
        print(err)
        print ("FT8 encoder error, check message!")
        symbols = None
        time.sleep(3)
    return symbols

def encode_ft4(msg):
    try:
        a77 = ft4_encoder.pack(msg, 1)
        symbols = ft4_encoder.make_symbols(a77)
    except Exception as err:
        print(err)
        print ("FT4 encoder error, check message!")
        symbols = None
        time.sleep(3)
    return symbols

def load_symbols(symbols):
    print ("Load symbols into transmitter..")
    puerto.write(b'm')
    for symbol in symbols:
        puerto.write(struct.pack('>B', symbol))
    puerto.write(b'\0')
    time.sleep(1)


def new_msg(msg, isContinue):
    global current_msg
    global mode
    print (msg)
    if msg != current_msg:
        if 'FT8' in mode:
            symbols = encode_ft8(msg)
        else:
            symbols = encode_ft4(msg)            
        if symbols.any():
            load_symbols(symbols)
            current_msg = msg
        else:
            return
    transmit(isContinue) 

def call_cq(isContinue):
    msg = 'CQ ' + callsign + ' ' + grid
    new_msg(msg, isContinue)

def transmit(isContinue):
    if not current_msg:
        print ("No previous message!")
        time.sleep(1)
    else:
        print ("Waiting for slot..")
        while True:
            utc_time = datetime.datetime.utcnow()
            if 'FT8' in mode:
                if (utc_time.second % 15 == 14 and utc_time.second % 2 == 1):
                    print ("TX!")
                    puerto.write(b't')        
                    time.sleep(1)
                    if (not isContinue)
                        break
            else:
                mscount = utc_time.second + utc_time.microsecond/1e6
                if (abs(mscount%7.5 - 6.5) < 0.05):
                    print ("TX!")
                    puerto.write(b't')        
                    time.sleep(1)
                    if (not isContinue)
                        break     
    
def resp_new():
    global rx_callsign
    rx_callsign = input("Respond to callsign: ")
    resp_submenu.show()
    
def resp_last():
    if not rx_callsign:
        print ("No previous callsign!")
        time.sleep(1)
    else:
        resp_submenu.show()

def change_freq():
    no_freq = True
    while(no_freq):
        new_freq = int(input("Enter new offset frequency (0 - 2000Hz): "))
        if (new_freq > 0 and new_freq < 2000):
            no_freq = False
    puerto.write(b'o')
    for kk in range(2):
        puerto.write(struct.pack('>B', (new_freq >> 8*kk) & 0xFF))
    time.sleep(1)

def change_mode():
    global mode
    if 'FT8' in mode:
        print ("Switch mode to FT4!")
        menu.remove_item(chft4_item)
        menu.append_item(chft8_item)
        mode = 'FT4'
    else:
        print ("Switch mode to FT8!")
        menu.remove_item(chft8_item)
        menu.append_item(chft4_item)
        mode = 'FT8'
    puerto.write(b's')
    current_msg = ''    
    time.sleep(1)
    menu.show()
    
def respond(response):
    if 'grid' in response:
        msg = rx_callsign + ' ' + callsign + ' ' + grid
    elif 'signal' in response:
        snr = input("Signal strength: ")        
        msg = rx_callsign + ' ' + callsign + ' ' + snr
    elif 'RR73' in response:
        msg = rx_callsign + ' ' + callsign + ' RR73'
    new_msg(msg)
  

#Create the menus
menu = ConsoleMenu("WJSTX Transceiver Control ", "FT8 and FT4")
resp_submenu = ConsoleMenu("Respond with: ", "", exit_option_text = "Go back")

#Main menu
cq_item          = FunctionItem("Call CQ", call_cq, [false])
continue_cq_item = FunctionItem("Continue Call CQ", call_cq, [true])
retransmit_item  = FunctionItem("Retransmit last", transmit, [])
resp_new_item    = FunctionItem("Respond to new callsign", resp_new, [])
submenu_item     = FunctionItem("Respond to last callsign", resp_last, [])
chfreq_item      = FunctionItem("Change TX frequency", change_freq, [])
chft4_item       = FunctionItem("Change mode to FT4", change_mode, [])
chft8_item       = FunctionItem("Change mode to FT8", change_mode, [])

resp_grid_item   = FunctionItem("Respond with grid", respond, ['grid'])
resp_signal_item = FunctionItem("Respond with R + signal strenght", respond, ['signal'])
resp_73_item     = FunctionItem("Respond with RR73", respond, ['RR73'])

resp_submenu.append_item(resp_grid_item)
resp_submenu.append_item(resp_signal_item)
resp_submenu.append_item(resp_73_item)

menu.append_item(cq_item)
menu.append_item(continue_cq_item)
menu.append_item(resp_new_item)
menu.append_item(submenu_item)
menu.append_item(retransmit_item)
menu.append_item(chfreq_item)
menu.append_item(chft4_item)

menu.show()