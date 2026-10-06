# Build the C encoder and run the tests.
#
#   make            build bin/roi_x265_encode
#   make test       run all tests (integration tests skip if the encoder isn't built)
#   make clean
#
# x265 is found with pkg-config; override if it lives somewhere else, e.g.
#   make X265_CFLAGS="-I$HOME/x265/include" X265_LIBS="-L$HOME/x265/lib -lx265"
# STATIC=1 links x265 statically (single self-contained executable, handy on Windows).

CC      ?= cc
CFLAGS  ?= -O2 -Wall -Wextra -std=gnu11
PYTHON  ?= python3

ifeq ($(STATIC),1)
# -lgcc_s only exists as a shared library, so drop it for static links
X265_LIBS   ?= $(filter-out -lgcc_s,$(shell pkg-config --static --libs x265))
LDFLAGS     += -static -pthread
else
X265_LIBS   ?= $(shell pkg-config --libs x265)
endif
X265_CFLAGS ?= $(shell pkg-config --cflags x265)

ifeq ($(OS),Windows_NT)
EXE = .exe
endif

BIN = bin/roi_x265_encode$(EXE)

all: $(BIN)

$(BIN): src/encoder/roi_x265_encode.c
	@mkdir -p bin
	$(CC) $(CFLAGS) -D_POSIX_C_SOURCE=200809L $(X265_CFLAGS) -o $@ $< $(LDFLAGS) $(X265_LIBS) -lm

test:
	$(PYTHON) -m unittest discover -s tests -t . -v

clean:
	rm -rf bin

.PHONY: all test clean
