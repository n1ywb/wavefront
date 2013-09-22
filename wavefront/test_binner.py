from wavefront.binner import Binner, Bin
from wavefront.timebuf import TimeBuffer
from unittest import TestCase
from mock import Mock

element_time = 0.25

class Test_Bin(TestCase):
    def test_bin(self):
        bin = Bin(size=1, timestamp=0)
        bin.add((0,1))

class Test_Binner(TestCase):
    def setUp(self):
        self.store = dict()
        #self.tb = TimeBuffer(size=4, head_time=1, element_time=element_time)
        self.binner = Binner(1, self.store)

    def test_update_1(self):
        self.assertEquals(self.binner.update(0, tuple(), 4), set())
        updated = self.binner.update(0, [0], 4)
        self.assertEquals(updated, set())
        updated = self.binner.update(-1, [0], 4)
        self.assertEquals(updated.pop().timestamp, 0)
        updated = self.binner.update(1, [0], 4)
        self.assertEquals(updated.pop().timestamp, -1)

    def test_update_2(self):
        self.binner.update(0, [0, 1, 0], 4)
