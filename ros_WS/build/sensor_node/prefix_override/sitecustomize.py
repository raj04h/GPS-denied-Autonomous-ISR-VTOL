import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/mnt/nvme0n1p6/HRaj_WS/Autonomous-ISR-VTOL/ros_WS/install/sensor_node'
