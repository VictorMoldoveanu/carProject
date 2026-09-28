import serial
import keyboard
import time

arduino = serial.Serial('COM6', 9600)
time.sleep(2)

l_was_down = False

while True:
    c1 = 'x'
    if (keyboard.is_pressed('left') and not keyboard.is_pressed('right')):
        c1 = 'a'
    if (keyboard.is_pressed('right') and not keyboard.is_pressed('left')):
        c1 = 'd'

    c2 = 'x'
    if (keyboard.is_pressed('up') and not keyboard.is_pressed('down')):
        c2 = 'w'
    if (keyboard.is_pressed('down') and not keyboard.is_pressed('up')):
        c2 = 's'

    c3 = 'x'
    if (keyboard.is_pressed('h')):
        c3 = 'h'

    c4 = 'x'
    l_is_down = keyboard.is_pressed('l')
    if (l_is_down and not l_was_down):
        c4 = 'l'
    l_was_down = l_is_down

    arduino.write((c1 + c2 + c3 + c4 + '\n').encode())
    time.sleep(0.02)