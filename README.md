rasp-tv-listing
===============

Transform raspberry pi as a permanent TV Guide

![Image](./rasp-tv-listing.png?raw=true)

Requirements
------------
1. Python packages

Please look the pip generated `requirements.txt` file. The hardest to install is PyGame. For the rest it is all straightfowarrd.

2. Rovi's TV Listing api key

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
