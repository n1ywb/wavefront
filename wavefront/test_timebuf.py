from wavefront.timebuf import TimeBuffer
from unittest import TestCase

class Test_TimeBuffer(TestCase):
    def setUp(self):
        self.tb = TimeBuffer(size=4, head_time=1, element_time=0.25)

    def test_tail_num(self):
        self.assertEquals(self.tb.tail_num, 0)

    def test_tail_time(self):
        self.assertEquals(self.tb.tail_time, 0)

    def test_head_time(self):
        self.assertEquals(self.tb.head_time, 1)

    def test_head_num(self):
        self.assertEquals(self.tb.head_num, 4)

    def test_repr(self):
        repr(self.tb)

    def test_str(self):
        str(self.tb)

    timestamps = [0,0.25,0.5,0.75,1,1.25]

    def test_index(self):
        for n, ts in enumerate(self.timestamps):
            self.assertEquals(self.tb.index(ts), n)

    def test_timestamp(self):
        for n, ts in enumerate(self.timestamps):
            self.assertEquals(self.tb.timestamp(n), ts)

    def test_append(self):
        self.tb.append(0)

        self.assertEquals(self.tb.head_time, 1.25)
        self.assertEquals(self.tb.tail_time, 0.25)
        self.assertEquals(self.tb.head_num, 5)
        self.assertEquals(self.tb.tail_num, 1)

        self.assertEquals(self.tb[0.25], None)
        self.assertEquals(self.tb[0.5], None)
        self.assertEquals(self.tb[0.75], None)
        self.assertEquals(self.tb[1.0], 0)

        self.assertEquals(list(self.tb.itervalues()), [None, None, None, 0])

