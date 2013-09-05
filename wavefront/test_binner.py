from wavefront.binner import Binner, Bin
from wavefront.timebuf import TimeBuffer
from unittest import TestCase
from mock import Mock

class Test_Bin(TestCase):
    def test_bin(self):
        bin = Bin()
        bin = Bin(0,1,2,3,4)
        bin = Bin(timestamp=None, max=None, min=None, mean=None, nsamples=0)

class Test_Binner_Const(TestCase):
    def test_binner_init(self):
        Binner(9, Mock())
        Binner(nsamples=9, timebuf=Mock())

class Test_Binner(TestCase):
    def setUp(self):
        self.tb = TimeBuffer(size=4, head_time=1, element_time=0.25)
        self.binner = Binner(3, self.tb)

    def test_update_1(self):
        self.binner.update(tuple())
        self.binner.update(((0, 0),))
        self.binner.update(((-1, 0),))
        self.binner.update(((1, 0),))
        self.assertEquals(self.tb[1], Bin(1, 0, 0, 0, 1))
        self.assertEquals(self.tb[0.75], None)
        self.assertEquals(self.tb[0.5], None)
        self.assertEquals(self.tb[0.25], None)
        self.assertRaises(IndexError, self.tb.__getitem__, 0)
        self.assertRaises(IndexError, self.tb.__getitem__, 1.25)

    def test_update_2(self):
        self.binner.update(((0, 0), (0.25, 1), (0.5, 0)))
