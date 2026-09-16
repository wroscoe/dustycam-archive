#!/bin/bash
# Build Dusty.apk with the bare Android toolchain — no Gradle, no Android
# Studio. Runs INSIDE the build container: docker exec dustybuild bash tools/build.sh
set -euo pipefail
cd "$(dirname "$0")/.."
SDK=${SDK:-/sdk}
BT=$SDK/build-tools/34.0.0
PLAT=$SDK/platforms/android-34/android.jar
OUT=build
rm -rf $OUT && mkdir -p $OUT/gen $OUT/obj $OUT/dex

echo "[1/7] aapt2 compile  (res/ -> flat resources)"
$BT/aapt2 compile --dir res -o $OUT/res.zip

echo "[2/7] aapt2 link     (manifest + resources -> resource-only APK, and R.java)"
$BT/aapt2 link -o $OUT/res.apk -I $PLAT --manifest AndroidManifest.xml \
    --java $OUT/gen $OUT/res.zip

echo "[3/7] javac          (sources + R.java -> .class)"
javac --release 11 -classpath $PLAT -d $OUT/obj \
    $(find src $OUT/gen -name '*.java')

echo "[4/7] d8             (.class -> classes.dex, desugared to min-api 26)"
$BT/d8 --release --lib $PLAT --min-api 26 --output $OUT/dex \
    $(find $OUT/obj -name '*.class')

echo "[5/7] zip            (classes.dex into the APK)"
cp $OUT/res.apk $OUT/unsigned.apk
(cd $OUT/dex && zip -q -u ../unsigned.apk classes.dex)

echo "[6/7] zipalign"
$BT/zipalign -f -p 4 $OUT/unsigned.apk $OUT/aligned.apk

echo "[7/7] apksigner      (v1+v2+v3 with the project's own debug key)"
KS=keystore/debug.keystore
if [ ! -f $KS ]; then
  mkdir -p keystore
  keytool -genkeypair -keystore $KS -alias dusty -storepass android -keypass android \
      -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Dusty,O=dustycam,C=US" >/dev/null
  echo "      (generated $KS — keep it: updates must be signed with the same key)"
fi
$BT/apksigner sign --ks $KS --ks-pass pass:android --key-pass pass:android \
    --out Dusty.apk $OUT/aligned.apk
$BT/apksigner verify --verbose Dusty.apk | head -4
$BT/aapt2 dump badging Dusty.apk | grep -E '^(package|sdkVersion|targetSdkVersion|application-label|launchable-activity)'
ls -l Dusty.apk
