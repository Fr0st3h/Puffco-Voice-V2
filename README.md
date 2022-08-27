# Puffco-Voice-V2

Welcome to Puffco Voice V2

SUPPORTS FIRMWARE W AND FIRMWARE X!!

Note: Since this project emulates a Hue Light, there are limited voice commands, you can really only start and stop a session on your puffco.
You can create routines to preheat a specific profile by setting the brightness

- 0%-25% is profile 1
- 25%-50% is profile 2
- 50%-75% is profile 3
- 75%-100% is profile 4

You can refer to the screenshots in the screenshots folder for an example

Before you start, please have python version 3.8

1. Put all the files you downloaded from this git in a folder
2. Run Install_Requirements.bat
3. Once its done, open a command prompt and type in 'ipconfig' (without the single quotes)
4. Note down your "IPv4 Address" for the adapter you're using (Lan or Wifi)
5. Open the config.json in the Puffco Voice folder and paste your IPv4 Address in between the empty quotes after "Local_IPv4": 
6. Save the config, you don't not need to edit anything else.
7. Run Start.bat, the program will start searching for your puffco, if its having trouble being found or connecting, pair it in your bluetooth settings of your PC.
8. When the puffco is found, click y and then enter
9. Once your puffco is connected, open up the alexa app on your phone and add a new 'Other' device, or you can ask alexa to discover devices
10. Your puffco will be found as a light named whatever your puffco name is with (Puffco) at the end
11. Once you're finish adding the device, you're free to make some routines to control the puffco even more (Preheat profiles 1-4 mainly)

Thank you to https://github.com/blocke/ha-local-echo for the Hue Emulation
