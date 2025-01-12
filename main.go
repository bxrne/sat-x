package main

import (
	"fmt"
	"log"
	"periph.io/x/conn/v3/i2c"
	"periph.io/x/conn/v3/i2c/i2creg"
	"periph.io/x/host/v3"
	"time"
)

const (
	// BMP390 specific registers
	regChipID    = 0x00
	regErr       = 0x02
	regStatus    = 0x03
	regPressData = 0x04
	regTempData  = 0x07
	regPWRCtrl   = 0x1B
	regOSR       = 0x1C
	regODR       = 0x1D
	regConfig    = 0x1F
	regCmd       = 0x7E
)

type BMP390 struct {
	dev i2c.Dev
}

func writeReg(dev *i2c.Dev, reg, value uint8) error {
	n, err := dev.Write([]byte{reg, value})
	if err != nil {
		return fmt.Errorf("write failed: %v", err)
	}
	if n != 2 {
		return fmt.Errorf("write: expected 2 bytes written, got %d", n)
	}
	return nil
}

func NewBMP390(bus i2c.BusCloser) (*BMP390, error) {
	dev := &i2c.Dev{Bus: bus, Addr: 0x77}

	// Read error register first to check device state
	var errReg [1]byte
	if err := dev.Tx([]byte{regErr}, errReg[:]); err != nil {
		return nil, fmt.Errorf("failed to read error register: %v", err)
	}
	log.Printf("Error register value: 0x%02X", errReg[0])

	// Read chip ID
	var id [1]byte
	if err := dev.Tx([]byte{regChipID}, id[:]); err != nil {
		return nil, fmt.Errorf("failed to read chip ID: %v", err)
	}
	log.Printf("Chip ID: 0x%02X", id[0])

	// Soft reset the device
	if err := writeReg(dev, regCmd, 0xB6); err != nil {
		return nil, fmt.Errorf("reset failed: %v", err)
	}
	time.Sleep(20 * time.Millisecond)

	// Wait for power-up
	time.Sleep(10 * time.Millisecond)

	// Read status after reset
	var status [1]byte
	if err := dev.Tx([]byte{regStatus}, status[:]); err != nil {
		return nil, fmt.Errorf("failed to read status: %v", err)
	}
	log.Printf("Status after reset: 0x%02X", status[0])

	// Configure the sensor step by step with error checking
	steps := []struct {
		reg   uint8
		value uint8
		name  string
	}{
		{regPWRCtrl, 0x33, "power control"}, // Enable pressure and temp
		{regOSR, 0x03 | (0x02 << 3), "OSR"}, // Oversampling settings
		{regODR, 0x02, "ODR"},               // Output data rate
		{regConfig, 0x02, "config"},         // IIR filter settings
	}

	for _, step := range steps {
		if err := writeReg(dev, step.reg, step.value); err != nil {
			return nil, fmt.Errorf("failed to set %s: %v", step.name, err)
		}
		time.Sleep(5 * time.Millisecond)

		// Verify write
		var readback [1]byte
		if err := dev.Tx([]byte{step.reg}, readback[:]); err != nil {
			return nil, fmt.Errorf("failed to verify %s: %v", step.name, err)
		}
		if readback[0] != step.value {
			return nil, fmt.Errorf("%s verification failed: wrote 0x%02X, read 0x%02X",
				step.name, step.value, readback[0])
		}
		log.Printf("Successfully configured %s", step.name)
	}

	return &BMP390{dev: *dev}, nil
}

func (b *BMP390) ReadRawData() (int32, int32, error) {
	// Check if data is ready
	var status [1]byte
	if err := b.dev.Tx([]byte{regStatus}, status[:]); err != nil {
		return 0, 0, fmt.Errorf("failed to read status: %v", err)
	}
	log.Printf("Status before read: 0x%02X", status[0])

	// Read pressure (24 bits) and temperature (24 bits)
	var pressData [3]byte
	var tempData [3]byte

	if err := b.dev.Tx([]byte{regPressData}, pressData[:]); err != nil {
		return 0, 0, fmt.Errorf("failed to read pressure: %v", err)
	}

	if err := b.dev.Tx([]byte{regTempData}, tempData[:]); err != nil {
		return 0, 0, fmt.Errorf("failed to read temperature: %v", err)
	}

	pressure := int32(uint32(pressData[2])<<16 | uint32(pressData[1])<<8 | uint32(pressData[0]))
	temperature := int32(uint32(tempData[2])<<16 | uint32(tempData[1])<<8 | uint32(tempData[0]))

	return pressure, temperature, nil
}

func main() {
	log.SetFlags(log.Lshortfile | log.LstdFlags)
	log.Println("Starting BMP390 reader...")

	// Initialize periph.io
	if _, err := host.Init(); err != nil {
		log.Fatal(err)
	}

	// Open I2C bus 1 specifically
	bus, err := i2creg.Open("/dev/i2c-1")
	if err != nil {
		log.Fatal("Failed to open I2C bus:", err)
	}
	defer bus.Close()

	// Create new BMP390 instance
	bmp, err := NewBMP390(bus)
	if err != nil {
		log.Fatal("Failed to initialize BMP390:", err)
	}

	log.Println("BMP390 initialized successfully!")

	// Read values in a loop
	for {
		pressure, temp, err := bmp.ReadRawData()
		if err != nil {
			log.Printf("Error reading values: %v", err)
			time.Sleep(time.Second)
			continue
		}

		log.Printf("Raw Pressure: %d", pressure)
		log.Printf("Raw Temperature: %d", temp)
		log.Println("---")

		time.Sleep(time.Second)
	}
}
