#!/usr/bin/env python3
import sys
import os
import json
import argparse
import logging
import re
import time
from subprocess import Popen, PIPE

# Program return codes
ARGUMENT_ERROR = 1
CONFIG_NOT_FOUND_ERROR = 2
CONFIG_ERROR = 3
HOME_NOT_FOUND_ERROR = 4
OK = 0

# Last command global cache
last_cmd = None
running = True

class ProcessError(Exception): pass

def get_xrandr_output():
  proc = Popen(["xrandr"], stdout=PIPE, stderr=PIPE)
  out, err = proc.communicate()
  if proc.returncode != 0:
    raise ProcessError("xrandr returned %d during execution" % proc.returncode)
  return out.decode("UTF-8")

def get_xrandr_active_monitors():
  proc = Popen(["xrandr", "--listactivemonitors"], stdout=PIPE, stderr=PIPE)
  out, err = proc.communicate()
  if proc.returncode != 0:
    raise ProcessError("xrandr --listactivemonitors returned %d during execution" % proc.returncode)
  return out.decode("UTF-8")

def get_active_monitors():
  monitors = []
  output = get_xrandr_active_monitors()
  for line in output.splitlines():
    if line[0] == ' ':
      pos = line.rfind(' ') + 1
      end = len(line)
      monitors.append(line[pos : end])
  return monitors

def get_monitors():
  monitors = []
  output = get_xrandr_output()
  for line in output.splitlines():
    if " connected" in line:
      pos = line.find(' ')
      monitors.append(line[:pos])
  return monitors

def docked_monitors(monitors, config):
  docked = {
    e["name"] for e in config if e["docked"]
  }
  output = []
  for monitor in monitors:
    if monitor in docked:
      output.append(monitor)
  return output

def is_docked(monitors, config):
  config_set = { e["name"] for e in config }
  logging.debug("config_set: %s" % str(config_set))
  for monitor in monitors:
    if not monitor in config_set:
      return False
  return len(monitors) == len(config)

def fix_monitors(monitors, active, config):
  found = 0
  cmd = ["xrandr"]

  valid_monitors = monitors
  if is_docked(monitors, config):
    valid_monitors = docked_monitors(monitors, config)

  last = config[0]["name"]
  for monitor in config:
    if monitor["name"] in valid_monitors:
      cmd.append("--output")
      cmd.append(monitor["name"])
      cmd.append("--auto")
      if found == 0:
        cmd.append("--primary")
      else:
        cmd.append("--right-of")
        cmd.append(last)
      found += 1
    else:
      cmd.append("--output")
      cmd.append(monitor["name"])
      cmd.append("--off")
    last = monitor["name"]

  global last_cmd
  rc = 0

  if cmd != last_cmd:
    logging.info("Executing: '%s'" % ' '.join(cmd))
    proc = Popen(cmd, stdout=PIPE, stderr=PIPE)
    proc.wait()
    rc = proc.returncode
    last_cmd = cmd

  return rc == 0

def do_manage(config, timeout):
  # Convert config list into { "name": <config_item> }

  logging.info("mond started")
  is_running = True
  while is_running:
    monitors = []
    active_monitors = []
    try:
      monitors = get_monitors()
      active_monitors = get_active_monitors()
    except ProcessError as e:
      logging.error(e)
      logging.error("quitting...")
      break

    fix_monitors(monitors, active_monitors, config)

    logging.debug("Monitors: %s" % str(monitors))
    logging.debug("Active Monitors: %s" % str(active_monitors))
    time.sleep(timeout)

    global running
    is_running = running

def parse_arguments(args):
  parser = argparse.ArgumentParser()
  parser.add_argument(
      "-d", "--daemon",
      dest="daemon",
      action="store_true",
      default=False)
  parser.add_argument(
      "-v", "--verbose",
      dest="verbose",
      action="store_true",
      default=False)
  parser.add_argument(
      "-l", "--log",
      dest="log_path",
      default=None)
  parser.add_argument(
      "-t", "--timeout",
      dest="timeout",
      default=5)
  args = parser.parse_args(args)
  if args.daemon and not args.log_path:
    raise ValueError("--daemon requires a --log to be provided")
  return args

def main(): 
  try:
    args = parse_arguments(sys.argv[1:])
  except ValueError as e:
    print("ERROR: %s" % e)
    return ARGUMENT_ERROR

  # Setup logging
  log_level = logging.INFO
  if args.verbose:
    log_level = logging.DEBUG

  if args.log_path:
    logging.basicConfig(
        filename=args.log_path,
        level=log_level,
        format="%(levelname)s: %(message)s")
  else:
    logging.basicConfig(
        level=log_level,
        format="%(levelname)s: %(message)s")

  logging.debug("Starting mond...")

  if "HOME" not in os.environ:
    logging.error("Unable to find HOME environment variable")
    return HOME_NOT_FOUND_ERROR

  home_dir = os.environ["HOME"]
  config_dir = os.path.join(home_dir, ".config/mond")
  config_path = os.path.join(config_dir, "config.json")
  if not os.path.exists(config_path):
    logging.error("Configuration file not found at %s" % config_path)
    return CONFIG_NOT_FOUND_ERROR

  config = None
  try:
    with open(config_path) as f:
      config = json.load(f)
  except Exception as e:
    logging.error("Encountered an error while loading %s..." % config_path)
    logging.error(e)
    return CONFIG_ERROR

  if args.daemon:
    # If -d was given, fork and allow the child to do_manage
    pid = os.fork()
    if pid == 0:
      do_manage(config, args.timeout)
  else:
    # Otherwise, don't fork
    do_manage(config, args.timeout)

  return OK

if __name__ == "__main__": # pragma: no cover
  e = main() # pragma: no cover
  exit(e) # pragma: no cover
