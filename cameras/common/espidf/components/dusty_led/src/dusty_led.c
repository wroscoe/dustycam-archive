#include "dusty_led.h"

#include <stdbool.h>
#include "driver/gpio.h"
#include "esp_log.h"
#include "freertos/task.h"

static const char *TAG = "dusty_led";

static int s_gpio = -1;
static int s_active_low = 1;
static SemaphoreHandle_t s_bus_mutex;
static volatile dusty_led_pattern_t s_pattern = DUSTY_LED_OFF;
static volatile int s_oneshot_ms;
static TaskHandle_t s_task;
static volatile int s_suspended;

#define STEP_MS 20 /* granularity: how quickly a pattern change or a
                      blink_ms request is noticed */

/* Write the pin, taking the bus mutex (0 timeout: skip rather than block
 * behind an in-flight SD transaction) when one was given. */
static void pin_write(int on)
{
    if (s_suspended || s_gpio < 0) return; /* pin belongs to the SD bus right now */
    int level = s_active_low ? !on : on;
    if (s_bus_mutex) {
        if (xSemaphoreTake(s_bus_mutex, 0) != pdTRUE) return; /* SD bus busy: skip this toggle */
        gpio_set_level(s_gpio, level);
        xSemaphoreGive(s_bus_mutex);
    } else {
        gpio_set_level(s_gpio, level);
    }
}

/* Sleep `ms`, in STEP_MS slices, servicing a pending one-shot blink and
 * returning early (1) if the pattern changed underneath us. */
static int sleep_slices(dusty_led_pattern_t want, int ms)
{
    while (ms > 0) {
        if (s_oneshot_ms > 0) {
            int dur = s_oneshot_ms;
            s_oneshot_ms = 0;
            pin_write(1);
            vTaskDelay(pdMS_TO_TICKS(dur));
            pin_write(0);
        }
        int slice = ms < STEP_MS ? ms : STEP_MS;
        vTaskDelay(pdMS_TO_TICKS(slice));
        ms -= slice;
        if (s_pattern != want) return 1;
    }
    return 0;
}

static void led_task(void *arg)
{
    (void)arg;
    for (;;) {
        dusty_led_pattern_t p = s_pattern;
        switch (p) {
        case DUSTY_LED_OFF:
            pin_write(0);
            sleep_slices(p, 500);
            break;
        case DUSTY_LED_SOLID:
            /* Fast pulse, not a held-low line: on boards where this pin
             * also drives SD CS, a truly solid line would starve the SD
             * bus. This reads as solid to the eye and yields to SD I/O
             * (README: "draining: the LED shows card activity (flicker)
             * instead of solid"). */
            pin_write(1);
            if (sleep_slices(p, 20)) break;
            pin_write(0);
            sleep_slices(p, 5);
            break;
        case DUSTY_LED_SEARCHING:
            pin_write(1);
            if (sleep_slices(p, 100)) break;
            pin_write(0);
            sleep_slices(p, 900);
            break;
        case DUSTY_LED_UPDATED:
            for (int i = 0; i < 3 && s_pattern == p; i++) {
                pin_write(1);
                if (sleep_slices(p, 100)) break;
                pin_write(0);
                if (sleep_slices(p, 100)) break;
            }
            if (s_pattern == p) s_pattern = DUSTY_LED_SOLID;
            break;
        case DUSTY_LED_FAIL:
            for (int i = 0; i < 5 && s_pattern == p; i++) {
                pin_write(1);
                if (sleep_slices(p, 80)) break;
                pin_write(0);
                if (sleep_slices(p, 80)) break;
            }
            if (s_pattern == p) s_pattern = DUSTY_LED_OFF;
            break;
        case DUSTY_LED_UNPROVISIONED:
            pin_write(1);
            if (sleep_slices(p, 80)) break;
            pin_write(0);
            if (sleep_slices(p, 80)) break;
            pin_write(1);
            if (sleep_slices(p, 80)) break;
            pin_write(0);
            sleep_slices(p, 760);
            break;
        case DUSTY_LED_RECOVERY:
            pin_write(1);
            if (sleep_slices(p, 100)) break;
            pin_write(0);
            sleep_slices(p, 1900);
            break;
        }
    }
}

static void pin_claim(void)
{
    gpio_config_t io = {
        .pin_bit_mask = 1ULL << s_gpio,
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&io);
    gpio_set_level(s_gpio, s_active_low ? 1 : 0); /* off = inactive = CS deasserted, if shared */
}

void dusty_led_init(int gpio, int active_low, SemaphoreHandle_t bus_mutex)
{
    s_gpio = gpio;
    s_active_low = active_low ? 1 : 0;
    s_bus_mutex = bus_mutex;
    s_suspended = 0;
    pin_claim();

    if (!s_task) {
        xTaskCreate(led_task, "dusty_led", 2560, NULL, tskIDLE_PRIORITY + 1, &s_task);
    }
    ESP_LOGI(TAG, "led on gpio %d (active %s)%s", s_gpio, s_active_low ? "low" : "high",
             bus_mutex ? ", sharing an SD bus mutex" : "");
}

void dusty_led_set(dusty_led_pattern_t p)
{
    s_pattern = p;
}

void dusty_led_blink_ms(int ms)
{
    if (ms > 0) s_oneshot_ms = ms;
}

void dusty_led_suspend(void)
{
    if (s_gpio < 0 || s_suspended) return;
    /* leave the pin inactive (CS deasserted) and stop touching it */
    if (s_bus_mutex) xSemaphoreTake(s_bus_mutex, portMAX_DELAY);
    gpio_set_level(s_gpio, s_active_low ? 1 : 0);
    s_suspended = 1;
    if (s_bus_mutex) xSemaphoreGive(s_bus_mutex);
}

void dusty_led_resume(void)
{
    if (s_gpio < 0 || !s_suspended) return;
    if (s_bus_mutex) xSemaphoreTake(s_bus_mutex, portMAX_DELAY);
    pin_claim(); /* the SD driver left it routed to the SPI CS signal */
    s_suspended = 0;
    if (s_bus_mutex) xSemaphoreGive(s_bus_mutex);
}

int dusty_led_suspended(void)
{
    return s_suspended;
}
