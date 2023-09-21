import cocotb
from cocotb.triggers import Timer, RisingEdge, Event
import threading
from cocotb.simulator import *
from cocotb.simulator import *
from cocotb.queue import *
from cocotb_coverage.coverage import *
from cocotb_coverage.crv import *

# ***********************************[COVERAGE SECTION]********************************************************************
Coverage = coverage_section(
    CoverPoint("top.a", vname="a", bins=list(range(0, 16))),
    CoverPoint("top.b", vname="b", bins=list(range(0, 16))),
    CoverPoint("top.op", vname="op", bins=list(range(0, 4))),
    CoverCross("top.all_cases", items=["top.a", "top.b", "top.op"])

)


@Coverage
def sample(a, b, op):
    cocotb.log.info("The randomized values are a= " + bin(int(a)) + " b= " + bin(int(b)) + " op= " + bin(int(op)))


# ***********************************************[TRANSACTION CLASS]*****************************************************
"""""
This class has the inputs and the outputs of the ALU. It gives the inputs the ranges for their randomization.
It has two functions:
print_signals: to print the inputs and outputs of a packet(item) and the name of the class who called it.
copy_data : copies the the values of the given item to another one and it will only be used in the scoreboard
"""""
class Transaction(Randomized):
    def __init__(self):
        Randomized.__init__(self)
        self.a = 0
        self.b = 0
        self.op = 0
        self.c = 0
        self.out = 0
        self.add_rand("a", list(range(0, 16)))
        self.add_rand("b", list(range(0, 16)))
        self.add_rand("op", list(range(0, 4)))

    def print_signals(self, name="Transaction"):
        cocotb.log.info(str(name) + " a=" + bin(int(self.a)) + " b=" + bin(int(self.b)) + " op=" + bin(
            int(self.op)) + " c=" + bin(int(self.c)) + " out=" + bin(int(self.out)))

    def copy_data(self, tmp):
        self.a = tmp.a
        self.b = tmp.b
        self.op = tmp.op
        self.c = tmp.c
        self.out = tmp.out


# ***********************************************[GENERATOR CLASS]*******************************************************

"""""
In this class the run function does the randomization and calls the function (sample) for the coverage

It also passes the randomized item to the Driver by putting it in the the queue and uses an event and a timer to sync.
with the Driver.

"""""

class Generator:
    def __init__(self):
        pass

    async def run(self, drv_mbx, drv_done, item):
        item = Transaction()
        loop = 10000
        for i in range(loop):
            item.randomize()
            sample(item.a, item.b, item.op)
            cocotb.log.info("[Generator] Loop:%0d/%0d create next item ", i + 1, loop)
            await drv_mbx.put(item)
            cocotb.log.info("[Generator] Wait for Driver to receive data")
            await drv_done.wait()
            await Timer(500, units="ns")


# ***********************************************[DRIVER CLASS]**********************************************************

"""""
In this class in the run function the Driver takes the data sent by the Generator from the queue and sets the event 
informing the Generator it has received the item

It also passes the item to the DUT so the DUT can calculate the output and uses an event and a timer to sync.
with the Monitor.

"""""

class Driver:
    def __int__(self):
        pass

    async def run(self, drv_mbx, mon_done, drv_done, dut):
        cocotb.log.info(" [Driver] Starting ....", )
        while True:
            await Timer(500, units="ns")
            item = await drv_mbx.get()
            cocotb.log.info(" [Driver] Waiting for item from Generator ....")
            item.print_signals("[Driver]")
            dut.a = item.a
            dut.b = item.b
            dut.op = item.op
            drv_done.set()
            cocotb.log.info(" [Driver] Transferring data to DUT ....")
            await mon_done.wait()


# ***********************************************[MONITOR CLASS]*********************************************************
"""""
In this class in the run function the Monitor receives the item from the DUT with the output calculated

It also passes the item to the Scoreboard by putting it in the the queue. It sets the event informing the Driver it 
received the item from the DUT.
"""""


class Monitor:
    def __init__(self):
        pass

    async def run(self, item_m, mon_done, scb_mbx, dut):
        cocotb.log.info(" [Monitor] starting ....")
        while True:
            await Timer(499, units="ns")
            cocotb.log.info("[Monitor] Waiting for item from DUT ....")
            item_m.print_signals("[Monitor]")
            item_m.a = dut.a
            item_m.b = dut.b
            item_m.op = dut.op
            item_m.c = dut.c
            item_m.out = dut.out
            await scb_mbx.put(item_m)
            mon_done.set()


# ***********************************************[SCOREBOARD CLASS]******************************************************

"""""
In this class in the run function a comparison is done between the received item from the DUT and a reference output 
to see which cases failed and which passed.
A dictionary (unique_bugs) is used to count the number of unique bugs so its keys are a combination of the inputs
(a, b, op) and it checks whether each combination exists as a key from before or not if not then this means that
this combination is unique and if it fails then put a value to this key.
"""""


class ScoreBoard:
    def __int__(self):
        pass

    async def run(self, scb_mbx, unique_bugs={}):
        ref_item = Transaction()
        while True:
            await Timer(600, units="ns")
            item = await scb_mbx.get()
            cocotb.log.info(" [ScoreBoard] Waiting for item from Monitor ....")
            item.print_signals("ScoreBoard")
            ref_item.copy_data(item)

            if ref_item.op == 0:
                temp = str(item.a) + str(item.b) + str(item.op)
                if int(ref_item.a) + int(ref_item.b) > 16:
                    ref_output = int(ref_item.a) + int(ref_item.b) - 16
                    ref_carry = 1
                elif int(ref_item.a) + int(ref_item.b) == 16:
                    ref_output = 0
                    ref_carry = 1
                else:
                    ref_output = int(ref_item.a) + int(ref_item.b)
                    ref_carry = 0
                alu_output = int(item.out)
                if int(ref_output) == alu_output and (ref_carry == item.c):
                    cocotb.log.info(
                        "Scoreboard Pass! Carry and Sum match, ref_output = " + bin(ref_output) + ", alu_out = " + bin(
                            alu_output))

                else:
                    if temp in unique_bugs.keys() is True:
                        pass
                    else:
                        unique_bugs[temp] = 1
                    cocotb.log.info("Scoreboard Error! Carry and Sum mismatch, ref_output = " + bin(
                        ref_output) + ", alu_out = " + bin(alu_output))

            if ref_item.op == 1:
                temp = str(item.a) + str(item.b) + str(item.op)
                ref_output = int(ref_item.a) ^ int(ref_item.b)
                alu_output = int(item.out)
                if int(ref_output) == alu_output and (item.c == 0):
                    cocotb.log.info(
                        "Scoreboard Pass! XOR match, ref_output = " + bin(ref_output) + ", alu_out = " + bin(
                            alu_output))

                else:
                    if temp in unique_bugs.keys() is True:
                        pass
                    else:
                        unique_bugs[temp] = 1
                    cocotb.log.info(
                        "Scoreboard Error! XOR mismatch, ref_output = " + bin(ref_output) + ", alu_out = " + bin(
                            alu_output))

            if ref_item.op == 2:
                temp = str(item.a) + str(item.b) + str(item.op)
                ref_output = int(ref_item.a) & int(ref_item.b)
                alu_output = int(item.out)
                if int(ref_output) == alu_output and (item.c == 0):
                    cocotb.log.info(
                        "Scoreboard Pass! AND match, ref_output = " + bin(ref_output) + ", alu_out = " + bin(
                            alu_output))

                else:
                    if temp in unique_bugs.keys() is True:
                        pass
                    else:
                        unique_bugs[temp] = 1
                    cocotb.log.info(
                        "Scoreboard Error! AND mismatch, ref_output = " + bin(ref_output) + ", alu_out = " + bin(
                            alu_output))

            if ref_item.op == 3:
                temp = str(item.a) + str(item.b) + str(item.op)
                ref_output = int(ref_item.a) | int(ref_item.b)

                alu_output = int(item.out)
                if int(ref_output) == alu_output and (item.c == 0):
                    cocotb.log.info(
                        "Scoreboard Pass! OR match, ref_output = " + bin(ref_output) + ", alu_out = " + bin(alu_output))

                else:
                    if temp in unique_bugs.keys() is True:
                        pass
                    else:
                        unique_bugs[temp] = 1
                    cocotb.log.info(
                        "Scoreboard Error! OR mismatch, ref_output = " + bin(ref_output) + ", alu_out = " + bin(
                            alu_output))


# ***********************************************[ENVORONMENT CLASS]****************************************************

"""""
There is no need for the environment class

In this class in the run function awaits the above classes and generates the file including the coverage information
and it calculated the length of the dictionary to get the number of unique bugs.

"""""

class Envoronment:
    def __init__(self):
        self.t = Transaction()
        self.g = Generator()
        self.Gen_Driv_event = Event()
        self.Driv_Mon_event = Event()
        self.d = Driver()
        self.Gen_Driv_queue = Queue()
        self.Mon_Scb_queue = Queue()
        self.m = Monitor()
        self.s = ScoreBoard()
        self.u = {}

    async def run(self, dut):
        await cocotb.start(self.d.run(self.Gen_Driv_queue, self.Driv_Mon_event, self.Gen_Driv_event, dut))
        await cocotb.start(self.m.run(self.t, self.Driv_Mon_event, self.Mon_Scb_queue, dut))
        await cocotb.start(self.g.run(self.Gen_Driv_queue, self.Gen_Driv_event, self.t))
        await cocotb.start(self.s.run(self.Mon_Scb_queue, self.u))
        await Timer(5001000, units="ns")
        coverage_db.export_to_xml(filename="ALU_coverage.xml")
        cocotb.log.info("Number of unique bugs =%0d", len(self.u.keys()))

# ***********************************************[TEST CLASS]*****************************************************

"""""
In this class in the test function awaits the environment class so the test runs.
There is no need for the environment class
"""""

@cocotb.test()
async def test(dut):
    e = Envoronment()
    await e.run(dut)
