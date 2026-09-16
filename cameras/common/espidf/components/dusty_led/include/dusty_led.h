/* dusty_led: one-LED pattern language. Contract: docs/camera_operation.md
 * §10. On boards where the LED pin doubles as the SD chip select (the
 * XIAO, GPIO21), pass the SD bus mutex so the driving task only toggles
 * the pin while no card transaction is in flight, and restores it HIGH
 * (inactive / CS deasserted) after every toggle.
 */
#ifndef DUSTY_LED_H
#define DUSTY_LED_H

#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    DUSTY_LED_OFF,
    DUSTY_LED_SOLID,
    DUSTY_LED_SEARCHING,     /* 1 Hz blink: searching for the hotspot */
    DUSTY_LED_UPDATED,       /* 3 quick blinks, then solid */
    DUSTY_LED_FAIL,          /* 5 fast blinks, then off */
    DUSTY_LED_UNPROVISIONED, /* double blink every second */
    DUSTY_LED_RECOVERY,      /* one blink every 2 s */
} dusty_led_pattern_t;

/* bus_mutex may be NULL when the LED pin is not shared with anything. */
void dusty_led_init(int gpio, int active_low, SemaphoreHandle_t bus_mutex);
void dusty_led_set(dusty_led_pattern_t p);
void dusty_led_blink_ms(int ms); /* one-shot, overlaid on the current pattern */
/* On boards where the LED pin is also the SD chip select (XIAO ESP32S3
 * Sense: GPIO21) the pin is routed to the SPI peripheral through the GPIO
 * matrix while the card is mounted, so GPIO writes are ignored and a GPIO
 * reconfiguration would break the card. Call suspend() BEFORE mounting the
 * card (the task stops touching the pin; the card's own CS activity is the
 * "draining" flicker) and resume() AFTER unmounting (the pin is reclaimed as
 * a GPIO output and the current pattern continues). Harmless on boards
 * without the conflict. */
void dusty_led_suspend(void);
void dusty_led_resume(void);
int  dusty_led_suspended(void);

#ifdef __cplusplus
}
#endif
#endif
