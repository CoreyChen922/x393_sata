from __future__ import print_function
from __future__ import division

'''
# Copyright (C) 2015, Elphel.inc.
# Parsing Verilog parameters from the header files
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author:     Andrey Filippov
@copyright:  2015 Elphel, Inc.
@license:    GPLv3.0+
@contact:    andrey@elphel.coml
@deffield    updated: Updated
'''
__author__ = "Andrey Filippov"
__copyright__ = "Copyright 2015, Elphel, Inc."
__license__ = "GPL"
__version__ = "3.0+"
__maintainer__ = "Andrey Filippov"
__email__ = "andrey@elphel.com"
__status__ = "Development"

import os
from x393_mem import X393Mem
from x393_vsc3304 import x393_vsc3304
from time import sleep
import shutil
DEFAULT_BITFILE="/usr/local/verilog/x393_sata.bit"
SI5338_PATH =   '/sys/devices/amba.0/e0004000.ps7-i2c/i2c-0/0-0070'
FPGA_RST_CTRL= 0xf8000240
FPGA0_THR_CTRL=0xf8000178
FPGA_LOAD_BITSTREAM="/dev/xdevcfg"
INT_STS=       0xf800700c
class x393sata(object):
    DRY_MODE= True # True
    DEBUG_MODE=1
    x393_mem=None
    vsc3304 = None
    def __init__(self, debug_mode=1,dry_mode=False, pcb_rev = "10389"):
        self.DEBUG_MODE=debug_mode
        if not dry_mode:
            if not os.path.exists("/dev/xdevcfg"):
                dry_mode=True
                print("Program is forced to run in SIMULATED mode as '/dev/xdevcfg' does not exist (not a camera)")
        self.DRY_MODE=dry_mode
        self.x393_mem=X393Mem(debug_mode,dry_mode, 1)
        self.vsc3304= x393_vsc3304(debug_mode, dry_mode, pcb_rev)
    def reset_get(self):
        """
        Get current reset state
        """
        return self.x393_mem.read_mem(FPGA_RST_CTRL)
    def reset_once(self):
        """
        Pulse reset ON, then OFF
        """
        self.reset((0,0xa))
    def reset(self,data):
        """
        Write data to FPGA_RST_CTRL register
        <data> currently data=1 - reset on, data=0 - reset on
               data can also be a list/tuple of integers, then it will be applied
               in sequence (0,0xe) will turn reset on, then off
        """
        if isinstance(data, (int,long)):
            self.x393_mem.write_mem(FPGA_RST_CTRL,data)
        else:
            for d in data:
                self.x393_mem.write_mem(FPGA_RST_CTRL,d)
    def bitstream(self,
                  bitfile=None,
                  quiet=1):
        """
        Turn FPGA clock OFF, reset ON, load bitfile, turn clock ON and reset OFF
        @param bitfile path to bitfile if provided, otherwise default bitfile will be used
        @param quiet Reduce output
        """
        if bitfile is None:
            bitfile=DEFAULT_BITFILE
        """            
        print ("Sensor ports power off")
        POWER393_PATH = '/sys/devices/elphel393-pwr.1'
        with open (POWER393_PATH + "/channels_dis","w") as f:
            print("vcc_sens01 vp33sens01 vcc_sens23 vp33sens23", file = f)
        """
        #Spread Spectrum off on channel 3
        print ("Spread Spectrum off on channel 3")
        with open (SI5338_PATH+"/spread_spectrum/ss3_values","w") as f:
            print ("0",file=f)
            
        print ("FPGA clock OFF")
        self.x393_mem.write_mem(FPGA0_THR_CTRL,1)
        print ("Reset ON")
        self.reset(0)
        print ("cat %s >%s"%(bitfile,FPGA_LOAD_BITSTREAM))
        if not self.DRY_MODE:
            l=0
            with open(bitfile, 'rb') as src, open(FPGA_LOAD_BITSTREAM, 'wb') as dst:
                buffer_size=1024*1024
                while True:
                    copy_buffer=src.read(buffer_size)
                    if not copy_buffer:
                        break
                    dst.write(copy_buffer)
                    l+=len(copy_buffer)
                    if quiet < 4 :
                        print("sent %d bytes to FPGA"%l)                            

            print("Loaded %d bytes to FPGA"%l)                            
#            call(("cat",bitfile,">"+FPGA_LOAD_BITSTREAM))
        if quiet < 4 :
            print("Wait for DONE")
        if not self.DRY_MODE:
            for _ in range(100):
                if (self.x393_mem.read_mem(INT_STS) & 4) != 0:
                    break
                sleep(0.1)
            else:
                print("Timeout waiting for DONE, [0x%x]=0x%x"%(INT_STS,self.x393_mem.read_mem(INT_STS)))
                return
        if quiet < 4 :
            print ("FPGA clock ON")
        self.x393_mem.write_mem(FPGA0_THR_CTRL,0)
        if quiet < 4 :
            print ("Reset OFF")
        self.reset(0xa)
#        self.x393_axi_tasks.init_state()
#        self.set_zynq()
        self.set_debug()
        print("Use 'set_zynq()', 'set_esata()' or 'set_debug() to switch SSD connection")
        
    def set_zynq(self):    
        self.vsc3304.connect_zynq_ssd()
        self.vsc3304.connection_status()

    def set_esata(self):    
        self.vsc3304.connect_esata_ssd()
        self.vsc3304.connection_status()
        
    def set_debug(self):    
        self.vsc3304.connect_debug()
        self.vsc3304.connection_status()

    def exp_gpio (self,
                  mode="in",
                  gpio_low=54,
                  gpio_high=None):
        """
        Export GPIO pins connected to PL (full range is 54..117)
        <mode>     GPIO mode: "in" or "out"
        <gpio_low> lowest GPIO to export     
        <gpio_hi>  Highest GPIO to export. Set to <gpio_low> if not provided     
        """
        if gpio_high is None:
            gpio_high=gpio_low
        print ("Exporting as \""+mode+"\":", end=""),    
        for gpio_n in range (gpio_low, gpio_high + 1):
            print (" %d"%gpio_n, end="")
        print() 
        if not self.DRY_MODE:
            for gpio in range (gpio_low, gpio_high + 1):
                try:
                    with open ("/sys/class/gpio/export","w") as f:
                        print (gpio,file=f)
                except:
                    print ("failed \"echo %d > /sys/class/gpio/export"%gpio)
                try:
                    with open ("/sys/class/gpio/gpio%d/direction"%gpio,"w") as f:
                        print (mode,file=f)
                except:
                    print ("failed \"echo %s > /sys/class/gpio/gpio%d/direction"%(mode,gpio))

    def mon_gpio (self,
                  gpio_low=54,
                  gpio_high=None):
        """
        Get state of the GPIO pins connected to PL (full range is 54..117)
        <gpio_low> lowest GPIO to export     
        <gpio_hi>  Highest GPIO to export. Set to <gpio_low> if not provided
        Returns data as list of 0,1 or None    
        """
        if gpio_high is None:
            gpio_high=gpio_low
        print ("gpio %d.%d: "%(gpio_high,gpio_low), end="")
        d=[]
        for gpio in range (gpio_high, gpio_low-1,-1):
            if gpio != gpio_high and ((gpio-gpio_low+1) % 4) == 0:
                print (".",end="")
            if not self.DRY_MODE:
                try:
                    with open ("/sys/class/gpio/gpio%d/value"%gpio,"r") as f:
                        b=int(f.read(1))
                        print ("%d"%b,end="")
                        d.append(b)
                except:
                    print ("X",end="")
                    d.append(None)
            else:
                print ("X",end="")
                d.append(None)
        print()
        return d
    

    def copy (self,
              src,
              dst):
        """
        Copy files in the file system
        @param src - source path
        @param dst - destination path/directory
        """
        shutil.copy2(src, dst)    
        
    """
from __future__ import print_function
from __future__ import division
import x393sata
import x393_mem
mem = x393_mem.X393Mem(1,0,1)
sata = x393sata.x393sata()
sata.bitstream()
mem.maxi_base()
hex(mem.read_mem(0x80000180))
mem.mem_dump (0x80000000, 0x200,1)
mem.mem_dump (0x80000000, 0x100,4)
0x80000000:00240020 80000000 00000000 00000001 00010301 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 
0x80000040:00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 
0x80000080:00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 
0x800000c0:00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 
0x80000100:80000800 00000000 80000c00 00000000 00000000 00000000 00240006 00000000 00000000 ffffffff 00000000 00000000 00000000 00000000 00000000 00000000 
0x80000140:00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000033 00000003 00000000 00000000 
0x80000180:0001fffe 00100000 01010001 00000000 00000000 00000000 00000000 00000000 00000000 80000000 00000000 0001fffe 00000000 00000040 00000000 00000100 
0x800001c0:40000001 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 
0x80000200:00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 
0x80000240:00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 
0x80000280:00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 
0x800002c0:00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 
0x80000300:00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 
0x80000340:00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 
0x80000380:00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 
0x800003c0:00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 

0x80000000:00240020 80000000 00000000 00000001 00010301 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 
0x80000040:00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 
0x80000080:00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 
0x800000c0:00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 
0x80000100:80000800 00000000 80000c00 00000000 00400040 00000000 00040006 00000000 00000080 ffffffff 00000123 00000000 040d0000 00000000 00000000 00000000 
0x80000140:00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000033 00000003 00000000 00000000 
0x80000180:0001fffe 00100000 01010002 00000000 00000000 00000000 00000000 00000000 00000000 80000000 00000000 0001fffe 00000000 00000040 00000000 00000100 
0x800001c0:40000001 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 
0x80000200:00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 
0x80000240:00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 
0x80000280:00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 
0x800002c0:00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 
0x80000300:00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 
0x80000340:00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 
0x80000380:00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 
0x800003c0:00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000 


mem.write_mem(0x8000012c,1)
hex(mem.read_mem(0x8000012c))
mem.write_mem(0x8000012c,0)   
hex(mem.read_mem(0x8000012c))
hex(mem.read_mem(0x80000130))
hex(mem.read_mem(0x80000ff0))

    
    """