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

    def test_append_1(self):
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

    def test_append_2(self):
        self.tb.append(0)
        self.tb.append(1)

        self.assertEquals(self.tb.head_time, 1.5)
        self.assertEquals(self.tb.tail_time, 0.5)
        self.assertEquals(self.tb.head_num, 6)
        self.assertEquals(self.tb.tail_num, 2)

        self.assertEquals(list(self.tb.itervalues()), [None, None, 0, 1])

    def test_append_3(self):
        [self.tb.append(n) for n in xrange(5)]
        self.assertEquals(list(self.tb.itervalues()), [1, 2, 3, 4])

    def test_update(self):
        self.tb.update([(0,0)])
        self.assertEquals(list(self.tb.itervalues()), [0, None, None, None])

    def test_update_2(self):
        self.tb.update([(10,0)])
        self.assertEquals(list(self.tb.itervalues()), [None, None, None, 0])

    def test_update_3(self):
        self.tb.update([(0,0), (0.5,1)])
        self.assertEquals(list(self.tb.itervalues()), [0, None, 1, None])

    def test_update_4(self):
        self.tb.update([(0.5,1), (0,0)])
        self.assertEquals(list(self.tb.itervalues()), [0, None, 1, None])

    def test_update_5(self):
        self.tb.update([(1.5,0), (2,1)])
        self.assertEquals(list(self.tb.itervalues()), [None, 0, None, 1])

    def test_getitem(self):
        self.tb.update(zip(self.timestamps[:4], range(4)))
        self.assertEquals(self.tb[0], 0)
        self.assertEquals(self.tb[0.25], 1)
        self.assertEquals(self.tb[0.75], 3)
        self.assertRaises(IndexError, self.tb.__getitem__, 1)

    def test_setitem(self):
        for n, ts in enumerate(self.timestamps[:4]):
            self.tb[ts] = n
        self.assertEquals(list(self.tb.itervalues()), [0,1,2,3])
        self.assertRaises(IndexError, self.tb.__setitem__, 1, 1)

    def test_has_key(self):
        self.assertTrue(self.tb.has_key(0))
        self.assertFalse(self.tb.has_key(1))

    def test_contains(self):
        self.assertTrue(0 in self.tb)
        self.assertFalse(1 in self.tb)

    def test_iteritems(self):
        self.tb.update(zip(self.timestamps[:4], range(4)))
        i = self.tb.iteritems()
        self.assertEquals(i.next(), (0.0, 0))
        self.assertEquals(i.next(), (0.25, 1))
        self.assertEquals(i.next(), (0.5, 2))
        self.assertEquals(i.next(), (0.75, 3))
        self.assertRaises(StopIteration, i.next)

    def test_itervalues(self):
        self.tb.update(zip(self.timestamps[:4], range(4)))
        i = self.tb.itervalues()
        self.assertEquals(i.next(), 0)
        self.assertEquals(i.next(), 1)
        self.assertEquals(i.next(), 2)
        self.assertEquals(i.next(), 3)
        self.assertRaises(StopIteration, i.next)

    def test_iter(self):
        self.tb.update(zip(self.timestamps[:4], range(4)))
        i = iter(self.tb)
        self.assertEquals(i.next(), 0.0)
        self.assertEquals(i.next(), 0.25)
        self.assertEquals(i.next(), 0.5)
        self.assertEquals(i.next(), 0.75)
        self.assertRaises(StopIteration, i.next)


