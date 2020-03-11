mond
----

[![Build Status](https://travis-ci.org/kevr/mond.svg?branch=master)](https://travis-ci.org/kevr/mond)

A monitor management daemon for X sessions.

## Configuration

`mond` requires a configuration file to operate. The configuration file is
quite simple: a left-to-right ordered array of objects that represent a
monitor.

Your computing device is said to be `docked` when all configured monitors
are connected.

```
# $HOME/.config/mond/config.json
[
	{
		# Monitor device name in `xrandr`
		"name": "DP-0",

		# Monitor enabled while docked
		"docked": true
	},
	{
		"name": "DP-2",
		"docked": true
	},
	{
		"name": "eDP-1-1",
		"docked": false
	}
]
```

