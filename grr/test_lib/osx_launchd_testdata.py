#!/usr/bin/env python
"""OS X Launchd process listing test data.

These dicts are python representations of the pyobjc NSCFDictionarys returned by
the ServiceManagement framework.  It's close enough to the pyobjc object that we
can use it to test the parsing code without needing to run on OS X.
"""


# Disable some lint warnings to avoid tedious fixing of test data
# pylint: disable=g-line-too-long

# Number of entries we expect to be dropped due to filtering
FILTERED_COUNT = 84


class FakeCFDict(object):
  """Fake out the CFDictionary python wrapper."""

  def __init__(self, value):
    self.value = value

  def __contains__(self, key):
    return key in self.value

  def __getitem__(self, key):
    return self.value[key]

  # pylint: disable=g-bad-name
  def get(self, key, default='', stringify=False):
    if key in self.value:
      if stringify:
        obj = str(self.value[key])
      else:
        obj = self.value[key]
    else:
      obj = default
    return obj

  # pylint: enable=g-bad-name


class FakeCFObject(object):
  """Fake CFString and other wrapped objects."""

  def __init__(self, value):
    self.value = value

  def __int__(self):
    return int(self.value)


JOB = [
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'com.apple.FileSyncAgent.PHD',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Background',
        'MachServices': {
            'com.apple.FileSyncAgent.PHD': 0,
            'com.apple.FileSyncAgent.PHD.isRunning': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/CoreServices/FileSyncAgent.app/Contents/MacOS/FileSyncAgent'
            ),
            FakeCFObject('-launchedByLaunchd'),
            FakeCFObject('-PHDPlist')
        ],
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            '-1',
    }),
]

JOBS = [
    FakeCFDict({
        'Label':
            '0x7f8759d20ab0.mach_init.Inspector',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            '[0x0-0x4d44d4].com.google.GoogleTalkPluginD[32298].subset.257',
        'MachServices': {
            'com.Google.BreakpadInspector32298': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/Library/Application '
                'Support/Google/GoogleTalkPlugin.app/Contents/Frameworks/GoogleBreakpad.framework/Versions/A/Resources/Inspector'
            ),
            FakeCFObject('com.Google.BreakpadInspector32298')
        ],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label':
            '0x7f8759c23570.mach_init.crash_inspector',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Google Chrome H[32284].subset.584',
        'MachServices': {
            'com.Breakpad.Inspector32284': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/Applications/Google '
                'Chrome.app/Contents/Versions/21.0.1180.79/Google Chrome '
                'Framework.framework/Resources/crash_inspector'),
            FakeCFObject('com.Breakpad.Inspector32284')
        ],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': 'com.apple.coreservices.appleid.authentication',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.coreservices.appleid.authentication': 0,
        },
        'OnDemand': FakeCFObject(1),
        'Program': '/System/Library/CoreServices/AppleIDAuthAgent',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759d30310.anonymous.launchd',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Google Chrome H[35271].subset.440',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(499),
        'Program': 'launchd',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759c23ae0.anonymous.launchd',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Google Chrome H[32282].subset.281',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(499),
        'Program': 'launchd',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label':
            '0x7f8759d30610.mach_init.crash_inspector',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Google Chrome H[35271].subset.440',
        'MachServices': {
            'com.Breakpad.Inspector35271': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/Applications/Google '
                'Chrome.app/Contents/Versions/21.0.1180.79/Google Chrome '
                'Framework.framework/Resources/crash_inspector'),
            FakeCFObject('com.Breakpad.Inspector35271')
        ],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': 'com.apple.systemprofiler',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.systemprofiler': 0,
        },
        'OnDemand': FakeCFObject(1),
        'Program': '/Applications/Utilities/System '
                   'Information.app/Contents/MacOS/System Information',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759d2b140.anonymous.bash',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(69813),
        'Program': 'login',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759d318d0.anonymous.Google Chrome H',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {},
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(60522),
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.axserver': 0,
            'com.apple.tsm.portname': 0,
        },
        'Program': 'Google Chrome H',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759d1fb70.anonymous.Google Chrome H',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {},
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(32285),
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.axserver': 0,
            'com.apple.tsm.portname': 0,
        },
        'Program': 'Google Chrome H',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759c22f60.anonymous.Google Chrome',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Google Chrome H[32284].subset.584',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(32275),
        'Program': 'Google Chrome',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'com.apple.FontWorker',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.FontWorker': 0,
            'com.apple.FontWorker.ATS': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'Program':
            '/System/Library/Frameworks/ApplicationServices.framework/Versions/A/Frameworks/ATS.framework/Versions/A/Support/fontworker',
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            '-1',
    }),
    FakeCFDict({
        'Label':
            '0x7f8759d1d200.mach_init.crash_inspector',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            '[0x0-0x4c54c5].com.google.Chrome[32275].subset.632',
        'MachServices': {
            'com.Breakpad.Inspector32275': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/Applications/Google '
                'Chrome.app/Contents/Versions/21.0.1180.79/Google Chrome '
                'Framework.framework/Resources/crash_inspector'),
            FakeCFObject('com.Breakpad.Inspector32275')
        ],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label':
            'com.apple.UserNotificationCenterAgent',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.UNCUserNotificationAgent': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/CoreServices/UserNotificationCenter.app/Contents/MacOS/UserNotificationCenter'
            )
        ],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759d30f40.anonymous.Google Chrome C',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Google Chrome H[60520].subset.399',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(60513),
        'Program': 'Google Chrome C',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label':
            'com.apple.bluetoothUIServer',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.bluetoothUIServer': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'Program':
            '/System/Library/CoreServices/BluetoothUIServer.app/Contents/MacOS/BluetoothUIServer',
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'com.apple.SubmitDiagInfo',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject('/System/Library/CoreServices/SubmitDiagInfo')
        ],
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            '-1',
    }),
    FakeCFDict({
        'EnableTransactions': 1,
        'Label': 'com.apple.gssd-agent',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Background',
        'MachServices': {
            'com.apple.gssd-agent': 0,
        },
        'OnDemand': FakeCFObject(1),
        'Program': '/usr/sbin/gssd',
        'ProgramArguments': [FakeCFObject('gssd-agent')],
        'TimeOut': FakeCFObject(30),
        'TransactionCount': '-1',
    }),
    FakeCFDict({
        'Label':
            '[0x0-0x4d44d4].com.google.GoogleTalkPluginD',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {},
        'OnDemand':
            FakeCFObject(1),
        'PID':
            FakeCFObject(32298),
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.CFPasteboardClient': 0,
            'com.apple.axserver': 0,
            'com.apple.tsm.portname': 0,
        },
        'ProgramArguments': [
            FakeCFObject(
                '/Library/Application '
                'Support/Google/GoogleTalkPlugin.app/Contents/MacOS/GoogleTalkPlugin'
            ),
            FakeCFObject('-psn_0_5063892')
        ],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'com.apple.quicklook.config',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.quicklook.config': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/Frameworks/QuickLook.framework/Resources/quicklookconfig'
            )
        ],
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            '-1',
    }),
    FakeCFDict({
        'Label': '0x7f8759c2fda0.anonymous.login',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(83461),
        'Program': 'login',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759c12410.anonymous.Google Chrome H',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {},
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(32297),
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.CFPasteboardClient': 0,
            'com.apple.axserver': 0,
            'com.apple.tsm.portname': 0,
        },
        'Program': 'Google Chrome H',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759c2cec0.anonymous.bash',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(73991),
        'Program': 'login',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759c24ca0.anonymous.login',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(24592),
        'Program': 'login',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label':
            '0x7f8759c17720.mach_init.crash_inspector',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Google Chrome H[35104].subset.553',
        'MachServices': {
            'com.Breakpad.Inspector35104': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/Applications/Google '
                'Chrome.app/Contents/Versions/21.0.1180.79/Google Chrome '
                'Framework.framework/Resources/crash_inspector'),
            FakeCFObject('com.Breakpad.Inspector35104')
        ],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759d1cf00.anonymous.login',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(38234),
        'Program': 'login',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759c2e870.anonymous.configd',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Background',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(17),
        'Program': 'configd',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label':
            '0x7f8759c23de0.mach_init.crash_inspector',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Google Chrome H[32282].subset.281',
        'MachServices': {
            'com.Breakpad.Inspector32282': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/Applications/Google '
                'Chrome.app/Contents/Versions/21.0.1180.79/Google Chrome '
                'Framework.framework/Resources/crash_inspector'),
            FakeCFObject('com.Breakpad.Inspector32282')
        ],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'EnableTransactions': 1,
        'Label': 'com.apple.spindump_agent',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.spinreporteragent': 0,
        },
        'OnDemand': FakeCFObject(1),
        'ProgramArguments': [FakeCFObject('/usr/libexec/spindump_agent')],
        'TimeOut': FakeCFObject(30),
        'TransactionCount': '-1',
    }),
    FakeCFDict({
        'Label': '0x7f8759c16550.anonymous.login',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(73954),
        'Program': 'login',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759c2f1a0.anonymous.configd',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(17),
        'Program': 'configd',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'com.apple.ZoomWindow',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.ZoomWindow.running': 0,
            'com.apple.ZoomWindow.startup': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/CoreServices/ZoomWindow.app/Contents/MacOS/ZoomWindowStarter'
            ),
            FakeCFObject('launchd'),
            FakeCFObject('-s')
        ],
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            '-1',
    }),
    FakeCFDict({
        'Label': '0x7f8759c17a30.anonymous.Google Chrome H',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {},
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(35104),
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.axserver': 0,
            'com.apple.tsm.portname': 0,
        },
        'Program': 'Google Chrome H',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label':
            'com.apple.syncservices.uihandler',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.syncservices.uihandler': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'Program':
            '/System/Library/PrivateFrameworks/SyncServicesUI.framework/Versions/Current/Resources/syncuid.app/Contents/MacOS/syncuid',
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759c17110.anonymous.Google Chrome',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Google Chrome H[35104].subset.553',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(32275),
        'Program': 'Google Chrome',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label':
            'com.apple.DictionaryPanelHelper',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.DictionaryPanelHelper': 0,
            'com.apple.DictionaryPanelHelper.reply': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'Program':
            '/Applications/Dictionary.app/Contents/SharedSupport/DictionaryPanelHelper.app/Contents/MacOS/DictionaryPanelHelper',
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759c1d630.anonymous.Python',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Background',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(69592),
        'Program': 'python',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'EnableTransactions': 1,
        'Label': 'com.apple.talagent',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.window_proxies': 0,
            'com.apple.window_proxies.startup': 0,
        },
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(639),
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.CFPasteboardClient': 0,
            'com.apple.axserver': 0,
            'com.apple.tsm.portname': 0,
        },
        'Program': '/System/Library/CoreServices/talagent',
        'TimeOut': FakeCFObject(30),
        'TransactionCount': 0,
    }),
    FakeCFDict({
        'Label': '0x7f8759c1f7f0.anonymous.Google Chrome H',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Google Chrome H[60522].subset.309',
        'MachServices': {
            'com.Breakpad.BootstrapParent': 0,
        },
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(60522),
        'Program': 'Google Chrome H',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label':
            'com.apple.speech.recognitionserver',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.speech.recognitionserver': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'Program':
            '/System/Library/Frameworks/Carbon.framework/Frameworks/SpeechRecognition.framework/Versions/A/SpeechRecognitionServer.app/Contents/MacOS/SpeechRecognitionServer',
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759c2faa0.anonymous.Python',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(82320),
        'Program': 'python',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'com.apple.cvmsCompAgent_x86_64',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Background',
        'MachServices': {
            'com.apple.cvmsCompAgent_x86_64': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/Frameworks/OpenGL.framework/Versions/A/Libraries/CVMCompiler'
            ),
            FakeCFObject('1')
        ],
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            '-1',
    }),
    FakeCFDict({
        'Label': '0x7f8759c23270.anonymous.launchd',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Google Chrome H[32284].subset.584',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(499),
        'Program': 'launchd',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759d30c30.anonymous.Google Chrome H',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Google Chrome H[60520].subset.399',
        'MachServices': {
            'com.Breakpad.BootstrapParent': 0,
        },
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(60520),
        'Program': 'Google Chrome H',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'com.apple.printuitool.agent',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.printuitool.agent': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/PrivateFrameworks/PrintingPrivate.framework/Versions/A/PrintUITool'
            )
        ],
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            '-1',
    }),
    FakeCFDict({
        'Label': '0x7f8759d29b20.anonymous.bash',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(46172),
        'Program': 'login',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'com.apple.coreservices.uiagent',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.coreservices.launcherror-handler': 0,
            'com.apple.coreservices.quarantine-resolver': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'Program':
            '/System/Library/CoreServices/CoreServicesUIAgent.app/Contents/MacOS/CoreServicesUIAgent',
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            '-1',
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'com.apple.mdworker.pool.1',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Background',
        'MachServices': {
            'com.apple.mdworker.pool.1': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/Frameworks/CoreServices.framework/Frameworks/Metadata.framework/Versions/A/Support/mdworker'
            ),
            FakeCFObject('-s'),
            FakeCFObject('mdworker'),
            FakeCFObject('-c'),
            FakeCFObject('MDSImporterWorker'),
            FakeCFObject('-m'),
            FakeCFObject('com.apple.mdworker.pool.1')
        ],
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            '-1',
    }),
    FakeCFDict({
        'Label':
            '[0x0-0x21021].com.google.GoogleDrive',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {},
        'OnDemand':
            FakeCFObject(1),
        'PID':
            FakeCFObject(763),
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.CFPasteboardClient': 0,
            'com.apple.axserver': 0,
            'com.apple.coredrag': 0,
            'com.apple.tsm.portname': 0,
        },
        'ProgramArguments': [
            FakeCFObject(
                '/Applications/Google Drive.app/Contents/MacOS/Google Drive'),
            FakeCFObject('-psn_0_135201')
        ],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'com.apple.cvmsCompAgent_i386',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Background',
        'MachServices': {
            'com.apple.cvmsCompAgent_i386': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/Frameworks/OpenGL.framework/Versions/A/Libraries/CVMCompiler'
            ),
            FakeCFObject('1')
        ],
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            '-1',
    }),
    FakeCFDict({
        'Label': '0x7f8759c2b8b0.anonymous.Google Chrome H',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Google Chrome H[32284].subset.584',
        'MachServices': {
            'com.Breakpad.BootstrapParent': 0,
        },
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(32284),
        'Program': 'Google Chrome H',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759d1f860.anonymous.Google Chrome H',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {},
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(32283),
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.axserver': 0,
            'com.apple.tsm.portname': 0,
        },
        'Program': 'Google Chrome H',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'com.apple.VoiceOver',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.VoiceOver.running': 0,
            'com.apple.VoiceOver.startup': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/CoreServices/VoiceOver.app/Contents/MacOS/VoiceOver'
            ),
            FakeCFObject('launchd'),
            FakeCFObject('-s')
        ],
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            '-1',
    }),
    FakeCFDict({
        'Label': '0x7f8759d2e7b0.anonymous.tail',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(74455),
        'Program': 'tail',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label':
            'com.apple.PreferenceSyncAgent',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/CoreServices/PreferenceSyncClient.app/Contents/MacOS/PreferenceSyncClient'
            ),
            FakeCFObject('--sync'),
            FakeCFObject('--periodic')
        ],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759c15a50.anonymous.login',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Background',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(38234),
        'Program': 'login',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'com.apple.mdworker.i386.framework.0',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Background',
        'MachServices': {
            'com.apple.mdworker.i386.framework.0': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/Frameworks/CoreServices.framework/Frameworks/Metadata.framework/Versions/A/Support/mdworker32'
            ),
            FakeCFObject('-s'),
            FakeCFObject('mdworker-lsb'),
            FakeCFObject('-c'),
            FakeCFObject('MDSImporterWorker'),
            FakeCFObject('-m'),
            FakeCFObject('com.apple.mdworker.i386.framework.0')
        ],
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            '-1',
    }),
    FakeCFDict({
        'Label':
            'com.apple.launchctl.Background',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Background',
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject('/bin/launchctl'),
            FakeCFObject('bootstrap'),
            FakeCFObject('-S'),
            FakeCFObject('Background')
        ],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label':
            'com.apple.speech.synthesisserver',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.speech.synthesis.ScreenReaderPort': 0,
            'com.apple.speech.synthesis.SpeakingHotKeyPort': 0,
            'com.apple.speech.synthesis.TimeAnnouncementsPort': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'Program':
            '/System/Library/Frameworks/ApplicationServices.framework/Versions/A/Frameworks/SpeechSynthesis.framework/Versions/A/SpeechSynthesisServer.app/Contents/MacOS/SpeechSynthesisServer',
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label':
            '0x7f8759d207b0.anonymous.launchd',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            '[0x0-0x4d44d4].com.google.GoogleTalkPluginD[32298].subset.257',
        'OnDemand':
            FakeCFObject(1),
        'PID':
            FakeCFObject(499),
        'Program':
            'launchd',
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label':
            'com.apple.ATS.FontValidatorConduit',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.ATS.FontValidatorConduit': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'Program':
            '/System/Library/Frameworks/ApplicationServices.framework/Versions/A/Frameworks/ATS.framework/Versions/A/Support/FontValidatorConduit',
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'com.apple.fontd',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.FontObjectsServer': 0,
            'com.apple.FontServer': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'PID':
            FakeCFObject(640),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/Frameworks/ApplicationServices.framework/Frameworks/ATS.framework/Support/fontd'
            )
        ],
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            0,
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'com.apple.quicklook',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.quicklook': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/Frameworks/QuickLook.framework/Resources/quicklookd.app/Contents/MacOS/quicklookd'
            )
        ],
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            '-1',
    }),
    FakeCFDict({
        'Label': '0x7f8759d29e20.anonymous.Google Chrome H',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {},
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(35271),
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.axserver': 0,
            'com.apple.tsm.portname': 0,
        },
        'Program': 'Google Chrome H',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759d20db0.anonymous.sshd',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Background',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(68600),
        'Program': 'sshd',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'com.apple.unmountassistant.useragent',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.unmountassistant.useragent': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/CoreServices/UnmountAssistantAgent.app/Contents/MacOS/UnmountAssistantAgent'
            )
        ],
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            '-1',
    }),
    FakeCFDict({
        'Label': '0x7f8759d1ebf0.anonymous.Google Chrome H',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {},
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(32282),
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.axserver': 0,
            'com.apple.tsm.portname': 0,
        },
        'Program': 'Google Chrome H',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label':
            'com.apple.installd.user',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.installd.user': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/PrivateFrameworks/PackageKit.framework/Resources/installd'
            )
        ],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759d33ce0.anonymous.login',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(46170),
        'Program': 'login',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759c240f0.anonymous.Google Chrome H',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {},
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(32284),
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.axserver': 0,
            'com.apple.tsm.portname': 0,
        },
        'Program': 'Google Chrome H',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label':
            'com.apple.syncdefaultsd',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.syncdefaultsd': 0,
            'com.apple.syncdefaultsd.push': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/PrivateFrameworks/SyncedDefaults.framework/Support/syncdefaultsd'
            )
        ],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label':
            'com.apple.marcoagent',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.marco': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/PrivateFrameworks/Marco.framework/marcoagent')
        ],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'com.apple.distnoted.xpc.agent',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Background',
        'MachServices': {
            'com.apple.distributed_notifications@Uv3': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'PID':
            FakeCFObject(625),
        'ProgramArguments': [
            FakeCFObject('/usr/sbin/distnoted'),
            FakeCFObject('agent')
        ],
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            42,
    }),
    FakeCFDict({
        'Label': '0x7f8759c2eb70.anonymous.Google Chrome H',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Google Chrome H[32282].subset.281',
        'MachServices': {
            'com.Breakpad.BootstrapParent': 0,
        },
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(32282),
        'Program': 'Google Chrome H',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759d28f10.anonymous.login',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Background',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(83461),
        'Program': 'login',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759c1fb00.anonymous.Google Chrome C',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Google Chrome H[60522].subset.309',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(60513),
        'Program': 'Google Chrome C',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label':
            'com.apple.bluetoothAudioAgent',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.bluetoothAudioAgent': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/CoreServices/BluetoothAudioAgent.app/Contents/MacOS/BluetoothAudioAgent'
            )
        ],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'com.apple.mdworker.pool.framework.0',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Background',
        'MachServices': {
            'com.apple.mdworker.pool.framework.0': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/Frameworks/CoreServices.framework/Frameworks/Metadata.framework/Versions/A/Support/mdworker'
            ),
            FakeCFObject('-s'),
            FakeCFObject('mdworker'),
            FakeCFObject('-c'),
            FakeCFObject('MDSImporterWorker'),
            FakeCFObject('-m'),
            FakeCFObject('com.apple.mdworker.pool.framework.0')
        ],
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            '-1',
    }),
    FakeCFDict({
        'Label':
            '0x7f8759d20190.mach_init.crash_inspector',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Google Chrome H[32297].subset.637',
        'MachServices': {
            'com.Breakpad.Inspector32297': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/Applications/Google '
                'Chrome.app/Contents/Versions/21.0.1180.79/Google Chrome '
                'Framework.framework/Resources/crash_inspector'),
            FakeCFObject('com.Breakpad.Inspector32297')
        ],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            '[0x0-0x19019].com.apple.AppleSpell',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'Multilingual (Apple)_OpenStep': 0,
            'da (Apple)_OpenStep': 0,
            'de (Apple)_OpenStep': 0,
            'en (Apple)_OpenStep': 0,
            'en_AU (Apple)_OpenStep': 0,
            'en_CA (Apple)_OpenStep': 0,
            'en_GB (Apple)_OpenStep': 0,
            'en_JP (Apple)_OpenStep': 0,
            'en_US (Apple)_OpenStep': 0,
            'es (Apple)_OpenStep': 0,
            'fr (Apple)_OpenStep': 0,
            'it (Apple)_OpenStep': 0,
            'nl (Apple)_OpenStep': 0,
            'pt (Apple)_OpenStep': 0,
            'pt_BR (Apple)_OpenStep': 0,
            'pt_PT (Apple)_OpenStep': 0,
            'ru (Apple)_OpenStep': 0,
            'sv (Apple)_OpenStep': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'PID':
            FakeCFObject(727),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/Services/AppleSpell.service/Contents/MacOS/AppleSpell'
            ),
            FakeCFObject('-psn_0_102425')
        ],
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            0,
    }),
    FakeCFDict({
        'Label': '0x7f8759d22370.anonymous.Google Chrome',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Google Chrome H[32656].subset.619',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(32275),
        'Program': 'Google Chrome',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label':
            '0x7f8759d2f3c0.mach_init.crash_inspector',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            '[0x0-0x34c34c].com.google.Chrome.canary[60513].subset.374',
        'MachServices': {
            'com.Breakpad.Inspector60513': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/Applications/Google Chrome '
                'Canary.app/Contents/Versions/180.1.1025.40/Google Chrome '
                'Framework.framework/Resources/crash_inspector'),
            FakeCFObject('com.Breakpad.Inspector60513')
        ],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'com.apple.mdworker.pool.framework.1',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Background',
        'MachServices': {
            'com.apple.mdworker.pool.framework.1': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/Frameworks/CoreServices.framework/Frameworks/Metadata.framework/Versions/A/Support/mdworker'
            ),
            FakeCFObject('-s'),
            FakeCFObject('mdworker'),
            FakeCFObject('-c'),
            FakeCFObject('MDSImporterWorker'),
            FakeCFObject('-m'),
            FakeCFObject('com.apple.mdworker.pool.framework.1')
        ],
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            '-1',
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'com.apple.mdworker.lsb.framework.0',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Background',
        'MachServices': {
            'com.apple.mdworker.lsb.framework.0': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/Frameworks/CoreServices.framework/Frameworks/Metadata.framework/Versions/A/Support/mdworker'
            ),
            FakeCFObject('-s'),
            FakeCFObject('mdworker-lsb'),
            FakeCFObject('-c'),
            FakeCFObject('MDSImporterWorker'),
            FakeCFObject('-m'),
            FakeCFObject('com.apple.mdworker.lsb.framework.0')
        ],
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            '-1',
    }),
    FakeCFDict({
        'Label': '0x7f8759c16060.anonymous.bash',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Background',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(68666),
        'Program': 'sshd',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'com.apple.store_helper',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.store_helper': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'Program':
            '/System/Library/PrivateFrameworks/CommerceKit.framework/Resources/store_helper.app/Contents/MacOS/store_helper',
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            '-1',
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'com.apple.mdworker.pool.framework.2',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Background',
        'MachServices': {
            'com.apple.mdworker.pool.framework.2': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/Frameworks/CoreServices.framework/Frameworks/Metadata.framework/Versions/A/Support/mdworker'
            ),
            FakeCFObject('-s'),
            FakeCFObject('mdworker'),
            FakeCFObject('-c'),
            FakeCFObject('MDSImporterWorker'),
            FakeCFObject('-m'),
            FakeCFObject('com.apple.mdworker.pool.framework.2')
        ],
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            '-1',
    }),
    FakeCFDict({
        'Label':
            'com.apple.FontRegistryUIAgent',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.FontRegistry.FontRegistryUIAgent': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'Program':
            '/System/Library/Frameworks/ApplicationServices.framework/Frameworks/ATS.framework/Support/FontRegistryUIAgent.app/Contents/MacOS/FontRegistryUIAgent',
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label':
            'com.apple.softwareupdateagent',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject('/System/Library/CoreServices/Software '
                         'Update.app/Contents/Resources/SoftwareUpdateCheck'),
            FakeCFObject('-LaunchApp'),
            FakeCFObject('YES')
        ],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label':
            'com.apple.ubd',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/PrivateFrameworks/Ubiquity.framework/Versions/A/Support/ubd'
            )
        ],
        'Sockets': {
            'Apple_Ubiquity_Message': ('-1'),
        },
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759d07d60.anonymous.applepushservic',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Background',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(85),
        'Program': 'applepushservic',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759c1c700.anonymous.Google Chrome H',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Google Chrome H[32291].subset.223',
        'MachServices': {
            'com.Breakpad.BootstrapParent': 0,
        },
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(32291),
        'Program': 'Google Chrome H',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759d2c7e0.anonymous.Google Chrome',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Google Chrome H[32438].subset.554',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(32275),
        'Program': 'Google Chrome',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759c103c0.anonymous.bash',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(24593),
        'Program': 'login',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'com.apple.mdworker.pool.framework.3',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Background',
        'MachServices': {
            'com.apple.mdworker.pool.framework.3': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/Frameworks/CoreServices.framework/Frameworks/Metadata.framework/Versions/A/Support/mdworker'
            ),
            FakeCFObject('-s'),
            FakeCFObject('mdworker'),
            FakeCFObject('-c'),
            FakeCFObject('MDSImporterWorker'),
            FakeCFObject('-m'),
            FakeCFObject('com.apple.mdworker.pool.framework.3')
        ],
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            '-1',
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'com.apple.ScreenReaderUIServer',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.ScreenReaderUIServer': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'Program':
            '/System/Library/PrivateFrameworks/ScreenReader.framework/Resources/ScreenReaderUIServer.app/Contents/MacOS/ScreenReaderUIServer',
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            '-1',
    }),
    FakeCFDict({
        'Label': '0x7f8759c1ab70.anonymous.Google Chrome',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Google Chrome H[32283].subset.231',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(32275),
        'Program': 'Google Chrome',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label':
            '[0x0-0x34c34c].com.google.Chrome.canary',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.google.Chrome.canary.rohitfork.60513': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'PID':
            FakeCFObject(60513),
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.CFPasteboardClient': 0,
            'com.apple.axserver': 0,
            'com.apple.coredrag': 0,
            'com.apple.tsm.portname': 0,
        },
        'ProgramArguments': [
            FakeCFObject(
                '/Applications/Google Chrome Canary.app/Contents/MacOS/Google '
                'Chrome Canary'),
            FakeCFObject('-psn_0_3457868')
        ],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759c1bde0.anonymous.launchd',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Google Chrome H[32285].subset.229',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(499),
        'Program': 'launchd',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'EnableTransactions': 1,
        'Label': 'com.apple.warmd_agent',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(737),
        'ProgramArguments': [FakeCFObject('/usr/libexec/warmd_agent')],
        'TimeOut': FakeCFObject(30),
        'TransactionCount': 0,
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'com.apple.ATS.FontValidator',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.ATS.FontValidator': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'Program':
            '/System/Library/Frameworks/ApplicationServices.framework/Versions/A/Frameworks/ATS.framework/Versions/A/Support/FontValidator',
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            '-1',
    }),
    FakeCFDict({
        'Label': '0x7f8759c115d0.anonymous.Google Chrome C',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Google Chrome H[60518].subset.363',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(60513),
        'Program': 'Google Chrome C',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'com.apple.mdworker.pool.3',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Background',
        'MachServices': {
            'com.apple.mdworker.pool.3': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/Frameworks/CoreServices.framework/Frameworks/Metadata.framework/Versions/A/Support/mdworker'
            ),
            FakeCFObject('-s'),
            FakeCFObject('mdworker'),
            FakeCFObject('-c'),
            FakeCFObject('MDSImporterWorker'),
            FakeCFObject('-m'),
            FakeCFObject('com.apple.mdworker.pool.3')
        ],
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            '-1',
    }),
    FakeCFDict({
        'Label':
            '0x7f8759c1e5a0.mach_init.crash_inspector',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Google Chrome H[60518].subset.363',
        'MachServices': {
            'com.Breakpad.Inspector60518': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/Applications/Google Chrome '
                'Canary.app/Contents/Versions/180.1.1025.40/Google Chrome '
                'Framework.framework/Resources/crash_inspector'),
            FakeCFObject('com.Breakpad.Inspector60518')
        ],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label':
            'com.apple.RemoteDesktop.agent',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.RemoteDesktop.agent': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'Program':
            '/System/Library/CoreServices/RemoteManagement/ARDAgent.app/Contents/MacOS/ARDAgent',
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759c24490.anonymous.launchd',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Google Chrome H[60518].subset.363',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(499),
        'Program': 'launchd',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759c18730.anonymous.sh',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(68799),
        'Program': 'sh',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759d2fcf0.anonymous.Google Chrome H',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Google Chrome H[35271].subset.440',
        'MachServices': {
            'com.Breakpad.BootstrapParent': 0,
        },
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(35271),
        'Program': 'Google Chrome H',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label':
            'com.apple.FTCleanup',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject('/bin/sh'),
            FakeCFObject('-c'),
            FakeCFObject(
                "if [ \"$HOME\" == \"/System\" ], then exit 0, fi, if [ -f "
                "\"$HOME/Library/LaunchAgents/com.apple.imagent.plist\" ] , "
                'then launchctl unload -wF '
                '~/Library/LaunchAgents/com.apple.imagent.plist , launchctl '
                'load -wF /System/Library/LaunchAgents/com.apple.imagent.plist'
                ' , fi , if [ -f '
                "\"$HOME/Library/LaunchAgents/com.apple.apsd-ft.plist\" ] , "
                "then launchctl unload -wF -S 'Aqua' "
                '~/Library/LaunchAgents/com.apple.apsd-ft.plist, fi , if [ -f '
                "\"$HOME/Library/LaunchAgents/com.apple.marcoagent.plist\" ] ,"
                ' then launchctl unload -wF '
                '~/Library/LaunchAgents/com.apple.marcoagent.plist , launchctl'
                ' load -wF '
                '/System/Library/LaunchAgents/com.apple.marcoagent.plist , fi '
                ', if [ -f '
                "\"$HOME/Library/LaunchAgents/com.apple.FTMonitor.plist\" ] , "
                'then launchctl unload -wF '
                '~/Library/LaunchAgents/com.apple.FTMonitor.plist , fi ,')
        ],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'com.apple.mdworker.isolation.0',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Background',
        'MachServices': {
            'com.apple.mdworker.isolation.0': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/Frameworks/CoreServices.framework/Frameworks/Metadata.framework/Versions/A/Support/mdworker'
            ),
            FakeCFObject('-s'),
            FakeCFObject('mdworker'),
            FakeCFObject('-c'),
            FakeCFObject('MDSImporterWorker'),
            FakeCFObject('-m'),
            FakeCFObject('com.apple.mdworker.isolation.0')
        ],
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            '-1',
    }),
    FakeCFDict({
        'Label':
            'com.apple.netauth.user.gui',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.netauth.user.gui': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/CoreServices/NetAuthAgent.app/Contents/MacOS/NetAuthAgent'
            )
        ],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759d28310.anonymous.bash',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(83462),
        'Program': 'login',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759d31250.anonymous.launchd',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Google Chrome H[60520].subset.399',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(499),
        'Program': 'launchd',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            '[0x0-0x9009].com.apple.Terminal',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.Terminal.ServiceProvider': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'PID':
            FakeCFObject(634),
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.CFPasteboardClient': 0,
            'com.apple.axserver': 0,
            'com.apple.coredrag': 0,
            'com.apple.tsm.portname': 0,
        },
        'ProgramArguments': [
            FakeCFObject(
                '/Applications/Utilities/Terminal.app/Contents/MacOS/Terminal'),
            FakeCFObject('-psn_0_36873')
        ],
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            1,
    }),
    FakeCFDict({
        'Label': '0x7f8759c2d1c0.anonymous.su',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(74539),
        'Program': 'su',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759c1d940.anonymous.sshd',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Background',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(68714),
        'Program': 'sshd',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'org.openbsd.ssh-agent',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'OnDemand':
            FakeCFObject(1),
        'PID':
            FakeCFObject(46009),
        'ProgramArguments': [
            FakeCFObject('/usr/bin/ssh-agent'),
            FakeCFObject('-l')
        ],
        'Sockets': {
            'Listeners': ('-1'),
        },
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            0,
    }),
    FakeCFDict({
        'Label':
            'com.apple.familycontrols.useragent',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.familycontrols.useragent': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/PrivateFrameworks/FamilyControls.framework/Resources/ParentalControls.app/Contents/MacOS/ParentalControls'
            )
        ],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759c1b7c0.anonymous.Google Chrome H',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Google Chrome H[32285].subset.229',
        'MachServices': {
            'com.Breakpad.BootstrapParent': 0,
        },
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(32285),
        'Program': 'Google Chrome H',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label':
            'com.apple.AppStoreUpdateAgent',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.AppStoreUpdateAgent': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'Program':
            '/Applications/App Store.app/Contents/Resources/appstoreupdateagent',
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label':
            'com.apple.csuseragent',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.csuseragent': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject('/System/Library/CoreServices/CSUserAgent')
        ],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label':
            'com.apple.PubSub.Agent',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.pubsub.ipc': 0,
            'com.apple.pubsub.notification': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/Frameworks/PubSub.framework/Versions/A/Resources/PubSubAgent.app/Contents/MacOS/PubSubAgent'
            )
        ],
        'Sockets': {
            'Render': ('-1'),
        },
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'com.apple.rcd',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.rcd': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/CoreServices/rcd.app/Contents/MacOS/rcd')
        ],
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            '-1',
    }),
    FakeCFDict({
        'Label':
            'com.apple.netauth.user.auth',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Background',
        'MachServices': {
            'com.apple.netauth.user.auth': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/CoreServices/NetAuthAgent.app/Contents/MacOS/NetAuthSysAgent'
            )
        ],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759c1dc40.anonymous.bash',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Background',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(68720),
        'Program': 'sshd',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759c2f7a0.anonymous.bash',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(75030),
        'Program': 'login',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label':
            'com.apple.BezelUIServer',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.BezelUI': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/LoginPlugins/BezelServices.loginPlugin/Contents/Resources/BezelUI/BezelUIServer'
            )
        ],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759c0cf00.anonymous.com.apple.dock.',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {},
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(652),
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.CFPasteboardClient': 0,
            'com.apple.axserver': 0,
            'com.apple.tsm.portname': 0,
        },
        'Program': 'com.apple.dock.',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759d28c10.anonymous.bash',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Background',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(83462),
        'Program': 'bash',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'EnableTransactions': 1,
        'Label': 'com.apple.xgridd',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.xgridd': 0,
        },
        'OnDemand': FakeCFObject(1),
        'ProgramArguments': [FakeCFObject('/usr/libexec/xgrid/xgridd')],
        'TimeOut': FakeCFObject(30),
        'TransactionCount': '-1',
    }),
    FakeCFDict({
        'Label':
            'com.apple.reclaimspace',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.ReclaimSpace': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'Program':
            '/System/Library/CoreServices/backupd.bundle/Contents/Resources/ReclaimSpaceAgent.app/Contents/MacOS/ReclaimSpaceAgent',
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label':
            '0x7f8759d31550.mach_init.crash_inspector',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Google Chrome H[60520].subset.399',
        'MachServices': {
            'com.Breakpad.Inspector60520': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/Applications/Google Chrome '
                'Canary.app/Contents/Versions/180.1.1025.40/Google Chrome '
                'Framework.framework/Resources/crash_inspector'),
            FakeCFObject('com.Breakpad.Inspector60520')
        ],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label':
            '[0x0-0x4c54c5].com.google.Chrome',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.google.Chrome.rohitfork.32275': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'PID':
            FakeCFObject(32275),
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.CFPasteboardClient': 0,
            'com.apple.axserver': 0,
            'com.apple.coredrag': 0,
            'com.apple.tsm.portname': 0,
        },
        'ProgramArguments': [
            FakeCFObject(
                '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'),
            FakeCFObject('-psn_0_5002437')
        ],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759c0c320.anonymous.loginwindow',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Background',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(71),
        'Program': 'loginwindow',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'com.apple.mdworker.lsb.0',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Background',
        'MachServices': {
            'com.apple.mdworker.lsb.0': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/Frameworks/CoreServices.framework/Frameworks/Metadata.framework/Versions/A/Support/mdworker'
            ),
            FakeCFObject('-s'),
            FakeCFObject('mdworker-lsb'),
            FakeCFObject('-c'),
            FakeCFObject('MDSImporterWorker'),
            FakeCFObject('-m'),
            FakeCFObject('com.apple.mdworker.lsb.0')
        ],
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            '-1',
    }),
    FakeCFDict({
        'Label':
            'com.apple.midiserver',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.midiserver': 0,
            'com.apple.midiserver.io': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/Frameworks/CoreMIDI.framework/MIDIServer')
        ],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759c15d50.anonymous.eapolclient',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(68168),
        'Program': 'eapolclient',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label':
            'com.apple.AddressBook.SourceSync',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.AddressBook.PushNotification': 0,
            'com.apple.AddressBook.SourceSync': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/Frameworks/AddressBook.framework/Versions/A/Resources/AddressBookSourceSync.app/Contents/MacOS/AddressBookSourceSync'
            )
        ],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'com.apple.mdworker.i386.0',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Background',
        'MachServices': {
            'com.apple.mdworker.i386.0': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/Frameworks/CoreServices.framework/Frameworks/Metadata.framework/Versions/A/Support/mdworker32'
            ),
            FakeCFObject('-s'),
            FakeCFObject('mdworker-lsb'),
            FakeCFObject('-c'),
            FakeCFObject('MDSImporterWorker'),
            FakeCFObject('-m'),
            FakeCFObject('com.apple.mdworker.i386.0')
        ],
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            '-1',
    }),
    FakeCFDict({
        'Label':
            '0x7f8759d2a8d0.mach_init.crash_inspector',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Google Chrome H[32438].subset.554',
        'MachServices': {
            'com.Breakpad.Inspector32438': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/Applications/Google '
                'Chrome.app/Contents/Versions/21.0.1180.79/Google Chrome '
                'Framework.framework/Resources/crash_inspector'),
            FakeCFObject('com.Breakpad.Inspector32438')
        ],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759d2a130.anonymous.launchd',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Google Chrome H[32656].subset.619',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(499),
        'Program': 'launchd',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label':
            '0x7f8759c1c0e0.mach_init.crash_inspector',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Google Chrome H[32285].subset.229',
        'MachServices': {
            'com.Breakpad.Inspector32285': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/Applications/Google '
                'Chrome.app/Contents/Versions/21.0.1180.79/Google Chrome '
                'Framework.framework/Resources/crash_inspector'),
            FakeCFObject('com.Breakpad.Inspector32285')
        ],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759c15450.anonymous.sshd',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Background',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(68665),
        'Program': 'sshd',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': 'com.apple.tiswitcher',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.inputswitcher.running': 0,
            'com.apple.inputswitcher.startup': 0,
            'com.apple.inputswitcher.stop': 0,
        },
        'OnDemand': FakeCFObject(1),
        'Program':
            '/System/Library/CoreServices/Menu '
            'Extras/TextInput.menu/Contents/SharedSupport/TISwitcher.app/Contents/MacOS/TISwitcher',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': 'com.apple.java.InstallOnDemandAgent',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.java.installondemand': 0,
        },
        'OnDemand': FakeCFObject(1),
        'Program':
            '/System/Library/Java/Support/CoreDeploy.bundle/Contents/Download '
            'Java Components.app/Contents/MacOS/Download Java Components',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759c1a860.anonymous.Google Chrome H',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Google Chrome H[32283].subset.231',
        'MachServices': {
            'com.Breakpad.BootstrapParent': 0,
        },
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(32283),
        'Program': 'Google Chrome H',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'com.apple.cookied',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.cookied': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/CFNetwork.framework/Versions/A/Support/cookied'
            )
        ],
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            '-1',
    }),
    FakeCFDict({
        'Label':
            'com.apple.speech.feedbackservicesserver',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.speech.feedbackservicesserver': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'Program':
            '/System/Library/Frameworks/Carbon.framework/Frameworks/SpeechRecognition.framework/Versions/A/SpeechFeedbackWindow.app/Contents/MacOS/SpeechFeedbackWindow',
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label':
            '0x7f8759c1d020.mach_init.crash_inspector',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Google Chrome H[32291].subset.223',
        'MachServices': {
            'com.Breakpad.Inspector32291': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/Applications/Google '
                'Chrome.app/Contents/Versions/21.0.1180.79/Google Chrome '
                'Framework.framework/Resources/crash_inspector'),
            FakeCFObject('com.Breakpad.Inspector32291')
        ],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'com.apple.AddressBook.abd',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.AddressBook.abd': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/Frameworks/AddressBook.framework/Versions/A/Resources/AddressBookManager.app/Contents/MacOS/AddressBookManager'
            )
        ],
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            '-1',
    }),
    FakeCFDict({
        'Label':
            'com.apple.cfnetwork.AuthBrokerAgent',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.cfnetwork.AuthBrokerAgent': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject('/System/Library/CoreServices/AuthBrokerAgent')
        ],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'com.apple.SystemUIServer.agent',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.BluetoothMEDOServer': 0,
            'com.apple.SUISMessaging': 0,
            'com.apple.dockextra.server': 0,
            'com.apple.dockling.server': 0,
            'com.apple.ipodserver': 0,
            'com.apple.systemuiserver.ServiceProvider': 0,
            'com.apple.systemuiserver.screencapture': 0,
            'com.apple.tsm.uiserver': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'PID':
            FakeCFObject(641),
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.CFPasteboardClient': 0,
            'com.apple.axserver': 0,
            'com.apple.coredrag': 0,
            'com.apple.tsm.portname': 0,
        },
        'Program':
            '/System/Library/CoreServices/SystemUIServer.app/Contents/MacOS/SystemUIServer',
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            0,
    }),
    FakeCFDict({
        'Label':
            'com.apple.safaridavclient',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.safaridavclient': 0,
            'com.apple.safaridavclient.push': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/PrivateFrameworks/BookmarkDAV.framework/Helpers/SafariDAVClient'
            )
        ],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': 'com.apple.Dock.agent',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.dock.appstore': 0,
            'com.apple.dock.downloads': 0,
            'com.apple.dock.fullscreen': 0,
            'com.apple.dock.server': 0,
        },
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(638),
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.axserver': 0,
            'com.apple.coredrag': 0,
        },
        'Program': '/System/Library/CoreServices/Dock.app/Contents/MacOS/Dock',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label':
            'com.apple.TrustEvaluationAgent',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Background',
        'MachServices': {
            'com.apple.TrustEvaluationAgent': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'Program':
            '/System/Library/PrivateFrameworks/TrustEvaluationAgent.framework/Resources/trustevaluationagent',
        'ProgramArguments': [FakeCFObject('trustevaluationagent')],
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'com.apple.storeagent',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.storeagent': 0,
            'com.apple.storeagent-xpc': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'Program':
            '/System/Library/PrivateFrameworks/CommerceKit.framework/Versions/A/Resources/storeagent',
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            '-1',
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'com.apple.imklaunchagent',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Aqua',
        'MachServices': {
            'com.apple.inputmethodkit.launchagent': 0,
            'com.apple.inputmethodkit.launcher': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'Program':
            '/System/Library/Frameworks/InputMethodKit.framework/Resources/imklaunchagent',
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            '-1',
    }),
    FakeCFDict({
        'Label': '0x7f8759c1cd20.anonymous.launchd',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Google Chrome H[32291].subset.223',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(499),
        'Program': 'launchd',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759d2eab0.anonymous.su',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Background',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(74539),
        'Program': 'su',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759c2ee80.anonymous.Google Chrome',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Google Chrome H[32282].subset.281',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(32275),
        'Program': 'Google Chrome',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759d2f9e0.anonymous.Google Chrome H',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {},
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(60518),
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.axserver': 0,
            'com.apple.tsm.portname': 0,
        },
        'Program': 'Google Chrome H',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759c16e10.anonymous.launchd',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Background',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(499),
        'Program': 'launchd',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'EnableTransactions':
            1,
        'Label':
            'com.apple.mdworker.pool.0',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            'Background',
        'MachServices': {
            'com.apple.mdworker.pool.0': 0,
        },
        'OnDemand':
            FakeCFObject(1),
        'PID':
            FakeCFObject(68737),
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
        },
        'ProgramArguments': [
            FakeCFObject(
                '/System/Library/Frameworks/CoreServices.framework/Frameworks/Metadata.framework/Versions/A/Support/mdworker'
            ),
            FakeCFObject('-s'),
            FakeCFObject('mdworker'),
            FakeCFObject('-c'),
            FakeCFObject('MDSImporterWorker'),
            FakeCFObject('-m'),
            FakeCFObject('com.apple.mdworker.pool.0')
        ],
        'TimeOut':
            FakeCFObject(30),
        'TransactionCount':
            0,
    }),
    FakeCFDict({
        'Label':
            '0x7f8759d1f460.anonymous.launchd',
        'LastExitStatus':
            FakeCFObject(0),
        'LimitLoadToSessionType':
            '[0x0-0x4c54c5].com.google.Chrome[32275].subset.632',
        'OnDemand':
            FakeCFObject(1),
        'PID':
            FakeCFObject(499),
        'Program':
            'launchd',
        'TimeOut':
            FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759d1e8f0.anonymous.launchd',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Google Chrome H[32297].subset.637',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(499),
        'Program': 'launchd',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759c1d330.anonymous.sshd',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Background',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(68710),
        'Program': 'sshd',
        'TimeOut': FakeCFObject(30),
    }),
    FakeCFDict({
        'Label': '0x7f8759d2ba80.anonymous.sudo',
        'LastExitStatus': FakeCFObject(0),
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': FakeCFObject(1),
        'PID': FakeCFObject(68719),
        'Program': 'sudo',
        'TimeOut': FakeCFObject(30),
    })
]

# pylint: enable=g-line-too-long
