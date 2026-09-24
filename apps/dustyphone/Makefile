# dustyphone build/install/run — bare Android toolchain in a docker container,
# no Gradle, no Android Studio. See README.md.

ADB     ?= /hd2/temp_data/android-sdk/platform-tools/adb
PKG     := com.dustycam.phone
CONTAINER := dustybuild
SDKDIR  := /hd2/temp_data/android-sdk
# The tree bind-mounted into the build container as /work. Derived from this
# Makefile's own location rather than hardcoded, so it follows the repo through
# the restructure (docs/REPO_PLAN.md) instead of depending on a ~/code/dustycam
# symlink that is about to be removed. Override on the command line if needed.
REPO    ?= $(realpath $(dir $(lastword $(MAKEFILE_LIST)))/../..)

.PHONY: container build test install run log clean

# Create the long-lived build container once (mirrors hellobuild/photobuild).
container:
	@if [ -z "$$(docker ps -aq -f name=^/$(CONTAINER)$$)" ]; then \
		docker run -d --name $(CONTAINER) \
			-v $(REPO):/work \
			-v $(SDKDIR):/sdk \
			-w /work/apps/dustyphone \
			-e SDK=/sdk \
			eclipse-temurin:17-jdk sleep infinity ; \
		echo "created $(CONTAINER)" ; \
	else \
		docker start $(CONTAINER) >/dev/null 2>&1 || true ; \
		echo "$(CONTAINER) already exists" ; \
	fi

build:
	docker exec $(CONTAINER) bash tools/build.sh

# Framer and Crypto are pure Java (no Android imports) — compiled and run
# with the plain JDK in the container, no android.jar on the classpath.
test:
	docker exec $(CONTAINER) bash -c ' \
		set -e; \
		rm -rf /tmp/dustytest && mkdir -p /tmp/dustytest; \
		javac --release 11 -d /tmp/dustytest \
			src/com/dustycam/phone/ble/Framer.java \
			src/com/dustycam/phone/ble/Crypto.java \
			tests/FramerTest.java \
			tests/CryptoTest.java; \
		java -cp /tmp/dustytest com.dustycam.phone.ble.FramerTest; \
		java -cp /tmp/dustytest com.dustycam.phone.ble.CryptoTest'

install:
	$(ADB) install -r Dusty.apk
	$(ADB) shell pm grant $(PKG) android.permission.BLUETOOTH_SCAN || true
	$(ADB) shell pm grant $(PKG) android.permission.BLUETOOTH_CONNECT || true

run:
	$(ADB) shell am start -n $(PKG)/.ScanActivity

log:
	$(ADB) logcat -s Dusty

clean:
	rm -rf build Dusty.apk Dusty.apk.idsig
