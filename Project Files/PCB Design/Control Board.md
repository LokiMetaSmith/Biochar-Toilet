# Bio-Char Control Board v0.3.0

**ESP32-H2 Based Industrial Control System for Bio-Char Production**

---

## 📋 Overview

The Bio-Char Control Board is an industrial-grade PCB designed to control and monitor bio-char production processes. It features WiFi/Bluetooth connectivity, multi-voltage power management, high-power output control, and sensor interfaces.

### Key Features
- **ESP32-H2 Microcontroller** - WiFi 802.11n + Bluetooth 5.2
- **Multi-Voltage Power System** - 12V input, regulated 5V and 3.3V rails
- **High-Power Output Control** - 2× Solenoid valves / MOSFET outputs, 2× SSR outputs
- **Sensor Interfaces** - K-type thermocouple, analog pressure sensor
- **Manual Override** - Physical switches for safety
- **Professional Design** - 2-layer PCB, through-hole components for easy assembly

---

## 🔧 Hardware Specifications

### Power Supply
- **Input:** 12V DC (via Phoenix terminal block)
- **5V Rail:** R-78E5.0-1.0 switching regulator (1A, 95% efficiency)
- **3.3V Rail:** ESP32-H2 internal LDO
- **Protection:** 2A PTC resettable fuse, reverse polarity protection

### Microcontroller
- **IC:** Espressif ESP32-H2-DEVKITM-1-N4
- **Connectivity:** WiFi 802.11b/g/n (2.4GHz), BLE 5.2, Thread/Zigbee capable
- **Flash:** 4MB
- **RAM:** 272KB SRAM
- **Processor:** RISC-V 96MHz

### Output Control
- **Solenoid Valves / High Current Outputs:** 2× IRLB3813PBF N-channel MOSFETs (30V, 100A, 2.3mΩ)
- **SSR Control:** 2× NPN transistor drivers (2N3904)
- **Protection:** Flyback diodes on all inductive loads

### Sensor Interfaces
- **Thermocouple:** MAX31855 breakout module (K-type, -200°C to +700°C, SPI)
- **Pressure Sensor:** Analog input with voltage divider (0-5V → 0-3.3V)

### Connectors
- **Phoenix Contact Terminals:** 5.08mm pitch, 90° horizontal
  - 1× 3-position (pressure sensor)
  - 5× 2-position (power input, solenoids, SSRs)
- **Pin Headers:** 2.54mm pitch
  - 1× 8-pin (general I/O)
  - 1× 6-pin (MAX31855 interface)

---

## 📦 Bill of Materials (BOM)

**Complete BOM available:** [`Bio_Char_BOM_Mouser_FINAL.xlsx`](Bio_Char_BOM_Mouser_FINAL.xlsx)

---

## 🔌 Pin Assignments & Firmware Variants

### 1. Original Conductive Heating Firmware Variant (`Project Files/Conductive Heating Prototype/Firmware`)

| GPIO | Function | Hardware Connection | Notes |
|------|----------|---------------------|-------|
| GPIO0 | MAX31855 CLK | SPI Clock | Thermocouple SPI |
| GPIO1 | MAX31855 CS | SPI Chip Select | Thermocouple SPI |
| GPIO2 | MAX31855 DO | SPI Data Out (MISO) | Thermocouple SPI |
| GPIO3 | ADC Pressure | ADC1_CH2 Input | 0–100 PSI Sensor via voltage divider |
| GPIO4 | SSR 1 Control | Q2 base → SSR 1 | Main Resistance Heater |
| GPIO5 | SSR 2 Control | Q5 base → SSR 2 | Reserved / Secondary |
| GPIO10 | Solenoid 1 Control | Q1 MOSFET Driver | Main Vent Valve 1 |
| GPIO11 | Solenoid 2 Control | Q3 MOSFET Driver | Reserved / Valve 2 |

### 2. Dual Induction Heating Firmware Variant (`Project Files/Induction Heating Prototype/Firmware`)

| GPIO | Function | Hardware Connection | Notes |
|------|----------|---------------------|-------|
| GPIO0 | MAX31855 CLK | SPI Clock | Thermocouple SPI |
| GPIO1 | MAX31855 CS | SPI Chip Select | Thermocouple SPI |
| GPIO2 | MAX31855 DO | SPI Data Out (MISO) | Thermocouple SPI |
| GPIO3 | ADC Pressure | ADC1_CH2 Input | 0–15 PSI (0–5V) Sensor via voltage divider |
| GPIO4 | Main Coil Heater | Q2 base → SSR 1 | Main Vessel Induction Coil (PWM controlled) |
| GPIO5 | Catalyst Heater | Q5 base → SSR 2 | Catalytic Converter Induction Heater (Active during cycle) |
| GPIO10 | Solenoid 1 Control | Q1 MOSFET Driver | Main Vent Solenoid Valve 1 |
| GPIO11 | Recirculating Pump | Q3 MOSFET Driver | Water/Fluid Recirculating Pump (Feature flagged) |

*Note: GPIO8/9 are internally tied to the ESP32-H2 32 MHz crystal oscillator and cannot be used for general I/O. GPIO14/15 are reserved for the 32 kHz RTC crystal.*

---

## ⚡ Power Distribution

```
12V Input (J1)
  │
  ├─[F1: Polyfuse 2A]─┬─[D1: 1N4001RLG]─┬── +12V Rail (Solenoids, Pumps, SSR drivers)
  │                   │                  │
  │                   │                  └── [U3: R-78E5.0-1.0 Input] ──> 5V Rail
  │                   └─[C6: 47µF 25V]
  │
  └── ESP32 LDO ───> 3.3V Rail (Internal peripherals)
```

---

## 📂 Repository Structure

```
PCB Design/
├── Bio_Char_BOM_Mouser_FINAL.xlsx    # Bill of Materials
├── Control Board.kicad_sch            # Schematic
├── Control Board.kicad_pcb            # PCB Layout
├── Control Board.kicad_pro            # Project File
├── Control Board.md                   # This file
├── PCB_v0.4.0_Induction_Revision_Plan.md # Hardware Roadmap for v0.4.0
├── Gerber Files/                      # Manufacturing Files
└── Drill Files/                       # NC Drill Files
```
