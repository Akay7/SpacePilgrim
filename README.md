# Space Pilgrim
(previously Rice Rocks)

You control a little spaceship that is opposed to the cosmic asteroids.

## Idea

This game is remake of Rice Rocks the final project of [An Introduction to Interactive Programming in Python](https://www.coursera.org/learn/interactive-python-2) course on Coursera from Rice University.


## How to start play

You have two choices:

- Download in [Play Market](https://play.google.com/store/apps/details?id=pro.crazyrussian.games.spacepilgrim) for your Android device.

- You can start it from source code for this you need installing python and Kivy. [Here](https://kivy.org/docs/installation/installation-windows.html#install-win-dist) instructions for Windows users.

- I'm also planing share binary file for MS Windows systems, but it not ready yet.

## Development

### ToDo

1. Update game for two players on one device.
2. Draw normal joystick on screen instead buttons.
3. Add settings for key mapping and etc.
4. Allow multiplayer game on multiple devices.

### Build for Android

Build and run
```bash
buildozer android debug deploy run
```

View logs
```bash
adb logcat | grep -i python
```

Remove
```bash
adb shell pm uninstall pro.crazyrussian.games.spacepilgrim
```

Release
```bash
buildozer android release
```

## History versions

### 0.1.1

- first version on Play Market

- stable work on python 2.7

### 0.2.0

- public version on Play Market

- stable work on python 3

- renamed from Rice Rocks to Space Pilgrim

## Copyright and License

Copyright 2016 - 2017, 2024 Egor Poderiagin.

All source code released under MIT license, more details in LICENSE file.

All sound effects taken from http://www.freesfx.co.uk and remastered in Audacity, if you will reuse it, you must credit www.freesfx.co.uk in your project.

Some of images had taken from final project of "An Introduction to Interactive Programming in Python" course on Coursera from Rice Univercity and can used for not commercial purposes.
