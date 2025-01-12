package main

import (
	"fmt"
	"log"
	"path/filepath"
	"periph.io/x/conn/v3/i2c"
	"periph.io/x/conn/v3/i2c/i2creg"
	"periph.io/x/host/v3"
	"strings"
	"time"
)

const (
	// BMP390 registers
	regChipID    = 0x00
	regStatus    = 0x03
	regPressData = 0x04
	regTempData  = 0x07
	regPWRCtrl   = 0x1B
	regOSR       = 0x1C
	regCmd       = 0x7E
)

// Helper to list available I2C paths
func listI2CBuses() ([]string, error) {
	paths, err := filepath.Glob("/dev/i2c-*")
	if err != nil {
		return nil, fmt.Errorf("failed to list I2C buses: %v", err)
	}
	return paths, nil
}

// Write to a specific register
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

// BMP390 initialization
func initializeBMP390(bus i2c.BusCloser) (*i2c.Dev, error) {
	dev := &i2c.Dev{Bus: bus, Addr: 0x77}

	// Check chip ID
	var id [1]byte
	if err := dev.Tx([]byte{regChipID}, id[:]); err != nil {
		return nil, fmt.Errorf("failed to read chip ID: %v", err)
	}

	if id[0] != 0x60 { // Replace with your BMP390 chip ID from the datasheet
		return nil, fmt.Errorf("unexpected chip ID: 0x%02X", id[0])
	}
	log.Printf("Chip ID verified: 0x%02X", id[0])

	// Soft reset
	if err := writeReg(dev, regCmd, 0xB6); err != nil {
		return nil, fmt.Errorf("failed to reset sensor: %v", err)
	}
	time.Sleep(20 * time.Millisecond)

	// Configure the sensor
	steps := []struct {
		reg   uint8
		value uint8
		name  string
	}{
		{regPWRCtrl, 0x33, "Power Control"}, // Enable pressure and temperature
		{regOSR, 0x27, "Oversampling"},      // Oversampling settings
	}

	for _, step := range steps {
		if err := writeReg(dev, step.reg, step.value); err != nil {
			return nil, fmt.Errorf("failed to set %s: %v", step.name, err)
		}
		time.Sleep(10 * time.Millisecond)
		log.Printf("%s configured", step.name)
	}

	return dev, nil
}

// Read raw data from BMP390
func readRawData(dev *i2c.Dev) (int32, int32, error) {
	// Check if data is ready
	var status [1]byte
	if err := dev.Tx([]byte{regStatus}, status[:]); err != nil {
		return 0, 0, fmt.Errorf("failed to read status: %v", err)
	}
	if status[0]&0x08 == 0 || status[0]&0x04 == 0 {
		return 0, 0, fmt.Errorf("data not ready")
	}

	// Read pressure and temperature
	var pressData, tempData [3]byte
	if err := dev.Tx([]byte{regPressData}, pressData[:]); err != nil {
		return 0, 0, fmt.Errorf("failed to read pressure: %v", err)
	}
	if err := dev.Tx([]byte{regTempData}, tempData[:]); err != nil {
		return 0, 0, fmt.Errorf("failed to read temperature: %v", err)
	}

	pressure := int32(uint32(pressData[2])<<16 | uint32(pressData[1])<<8 | uint32(pressData[0]))
	temperature := int32(uint32(tempData[2])<<16 | uint32(tempData[1])<<8 | uint32(tempData[0]))
	return pressure, temperature, nil
}

func main() {
	log.SetFlags(log.Lshortfile | log.LstdFlags)
	log.Println("Starting BMP390 script...")

	// Initialize periph.io
	if _, err := host.Init(); err != nil {
		log.Fatalf("Failed to initialize periph.io: %v", err)
	}

	// List available I2C buses
	paths, err := listI2CBuses()
	if err != nil {
		log.Fatal(err)
	}
	if len(paths) == 0 {
		log.Fatal("No I2C buses found!")
	}
	log.Printf("Available I2C buses: %s", strings.Join(paths, ", "))

	// Prompt user for I2C bus selection if multiple are available
	selectedBus := paths[0]
	if len(paths) > 1 {
		fmt.Println("Select an I2C bus from the following:")
		for i, path := range paths {
			fmt.Printf("[%d] %s\n", i, path)
		}
		fmt.Print("Enter the number corresponding to your choice: ")
		var choice int
		if _, err := fmt.Scan(&choice); err != nil || choice < 0 || choice >= len(paths) {
			log.Fatal("Invalid choice, exiting.")
		}
		selectedBus = paths[choice]
	}

	log.Printf("Using I2C bus: %s", selectedBus)

	// Open the selected I2C bus
	bus, err := i2creg.Open(selectedBus)
	if err != nil {
		log.Fatalf("Failed to open I2C bus: %v", err)
	}
	defer bus.Close()

	// Initialize BMP390
	dev, err := initializeBMP390(bus)
	if err != nil {
		log.Fatalf("Failed to initialize BMP390: %v", err)
	}

	log.Println("BMP390 initialized successfully!")

	// Read data in a loop
	for {
		pressure, temperature, err := readRawData(dev)
		if err != nil {
			log.Printf("Error reading data: %v", err)
		} else {
			log.Printf("Pressure: %d, Temperature: %d", pressure, temperature)
		}
		time.Sleep(1 * time.Second)
	}
}
