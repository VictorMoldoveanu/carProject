#include <Servo.h>

const int steerPin = 13;
const int straight = 90;
const int left = 145;
const int right = 35;
int target = straight;
int current = straight;
int stepSize = 1;
Servo steerMotor;

const int drivePin = 12;
const int go = 0;
const int stop = 87.5;
const int reverse = 180;
Servo driveMotor;

const int piezoPin = 11;
const int honkTone = 400;

const int FrtLftPin = 7;
const int FrtRtPin = 8;
const int BckLftPin = 9;
const int BckRtPin = 10;
enum class blinkMode : uint8_t{
  normal,
  leftSignal,
  hazzard,
  rightSignal
};
blinkMode currentBlinkMode = blinkMode::normal;
bool turnStarted = false;
const unsigned long blinkInterval = 400;  // ms on, then ms off
unsigned long lastBlink = 0;
bool blinkOn = false;

bool frontLightsOn = true;

void setup() {
  Serial.begin(9600);

  steerMotor.attach(steerPin);
  driveMotor.attach(drivePin);

  delay(2000);

  steerMotor.write(straight);
  driveMotor.write(stop);

  pinMode(piezoPin, OUTPUT);

  pinMode(FrtLftPin,OUTPUT);
  pinMode(FrtRtPin,OUTPUT);
  pinMode(BckLftPin,OUTPUT);
  pinMode(BckRtPin,OUTPUT);
}

void loop() {
  if (millis() - lastBlink >= blinkInterval) {
    lastBlink = millis();
    blinkOn = !blinkOn;
  }

  // updates steering angle outside of data reading to be smoother
  // slowly increments steering to not draw too much power from the motor
  if (current < target)
    current += stepSize;
  else if (current > target)
    current -= stepSize;
  steerMotor.write(current);

  if (Serial.available()){
    String input = Serial.readStringUntil('\n');
    
    char steerInput = '7'; // middle 55 is '7'
    char driveInput = 'x';
    char honkInput = 'x';
    char headLightInput = 'x';
    char blinkerInput = 'x';

    // ensure the string is exactly 4 characters before acting
    if (input.length() == 5) {
      steerInput = input[0];
      driveInput = input[1];
      honkInput = input[2];
      headLightInput = input[3];
      blinkerInput = input[4];
    }

    target = static_cast<int>(steerInput)+35;

    if (blinkerInput == 'a')
      currentBlinkMode = blinkMode::leftSignal;
    else if (blinkerInput == 'd')
      currentBlinkMode = blinkMode::rightSignal;
    else if ((blinkerInput == 's') && (currentBlinkMode == blinkMode::hazzard))
      currentBlinkMode = blinkMode::normal;
    else if (blinkerInput == 's')
      currentBlinkMode = blinkMode::hazzard;

    if (blinkerInput == 'a' || blinkerInput == 'd')
      turnStarted = false;
    if (currentBlinkMode == blinkMode::leftSignal || currentBlinkMode == blinkMode::rightSignal) {
      if (target != straight)
        turnStarted = true;
      else if (turnStarted)
        currentBlinkMode = blinkMode::normal;
    }

    // Huge block of code deals with driving and blink handling, could split into multiple functions to be more manageable
    if (currentBlinkMode == blinkMode::normal){//normal case
      if (frontLightsOn){
        digitalWrite(FrtLftPin, HIGH);
        digitalWrite(FrtRtPin, HIGH);
      }
      else{
        digitalWrite(FrtLftPin, LOW);
        digitalWrite(FrtRtPin, LOW);
      }
      digitalWrite(BckLftPin, HIGH);
      digitalWrite(BckRtPin, HIGH);
      if (driveInput == 'w'){
        driveMotor.write(go);
        digitalWrite(BckLftPin, LOW);
        digitalWrite(BckRtPin, LOW);
      }
      else if (driveInput == 's')
        driveMotor.write(reverse);
      else
        driveMotor.write(stop);
    }
    else if (currentBlinkMode == blinkMode::hazzard){//hazzard case
      if (blinkOn){
        digitalWrite(BckLftPin, HIGH);
        digitalWrite(BckRtPin, HIGH);
        digitalWrite(FrtLftPin, HIGH);
        digitalWrite(FrtRtPin, HIGH);
      }
      else{
        digitalWrite(BckLftPin, LOW);
        digitalWrite(BckRtPin, LOW);
        digitalWrite(FrtLftPin, LOW);
        digitalWrite(FrtRtPin, LOW);
      }
      if (driveInput == 'w')
        driveMotor.write(go);
      else if (driveInput == 's')
        driveMotor.write(reverse);
      else
        driveMotor.write(stop);
    }
    else if (currentBlinkMode == blinkMode::leftSignal){//left signal case
      if (frontLightsOn)
        digitalWrite(FrtRtPin, HIGH);
      else
        digitalWrite(FrtRtPin, LOW);
      if (blinkOn){
        digitalWrite(BckLftPin, HIGH);
        digitalWrite(FrtLftPin, HIGH);
      }
      else{
        digitalWrite(BckLftPin, LOW);
        digitalWrite(FrtLftPin, LOW);
      }
      digitalWrite(BckRtPin, HIGH);
      if (driveInput == 'w'){
        driveMotor.write(go);
        digitalWrite(BckRtPin, LOW);
      }
      else if (driveInput == 's')
        driveMotor.write(reverse);
      else
        driveMotor.write(stop);
    }
    else{//right signal case
      if (frontLightsOn)
        digitalWrite(FrtLftPin, HIGH);
      else
        digitalWrite(FrtLftPin, LOW);
      if (blinkOn){
        digitalWrite(BckRtPin, HIGH);
        digitalWrite(FrtRtPin, HIGH);
      }
      else{
        digitalWrite(BckRtPin, LOW);
        digitalWrite(FrtRtPin, LOW);
      }
      digitalWrite(BckLftPin, HIGH);
      if (driveInput == 'w'){
        driveMotor.write(go);
        digitalWrite(BckLftPin, LOW);
      }
      else if (driveInput == 's')
        driveMotor.write(reverse);
      else
        driveMotor.write(stop);
    }

    if (honkInput == 'h')
      tone(piezoPin,honkTone);
    else
      noTone(piezoPin);

    if (headLightInput == 'l')
      frontLightsOn = !frontLightsOn;
  }
}