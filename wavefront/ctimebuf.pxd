cdef class TimeUtil:
    cdef public double element_time
    cpdef int index(self, double timestamp)
    cpdef double timestamp(self, int index)
    cpdef double floor(self, double timestamp)

