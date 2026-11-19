# SM-B --- Timing and Synchronization

**Project:** Autonomous UAV / Sovereign Autonomy\
**Hardware:** Intel RealSense D455 + Strix R0.1\
**Compute and middleware:** Jetson Orin NX, ROS 2 Humble, MAVLink /
MAVROS\
**Evidence baseline:** Existing SM-B records and October 26, 2026
concurrent sensor dataset\
**Overall status:** **PARTIALLY ESTABLISHED --- EVIDENCE REVIEW
COMPLETE**\
**Physical camera--IMU synchronization:** **NOT DEMONSTRATED**

------------------------------------------------------------------------

## 1. Purpose and scope

SM-B investigates timestamp provenance, observed timing behaviour,
clock-domain relationships and the temporal relationship between the
D455 camera and Strix IMU.

It contains five work packages:

1.  B4.1 --- RealSense camera timestamp provenance.
2.  B4.2 --- Strix RAW_IMU timestamp provenance.
3.  B4.3 --- Clock-domain relationship.
4.  B4.4 --- Camera--IMU temporal relationship.
5.  B4.5 --- Synchronization acceptance evidence.

**Completion of the evidence review is not equivalent to implementation
or validation of physical camera--IMU synchronization.** The current
evidence establishes timestamp fields and software observation points,
per-stream timing behaviour, concurrent host-arrival logging and
RGB--Depth software association. It does not establish end-to-end
physical measurement-time synchronization between the D455 and Strix
IMU.

### 1.1 System context

  Element                Role
  ---------------------- --------------------------------------
  Intel RealSense D455   RGB and depth source
  Strix R0.1             MAVLink RAW_IMU source
  Jetson Orin NX         Host-side acquisition and processing
  ROS 2 Humble           Sensor middleware interfaces
  MAVLink / MAVROS       Strix telemetry and IMU data path

Topics identified in the project interface inventory include
`/camera/camera/color/image_raw`, `/camera/camera/depth/image_rect_raw`,
`/uas1/mavros/imu/data_raw`, `/uas1/mavros/imu/data`, `/sensor/imu` and
`/sensor_management/health`. Their presence in the interface inventory
does not prove that every topic was active in every capture.

## 2. Work-package completion summary

  ----------------------------------------------------------------------------
  Work package      Activity          Work completed         Status
  ----------------- ----------------- ---------------------- -----------------
  B4.1              RealSense camera  D455 timestamp fields, Completed with
                    timestamp         ROS headers, host      limitations
                    provenance        callback timestamps    
                                      and SDK                
                                      timestamp-domain       
                                      mechanisms reviewed    

  B4.2              Strix RAW_IMU     `RAW_IMU.time_usec`,   Completed with
                    timestamp         host receive           limitations
                    provenance        timestamps and ROS     
                                      publisher timestamp    
                                      behaviour reviewed     

  B4.3              Clock-domain      Sensor/host timestamp  Completed with
                    relationship      comparisons and        limitations
                                      offset/drift           
                                      limitations assessed   

  B4.4              Camera--IMU       Host-arrival           Completed with
                    temporal          relationship,          limitations
                    relationship      measurement-time       
                                      semantics and          
                                      calibration            
                                      applicability assessed 

  B4.5              Synchronization   Requirements, camera   Complete ---
                    acceptance        integrity, IMU         conditional
                    evidence          integrity,             acceptance
                                      cross-sensor evidence  
                                      and final report       
                                      completed              
  ----------------------------------------------------------------------------

"Completed with limitations" means the investigation and available
evidence have been reviewed and recorded. It does not mean every
underlying engineering requirement has passed.

## 3. B4.1 --- RealSense camera timestamp provenance

**Status: COMPLETED WITH LIMITATIONS**

### 3.1 Hardware and software identity

  Item                  Recorded value
  --------------------- ----------------------
  Camera                Intel RealSense D455
  Serial number         `235422301824`
  Firmware              `5.17.0.9`
  `realsense2_camera`   `4.58.4`
  `librealsense2`       `2.58.4`

### 3.2 Evidence reviewed

-   [x] Identified D455 RGB and depth streams.
-   [x] Identified ROS camera header timestamps.
-   [x] Identified host monotonic timestamps recorded at camera callback
    entry.
-   [x] Reviewed SDK timestamp domains: `HARDWARE_CLOCK`, `SYSTEM_TIME`
    and `GLOBAL_TIME`.
-   [x] Reviewed RGB--Depth timestamp association evidence.
-   [x] Reviewed per-stream timestamp monotonicity, interval
    distributions and gaps in the October 26 dataset.
-   [x] Distinguished camera header timestamps from host
    callback-arrival timestamps.
-   [x] Documented why monotonicity and software pairing do not prove
    hardware exposure synchronization.

### 3.3 Established

The records identify the camera timestamp fields and the software
observation point at which host callback timestamps were recorded. ROS
header timestamps and host callback monotonic timestamps are preserved
as separate fields.

### 3.4 Not established

-   Active D455 timestamp domain during the historical capture.
-   Whether the header timestamp denotes exposure start, exposure
    midpoint, exposure end, frame delivery or another event.
-   A verified mapping from the camera timestamp domain to the Jetson
    host monotonic clock.
-   Physical exposure-time relationship between RGB and depth.
-   Hardware trigger or exposure synchronization status.

### 3.5 Limitation

A ROS header timestamp is not automatically an exposure timestamp. The
active SDK timestamp domain and the event represented by that timestamp
must be established before treating it as physical measurement time. A
host callback timestamp records software delivery and includes
acquisition, transport, driver, scheduling and callback delays.

## 4. B4.2 --- Strix RAW_IMU timestamp provenance

**Status: COMPLETED WITH LIMITATIONS**

### 4.1 Evidence reviewed

-   [x] Identified MAVLink `RAW_IMU`.
-   [x] Identified `RAW_IMU.time_usec` as the recorded sensor timestamp
    field.
-   [x] Identified `host_receive_monotonic_ns` as the host receive-time
    observation.
-   [x] Distinguished sensor timestamp from host receive timestamp.
-   [x] Reviewed permitted MAVLink timestamp interpretations: UNIX epoch
    or time since boot.
-   [x] Reviewed the Strix-to-MAVLink-to-host data path.
-   [x] Reviewed ROS IMU publisher timestamp behaviour.
-   [x] Established from the reviewed publisher source that the ROS
    header stamp is assigned using the ROS node clock at publication
    time rather than copying `RAW_IMU.time_usec` directly.

### 4.2 Established

The evidence identifies the Strix sensor timestamp field, host receive
observation and ROS publication timestamp behaviour. These are distinct
timestamp events and must remain distinct in downstream records.

### 4.3 Not established

-   Actual epoch-versus-boot origin used by installed Strix firmware.
-   Exact physical measurement event represented by `RAW_IMU.time_usec`.
-   Calibrated Strix clock-to-host clock mapping.
-   Sensor-to-host clock offset and relative drift.
-   Whether every downstream ROS IMU message preserves original
    measurement-time semantics.

### 4.4 Limitation

The host receive timestamp is generated after the MAVLink receive call
returns. It includes transport and software scheduling effects. The ROS
publication timestamp is assigned from the ROS clock and is not evidence
that the original sensor measurement occurred at that ROS time.

## 5. B4.3 --- Clock-domain relationship

**Status: COMPLETED WITH LIMITATIONS**

### 5.1 Clock observations considered

-   D455 ROS header timestamps.
-   D455 host callback timestamps using `time.monotonic_ns()`.
-   Strix `RAW_IMU.time_usec`.
-   Strix host receive timestamps using `time.monotonic_ns()`.
-   ROS publication timestamps assigned using the ROS node clock.
-   Capture wall-time and monotonic-time metadata.

### 5.2 Established

-   [x] Compared camera header timestamps with camera host callback
    timestamps.
-   [x] Compared IMU sensor timestamps with IMU host receive timestamps.
-   [x] Reviewed per-stream timestamp interval distributions.
-   [x] Reviewed monotonicity and discontinuities.
-   [x] Documented that numeric subtraction between different clock
    domains is not automatically a calibrated offset.
-   [x] Documented limitations in estimating offset and drift from
    available captures.
-   [x] Identified that capture-start wall time and monotonic time were
    sampled sequentially rather than atomically; the interval was not
    recorded.
-   [x] Identified that capture-end metadata records monotonic time but
    not an equivalent paired wall-clock sample.

### 5.3 Not established

-   Calibrated camera-to-host clock mapping.
-   Calibrated Strix-to-host clock mapping.
-   Validated relative camera-to-IMU clock offset.
-   Relative clock drift over time.
-   Complete uncertainty budget for timestamp conversion and event
    timing.

### 5.4 Clock mapping concept

A relative clock relationship may require both a rate term and an offset
term:

\[ t_B = a,t_A + b \]

Here, (a) represents relative clock-rate scale and (b) represents
relative offset. This is a possible characterization model only. No
validated values for either parameter have been established by the
current evidence.

### 5.5 Limitation

A one-time apparent difference between timestamp values cannot separate
clock-origin difference, clock-rate difference, transport delay,
callback scheduling delay and measurement-event semantics. A clock
mapping requires evidence identifying the event represented by each
timestamp and supporting estimation over a suitable interval.

## 6. B4.4 --- Camera--IMU temporal relationship

**Status: COMPLETED WITH LIMITATIONS**

### 6.1 Evidence reviewed

-   [x] Completed camera--IMU evidence inventory.
-   [x] Reviewed camera and IMU measurement-time semantics.
-   [x] Compared camera callback arrival timestamps with IMU host
    receive timestamps.
-   [x] Reviewed available temporal relationship evidence.
-   [x] Assessed offline temporal-calibration applicability.
-   [x] Reviewed available camera and IMU frame/transform evidence.
-   [x] Documented why existing data does not establish reliable
    physical camera--IMU temporal calibration.
-   [x] Prepared calibration applicability and limitations record.
-   [x] Prepared final camera--IMU temporal relationship record.

### 6.2 October 26 host-arrival comparison

For dataset `20261026_212010`, nearest-neighbour comparisons between
host-arrival timestamp streams produced:

  -----------------------------------------------------------------------
  Comparison        Median absolute       P95 absolute   Maximum absolute
                         separation         separation         separation
  -------------- ------------------ ------------------ ------------------
  RGB callback            4.7233 ms          9.5835 ms         10.5616 ms
  to nearest IMU                                       
  receive                                              

  Depth callback          5.0622 ms          9.5680 ms         10.7037 ms
  to nearest IMU                                       
  receive                                              
  -----------------------------------------------------------------------

These are software-observed arrival-time differences. They are not
physical camera--IMU measurement-time offsets.

### 6.3 Established

The available host-arrival relationship has been characterized for the
recorded dataset. Evidence limitations and calibration applicability
have been documented.

### 6.4 Not established

-   Physical camera--IMU measurement-time offset.
-   Validated camera--IMU temporal calibration.
-   Validated camera-to-IMU clock mapping.
-   Hardware synchronization between D455 exposure and Strix IMU
    sampling.
-   Repeatable synchronization accuracy across independent captures.

### 6.5 Limitation

Nearest-neighbour matching between callback and receive timestamps
describes the closest logged software events. It does not identify the
physical time at which the camera exposed a frame or the IMU sampled its
measurements. The result is also influenced by different stream rates
and message delivery behaviour.

## 7. B4.5 --- Synchronization acceptance evidence

**Status: COMPLETE --- CONDITIONAL ACCEPTANCE**

B4.5 was completed as an evidence-review package using the existing
October 26 dataset and prior records. No sensor-driver, timestamp
pipeline or hardware configuration changes were made as part of this
evidence review.

### 7.1 B4.5 sub-checklist

-   [x] B4.5.1 --- Synchronization requirements documented and approved.
-   [x] B4.5.2 --- Camera timestamp integrity reviewed.
-   [x] B4.5.3 --- IMU timestamp integrity reviewed.
-   [x] B4.5.4 --- Cross-sensor synchronization evidence reviewed.
-   [x] B4.5.5 --- Final synchronization acceptance report prepared.

### 7.2 Approved nominal rates

  Stream            Nominal target   Nominal interval
  --------------- ---------------- ------------------
  D455 RGB                   30 Hz          33.333 ms
  D455 Depth                 30 Hz          33.333 ms
  Strix RAW_IMU              50 Hz              20 ms

These are the nominal targets used in the evidence review. They do not
by themselves define all allowable jitter, latency, maximum-gap or
physical synchronization-error tolerances.

### 7.3 October 26 dataset

**Dataset path:**
`~/Autonomous-ISR-VTOL/data/concurrent_sensor_captures/20261026_212010/`

  Metadata field               Value
  ---------------------------- ------------------------------------
  Capture start wall time      `2026-10-26T21:20:10.179104+05:30`
  Requested capture duration   60 s
  Recorded elapsed time        60.265967 s
  Host clock                   `time.monotonic_ns`
  RGB samples                  836
  Depth samples                865
  RAW_IMU samples              3,007
  IMU capture error            None recorded

The metadata describes concurrent arrival-time logging and does not
claim hardware exposure synchronization or a calibrated clock
offset/drift.

### 7.4 Camera timestamp integrity

  Metric                               RGB         Depth
  -------------------------- ------------- -------------
  Samples                              836           865
  Header timestamp elapsed     60.048716 s   59.981996 s
  Effective observed rate       13.9054 Hz    14.4043 Hz
  Median header interval        66.7212 ms    66.7212 ms
  Maximum header interval      333.6067 ms   333.5662 ms
  Duplicate timestamps                   0             0
  Timestamp regressions                  0             0
  Sample-index jumps                     0             0

Assessment:

-   Timestamp monotonicity: PASS.
-   Duplicate/regression screening: PASS.
-   Nominal 30 Hz camera rate: NOT DEMONSTRATED in this dataset.
-   Continuity and provenance: CONDITIONAL.

The observed rates are materially below the 30 Hz nominal target. The
cause is not established by the timing CSV alone. Continuous sample
indices do not prove that every expected physical camera frame was
delivered.

### 7.5 IMU timestamp integrity

  Metric                                   Result
  --------------------------------- -------------
  Samples                                   3,007
  Effective sensor timestamp rate     50.00005 Hz
  Sensor timestamp elapsed            60.119942 s
  Median sensor interval                20.003 ms
  Minimum sensor interval               19.273 ms
  Maximum sensor interval               20.713 ms
  Sensor intervals above 30 ms                  0
  Sensor timestamp duplicates                   0
  Sensor timestamp regressions                  0
  Host receive timestamp elapsed      60.085710 s
  Host receive effective rate         50.02853 Hz

Assessment:

-   Sensor timestamp monotonicity: PASS.
-   Duplicate/regression screening: PASS.
-   Observed sensor cadence: consistent with nominal 50 Hz.
-   Formal cadence acceptance: CONDITIONAL because application-specific
    tolerance limits have not been defined.
-   Clock provenance: NOT DEMONSTRATED.

The 30 ms interval threshold was a dataset anomaly-screening threshold,
not a formally approved operational maximum-gap requirement.

### 7.6 Cross-sensor host timestamp overlap

  Stream     First host timestamp (ns)   Last host timestamp (ns)          Span
  -------- --------------------------- -------------------------- -------------
  RGB                    9676743944800              9736792649728   60.048705 s
  Depth                  9676745483040              9736727375712   59.981893 s
  IMU                    9676724473536              9736810183232   60.085710 s

Common host timestamp interval: **59.981893 seconds**.

Assessment: PASS for overlapping logged host-arrival intervals. This
does not establish physical measurement-time synchronization.

### 7.7 RGB--Depth software association

The October 26 SM-02B association report used `header_stamp_ns`, a 10.0
ms tolerance, and monotonic one-to-one association.

  Metric                                                Result
  ---------------------------------------------- -------------
  RGB frames                                               836
  Depth frames                                             865
  Accepted pairs                                           821
  Unmatched RGB                                             15
  Unmatched Depth                                           44
  Median absolute header timestamp difference      0.065186 ms
  P95 absolute header timestamp difference         0.066162 ms
  Maximum absolute header timestamp difference     0.066163 ms
  All accepted pairs within tolerance                     True

Assessment: PASS for the existing software header-timestamp association.

This is not proof of physical exposure synchronization. The report
explicitly states that hardware exposure synchronization is not proven
and timestamp clock-domain and exposure-time semantics are not
established.

**Historical-report distinction:** Another historical association report
records 821 pairs, 10 unmatched RGB frames, 50 unmatched Depth frames, a
16.667 ms tolerance and approximately 0.0659 ms median difference. Those
figures belong to a different historical report/capture context and must
not be substituted for the October 26 `20261026_212010` results above.

## 8. Consolidated SM-B acceptance matrix

  -----------------------------------------------------------------------
  Requirement             Final classification    Basis
  ----------------------- ----------------------- -----------------------
  Camera timestamp        Completed with          Fields and recording
  provenance              limitations             path identified; active
  investigation                                   domain and exposure
                                                  semantics unresolved

  IMU timestamp           Completed with          MAVLink field and
  provenance              limitations             software path
  investigation                                   identified; actual
                                                  clock origin unresolved

  Clock-domain            Completed with          Comparisons and
  investigation           limitations             limitations documented;
                                                  calibrated mappings
                                                  absent

  Camera--IMU temporal    Completed with          Host-arrival
  investigation           limitations             relationship
                                                  characterized; physical
                                                  measurement-time
                                                  relationship absent

  Camera timestamp        PASS                    No duplicates or
  monotonicity                                    regressions in reviewed
                                                  dataset

  Camera nominal 30 Hz    NOT DEMONSTRATED        October 26 observed
  cadence                                         rates approximately
                                                  13.9--14.4 Hz

  IMU timestamp           PASS                    No duplicates or
  monotonicity                                    regressions in reviewed
                                                  dataset

  IMU nominal cadence     CONDITIONAL             Approximately 50 Hz
                                                  observed; formal
                                                  tolerance not
                                                  established

  Concurrent host-arrival PASS                    Common host timestamp
  logging                                         interval of 59.981893 s

  RGB--Depth software     PASS                    821 accepted pairs
  association                                     within 10 ms tolerance

  Physical camera--IMU    NOT DEMONSTRATED        No verified
  synchronization                                 measurement-time
                                                  reference or hardware
                                                  synchronization
                                                  evidence

  Calibrated clock offset NOT DEMONSTRATED        No independently
  and drift                                       validated clock mapping

  Overall SM-B            CONDITIONAL             Evidence review
                                                  complete; physical
                                                  synchronization
                                                  objective remains open
  -----------------------------------------------------------------------

## 9. Online camera--IMU synchronization: objective and limitations

### 9.1 Meaning of online synchronization

For this project, online synchronization means maintaining a defensible
temporal relationship between camera and IMU measurements while data is
being acquired, rather than relying only on post-capture analysis.

A valid online synchronization claim must distinguish:

1.  **Timestamp interpretation:** knowing what event each timestamp
    represents and which clock produced it.
2.  **Clock relationship estimation:** characterizing the relationship
    between sensor clocks and the system time reference, including
    offset, relative rate and uncertainty.
3.  **Measurement-time alignment:** associating camera and IMU
    measurements according to their physical measurement times, with
    known residual uncertainty.

A software synchronizer or approximate-time message filter can associate
messages. It cannot, by itself, correct unknown timestamp semantics or
prove that the underlying sensors measured at those times.

### 9.2 Current blockers to an online synchronization claim

  ---------------------------------------------------------------------------
  Limitation              Current evidence /          Why it matters online
                          condition                   
  ----------------------- --------------------------- -----------------------
  Camera timestamp domain SDK domains reviewed, but   Camera timestamp cannot
  unknown for historical  active capture domain not   yet be safely
  capture                 verified                    interpreted as a known
                                                      host or hardware-clock
                                                      time

  Camera exposure-time    Exact event represented by  Frame delivery time may
  semantics unknown       header timestamp unverified differ from physical
                                                      exposure time

  Strix `time_usec`       Epoch-versus-boot           IMU sensor clock cannot
  origin unknown          interpretation unconfirmed  yet be mapped
                                                      unambiguously to host
                                                      time

  ROS IMU stamp differs   Reviewed publisher assigns  Downstream consumers
  from source sensor time ROS clock `now()` rather    may see publication
                          than copying                time rather than
                          `RAW_IMU.time_usec`         original measurement
                                                      time

  Different timestamp     Camera callback entry and   Their difference
  event semantics         IMU receive return are      includes transport and
                          software arrival events     scheduling delay

  Clock offset not        No independently validated  A fixed timestamp
  calibrated              mapping                     difference cannot be
                                                      treated as a
                                                      measurement-time
                                                      correction

  Clock drift not         No validated relative       A one-time offset may
  calibrated              clock-rate estimate         become inaccurate over
                                                      longer operation

  Transport and           Host arrival observations   Arrival-time matching
  scheduling latency      include variable delay      can vary even if sensor
                                                      measurement timing is
                                                      stable

  Camera cadence          October 26 dataset shows    Online association may
  inconsistency           approximately 14 Hz rather  encounter irregular
                          than 30 Hz                  camera updates and
                                                      longer gaps

  Historical IMU          Earlier captures contain    Monotonicity-only
  timestamp               very large positive sensor  checks can miss severe
  discontinuities         timestamp intervals         discontinuities

  No physical             No independent              Online software
  synchronization         exposure/measurement-time   association cannot be
  evidence                reference supplied          accepted as physical
                                                      synchronization

  No formal               Application-specific        No defensible numerical
  residual-error budget   maximum timing error and    threshold for online
                          uncertainty limits not      acceptance
                          established                 

  No repeatability        Current result based on     Stability across
  evidence                existing captures and       sessions, restarts and
                          records                     operating duration is
                                                      not established
  ---------------------------------------------------------------------------

### 9.3 Online estimator limitations

An online temporal estimator may estimate a residual time shift from
sensor observations, but that estimate is meaningful only if input
timestamps and measurement events are sufficiently well-defined.

Constraints for any future engineering assessment include:

-   **Observability:** data must contain enough temporal information to
    distinguish a time shift from other model errors.
-   **Motion and scene dependence:** visual and inertial observations
    may not provide equally informative timing constraints in every
    scene or motion condition.
-   **Initialization:** an estimator may require a sufficiently accurate
    initial clock relationship to associate data meaningfully.
-   **Time-varying offset:** a constant offset model may not represent
    relative clock drift.
-   **Latency versus offset ambiguity:** variable transport and
    processing latency can contaminate estimates based on arrival times.
-   **Timestamp semantic errors:** an estimator cannot automatically
    determine whether a timestamp represents exposure start, exposure
    midpoint, frame delivery or another event.
-   **Estimator convergence:** an available numerical estimate does not
    prove convergence to the physical measurement-time offset.
-   **Uncertainty reporting:** a timing estimate without uncertainty,
    validity state and supporting evidence is insufficient for
    acceptance.
-   **Loss and discontinuity handling:** missing frames, stale messages,
    timestamp jumps and stream restarts can invalidate a previously
    estimated relationship.
-   **Independent validation:** an online estimate must be checked
    against independent evidence; self-consistency within one estimator
    is not independent proof.

These are assessment constraints, not evidence that a particular
estimator has been implemented or validated on this hardware.

### 9.4 Online temporal calibration is not hardware synchronization

  -----------------------------------------------------------------------
  Concept                 What it can establish   What it does not
                                                  establish by itself
  ----------------------- ----------------------- -----------------------
  Software message        Which messages are      Physical
  association             paired by supplied      exposure/measurement
                          timestamps              simultaneity

  Common host clock       Common reference for    Sensor clock alignment
  timestamps              software-observed       or measurement-time
                          events, if verified     alignment

  Clock mapping           Relationship between    Correct
                          clock readings, if      measurement-event
                          calibrated              semantics

  Online temporal offset  Estimated residual      Hardware trigger
  estimation              temporal parameter      synchronization or
                          under estimator         independently verified
                          assumptions             timing

  Hardware                Physical timing         Correct downstream
  synchronization         relationship supported  timestamp propagation
                          by hardware and         unless separately
                          measurement evidence    verified
  -----------------------------------------------------------------------

### 9.5 Research reference applicability

The reviewed reference, *Online Temporal Calibration for Monocular
Visual-Inertial Systems* (Qin & Shen, 2018), may be retained as
background for future temporal-calibration assessment.

The reviewed RealSense experiment used a ZR300 integrated camera--IMU
arrangement. This project uses a D455 and a separate Strix IMU.
Experimental results from the paper must not be transferred directly to
this hardware configuration.

The method does not resolve the present timestamp-provenance and
clock-domain questions. An online VIO temporal estimator is a possible
future estimator approach, not proof that the current system is
synchronized.

### 9.6 Evidence required before an online synchronization claim

A future engineering acceptance assessment would need evidence for:

-   Verified timestamp source and measurement-event semantics for each
    sensor.
-   Verified interpretation of Strix `RAW_IMU.time_usec`.
-   Defensible common-time relationship or calibrated clock mapping.
-   Transport/arrival latency characterized separately from
    measurement-time offset.
-   Defined allowable timing error, jitter, gap and uncertainty
    requirements.
-   Documented validity state for the synchronization estimate.
-   Detection and handling of stale data, dropped data, timestamp
    discontinuities and restarts.
-   Independent evidence of residual measurement-time alignment.
-   Repeatability across separate captures and operating sessions.

No numerical acceptance thresholds are invented here. They must be
defined and approved by the project against its intended
sensor-processing requirements.

## 10. Historical observations and unresolved anomalies

### 10.1 D455 rate variation across captures

  Capture               Requested rate   RGB observed rate   Depth observed rate
  ------------------- ---------------- ------------------- ---------------------
  `20261026_203917`              30 Hz            29.32 Hz             29.337 Hz
  `20261026_211906`              30 Hz           14.988 Hz             14.988 Hz
  `20261026_212010`              30 Hz          13.9054 Hz            14.4043 Hz

The difference between captures is significant. The approximately 15 Hz
observations have not been explained by the timing evidence alone.

### 10.2 Strix IMU historical timestamp discontinuities

  Capture               Samples   Median sensor interval   Maximum sensor interval
  ------------------- --------- ------------------------ -------------------------
  `20261026_203459`       3,107                20.002 ms          4,360,320.105 ms
  `20261026_211803`       3,109                19.997 ms          4,810,717.405 ms

Historical records report very large positive sensor timestamp
intervals, while host arrival intervals were substantially more regular.
The cause of these sensor timestamp discontinuities remains unknown.

**Key finding:** Monotonic timestamps do not necessarily imply
continuous or reliable timing. A stream can remain monotonic while
containing a very large positive gap.

These historical anomalies remain part of the limitation register and
must not be silently replaced by the cleaner October 26
`20261026_212010` result.

## 11. Limitations register

  -----------------------------------------------------------------------------
  ID                Limitation             Impact             Disposition
  ----------------- ---------------------- ------------------ -----------------
  SM-B-L01          Active D455 timestamp  Camera clock       Open
                    domain for historical  interpretation     
                    capture unverified     uncertain          

  SM-B-L02          Camera exposure-time   Physical frame     Open
                    semantics unverified   measurement time   
                                           uncertain          

  SM-B-L03          Strix `time_usec`      IMU clock          Open
                    origin unverified      interpretation     
                                           uncertain          

  SM-B-L04          ROS IMU publication    Downstream         Documented;
                    timestamp does not     timestamp may      source-time
                    directly preserve      represent          provenance open
                    `RAW_IMU.time_usec`    publication time   

  SM-B-L05          Camera-to-host clock   Camera time cannot Open
                    mapping absent         be calibrated to   
                                           host time          

  SM-B-L06          Strix-to-host clock    IMU time cannot be Open
                    mapping absent         calibrated to host 
                                           time               

  SM-B-L07          Relative clock offset  Cross-sensor       Open
                    and drift uncalibrated measurement-time   
                                           relationship       
                                           uncertain          

  SM-B-L08          Host arrival times     Arrival-time       Documented
                    include                differences are    
                    software/transport     not physical       
                    delay                  offsets            

  SM-B-L09          D455 observed rate     Nominal camera     Open
                    below 30 Hz in two     cadence not        
                    reviewed captures      consistently       
                                           demonstrated       

  SM-B-L10          Historical IMU         Long-term timing   Open
                    timestamp              reliability        
                    discontinuities        uncertain          
                    unexplained                               

  SM-B-L11          Application-specific   Formal numerical   Open
                    timing tolerances not  acceptance         
                    finalized              incomplete         

  SM-B-L12          No independent         Physical           Open
                    physical camera--IMU   synchronization    
                    timing evidence        cannot be accepted 

  SM-B-L13          Online estimator       No online          Not demonstrated
                    behaviour and          synchronization    
                    uncertainty not        performance claim  
                    validated on this                         
                    configuration                             

  SM-B-L14          Repeatability across   Operational        Not demonstrated
                    sessions not           consistency        
                    established            unknown            
  -----------------------------------------------------------------------------

## 12. Final deliverables register

  --------------------------------------------------------------------------------------------------------------
  Deliverable                                                    Description             Status
  -------------------------------------------------------------- ----------------------- -----------------------
  `SM_B4_1_RealSense_Timestamp_Provenance.md`                    Camera timestamp source Evidence reviewed;
                                                                 and recording-path      limitations retained
                                                                 investigation           

  `SM_B4_2_Strix_RAW_IMU_Timestamp_Provenance.md`                Strix timestamp source  Evidence reviewed;
                                                                 and recording-path      limitations retained
                                                                 investigation           

  `SM_B4_3_Clock_Domain_Relationship.md`                         Clock-domain evidence,  Completed
                                                                 comparisons and         
                                                                 limitations             

  `SM_B4_4_Calibration_Applicability_and_Limitations.md`         Temporal-calibration    Completed
                                                                 applicability and       
                                                                 limitations             

  `SM_B4_4_5_Final_Camera_IMU_Temporal_Relationship_Record.md`   Camera--IMU temporal    Completed
                                                                 relationship record     

  `SM_B4_5_1_Synchronization_Requirements.md`                    Requirements and        Completed
                                                                 acceptance criteria     

  `SM_B4_5_2_Camera_Timestamp_Integrity.md`                      Camera integrity        Completed ---
                                                                 evidence                conditional

  `SM_B4_5_3_IMU_Timestamp_Integrity.md`                         IMU integrity evidence  Completed ---
                                                                                         conditional

  `SM_B4_5_4_Cross_Sensor_Synchronization_Evidence.md`           Cross-sensor evidence   Completed ---
                                                                                         conditional

  `SM_B4_5_Synchronization_Acceptance_Report.md`                 Consolidated acceptance Completed ---
                                                                 decision                conditional
  --------------------------------------------------------------------------------------------------------------

This register records deliverables and their review status. It does not
assert that every file has been independently archived or verified at a
particular filesystem path.

## 13. Final engineering conclusion

### 13.1 Established

-   D455 camera timestamp fields and recording path reviewed.
-   Strix `RAW_IMU.time_usec`, host receive timestamp and ROS
    publication behaviour reviewed.
-   Sensor timestamps distinguished from host arrival timestamps.
-   Historical per-stream timing behaviour, monotonicity, intervals and
    anomalies characterized.
-   October 26 dataset demonstrates concurrent host-arrival logging over
    a common interval.
-   Existing October 26 RGB--Depth software association reviewed.
-   Camera--IMU host-arrival comparisons quantified.
-   Clock-domain, measurement-time and online synchronization
    limitations documented.
-   B4.5 evidence review and conditional acceptance documentation
    completed.

### 13.2 Not demonstrated

-   Verified physical D455 exposure-time provenance.
-   Verified physical Strix IMU measurement-time provenance.
-   Calibrated camera-to-host and Strix-to-host clock mappings.
-   Calibrated camera--IMU clock offset and drift.
-   Validated physical camera--IMU measurement-time alignment.
-   Hardware exposure synchronization between D455 and Strix.
-   Validated online temporal synchronization on the selected hardware.
-   Repeatable synchronization performance against approved numerical
    timing tolerances.

### 13.3 Final disposition

**SM-B --- Timing and Synchronization: PARTIALLY ESTABLISHED.**

**Evidence-review status: COMPLETE.**

**B4.5 status: COMPLETE --- CONDITIONAL ACCEPTANCE.**

**Physical camera--IMU synchronization: NOT DEMONSTRATED.**

The engineering objective of verified real-hardware camera--IMU
synchronization remains **OPEN**. The system must not be described as
physically synchronized or online-synchronization validated on the basis
of current evidence.

The next project workstream should follow the approved Sensor Management
Plan (SM-C --- Sensor Calibration and Coordinates). Unresolved SM-B
synchronization requirements must remain visible in the project-level
open-requirements register and must not be treated as closed merely
because the evidence-review package is complete.

## 14. Evidence interpretation rules

1.  Do not describe host callback or receive timestamps as physical
    sensor measurement timestamps.
2.  Do not interpret timestamp monotonicity as proof of continuous
    sampling.
3.  Do not interpret RGB--Depth software association as hardware
    exposure synchronization.
4.  Do not interpret nearest-neighbour camera--IMU arrival differences
    as physical temporal offsets.
5.  Do not claim calibrated clock offset or drift without a validated
    clock mapping and uncertainty.
6.  Do not claim online synchronization merely because an online
    estimator outputs a time-shift estimate.
7.  Keep historical captures and their distinct association
    tolerances/results separate.
8.  Preserve unknowns as unknown; do not fill missing evidence with
    assumptions.
9.  Keep evidence-review completion separate from implementation and
    physical validation.
10. Update the acceptance disposition only when new, traceable evidence
    supports the changed claim.

**End of SM-B engineering record.**