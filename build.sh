#!/data/data/com.termux/files/usr/bin/bash

p4a apk --private . --package=org.monitor.filemonitor --name "FileMonitor" --version 1.0 --bootstrap=sdl2 --requirements=python3,kivy,requests,watchdog,android --permission INTERNET --permission READ_EXTERNAL_STORAGE --permission WRITE_EXTERNAL_STORAGE --arch=arm64-v8a --android-api 30 --ndk-dir /data/data/com.termux/files/home/.buildozer/android/platform/android-ndk-r25b --sdk-dir /data/data/com.termux/files/home/.buildozer/android/platform/android-sdk --release
