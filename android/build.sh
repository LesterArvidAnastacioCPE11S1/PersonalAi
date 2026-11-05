#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
TOOLS="${PAI_ANDROID_TOOLS:-F:/AndroidBuild}"
JDK_HOME="${PAI_JDK_HOME:-$(echo "$TOOLS"/jdk17/jdk-*)}"
SDK="${PAI_ANDROID_SDK:-$TOOLS/sdk}"
BUILD_TOOLS="$SDK/build-tools/34.0.0"
PLATFORM="$SDK/platforms/android-34/android.jar"
APK="$ROOT/PersonalAI.apk"
KEYSTORE="$ROOT/personalai.keystore"

export JAVA_HOME="$JDK_HOME"
export PATH="$JDK_HOME/bin:$PATH"

cd "$ROOT"

rm -rf build
mkdir -p build/gen build/classes build/dex

"$BUILD_TOOLS/aapt2.exe" compile --dir res -o build/resources.zip

"$BUILD_TOOLS/aapt2.exe" link \
    -o build/base.apk \
    -I "$PLATFORM" \
    --manifest AndroidManifest.xml \
    --java build/gen \
    --min-sdk-version 24 \
    --target-sdk-version 34 \
    --version-code 1 \
    --version-name 1.0 \
    build/resources.zip

find build/gen src -name '*.java' > build/sources.txt

"$JDK_HOME/bin/javac.exe" \
    --release 8 \
    -classpath "$PLATFORM" \
    -d build/classes \
    @build/sources.txt

find build/classes -name '*.class' > build/classes.txt

"$BUILD_TOOLS/d8.bat" \
    --lib "$PLATFORM" \
    --min-api 24 \
    --output build/dex \
    $(cat build/classes.txt)

"$JDK_HOME/bin/jar.exe" uf build/base.apk -C build/dex classes.dex

"$BUILD_TOOLS/zipalign.exe" -f 4 build/base.apk build/unsigned.apk

if [ ! -f "$KEYSTORE" ]; then
    "$JDK_HOME/bin/keytool.exe" -genkeypair \
        -keystore "$KEYSTORE" \
        -storepass personalai \
        -keypass personalai \
        -alias personalai \
        -keyalg RSA \
        -keysize 2048 \
        -validity 10000 \
        -dname "CN=PersonalAI, OU=Personal, O=PersonalAI, L=Local, S=Local, C=US" \
        -noprompt
fi

"$BUILD_TOOLS/apksigner.bat" sign \
    --ks "$KEYSTORE" \
    --ks-key-alias personalai \
    --ks-pass pass:personalai \
    --key-pass pass:personalai \
    --out "$APK" \
    build/unsigned.apk

"$BUILD_TOOLS/apksigner.bat" verify "$APK"

ls -lh "$APK"
