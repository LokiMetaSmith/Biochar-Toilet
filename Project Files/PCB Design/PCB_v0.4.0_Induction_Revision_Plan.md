# Bio-Char Control Board v0.4.0 — Hardware Revision Roadmap

**Dedicated Hardware Modifications for Phase 2/3 Dual Induction & Closed-Loop Control**

---

## 📋 Revision Objectives

The current Control Board v0.3.0 supports single-thermocouple SPI sensing and basic dual SSR switching. To support dual independent temperature control (vessel + catalytic converter) and closed-loop liquid recirculation, Control Board v0.4.0 will introduce dedicated hardware routing modifications.

---

## 🛠️ Required Hardware Changes

### 1. Dual Thermocouple SPI Interface (Catalyst & Vessel Sensing)
- **New Feature:** Second MAX31855 SPI Chip Select line on **GPIO6**.
- **Bus Sharing:** Shares SPI CLK (**GPIO0**) and SPI MISO (**GPIO2**) with the primary vessel MAX31855 breakout.
- **Pin Assignment:**
  - `GPIO0`: MAX31855 SPI CLK (Shared)
  - `GPIO1`: MAX31855 CS1 (Vessel Thermocouple)
  - `GPIO2`: MAX31855 MISO (Shared)
  - `GPIO6`: MAX31855 CS2 (Catalytic Converter Thermocouple)

### 2. High-Current Recirculating Pump MOSFET Driver
- **Upgrade:** Dedicated high-current N-channel MOSFET driver (IRLB3813PBF or higher current rating) with flyback protection diode on **GPIO11**.
- **Connector:** Dedicated 2-position Phoenix 5.08mm terminal block for high-duty heat exchanger recirculating pump.

### 3. Closed-Loop Fluid Flow Sensor Header
- **New Connector:** 3-pin 2.54mm header / Phoenix terminal.
- **Signals:**
  - Pin 1: `+3.3V` / `+5V` Power
  - Pin 2: `GND`
  - Pin 3: `FLOW_SENSE` Signal (GPIO input with 10kΩ pull-up resistor and noise filter capacitor).

---

## 📂 Related Files & Documentation

- Current Board Schematic & Specs: [`Project Files/PCB Design/Control Board.md`](Control%20Board.md)
- Induction Firmware Location: [`Project Files/Induction Heating Prototype/Firmware`](../Induction%20Heating%20Prototype/Firmware)
