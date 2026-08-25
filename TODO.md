# Project Tasks

Based on `README.md` and `DESIGN_IDEAS.md`.

- [x] Implement Valve Controller logic (to address the "small bug controlling the valve").
- [x] Create dedicated ESP32-H2 firmware for Dual Induction Heating Prototype (`Project Files/Induction Heating Prototype/Firmware`).
- [x] Enhance `dryness_monitor.py` with EMA noise filtering & temperature slope thresholding for low-moisture samples.
- [ ] Implement Heater Controller (mentioned as a future step).
- [ ] Design reaction vessel (ongoing).
- [ ] Implement emergency pop-off valve safety logic.

### Hardware Roadmap
- [ ] Implement PCB v0.4.0 Revision Plan (Dual MAX31855 SPI thermocouples, high-current pump driver, fluid flow sensor header — see [`PCB_v0.4.0_Induction_Revision_Plan.md`](Project%20Files/PCB%20Design/PCB_v0.4.0_Induction_Revision_Plan.md)).

### Testing and Benchmarking Improvements
- [x] Fix lazy test `test_cooling_or_steady_temp` in `test_dryness_monitor.py` which only tests slow temperature rise instead of actual cooling (temperature dropping).
- [x] Fix lazy test `test_threshold_crossing` in `test_valve_controller.py` which only tests the boundary value exactly, instead of a true threshold crossing (transition from below to above threshold).
- [x] Add tests simulating noisy and high-frequency sensor data for `dryness_monitor.py` (rate calculation is highly sensitive to window size).
- [x] Develop tests and benchmarks for low-moisture samples (like the bread charring experiment) where the dryness algorithm failed to trigger due to lack of distinct pressure change.


Safety considerations:

We need to identify a safe opening temperature that we can open the lid

We should examine the component mix of materials safety, in addition at different temperatures and pressure, since our dynamic system covers a lot of different regions. 

We should consider opening the valve before the lid, allowing air into the system. 

We should wear PPE, respirator, eye protection, and heat resistant gloves. 

### Presentation Improvements
- [ ] Develop a snappy script for the presentation to keep the narrative engaging.
- [ ] Add story narrative slides to the presentation covering:
  - How the team conceived of the project.
  - The heat transfer difficulty discovered during Hardhik's experiment.
  - Lawrence's invention of the induction approach.
  - Progress and difficulties with charring things.
