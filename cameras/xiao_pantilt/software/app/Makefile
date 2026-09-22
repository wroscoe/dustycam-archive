.PHONY: build flash monitor clean web-package web-release
IDF_IMG = espressif/idf:release-v5.5
# Mount the repo root: EXTRA_COMPONENT_DIRS in CMakeLists.txt resolves
# cameras/common/espidf/components relative to this project via a path
# that walks back up to it, so the container needs the whole tree, not
# just this directory.
ROOT = $(realpath ../../../..)
PORT ?= /dev/ttyACM1
# The image's IDF_TOOLS_PATH (/opt/esp) is root:root; --user can't write
# a "root_managed_components" cache there (verified: PermissionError).
# Bind our own writable dir over just that one subpath instead of giving
# up --user (which would leave build/ root-owned on the host).
CACHE_DIR = $(CURDIR)/.idf_component_cache
CAMERA_DIR = $(ROOT)/cameras/xiao_pantilt
WEB_MERGED = build/xiao-wildlife-factory.bin
WEB_RELEASE_DIR ?= build/web

build:            ## build firmware in Docker (no network: managed_components/ + dependencies.lock are vendored)
	mkdir -p $(CACHE_DIR)
	docker run --rm -v $(ROOT):/work -w /work/cameras/xiao_pantilt/software/app \
	  --user $$(id -u):$$(id -g) -e HOME=/tmp -e IDF_TOOLS_PATH=/opt/esp \
	  -v $(CACHE_DIR):/opt/esp/root_managed_components \
	  $(IDF_IMG) bash -c "idf.py -DSDKCONFIG_DEFAULTS='sdkconfig.defaults;sdkconfig.secrets' build"

web-package:      ## package an already-built, verified blank image for ESP Web Tools
	$(ROOT)/tools/dustygen $(CAMERA_DIR) --verify-blank
	docker run --rm -v $(ROOT):/work -w /work/cameras/xiao_pantilt/software/app \
	  --user $$(id -u):$$(id -g) -e HOME=/tmp -e IDF_TOOLS_PATH=/opt/esp \
	  $(IDF_IMG) bash -c "python -m esptool --chip esp32s3 merge_bin -o $(WEB_MERGED) \
	    --flash_mode dio --flash_freq 80m --flash_size 8MB \
	    0x0 build/bootloader/bootloader.bin \
	    0xc000 build/partition_table/partition-table.bin \
	    0x13000 build/ota_data_initial.bin \
	    0x20000 build/xiaocam1.bin"
	python3 $(ROOT)/tools/package_xiao_web_firmware.py \
	  --app-dir $(CURDIR) --merged $(WEB_MERGED) --output-dir $(WEB_RELEASE_DIR)

web-release:      ## generate blank defaults, build, verify, and package browser firmware
	$(ROOT)/tools/dustygen $(CAMERA_DIR) --blank
	$(MAKE) build
	$(MAKE) web-package

flash:            ## NOT run by this Makefile's build target — bootstrap flash over USB, by hand only
	@echo "flash is intentionally not run automatically; invoke by hand when ready:"
	@echo "  esptool --port $(PORT) --baud 921600 write-flash \\"
	@echo "    0x0     build/bootloader/bootloader.bin \\"
	@echo "    0xc000  build/partition_table/partition-table.bin \\"
	@echo "    0x13000 build/ota_data_initial.bin \\"
	@echo "    0x20000 build/xiaocam1.bin"

monitor:          ## serial console over the XIAO's native USB-Serial-JTAG
	python3 ../host/monitor.py $(PORT)

clean:
	docker run --rm -v $(ROOT):/work -w /work/cameras/xiao_pantilt/software/app \
	  --user $$(id -u):$$(id -g) -e HOME=/tmp -e IDF_TOOLS_PATH=/opt/esp \
	  $(IDF_IMG) bash -c "rm -rf build sdkconfig sdkconfig.old"
	rm -rf $(CACHE_DIR)
