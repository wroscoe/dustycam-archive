/*
 * XIAO ESP32S3 + DRV8833 supervised motor bench test.
 *
 * Wiring only:
 *   XIAO D0 / GPIO1 -> DRV8833 AIN1
 *   XIAO D1 / GPIO2 -> DRV8833 AIN2
 *   XIAO D2 / GPIO3 -> DRV8833 SLP (driver sleeps LOW; raised only for a pulse)
 *
 * This sketch has no camera, switch, SD, scheduler, or automatic motion.
 * Both bridge inputs are actively held LOW at boot and after every command.
 */

#if __has_include("esp_arduino_version.h")
#include "esp_arduino_version.h"
#endif

#ifndef ESP_ARDUINO_VERSION_MAJOR
/* ESP32 Arduino Core 2.x did not consistently expose this header/macro. */
#define ESP_ARDUINO_VERSION_MAJOR 2
#endif

static constexpr uint8_t AIN1_PIN = 1;  // XIAO D0
static constexpr uint8_t AIN2_PIN = 2;  // XIAO D1
static constexpr uint8_t SLP_PIN = 3;   // XIAO D2; DRV8833 nSLEEP, internal pulldown on the breakout
static constexpr uint8_t SLP_WAKE_MS = 2;  // DRV8833 tWAKE is <= 1 ms
static constexpr uint32_t PWM_HZ = 18000;
static constexpr uint8_t PWM_BITS = 10;
static constexpr uint16_t PWM_MAX = (1u << PWM_BITS) - 1u;
static constexpr uint8_t DEFAULT_DUTY_PERCENT = 18;   // deliberately low for first bench test
static uint8_t duty_percent = DEFAULT_DUTY_PERCENT;    // keys 1-9 select 10-90 %, 0 = 100 % DC
static uint16_t duty_value() { return PWM_MAX * duty_percent / 100u; }

/* Battery demo: no host needed. The XIAO BOOT button (GPIO0, active LOW) is
 * only a strapping pin at reset; after boot it is a plain input. A press
 * starts DEMO_CYCLES bounded forward/reverse pulses at 100 % duty; a press
 * during the demo aborts it. Serial 'd' runs the same sequence. */
static constexpr uint8_t BOOT_BUTTON_PIN = 0;
/* Heartbeat on the XIAO user LED (GPIO21, active LOW): a 60 ms blink every 2 s
 * while idle so battery operation is visible without a host; solid during a
 * pulse or demo. */
static constexpr uint8_t HEARTBEAT_PIN = LED_BUILTIN;
static constexpr uint16_t HEARTBEAT_PERIOD_MS = 2000;
static constexpr uint16_t HEARTBEAT_ON_MS = 60;
static void led(bool on) { digitalWrite(HEARTBEAT_PIN, on ? LOW : HIGH); }
static constexpr uint8_t DEMO_CYCLES = 10;
static constexpr uint16_t DEMO_GAP_MS = 600;
static constexpr uint16_t PULSE_MS = 200;     // fixed, bounded command duration

#if ESP_ARDUINO_VERSION_MAJOR < 3
static constexpr uint8_t AIN1_CHANNEL = 0;
static constexpr uint8_t AIN2_CHANNEL = 1;
#endif

static bool pwm_attached = false;
static bool next_test_is_forward = true;

static void print_help()
{
  Serial.println();
  Serial.println(F("XIAO ESP32S3 DRV8833 supervised bench test"));
  Serial.println(F("GPIO1/D0 -> AIN1; GPIO2/D1 -> AIN2; GPIO3/D2 -> SLP (LOW = driver asleep)"));
  Serial.println(F("SLP is raised only for the duration of a pulse."));
  Serial.println(F("Also verify motor supply polarity and keep the mechanism clear."));
  Serial.println(F("Commands: f = forward 200 ms, r = reverse 200 ms,"));
  Serial.println(F("          t = one alternating 200 ms test pulse, h/? = help, s = stop."));
  Serial.println(F("          1..9 = set duty to 10..90 %, 0 = 100 % DC, for later pulses (no motion)."));
  Serial.println(F("          d = demo: 10 bounded forward/reverse cycles at 100 %."));
  Serial.println(F("BOOT button press (after boot) = same demo without a host; press again to abort."));
  Serial.print(F("Current duty: "));
  Serial.print(duty_percent);
  Serial.println(F("%"));
  Serial.println(F("No command causes automatic motion. Both inputs are LOW at boot and after each pulse."));
}

/* Force actual GPIO-low outputs, including after a PWM pulse. */
static void stop_motor()
{
  if (pwm_attached) {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
    ledcWrite(AIN1_PIN, 0);
    ledcWrite(AIN2_PIN, 0);
    ledcDetach(AIN1_PIN);
    ledcDetach(AIN2_PIN);
#else
    ledcWrite(AIN1_CHANNEL, 0);
    ledcWrite(AIN2_CHANNEL, 0);
    ledcDetachPin(AIN1_PIN);
    ledcDetachPin(AIN2_PIN);
#endif
    pwm_attached = false;
  }
  pinMode(AIN1_PIN, OUTPUT);
  pinMode(AIN2_PIN, OUTPUT);
  digitalWrite(AIN1_PIN, LOW);
  digitalWrite(AIN2_PIN, LOW);
  pinMode(SLP_PIN, OUTPUT);
  digitalWrite(SLP_PIN, LOW);      /* driver asleep whenever we are not pulsing */
  led(false);
}

static void driver_wake()
{
  led(true);
  pinMode(SLP_PIN, OUTPUT);
  digitalWrite(SLP_PIN, HIGH);
  delay(SLP_WAKE_MS);
}

static bool attach_pwm()
{
  if (pwm_attached) return true;
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  const bool ain1_attached = ledcAttach(AIN1_PIN, PWM_HZ, PWM_BITS);
  const bool ain2_attached = ain1_attached && ledcAttach(AIN2_PIN, PWM_HZ, PWM_BITS);
  if (!ain1_attached || !ain2_attached) {
    /* pwm_attached is not set until both attaches succeed, so explicitly
     * release a partially attached first pin before forcing GPIO LOW. */
    if (ain1_attached) {
      ledcWrite(AIN1_PIN, 0);
      ledcDetach(AIN1_PIN);
    }
    if (ain2_attached) {
      ledcWrite(AIN2_PIN, 0);
      ledcDetach(AIN2_PIN);
    }
    stop_motor();
    return false;
  }
  ledcWrite(AIN1_PIN, 0);
  ledcWrite(AIN2_PIN, 0);
#else
  if (!ledcSetup(AIN1_CHANNEL, PWM_HZ, PWM_BITS) || !ledcSetup(AIN2_CHANNEL, PWM_HZ, PWM_BITS)) {
    stop_motor();
    return false;
  }
  ledcAttachPin(AIN1_PIN, AIN1_CHANNEL);
  ledcAttachPin(AIN2_PIN, AIN2_CHANNEL);
  ledcWrite(AIN1_CHANNEL, 0);
  ledcWrite(AIN2_CHANNEL, 0);
#endif
  pwm_attached = true;
  return true;
}

static void pulse_motor(bool forward)
{
  /* Keep this synchronous and fixed-duration: serial input is not sampled
   * during the 200 ms pulse, and stop_motor() runs unconditionally after it. */
  if (duty_percent >= 100) {
    stop_motor();  /* guarantees plain GPIO outputs, both LOW */
    Serial.print(forward ? F("forward") : F("reverse"));
    Serial.print(F(" pulse: "));
    Serial.print(PULSE_MS);
    Serial.println(F(" ms at 100% (DC)"));
    driver_wake();
    digitalWrite(AIN1_PIN, forward ? HIGH : LOW);
    digitalWrite(AIN2_PIN, forward ? LOW : HIGH);
    delay(PULSE_MS);
    stop_motor();
    Serial.println(F("stopped: AIN1=LOW, AIN2=LOW, SLP=LOW"));
    return;
  }
  if (!attach_pwm()) {
    Serial.println(F("ERROR: could not attach PWM; outputs forced LOW."));
    return;
  }
  Serial.print(forward ? F("forward") : F("reverse"));
  Serial.print(F(" pulse: "));
  Serial.print(PULSE_MS);
  Serial.print(F(" ms at "));
  Serial.print(duty_percent);
  Serial.println(F("% duty"));
  driver_wake();
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  const uint16_t duty = duty_value();
  ledcWrite(AIN1_PIN, forward ? duty : 0);
  ledcWrite(AIN2_PIN, forward ? 0 : duty);
#else
  const uint16_t duty = duty_value();
  ledcWrite(AIN1_CHANNEL, forward ? duty : 0);
  ledcWrite(AIN2_CHANNEL, forward ? 0 : duty);
#endif
  delay(PULSE_MS);
  stop_motor();
  Serial.println(F("stopped: AIN1=LOW, AIN2=LOW, SLP=LOW"));
}

static bool button_pressed()
{
  return digitalRead(BOOT_BUTTON_PIN) == LOW;
}

/* Wait for the button to be released (debounced) so one press is one event. */
static void wait_button_release()
{
  while (button_pressed()) delay(10);
  delay(50);
}

/* Bounded demo: DEMO_CYCLES x (forward, gap, reverse, gap) at 100 % duty.
 * Any button press between pulses aborts. Always ends with outputs LOW. */
static void run_demo()
{
  const uint8_t saved_duty = duty_percent;
  duty_percent = 100;
  Serial.print(F("demo: "));
  Serial.print(DEMO_CYCLES);
  Serial.println(F(" forward/reverse cycles at 100%; press BOOT to abort"));
  bool aborted = false;
  for (uint8_t i = 0; i < DEMO_CYCLES && !aborted; ++i) {
    for (uint8_t leg = 0; leg < 2 && !aborted; ++leg) {
      pulse_motor(leg == 0);
      const unsigned long gap_end = millis() + DEMO_GAP_MS;
      while ((long)(millis() - gap_end) < 0) {
        if (button_pressed()) { aborted = true; break; }
        delay(10);
      }
    }
  }
  stop_motor();
  duty_percent = saved_duty;
  if (aborted) {
    wait_button_release();
    Serial.println(F("demo aborted: AIN1=LOW, AIN2=LOW"));
  } else {
    Serial.println(F("demo done: AIN1=LOW, AIN2=LOW"));
  }
}

void setup()
{
  /* Do this before USB serial is started: power-up is always non-actuating. */
  pinMode(HEARTBEAT_PIN, OUTPUT);
  stop_motor();
  pinMode(BOOT_BUTTON_PIN, INPUT_PULLUP);
  Serial.begin(115200);
  unsigned long deadline = millis() + 1500;
  while (!Serial && millis() < deadline) delay(10);
  print_help();
}

static void heartbeat()
{
  const uint32_t phase = millis() % HEARTBEAT_PERIOD_MS;
  led(phase < HEARTBEAT_ON_MS);
}

void loop()
{
  heartbeat();
  if (button_pressed()) {
    delay(30);                       /* debounce */
    if (button_pressed()) {
      wait_button_release();         /* a held button never auto-repeats */
      run_demo();
    }
    return;
  }
  if (!Serial.available()) return;
  const char command = (char)Serial.read();
  switch (command) {
    case 'f': case 'F': pulse_motor(true); break;
    case 'r': case 'R': pulse_motor(false); break;
    case 't': case 'T':
      pulse_motor(next_test_is_forward);
      next_test_is_forward = !next_test_is_forward;
      break;
    case 's': case 'S': stop_motor(); Serial.println(F("stopped: AIN1=LOW, AIN2=LOW, SLP=LOW")); break;
    case 'h': case 'H': case '?': print_help(); break;
    case 'd': case 'D': run_demo(); break;
    case '0':
      duty_percent = 100;
      Serial.println(F("duty set to 100% (DC) for later pulses (no motion)"));
      break;
    case '1': case '2': case '3': case '4': case '5':
    case '6': case '7': case '8': case '9':
      duty_percent = (uint8_t)((command - '0') * 10);
      Serial.print(F("duty set to "));
      Serial.print(duty_percent);
      Serial.println(F("% for later pulses (no motion)"));
      break;
    case '\r': case '\n': case ' ': break;
    default: Serial.println(F("Unknown command. Send h or ? for help.")); break;
  }
}
