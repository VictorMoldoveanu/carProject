import serial
import keyboard
import time

arduino = serial.Serial('COM6', 9600)
time.sleep(2)

l_was_down = False


while True:
    # logs inputs for turning
    c1 = 'x'
    if (keyboard.is_pressed('left') and not keyboard.is_pressed('right')):
        c1 = 'a'
    if (keyboard.is_pressed('right') and not keyboard.is_pressed('left')):
        c1 = 'd'

    # logs inputs for driving
    c2 = 'x'
    if (keyboard.is_pressed('up') and not keyboard.is_pressed('down')):
        c2 = 'w'
    if (keyboard.is_pressed('down') and not keyboard.is_pressed('up')):
        c2 = 's'

    # horn
    c3 = 'x'
    if (keyboard.is_pressed('h')):
        c3 = 'h'

    # switches headlights by keeping last input stored to only send 1 data packet at a time
    c4 = 'x'
    l_is_down = keyboard.is_pressed('l')
    if (l_is_down and not l_was_down):
        c4 = 'l'
    l_was_down = l_is_down

    # 50Hz control, arduino code waits until \n to process the message to make sure the whole thing is recieved
    arduino.write((c1 + c2 + c3 + c4 + '\n').encode())
    time.sleep(0.02)