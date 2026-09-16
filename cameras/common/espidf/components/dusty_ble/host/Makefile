# Host build of ble_frame (the portable half of dusty_ble) as a shared
# library, for the ctypes-driven test suite in
# cameras/common/espidf/tests/test_ble_frame.py. Plain gcc, no IDF. Mirrors
# dusty_core/host/Makefile.
CC ?= gcc
SRCDIR := ../src
INCDIR := ../include
CFLAGS := -std=c99 -Wall -Wextra -Werror -fPIC -O2 -I$(INCDIR)
LDLIBS :=

SRCS := $(SRCDIR)/ble_frame.c
OUT := libble_frame.so

.PHONY: all clean
all: $(OUT)

$(OUT): $(SRCS) $(wildcard $(INCDIR)/*.h)
	$(CC) $(CFLAGS) -shared -o $(OUT) $(SRCS) $(LDLIBS)

clean:
	rm -f $(OUT)
