/* On-device animal gate (TFLite Micro). Fail-open: if init fails the
 * caller must treat every motion frame as transmit-worthy. */
#ifndef CAMLOGGER_GATE_H_
#define CAMLOGGER_GATE_H_

#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define GATE_IMG 96   /* model input: GATE_IMG x GATE_IMG x 3, int8 */

bool gate_init(void);
/* img: 96*96*3 int8 (uint8 pixel ^ 0x80). Returns animal probability
 * 0..1, or -1.0 on inference failure. Never read `img` back out of the
 * interpreter's input tensor after this call (sarg:
 * tflite-micro-input-tensor-invalid-after-invoke-memcpy-before) -- gate.cc
 * copies it in before Invoke(), which is the only safe order. */
float gate_score(const int8_t *img);

/* Arena bookkeeping for the bench (PLAN.md §8 gate 6). Bytes requested at
 * init and bytes the interpreter actually used (0 before gate_init()
 * succeeds). */
size_t gate_arena_capacity(void);
size_t gate_arena_used(void);

#ifdef __cplusplus
}
#endif

#endif
