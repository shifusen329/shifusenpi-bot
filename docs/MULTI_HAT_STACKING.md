# Multi-HAT Stacking Solution
## Raspberry Pi 5 + Hailo AI HAT+ + WM8960 Audio HAT + Freenove Mainboard

## The Problem

You have **4 devices** competing for GPIO:

```
Raspberry Pi 5 (40-pin GPIO)
    ↓ ??? How to connect all three? ???
    ├─ Hailo AI HAT+ (26 TOPS) - needs PCIe + GPIO pass-through
    ├─ WM8960 Audio HAT - needs I2C + I2S
    └─ Freenove Mainboard - needs GPIO 2,3,4,10,17,22,27
```

## Pin Usage Analysis

### Freenove Mainboard (from code)
- **GPIO 2** - I2C SDA (PCA9685, MPU6050, ADS7830)
- **GPIO 3** - I2C SCL
- **GPIO 4** - Servo power control
- **GPIO 10** - LED control (SPI MOSI)
- **GPIO 17** - Buzzer
- **GPIO 22** - Ultrasonic echo
- **GPIO 27** - Ultrasonic trigger
- **Power/GND** - 5V, 3.3V, GND

### WM8960 Audio HAT (typical)
- **GPIO 2** - I2C SDA (WM8960 control) ⚠️ **CONFLICT**
- **GPIO 3** - I2C SCL (WM8960 control) ⚠️ **CONFLICT**
- **GPIO 18** - I2S PCM_CLK (bit clock)
- **GPIO 19** - I2S PCM_FS (frame sync/LR clock)
- **GPIO 20** - I2S PCM_DIN (data in)
- **GPIO 21** - I2S PCM_DOUT (data out)

### Hailo AI HAT+ (26 TOPS)
- **PCIe** - Primary data (separate connector)
- **GPIO** - Mostly pass-through, minimal usage
- Possibly I2C for config (shares bus)

## I2C Conflict Resolution ✅

**Good news**: I2C is a **shared bus**! Multiple devices can coexist if they have different addresses.

| Device | I2C Address | Bus |
|--------|-------------|-----|
| PCA9685 #1 | 0x40 | I2C-1 |
| PCA9685 #2 | 0x41 | I2C-1 |
| MPU6050 | 0x68 | I2C-1 |
| ADS7830 | 0x48 | I2C-1 |
| **WM8960** | **0x1A** | I2C-1 |
| Hailo (if used) | 0x?? | I2C-1 |

**All different addresses = No conflict!** 🎉

## Stacking Solutions

### Option 1: Full HAT Stack with Stacking Headers (Cleanest)

**What you need:**
- 2x20 extra-tall stacking header (20-25mm) x2
- Total cost: ~$8-10

**Stack order (bottom to top):**
```
┌─────────────────────────┐
│  Freenove Mainboard     │ ← Connected via cable or top pins
└─────────────────────────┘
            ↑
      Dupont cable or direct connection
            ↑
┌─────────────────────────┐
│  WM8960 Audio HAT       │ ← Top of stack
│  (stacking header on    │
│   bottom)               │
├─────────────────────────┤
│  Tall Stacking Header   │ ← 20-25mm
├─────────────────────────┤
│  Hailo AI HAT+          │ ← Middle (passes through GPIO)
│  (stacking header on    │
│   bottom)               │
├─────────────────────────┤
│  Tall Stacking Header   │ ← 20-25mm
├─────────────────────────┤
│  Raspberry Pi 5         │ ← Base
└─────────────────────────┘
```

**Pros:**
- ✅ Clean, professional look
- ✅ All GPIO accessible at top
- ✅ Secure mechanical connection
- ✅ Easy to troubleshoot

**Cons:**
- ⚠️ Tall stack (~6-8cm)
- ⚠️ Requires soldering headers
- ⚠️ $8-10 cost

---

### Option 2: Side-by-Side with Ribbon Cable (Flexible)

**What you need:**
- 40-pin GPIO ribbon cable extender (15-20cm)
- Small breadboard or mounting plate
- Total cost: ~$8

**Layout:**
```
┌─────────────────┐      ┌──────────────┐      ┌────────────┐
│  Raspberry Pi 5 │─────▶│ Ribbon Cable │─────▶│ GPIO Split │
└─────────────────┘      │  Extender    │      │  Board     │
        ↓                └──────────────┘      └──────┬─────┘
┌─────────────────┐                                   │
│  Hailo AI HAT+  │                          ┌────────┼─────────┐
│  (on RPi5)      │                          │        │         │
└─────────────────┘                   ┌──────▼──┐  ┌─▼─────┐ ┌─▼─────────┐
                                      │ WM8960  │  │Freenove│ │ Expansion │
                                      │AudioHAT │  │ Board  │ │ (future)  │
                                      └─────────┘  └────────┘ └───────────┘
```

**Pros:**
- ✅ No height restriction
- ✅ Flexible component placement
- ✅ Easy access to all components
- ✅ No soldering

**Cons:**
- ⚠️ Messy with cables
- ⚠️ Potential signal integrity issues
- ⚠️ Not as mechanically stable

---

### Option 3: Hybrid - Hailo Direct + Audio/Freenove on Cable (RECOMMENDED)

**What you need:**
- 2x20 stacking header (15-20mm) x1 - for Audio HAT
- 2x10 dupont cable - for Freenove
- Total cost: ~$6

**Setup:**
```
                    ┌─────────────────┐
                    │ Freenove Board  │ ← Off to side
                    └────────┬────────┘
                             │
                      2x10 Dupont cable
                             │
┌─────────────────┐          │
│ WM8960 Audio    │◀─────────┘ ← Plugs into stacking header
│ (on stacking    │
│  header)        │
├─────────────────┤
│ Stacking Header │ ← 15-20mm tall
├─────────────────┤
│ Hailo AI HAT+   │ ← Direct on RPi5
└─────────────────┘
        ↓
┌─────────────────┐
│ Raspberry Pi 5  │
└─────────────────┘
```

**Pros:**
- ✅ Moderate height (~4cm)
- ✅ Clean and organized
- ✅ Hailo gets solid PCIe connection
- ✅ Flexible Freenove placement
- ✅ Best cost/benefit

**Cons:**
- ⚠️ Requires soldering one stacking header to Hailo
- ⚠️ Audio HAT adds some height

---

## Pin Mapping for All Devices

### Complete GPIO Allocation

| GPIO | Freenove | WM8960 | Hailo | Available |
|------|----------|--------|-------|-----------|
| 2 | I2C SDA | I2C SDA | - | ⚠️ Shared bus (OK) |
| 3 | I2C SCL | I2C SCL | - | ⚠️ Shared bus (OK) |
| 4 | Servo PWR | - | - | Used |
| 10 | LED (SPI) | - | - | Used |
| 17 | Buzzer | - | - | Used |
| 18 | - | I2S CLK | - | Used (Audio) |
| 19 | - | I2S LRCK | - | Used (Audio) |
| 20 | - | I2S DIN | - | Used (Audio) |
| 21 | - | I2S DOUT | - | Used (Audio) |
| 22 | Ultrasonic Echo | - | - | Used |
| 27 | Ultrasonic Trig | - | - | Used |
| 5-9 | - | - | - | ✅ FREE |
| 11-16 | - | - | - | ✅ FREE |
| 23-26 | - | - | - | ✅ FREE |

**Total used**: 11 GPIO pins
**Total free**: 18+ GPIO pins for expansion! 🎉

---

## Installation Steps (Option 3 - Recommended)

### Step 1: Install Hailo AI HAT+
1. Solder 2x20 stacking header (15-20mm) to **TOP** of Hailo HAT+
2. Install Hailo HAT+ directly on Raspberry Pi 5 GPIO
3. Verify Hailo detected: `lspci | grep Hailo`

### Step 2: Install WM8960 Audio HAT
1. Plug WM8960 onto stacking header on top of Hailo
2. Test audio: `speaker-test -c2 -t wav`
3. Verify I2C: `i2cdetect -y 1` (should see 0x1A)

### Step 3: Connect Freenove
1. Get 2x10 female-to-female dupont cable
2. Connect from stacking header pins 1-20 to Freenove connector
3. Mount Freenove board off to side with standoffs

### Step 4: Test All Systems
```bash
# Test I2C devices
i2cdetect -y 1
# Should see: 0x1A (WM8960), 0x40, 0x41 (PCA9685), 0x48 (ADS7830), 0x68 (MPU6050)

# Test Hailo
lspci | grep Hailo

# Test audio
speaker-test -c2 -t wav

# Test robot
cd Code/Server
python3 test.py
```

---

## Potential Issues & Solutions

### Issue 1: I2C Bus Congestion
**Symptom**: Devices not responding or intermittent errors
**Solution**:
- Add I2C pull-up resistors (4.7kΩ on SDA/SCL)
- Reduce I2C clock speed in `/boot/firmware/config.txt`:
  ```
  dtparam=i2c_arm_baudrate=100000
  ```

### Issue 2: Power Draw Too High
**Symptom**: Devices resetting or not powering on
**Solution**:
- Use official RPi5 power supply (5V/5A minimum)
- Consider external power for servos (already implemented via GPIO 4 control)

### Issue 3: Audio Interference
**Symptom**: Noise in audio output when servos moving
**Solution**:
- Add filtering capacitors to servo power
- Use shielded audio cables
- Separate ground planes if possible

### Issue 4: Height Constraints
**Symptom**: Stack too tall for robot chassis
**Solution**:
- Switch to Option 2 (side-by-side ribbon cable)
- Use right-angle headers
- Modify chassis mounting

---

## Shopping List

### Option 3 (Recommended) - ~$6
- [ ] 2x20 Extra-Tall Stacking Header (15-20mm) - $4
  - Adafruit #1979 or equivalent
- [ ] 2x10 Female-to-Female Dupont Cable (10-15cm) - $2
  - Amazon/eBay generic

### Optional Accessories
- [ ] I2C Pull-up Resistors (4.7kΩ) - $1
- [ ] Mounting standoffs M2.5 - $3
- [ ] Nylon screws/nuts - $2

---

## Final Stack Height

**Option 3 Total Height:**
- Raspberry Pi 5: 20mm
- Hailo AI HAT+: 10mm
- Stacking Header: 15-20mm
- WM8960 Audio HAT: 10mm
- **Total: ~55-60mm (5.5-6cm)**

Plus Freenove board off to side via cable.

---

## Testing Checklist

After assembly:

- [ ] Hailo detected: `lspci | grep Hailo`
- [ ] I2C devices detected: `i2cdetect -y 1`
  - [ ] 0x1A (WM8960)
  - [ ] 0x40 (PCA9685 #1)
  - [ ] 0x41 (PCA9685 #2)
  - [ ] 0x48 (ADS7830)
  - [ ] 0x68 (MPU6050)
- [ ] Audio playback works
- [ ] Audio recording works
- [ ] Servos respond
- [ ] Ultrasonic sensor reads
- [ ] Buzzer sounds
- [ ] LEDs light up
- [ ] All vision systems operational

---

## Conclusion

**You CAN stack all three!** The key is:
1. I2C bus sharing (all different addresses)
2. Proper stacking order (Hailo→Audio→Freenove via cable)
3. Adequate power supply (5V/5A minimum)

**Recommended**: Option 3 - Hybrid approach with Hailo direct + Audio on stacking header + Freenove on cable.

---

**Status**: Multi-HAT solution designed ✅
**Next**: Order stacking header + dupont cable (~$6)
**ETA**: 5-10 days for parts + 30 min assembly
