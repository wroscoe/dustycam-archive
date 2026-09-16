# Host build of dusty_core as a shared library, for the ctypes-driven test
# suite in cameras/common/espidf/tests/test_core.py. Plain gcc, no IDF.
CC ?= gcc
SRCDIR := ../src
INCDIR := ../include
CFLAGS := -std=c99 -Wall -Wextra -Werror -fPIC -O2 -I$(INCDIR)
LDLIBS := -lm

SRCS := $(wildcard $(SRCDIR)/*.c)
OUT := libdusty_core.so

.PHONY: all clean
all: $(OUT)

$(OUT): $(SRCS) $(wildcard $(SRCDIR)/*.h) $(wildcard $(INCDIR)/*.h)
	$(CC) $(CFLAGS) -shared -o $(OUT) $(SRCS) $(LDLIBS)

clean:
	rm -f $(OUT)
