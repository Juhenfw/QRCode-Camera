import serial
import time

# Setup Serial Port
ser = serial.Serial('COM3', 9600, timeout=1)  # Ubah 'COM3' dengan port yang sesuai pada sistem Anda
time.sleep(2)  # Tunggu sampai serial terbuka

def trigger_flash():
    # Kirim sinyal trigger ke perangkat melalui serial
    ser.write(b'TRIGGER\n')  # Kirim sinyal yang sesuai, tergantung pada protokol perangkat
    print("Trigger signal sent")
    time.sleep(0.1)  # Delay untuk memberi waktu trigger

try:
    while True:
        input("Press Enter to trigger flash")
        trigger_flash()

except KeyboardInterrupt:
    print("Program stopped by user")

finally:
    # Tutup koneksi serial
    ser.close()
