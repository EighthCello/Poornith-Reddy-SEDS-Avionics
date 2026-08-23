#include <LiquidCrystal.h>
LiquidCrystal lcd(12, 11, 5, 4, 3, 2);

const int buttonPin = 7;
const int buzzerPin = 8;
const int trigPin = 9;
const int echoPin = 10;
const int ledPin = 6;
const int lightPin = A0;

// ---------------- THRESHOLDS ----------------

const int LIGHT_THRESHOLD = 512;   // Half of 0-1023
const int DISTANCE_THRESHOLD = 100; // cm

const unsigned long DANGER_TIME = 5000;

// ---------------- STATES ----------------

enum State {
  OPEN_SEA,
  ANCHOR_DROPPED,
  STORM,
  CHARYBDIS,
  WRECKED
};

State currentState = OPEN_SEA;

// ---------------- VARIABLES ----------------

unsigned long dangerStartTime = 0;

bool lastButtonState = HIGH;
bool buttonState = HIGH;

// LED blinking
unsigned long lastBlinkTime = 0;
bool ledState = false;

// ---------------- SETUP ----------------

void setup() {
  pinMode(buttonPin, INPUT_PULLUP);

  pinMode(buzzerPin, OUTPUT);
  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
  pinMode(ledPin, OUTPUT);

  lcd.begin(16, 2);

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Ship Starting");
  delay(1000);

  displayState();
}

// ---------------- MAIN LOOP ----------------

void loop() {

  
  if (currentState == WRECKED) {
    displayState();
    digitalWrite(ledPin, LOW);
    noTone(buzzerPin);
    return;
  }


  int lightValue = analogRead(lightPin);
  long distance = getDistance();

  bool stormDetected = lightValue < LIGHT_THRESHOLD;
  bool charybdisDetected = distance < DISTANCE_THRESHOLD;


  buttonState = digitalRead(buttonPin);

  // Detect button press
  if (lastButtonState == HIGH && buttonState == LOW) {

    if (currentState == ANCHOR_DROPPED) {
      currentState = OPEN_SEA;
    }
    else {
      currentState = ANCHOR_DROPPED;
    }

    
    dangerStartTime = 0;

    displayState();
    delay(50);
  }

  lastButtonState = buttonState;

  // ------------------------------------------------
  // ANCHOR DROPPED
  // ------------------------------------------------

  if (currentState == ANCHOR_DROPPED) {

    
    digitalWrite(ledPin, LOW);
    noTone(buzzerPin);

    displayState();

    return;
  }

  // ------------------------------------------------
  // OPEN SEA
  // ------------------------------------------------

  if (currentState == OPEN_SEA) {

    digitalWrite(ledPin, LOW);
    noTone(buzzerPin);

    
    if (stormDetected) {

      currentState = STORM;
      dangerStartTime = millis();

      displayState();
    }

    else if (charybdisDetected) {

      currentState = CHARYBDIS;
      dangerStartTime = millis();

      displayState();
    }
  }

  // ------------------------------------------------
  // STORM
  // ------------------------------------------------

  else if (currentState == STORM) {

    // Blink LED
    if (millis() - lastBlinkTime >= 500) {

      lastBlinkTime = millis();

      ledState = !ledState;
      digitalWrite(ledPin, ledState);
    }

    noTone(buzzerPin);

    // If storm ends
    if (!stormDetected) {

      currentState = OPEN_SEA;
      dangerStartTime = 0;

      digitalWrite(ledPin, LOW);

      displayState();
    }

    // Check 5-second wreck timer
    else if (millis() - dangerStartTime >= DANGER_TIME) {

      currentState = WRECKED;

      digitalWrite(ledPin, LOW);

      displayState();
    }
  }

  // ------------------------------------------------
  // CHARYBDIS
  // ------------------------------------------------

  else if (currentState == CHARYBDIS) {

    // Sound buzzer
    tone(buzzerPin, 1000);

    digitalWrite(ledPin, LOW);

    // If ship escapes
    if (!charybdisDetected) {

      currentState = OPEN_SEA;
      dangerStartTime = 0;

      noTone(buzzerPin);

      displayState();
    }

    // Check 5-second wreck timer
    else if (millis() - dangerStartTime >= DANGER_TIME) {

      currentState = WRECKED;

      noTone(buzzerPin);

      displayState();
    }
  }

  delay(20);
}

// ==================================================
// GET DISTANCE FROM ULTRASONIC SENSOR
// ==================================================

long getDistance() {

  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);

  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);

  digitalWrite(trigPin, LOW);

  long duration = pulseIn(echoPin, HIGH);

  long distance = duration * 0.034 / 2;

  return distance;
}

// ==================================================
// DISPLAY CURRENT STATE
// ==================================================

void displayState() {

  lcd.clear();

  lcd.setCursor(0, 0);

  switch (currentState) {

    case OPEN_SEA:
      lcd.print("OPEN SEA");
      break;

    case ANCHOR_DROPPED:
      lcd.print("ANCHOR");
      lcd.setCursor(0, 1);
      lcd.print("DROPPED");
      break;

    case STORM:
      lcd.print("STORM");
      break;

    case CHARYBDIS:
      lcd.print("CHARYBDIS");
      break;

    case WRECKED:
      lcd.print("WRECKED");
      break;
  }
}
