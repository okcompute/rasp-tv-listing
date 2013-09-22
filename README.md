rasp-tv-listing
===============

Transform raspberry pi as a permanent TV Guide

![OSX screenshot](./rasp-tv-listing.png?raw=true)

Requirements
------------
- Python packages  
    Please look the pip generated `requirements.txt` file.  
    Note about Pygame requirement:   
    On Raspberry Pi, this python package is already installed (Raspbian), no need to install.  

    On OSX, I used the following istallation steps:
    1. I installed Xquartz (not 100% sure it is required though). [Install info on Xquartz website](http://xquartz.macosforge.org/landing/ "Xquartz")
    2. I used Homebrew to install Pygame dependencies: brew install sdl sdl_ttf sdl_image sdl_mixer
    3. pip install hg+http://bitbucket.org/pygame/pygame  

    For Windows or Linux, I never tried so I don't know.
- Rovi's TV Listing api key  
    You need an API key for Rovi's Cloud services. Visit their developer website for more info.

Configuration
-----------

The script expect a config file names "rasp-tv-listing.cfg" in the CWD. Here how the content of the configuration file should looks like:

~~~
[rasp-tv-listing]  
api_key = Rovi TV Listing service api_key  
postal_code = Postal Code  
country_code = two letter country code  
channels = 2.1, 3,2, 10.1  
~~~
