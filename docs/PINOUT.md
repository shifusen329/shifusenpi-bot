# Freenove Hexapod Robot - GPIO Pinout

## Connector Information

**Mainboard Connector**: 2x10 female header (20 pins)
**Raspberry Pi Connector**: Uses first 20 pins of 40-pin GPIO header

## GPIO Pin Usage (from Code Analysis)

| Function | GPIO Pin | Physical Pin | Notes |
|----------|----------|--------------|-------|
| **Buzzer** | GPIO 17 | Pin 11 | Digital output |
| **Servo Power Control** | GPIO 4 | Pin 7 | Controls servo power enable/disable |
| **Ultrasonic Trigger** | GPIO 27 | Pin 13 | HC-SR04 trigger |
| **Ultrasonic Echo** | GPIO 22 | Pin 15 | HC-SR04 echo |
| **I2C SDA** | GPIO 2 | Pin 3 | PCA9685, MPU6050, ADS7830 |
| **I2C SCL** | GPIO 3 | Pin 5 | PCA9685, MPU6050, ADS7830 |
| **LED Control (V2)** | GPIO 10 | Pin 19 | SPI MOSI for WS281X |
| **Power - 5V** | - | Pin 2, 4 | Servo/logic power |
| **Power - 3.3V** | - | Pin 1, 17 | Logic power |
| **Ground** | - | Pin 6, 9, 14, 20 | Common ground |

## I2C Device Addresses

| Device | I2C Address | Purpose |
|--------|-------------|---------|
| PCA9685 #1 | 0x40 | Servo driver (16 channels) |
| PCA9685 #2 | 0x41 | Servo driver (16 channels) |
| MPU6050 | 0x68 | IMU sensor |
| ADS7830 | 0x48 | ADC for battery voltage |

## 2x10 Connector Pinout (First 20 pins of RPi GPIO)

```
PI-GPIO Connector (looking at connector on PCB)

    Pin 1  ●  ● Pin 2        3.3V      ●  ● 5V
    Pin 3  ●  ● Pin 4        GPIO2/SDA ●  ● 5V
    Pin 5  ●  ● Pin 6        GPIO3/SCL ●  ● GND
    Pin 7  ●  ● Pin 8        GPIO4     ●  ● GPIO14/TXD
    Pin 9  ●  ● Pin 10       GND       ●  ● GPIO15/RXD
    Pin 11 ●  ● Pin 12       GPIO17    ●  ● GPIO18
    Pin 13 ●  ● Pin 14       GPIO27    ●  ● GND
    Pin 15 ●  ● Pin 16       GPIO22    ●  ● GPIO23
    Pin 17 ●  ● Pin 18       3.3V      ●  ● GPIO24
    Pin 19 ●  ● Pin 20       GPIO10    ●  ● GND
```

## Used Pins Summary

**Total GPIO used by Freenove board**: 6 pins
- GPIO 2, 3, 4, 10, 17, 22, 27

**Total physical pins used**: 20 (2x10 connector)
- Includes power and ground

## Available GPIO on Hailo HAT+ Pass-Through

The Hailo AI HAT+ will pass through all 40 GPIO pins on its top header.

**Pins 21-40 are completely unused** by the Freenove connector and available for:
- Additional sensors
- LEDs
- Buttons
- Camera (CSI via dedicated connector)
- Other peripherals

## Connection Solution: 2x10 Dupont Cable

### Simple Wiring
```
Raspberry Pi 5 (40-pin GPIO)
    ↓
Hailo AI HAT+ (installs on all 40 pins)
    ↓ (passes through to top)
2x10 female-to-female dupont cable
    ↓
Freenove mainboard (2x10 connector)
```

### Pin Mapping
Connect dupont cable from:
- **Hailo HAT+ pins 1-20** → **Freenove connector pins 1-20**

It's a straight 1:1 connection.

## References

Pin definitions extracted from:
- `Code/Server/buzzer.py` - GPIO 17
- `Code/Server/control.py` - GPIO 4 (servo power)
- `Code/Server/ultrasonic.py` - GPIO 27, 22
- I2C devices on GPIO 2, 3 (standard I2C pins)

---

**Last Updated**: 2025-10-25
**Hardware**: Freenove Big Hexapod Robot Kit V2.0
**Connector**: 2x10 female header on mainboard
