What does each recorded field mean?
Field	Meaning
sample_index	Sequential index assigned by our script
sensor_time_usec	Timestamp reported in the MAVLink RAW_IMU message
host_receive_monotonic_ns	Jetson monotonic timestamp taken after recv_match() returns


# objective- measure strix IMU Timing Behavior.
# Input- MAVLink RAW_IMU messages and host arrival timestamps.
# Process- connect, receive, record and analyze

# output- csv dataset with timing statistics
# Failure loggiv- No heartbeat, No IMU messages, invalid timestamps or connection loss.

# import
# configuration
# DATA STRUCTURES
# core logic
# init logic
# business logic

# execution
# try catch
# input
# object
# output




# logic-
# Connect to Strix. Use the persistent USB path and MAVLink at the configured baud rate. Wait for a heartbeat to confirm communication.
# Request the IMU stream. Send MAV_CMD_SET_MESSAGE_INTERVAL requesting RAW_IMU at a nominal 50 Hz. This is a request, not a guarantee.
# Allow the stream to settle. Wait two seconds before starting the measurement.
#Start the capture clock. Use time.monotonic_ns() on the Jetson, which is appropriate for measuring elapsed time without wall-clock adjustments.
# Receive and record measurements. For each RAW_IMU message, record its sensor timestamp (time_usec) and the Jetson's host-arrival timestamp.
# Save the dataset. Write the measurements to raw_measurements.csv for later analysis.
# Close the connection. Release the MAVLink connection after the capture ends.


we will calculate:
- Observed message rate: how many RAW_IMU messages arrive per second.
- Sensor timestamp intervals: differences between consecutive sensor timestamps.
- Host arrival intervals: differences between consecutive host timestamps.
- Jitter: variation in those intervals relative to their typical period.
- Timestamp continuity: whether sensor timestamps progress consistently.
- Gaps and anomalies: unusually long intervals, repeated timestamps or backward jumps.

Stage 1 — Strix timing acquisition
Current stage
Create strix_timing.py, verify the Jetson connection and capture a controlled dataset.



Stage 2 — Timing analysis

Build the analysis logic and generate a report containing rate, interval statistics, jitter, timestamp continuity and gaps.



Stage 3 — RealSense timing characterization

Independently measure RGB and depth frame timing, including their relationship to each other.



Stage 4 — Time synchronization

Establish timestamp semantics, map clock domains where necessary, associate measurements and quantify synchronization uncertainty.



ls -l /dev/serial/by-id/

udevadm info --query=property \
  --name=/dev/ttyACM0

Sensor Mangement

The immediate software objective is to build a reliable sensor-management layer that feeds synchronized sensor data into state estimation and, subsequently, VIO/SLAM.

