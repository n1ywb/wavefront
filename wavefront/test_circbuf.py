from unittest import TestCase
from wavefront.circbuf import CircularBuffer

class Test_CircularBuffer_init_item_factory(TestCase):
    def test_CircularBuffer_init_item_factory(self):
        cb = CircularBuffer(1, lambda: "foo")
        self.assertEquals(cb[:], ["foo",])


class Test_CircularBuffer_1(TestCase):
    def setUp(self):
        self.cb = CircularBuffer(1)

    def test_len(self):
        self.assertEquals(len(self.cb), 1)

    def test_init(self):
        self.assertEquals(self.cb[:], [None,])

    def test_repr(self):
        self.assert_(isinstance(repr(self.cb), str))

    def test_append(self):
        self.cb.append('foo')
        self.assertEquals(self.cb[:], ['foo',])
        self.cb.append('bar')
        self.assertEquals(self.cb[:], ['bar',])

    def test_extend(self):
        self.cb.extend(('foo', 'bar'))
        self.assertEquals(self.cb[:], ['bar',])

    def test_getitem(self):
        self.assertEquals(self.cb[0], None)
        self.assertEquals(self.cb[1], None)
        self.assertEquals(self.cb[-1], None)

    def test_setitem(self):
        self.cb[0] = 'foo'
        self.assertEquals(self.cb[:], ['foo',])
        self.cb[1] = 'bar'
        self.assertEquals(self.cb[:], ['bar',])

    def test_iter(self):
        self.assertEquals(list(iter(self.cb)), [None,])

    def test_contains(self):
        self.assert_(None in self.cb)
        self.assert_(not 'foo' in self.cb)

class Test_CircularBuffer_2(TestCase):
    def setUp(self):
        i = iter([0,1])
        def f():
            return i.next()
        self.cb = CircularBuffer(2, f)

    def test_len(self):
        self.assertEquals(len(self.cb), 2)

    def test_init(self):
        self.assertEquals(self.cb[:], [0,1])

    def test_repr(self):
        self.assert_(isinstance(repr(self.cb), str))

    def test_append(self):
        self.cb.append('foo')
        self.assertEquals(self.cb[:], [1, 'foo'])
        self.cb.append('bar')
        self.assertEquals(self.cb[:], ['foo','bar'])
        self.cb.append('foo')
        self.assertEquals(self.cb[:], ['bar','foo'])

    def test_extend(self):
        self.cb.extend(('foo', 'bar'))
        self.assertEquals(self.cb[:], ['foo', 'bar'])

    def test_getitem(self):
        self.assertEquals(self.cb[0], 0)
        self.assertEquals(self.cb[1], 1)
        self.assertEquals(self.cb[-1], 1)

    def test_setitem(self):
        self.cb[0] = 'foo'
        self.assertEquals(self.cb[:], ['foo',1])
        self.cb[1] = 'bar'
        self.assertEquals(self.cb[:], ['foo', 'bar'])
        self.cb[-1] = 'bar'
        self.assertEquals(self.cb[:], ['foo', 'bar'])

    def test_iter(self):
        self.assertEquals(list(iter(self.cb)), [0,1])

    def test_contains(self):
        self.assert_(0 in self.cb)
        self.assert_(1 in self.cb)
        self.assert_(not 2 in self.cb)

