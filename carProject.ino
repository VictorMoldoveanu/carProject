#include <Servo.h>

const int steerPin = 9;
const int straight = 90;
const int left = 145;
const int right = 35;
int target = straight;
int current = straight;
int stepSize = 1;
Servo steerMotor;

const int drivePin = 8;
const int go = 0;
const int stop = 87.5;
const int reverse = 180;
Servo driveMotor;

const int piezoPin = 7;
const int honkTone = 400;

const int FrtLftPin = 2;
const int FrtRtPin = 3;
const int BckLftPin = 4;
const int BckRtPin = 5;

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
  // updates steering angle outside of data reading to be smoother
  // slowly increments steering to not draw too much power from the motor
  if (current < target)
    current += stepSize;
  else if (current > target)
    current -= stepSize;
  steerMotor.write(current);

  // switches the headlights on and off
  if (frontLightsOn){
    digitalWrite(FrtLftPin, HIGH);
    digitalWrite(FrtRtPin, HIGH);
  }
  else{
    digitalWrite(FrtLftPin, LOW);
    digitalWrite(FrtRtPin, LOW);
  }

  if (Serial.available()){
    String input = Serial.readStringUntil('\n');
    
    char steerInput = 'x';
    char driveInput = 'x';
    char honkInput = 'x';
    char headLightInput = 'x';

    // ensure the string is exactly 4 characters before acting
    if (input.length() == 4) {
      steerInput = input[0];
      driveInput = input[1];
      honkInput = input[2];
      headLightInput = input[3];
    }

    // instantly switches target to be responsive
    if (steerInput == 'a')
      target = left;
    else if (steerInput == 'd')
      target = right;
    else
      target = straight;

    // has tail lights on by default unless driving forward
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

    if (honkInput == 'h')
      tone(piezoPin,honkTone);
    else
      noTone(piezoPin);

    if (headLightInput == 'l')
      frontLightsOn = !frontLightsOn;
  }
}