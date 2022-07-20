#!python
# cython: language_level=3

from sys import int_info
import cython

cdef packed struct mvector_elem_struct:
    signed char x
    signed char y
    unsigned short sad
ctypedef mvector_elem_struct mvector_elem_struct_t


cdef packed struct sums_struct:
    int x 
    int y 

ctypedef sums_struct sums_struct_t



@cython.boundscheck(False) # turn off bounds-checking for entire function, speeds up array indexing
@cython.wraparound(False)  # turn off negative index wrapping for entire function, speeds up array indexing further
def sotv_fast(const mvector_elem_struct_t [:,:] motion_frame, int threshold_small):
    """A fast implementation of the sum of thresholded motion vectors.
    
    Intended as a direct replacement for the numpy operations shown below:
    
    magnitudes = np.sqrt(
        np.square(motion_frame["x"].astype(np.float))
        + np.square(motion_frame["y"].astype(np.float))
    )

    filtered = np.where(
        magnitudes > self.threshold_small,
        motion_frame,
        np.array(
            (0, 0, 0),
            dtype=[
                ("x", "i1"),
                ("y", "i1"),
                ("sad", "u2"),
            ],
        ),
    )
    x_sum = sum(sum(filtered["x"].astype(float))).astype(float)
    y_sum = sum(sum(filtered["y"].astype(float))).astype(float)
    return x_sum, y_sum


    To sidestep expensive sqrt calls, the threshold is instead squared and compared with the square of magnitude, additions to x_sum and y_sum are only performed when the threshold is passed. 
    
    Finally, the ndarray is converted to a Cython memoryview allowing element access at C-speed, see: http://docs.cython.org/en/latest/src/userguide/numpy_tutorial.html#numpy-tutorial and https://cython.readthedocs.io/en/latest/src/tutorial/numpy.html


    Args:
        const mvector_elem_struct_t (_type_): Pass a read-only memory view of the motion vector data, this can be a numpy ndarray. Array is expected to be two-dimensional with elements typed to fit :class:`~DynAIkonTrap.camera_to_disk.MotionData`
        threshold_small (int): integer threshold to pass over all motion vector magnitudes
    """
    cdef int frame_size_x = motion_frame.shape[0] 
    cdef int frame_size_y = motion_frame.shape[1]
    cdef int i, j
    cdef int thres_sqrd, mag_sqrd, x_sqrd, y_sqrd 
    thres_sqrd = threshold_small * threshold_small
    cdef int x, y
    cdef sums_struct_t ret
    ret.x = 0
    ret.y = 0

    for i in range(frame_size_x):
        for j in range(frame_size_y):
            x = motion_frame[i][j].x 
            y = motion_frame[i][j].y 
            mag_sqrd = x*x + y*y
            if mag_sqrd > thres_sqrd:
                ret.x += x
                ret.y += y
    return ret
