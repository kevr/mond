""" Simple test cases for the `mond` python program. """
import sys

# Mock version of a process that let's us change what we return
# in the mocking process.
class MockProcess:
  def __init__(self, cmd=[], rv=0, out='', active_out=''):
    self.returncode = rv
    self.cmd = cmd
    self.out = out.encode("UTF-8")
    self.active_out = active_out.encode("UTF-8")

  def communicate(self):
    print(self.cmd)
    if len(self.cmd) > 1 and "--listactivemonitors" in self.cmd:
      return (self.active_out, b'')
    return (self.out, b'')

  def wait(self):
    pass

# Make a function wrapper for Popen that would create
# a MockProcess when called.
def make_mock_popen(rv, out='', active_out=''):
  def Popen(command, stdout=None, stderr=None):
    return MockProcess(cmd=command, rv=rv, out=out, active_out=active_out)
  return Popen

# Perform some generic test mocks for mond and return the module.
def mock_mond(mocker, argv):
  mocker.patch('mond.running', False)
  mocker.patch('time.sleep', lambda secs: secs)
  mocker.patch('sys.argv', ["mond"] + argv)

  import mond
  return mond

def test_verbose(mocker):
  mocker.patch('mond.Popen', make_mock_popen(0))

  mond = mock_mond(mocker, ["-v"])
  mond.main()

def test_no_home_var(mocker):
  mocker.patch('os.environ', {})
  import os
  mond = mock_mond(mocker, ["-v"])
  rc = mond.main()
  assert rc == mond.HOME_NOT_FOUND_ERROR

def test_daemon_no_log(mocker):
  mond = mock_mond(mocker, ["--daemon"])
  rc = mond.main()
  assert rc == mond.ARGUMENT_ERROR

def test_daemon(mocker):

  mocker.patch('os.fork', return_value=0)
  mocker.patch('mond.Popen', make_mock_popen(0))

  import os
  mond = mock_mond(mocker, ["--daemon", "--log", "test.log"])
  mond.main()

  os.fork.assert_called()

def test_no_config(mocker):
  mocker.patch('mond.os.path.exists', return_value=False)

  mond = mock_mond(mocker, ["-v"])
  rc = mond.main()
  mond.os.path.exists.assert_called()

  assert rc == mond.CONFIG_NOT_FOUND_ERROR

def test_bad_config(mocker):
  mocker.patch('mond.os.path.exists', return_value=True)
  mocker.patch('mond.open', mocker.mock_open(read_data="BAD".encode("UTF-8")))

  mond = mock_mond(mocker, ["-v"])
  rc = mond.main()
  mond.os.path.exists.assert_called()
  mond.open.assert_called()

  assert rc == mond.CONFIG_ERROR

def test_docked(mocker):
  config = """
  [{"name": "DP-0", "docked": true}, {"name": "DP-2", "docked": true}]
  """

  mocker.patch('mond.os.path.exists', return_value=True)
  mocker.patch('mond.open',
    mocker.mock_open(read_data=config.encode("UTF-8"))
  )

  out = '''Screen 0: minimum 8 x 8, current 6400 x 2160, maximum 32767 x 32767
DP-0 connected primary 2560x1440+0+0 (normal left inverted right x axis y axis) 708mm x 399mm
	2560x1440     59.95*+  74.99
	1920x1200     59.88
	1920x1080     60.00    59.94    50.00
	1680x1050     59.95
	1600x1200     60.00
	1280x1024     75.02    60.02
	1280x800      59.81
	1280x720      60.00    59.94    50.00
	1152x864      75.00
	1024x768      75.03    60.00
	800x600       75.00    60.32
	720x576       50.00
	720x480       59.94
	640x480       75.00    59.94    59.93
DP-1 disconnected (normal left inverted right x axis y axis)
HDMI-0 disconnected (normal left inverted right x axis y axis)
DP-2 connected 3840x2160+2560+0 (normal left inverted right x axis y axis) 697mm x 392mm
	3840x2160     60.00*+  30.00    29.97
	2560x1440     59.95
	1920x1080     60.00    59.94
	1680x1050     59.95
	1600x900      60.00
	1440x900      59.89
	1280x1024     75.02    60.02
	1280x800      59.81
	1280x720      60.00
	1152x864      75.00
	1024x768      75.03    70.07    60.00
	800x600       75.00    72.19    60.32    56.25
	640x480       75.00    72.81    59.94
DP-3 disconnected (normal left inverted right x axis y axis)'''

  active_out = '''Monitors: 2
 0: +*DP-0 2560/708x1440/399+0+0  DP-0
 1: +DP-2 3840/697x2160/392+2560+0  DP-2'''

  mocker.patch('mond.Popen', make_mock_popen(0,
    out=out, active_out=active_out))

  mond = mock_mond(mocker, ["-v"])
  rc = mond.main()

  mond.os.path.exists.assert_called()
  mond.open.assert_called()

def test_bad_xrandr_cases(mocker):
  """
  Test here that xrandr functions raise ProcessError when a
  non-zero return code is produced by `xrandr`.
  """

  config = """
  [{"name": "DP-0", "docked": true}, {"name": "DP-2", "docked": true}]
  """

  mocker.patch('mond.os.path.exists', return_value=True)
  mocker.patch('mond.open',
    mocker.mock_open(read_data=config.encode("UTF-8"))
  )

  # Set returncode to 1
  mocker.patch('mond.Popen', make_mock_popen(1))

  mond = mock_mond(mocker, ["-v"])
  try:
    mond.get_xrandr_active_monitors()
  except mond.ProcessError as e:
    pass

  try:
    mond.get_xrandr_output()
  except mond.ProcessError as e:
    pass

  mond.main()

def test_undocked_situation(mocker):
  """
  Test that having monitors we found missing from the config set
  causes us to be undocked.
  """

  config = """
  [{"name": "DP-0", "docked": true}]
  """

  mocker.patch('mond.os.path.exists', return_value=True)
  mocker.patch('mond.open',
    mocker.mock_open(read_data=config.encode("UTF-8"))
  )

  out = '''Screen 0: minimum 8 x 8, current 6400 x 2160, maximum 32767 x 32767
DP-0 connected primary 2560x1440+0+0 (normal left inverted right x axis y axis) 708mm x 399mm
	2560x1440     59.95*+  74.99
	1920x1200     59.88
	1920x1080     60.00    59.94    50.00
	1680x1050     59.95
	1600x1200     60.00
	1280x1024     75.02    60.02
	1280x800      59.81
	1280x720      60.00    59.94    50.00
	1152x864      75.00
	1024x768      75.03    60.00
	800x600       75.00    60.32
	720x576       50.00
	720x480       59.94
	640x480       75.00    59.94    59.93
DP-1 disconnected (normal left inverted right x axis y axis)
HDMI-0 disconnected (normal left inverted right x axis y axis)
DP-2 connected 3840x2160+2560+0 (normal left inverted right x axis y axis) 697mm x 392mm
	3840x2160     60.00*+  30.00    29.97
	2560x1440     59.95
	1920x1080     60.00    59.94
	1680x1050     59.95
	1600x900      60.00
	1440x900      59.89
	1280x1024     75.02    60.02
	1280x800      59.81
	1280x720      60.00
	1152x864      75.00
	1024x768      75.03    70.07    60.00
	800x600       75.00    72.19    60.32    56.25
	640x480       75.00    72.81    59.94
DP-3 disconnected (normal left inverted right x axis y axis)'''

  active_out = '''Monitors: 2
 0: +*DP-0 2560/708x1440/399+0+0  DP-0
 1: +DP-2 3840/697x2160/392+2560+0  DP-2'''

  # Set returncode to 1
  mocker.patch('mond.Popen', make_mock_popen(0, out=out, active_out=active_out))

  mond = mock_mond(mocker, ["-v"])
  try:
    mond.get_xrandr_active_monitors()
  except mond.ProcessError as e:
    pass

  try:
    mond.get_xrandr_output()
  except mond.ProcessError as e:
    pass

  rc = mond.main()
  assert rc == mond.OK
