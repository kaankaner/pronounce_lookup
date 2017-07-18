pronounce-lookup - a small script for looking up the pronunciation of a word in youtube.com.

# INSTALLATION

Several tools and python modules are required:

	apt install youtube-dl
	apt install ffmpeg
	pip install bs4
	pip install lxml
	pip install appdirs

If Youtube Data API will be used:
	
	pip install --upgrade google-api-python-client

Install with:

	sudo ./install.sh

Uninstall with:

	sudo ./uninstall.sh

# USAGE

Look up a single word:

	pronounce-lookup otorhinolaryngologist

Look up multiple words:

	pronounce-lookup worcestershire sauce

Use Youtube Data API:

	pronounce-lookup --use-api --api-key YOUR_API_KEY otorhinolaryngologist

Use youtube.com search page directly (default, not recommended):

	pronounce-lookup --no-use-api otorhinolaryngologist

Use custom configuration file:

	pronounce-lookup --config CONFIG_FILE otorhinolaryngologist

Instead of using command line arguments, the options `use_api` (boolean) and `api_key` (string) can be placed in a configuration file. 

When the script is called for the first time, it will create a default configuration file under `$HOME/.config/pronounce-lookup/pronounce-lookup.cfg`. 

