import os
from collections import namedtuple

_ntuple_diskusage = namedtuple('usage', 'total used free')

def disk_usage(path):
    """Return disk usage statistics about the given path.

    Returned valus is a named tuple with attributes 'total', 'used' and
    'free', which are the amount of total, used and free space, in Megabytes.
    """
    st = os.statvfs(path)
    free = st.f_bavail * st.f_frsize
    total = st.f_blocks * st.f_frsize
    used = (st.f_blocks - st.f_bfree) * st.f_frsize
    return _ntuple_diskusage(total/1000000, used/1000000, free/1000000)
    

a = disk_usage('/')
print a.free, " free,", a.used, " used,", a.total, " total"
   
#print disk_usage('/').free, " FREE"
#print disk_usage('/').used, " USED"
#print disk_usage('/').total, " TOTAL"