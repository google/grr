#!/usr/bin/env python
# Copyright 2012 Google Inc. All Rights Reserved.

"""OS X Launchd process listing test data.

These dicts are python representations of the pyobjc NSCFDictionarys returned by
the ServiceManagement framework.  It's close enough to the pyobjc object that we
can use it to test the parsing code without needing to run on OS X.
"""



# Disable some lint warnings to avoid tedious fixing of test data
#pylint: disable=C6310


# Number of entries we expect to be dropped due to filtering
FILTERED_COUNT = 126


JOB = [
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.FileSyncAgent.PHD',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'MachServices': {
            'com.apple.FileSyncAgent.PHD': 0,
            'com.apple.FileSyncAgent.PHD.isRunning': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/CoreServices/FileSyncAgent.app/Contents/MacOS/FileSyncAgent',
            '-launchedByLaunchd',
            '-PHDPlist'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
]


JOBS = [
    {
        'Label': '0x7f8759d20ab0.mach_init.Inspector',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': '[0x0-0x4d44d4].com.google.GoogleTalkPluginD[32298].subset.257',
        'MachServices': {
            'com.Google.BreakpadInspector32298': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/Library/Application Support/Google/GoogleTalkPlugin.app/Contents/Frameworks/GoogleBreakpad.framework/Versions/A/Resources/Inspector',
            'com.Google.BreakpadInspector32298'
        ],
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c23570.mach_init.crash_inspector',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[32284].subset.584',
        'MachServices': {
            'com.Breakpad.Inspector32284': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/Applications/Google Chrome.app/Contents/Versions/21.0.1180.79/Google Chrome Framework.framework/Resources/crash_inspector',
            'com.Breakpad.Inspector32284'
        ],
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.coreservices.appleid.authentication',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.coreservices.appleid.authentication': 0,
        },
        'OnDemand': 1,
        'Program': '/System/Library/CoreServices/AppleIDAuthAgent',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d30310.anonymous.launchd',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[35271].subset.440',
        'OnDemand': 1,
        'PID': 499,
        'Program': 'launchd',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c23ae0.anonymous.launchd',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[32282].subset.281',
        'OnDemand': 1,
        'PID': 499,
        'Program': 'launchd',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d30610.mach_init.crash_inspector',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[35271].subset.440',
        'MachServices': {
            'com.Breakpad.Inspector35271': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/Applications/Google Chrome.app/Contents/Versions/21.0.1180.79/Google Chrome Framework.framework/Resources/crash_inspector',
            'com.Breakpad.Inspector35271'
        ],
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.systemprofiler',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.systemprofiler': 0,
        },
        'OnDemand': 1,
        'Program': '/Applications/Utilities/System Information.app/Contents/MacOS/System Information',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d2b140.anonymous.bash',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'PID': 69813,
        'Program': 'login',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d318d0.anonymous.Google Chrome H',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
        },
        'OnDemand': 1,
        'PID': 60522,
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.axserver': 0,
            'com.apple.tsm.portname': 0,
        },
        'Program': 'Google Chrome H',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d1fb70.anonymous.Google Chrome H',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
        },
        'OnDemand': 1,
        'PID': 32285,
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.axserver': 0,
            'com.apple.tsm.portname': 0,
        },
        'Program': 'Google Chrome H',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c22f60.anonymous.Google Chrome',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[32284].subset.584',
        'OnDemand': 1,
        'PID': 32275,
        'Program': 'Google Chrome',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.FontWorker',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.FontWorker': 0,
            'com.apple.FontWorker.ATS': 0,
        },
        'OnDemand': 1,
        'Program': '/System/Library/Frameworks/ApplicationServices.framework/Versions/A/Frameworks/ATS.framework/Versions/A/Support/fontworker',
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': '0x7f8759d1d200.mach_init.crash_inspector',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': '[0x0-0x4c54c5].com.google.Chrome[32275].subset.632',
        'MachServices': {
            'com.Breakpad.Inspector32275': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/Applications/Google Chrome.app/Contents/Versions/21.0.1180.79/Google Chrome Framework.framework/Resources/crash_inspector',
            'com.Breakpad.Inspector32275'
        ],
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.UserNotificationCenterAgent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.UNCUserNotificationAgent': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/CoreServices/UserNotificationCenter.app/Contents/MacOS/UserNotificationCenter'
        ],
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d30f40.anonymous.Google Chrome C',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[60520].subset.399',
        'OnDemand': 1,
        'PID': 60513,
        'Program': 'Google Chrome C',
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.bluetoothUIServer',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.bluetoothUIServer': 0,
        },
        'OnDemand': 1,
        'Program': '/System/Library/CoreServices/BluetoothUIServer.app/Contents/MacOS/BluetoothUIServer',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.SubmitDiagInfo',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/CoreServices/SubmitDiagInfo'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.gssd-agent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'MachServices': {
            'com.apple.gssd-agent': 0,
        },
        'OnDemand': 1,
        'Program': '/usr/sbin/gssd',
        'ProgramArguments': [
            'gssd-agent'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': '[0x0-0x4d44d4].com.google.GoogleTalkPluginD',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
        },
        'OnDemand': 1,
        'PID': 32298,
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.CFPasteboardClient': 0,
            'com.apple.axserver': 0,
            'com.apple.tsm.portname': 0,
        },
        'ProgramArguments': [
            '/Library/Application Support/Google/GoogleTalkPlugin.app/Contents/MacOS/GoogleTalkPlugin',
            '-psn_0_5063892'
        ],
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.quicklook.config',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.quicklook.config': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/Frameworks/QuickLook.framework/Resources/quicklookconfig'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': '0x7f8759c2fda0.anonymous.login',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'PID': 83461,
        'Program': 'login',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c12410.anonymous.Google Chrome H',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
        },
        'OnDemand': 1,
        'PID': 32297,
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.CFPasteboardClient': 0,
            'com.apple.axserver': 0,
            'com.apple.tsm.portname': 0,
        },
        'Program': 'Google Chrome H',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c2cec0.anonymous.bash',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'PID': 73991,
        'Program': 'login',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c24ca0.anonymous.login',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'PID': 24592,
        'Program': 'login',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c17720.mach_init.crash_inspector',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[35104].subset.553',
        'MachServices': {
            'com.Breakpad.Inspector35104': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/Applications/Google Chrome.app/Contents/Versions/21.0.1180.79/Google Chrome Framework.framework/Resources/crash_inspector',
            'com.Breakpad.Inspector35104'
        ],
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d1cf00.anonymous.login',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'PID': 38234,
        'Program': 'login',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c2e870.anonymous.configd',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'OnDemand': 1,
        'PID': 17,
        'Program': 'configd',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c23de0.mach_init.crash_inspector',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[32282].subset.281',
        'MachServices': {
            'com.Breakpad.Inspector32282': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/Applications/Google Chrome.app/Contents/Versions/21.0.1180.79/Google Chrome Framework.framework/Resources/crash_inspector',
            'com.Breakpad.Inspector32282'
        ],
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.spindump_agent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.spinreporteragent': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/usr/libexec/spindump_agent'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': '0x7f8759c16550.anonymous.login',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'PID': 73954,
        'Program': 'login',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c2f1a0.anonymous.configd',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'PID': 17,
        'Program': 'configd',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.ZoomWindow',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.ZoomWindow.running': 0,
            'com.apple.ZoomWindow.startup': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/CoreServices/ZoomWindow.app/Contents/MacOS/ZoomWindowStarter',
            'launchd',
            '-s'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': '0x7f8759c17a30.anonymous.Google Chrome H',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
        },
        'OnDemand': 1,
        'PID': 35104,
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.axserver': 0,
            'com.apple.tsm.portname': 0,
        },
        'Program': 'Google Chrome H',
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.syncservices.uihandler',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.syncservices.uihandler': 0,
        },
        'OnDemand': 1,
        'Program': '/System/Library/PrivateFrameworks/SyncServicesUI.framework/Versions/Current/Resources/syncuid.app/Contents/MacOS/syncuid',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c17110.anonymous.Google Chrome',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[35104].subset.553',
        'OnDemand': 1,
        'PID': 32275,
        'Program': 'Google Chrome',
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.DictionaryPanelHelper',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.DictionaryPanelHelper': 0,
            'com.apple.DictionaryPanelHelper.reply': 0,
        },
        'OnDemand': 1,
        'Program': '/Applications/Dictionary.app/Contents/SharedSupport/DictionaryPanelHelper.app/Contents/MacOS/DictionaryPanelHelper',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c1d630.anonymous.Python',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'OnDemand': 1,
        'PID': 69592,
        'Program': 'python',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.talagent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.window_proxies': 0,
            'com.apple.window_proxies.startup': 0,
        },
        'OnDemand': 1,
        'PID': 639,
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.CFPasteboardClient': 0,
            'com.apple.axserver': 0,
            'com.apple.tsm.portname': 0,
        },
        'Program': '/System/Library/CoreServices/talagent',
        'TimeOut': 30,
        'TransactionCount': 0,
    },
    {
        'Label': '0x7f8759c1f7f0.anonymous.Google Chrome H',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[60522].subset.309',
        'MachServices': {
            'com.Breakpad.BootstrapParent': 0,
        },
        'OnDemand': 1,
        'PID': 60522,
        'Program': 'Google Chrome H',
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.speech.recognitionserver',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.speech.recognitionserver': 0,
        },
        'OnDemand': 1,
        'Program': '/System/Library/Frameworks/Carbon.framework/Frameworks/SpeechRecognition.framework/Versions/A/SpeechRecognitionServer.app/Contents/MacOS/SpeechRecognitionServer',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c2faa0.anonymous.Python',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'PID': 82320,
        'Program': 'python',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.cvmsCompAgent_x86_64',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'MachServices': {
            'com.apple.cvmsCompAgent_x86_64': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/Frameworks/OpenGL.framework/Versions/A/Libraries/CVMCompiler',
            1
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': '0x7f8759c23270.anonymous.launchd',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[32284].subset.584',
        'OnDemand': 1,
        'PID': 499,
        'Program': 'launchd',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d30c30.anonymous.Google Chrome H',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[60520].subset.399',
        'MachServices': {
            'com.Breakpad.BootstrapParent': 0,
        },
        'OnDemand': 1,
        'PID': 60520,
        'Program': 'Google Chrome H',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.printuitool.agent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.printuitool.agent': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/PrivateFrameworks/PrintingPrivate.framework/Versions/A/PrintUITool'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': '0x7f8759d29b20.anonymous.bash',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'PID': 46172,
        'Program': 'login',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.coreservices.uiagent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.coreservices.launcherror-handler': 0,
            'com.apple.coreservices.quarantine-resolver': 0,
        },
        'OnDemand': 1,
        'Program': '/System/Library/CoreServices/CoreServicesUIAgent.app/Contents/MacOS/CoreServicesUIAgent',
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.mdworker.pool.1',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'MachServices': {
            'com.apple.mdworker.pool.1': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/Frameworks/CoreServices.framework/Frameworks/Metadata.framework/Versions/A/Support/mdworker',
            '-s',
            'mdworker',
            '-c',
            'MDSImporterWorker',
            '-m',
            'com.apple.mdworker.pool.1'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': '[0x0-0x21021].com.google.GoogleDrive',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
        },
        'OnDemand': 1,
        'PID': 763,
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.CFPasteboardClient': 0,
            'com.apple.axserver': 0,
            'com.apple.coredrag': 0,
            'com.apple.tsm.portname': 0,
        },
        'ProgramArguments': [
            '/Applications/Google Drive.app/Contents/MacOS/Google Drive',
            '-psn_0_135201'
        ],
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.cvmsCompAgent_i386',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'MachServices': {
            'com.apple.cvmsCompAgent_i386': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/Frameworks/OpenGL.framework/Versions/A/Libraries/CVMCompiler',
            1
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': '0x7f8759c2b8b0.anonymous.Google Chrome H',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[32284].subset.584',
        'MachServices': {
            'com.Breakpad.BootstrapParent': 0,
        },
        'OnDemand': 1,
        'PID': 32284,
        'Program': 'Google Chrome H',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d1f860.anonymous.Google Chrome H',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
        },
        'OnDemand': 1,
        'PID': 32283,
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.axserver': 0,
            'com.apple.tsm.portname': 0,
        },
        'Program': 'Google Chrome H',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.VoiceOver',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.VoiceOver.running': 0,
            'com.apple.VoiceOver.startup': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/CoreServices/VoiceOver.app/Contents/MacOS/VoiceOver',
            'launchd',
            '-s'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': '0x7f8759d2e7b0.anonymous.tail',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'PID': 74455,
        'Program': 'tail',
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.PreferenceSyncAgent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/CoreServices/PreferenceSyncClient.app/Contents/MacOS/PreferenceSyncClient',
            '--sync',
            '--periodic'
        ],
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c15a50.anonymous.login',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'OnDemand': 1,
        'PID': 38234,
        'Program': 'login',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.mdworker.i386.framework.0',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'MachServices': {
            'com.apple.mdworker.i386.framework.0': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/Frameworks/CoreServices.framework/Frameworks/Metadata.framework/Versions/A/Support/mdworker32',
            '-s',
            'mdworker-lsb',
            '-c',
            'MDSImporterWorker',
            '-m',
            'com.apple.mdworker.i386.framework.0'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': 'com.apple.launchctl.Background',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'OnDemand': 1,
        'ProgramArguments': [
            '/bin/launchctl',
            'bootstrap',
            '-S',
            'Background'
        ],
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.speech.synthesisserver',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.speech.synthesis.ScreenReaderPort': 0,
            'com.apple.speech.synthesis.SpeakingHotKeyPort': 0,
            'com.apple.speech.synthesis.TimeAnnouncementsPort': 0,
        },
        'OnDemand': 1,
        'Program': '/System/Library/Frameworks/ApplicationServices.framework/Versions/A/Frameworks/SpeechSynthesis.framework/Versions/A/SpeechSynthesisServer.app/Contents/MacOS/SpeechSynthesisServer',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d207b0.anonymous.launchd',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': '[0x0-0x4d44d4].com.google.GoogleTalkPluginD[32298].subset.257',
        'OnDemand': 1,
        'PID': 499,
        'Program': 'launchd',
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.ATS.FontValidatorConduit',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.ATS.FontValidatorConduit': 0,
        },
        'OnDemand': 1,
        'Program': '/System/Library/Frameworks/ApplicationServices.framework/Versions/A/Frameworks/ATS.framework/Versions/A/Support/FontValidatorConduit',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.fontd',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.FontObjectsServer': 0,
            'com.apple.FontServer': 0,
        },
        'OnDemand': 1,
        'PID': 640,
        'ProgramArguments': [
            '/System/Library/Frameworks/ApplicationServices.framework/Frameworks/ATS.framework/Support/fontd'
        ],
        'TimeOut': 30,
        'TransactionCount': 0,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.quicklook',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.quicklook': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/Frameworks/QuickLook.framework/Resources/quicklookd.app/Contents/MacOS/quicklookd'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': '0x7f8759d29e20.anonymous.Google Chrome H',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
        },
        'OnDemand': 1,
        'PID': 35271,
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.axserver': 0,
            'com.apple.tsm.portname': 0,
        },
        'Program': 'Google Chrome H',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d20db0.anonymous.sshd',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'OnDemand': 1,
        'PID': 68600,
        'Program': 'sshd',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.unmountassistant.useragent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.unmountassistant.useragent': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/CoreServices/UnmountAssistantAgent.app/Contents/MacOS/UnmountAssistantAgent'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': '0x7f8759d1ebf0.anonymous.Google Chrome H',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
        },
        'OnDemand': 1,
        'PID': 32282,
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.axserver': 0,
            'com.apple.tsm.portname': 0,
        },
        'Program': 'Google Chrome H',
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.installd.user',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.installd.user': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/PrivateFrameworks/PackageKit.framework/Resources/installd'
        ],
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d33ce0.anonymous.login',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'PID': 46170,
        'Program': 'login',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c240f0.anonymous.Google Chrome H',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
        },
        'OnDemand': 1,
        'PID': 32284,
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.axserver': 0,
            'com.apple.tsm.portname': 0,
        },
        'Program': 'Google Chrome H',
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.syncdefaultsd',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.syncdefaultsd': 0,
            'com.apple.syncdefaultsd.push': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/PrivateFrameworks/SyncedDefaults.framework/Support/syncdefaultsd'
        ],
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.marcoagent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.marco': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/PrivateFrameworks/Marco.framework/marcoagent'
        ],
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.distnoted.xpc.agent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'MachServices': {
            'com.apple.distributed_notifications@Uv3': 0,
        },
        'OnDemand': 1,
        'PID': 625,
        'ProgramArguments': [
            '/usr/sbin/distnoted',
            'agent'
        ],
        'TimeOut': 30,
        'TransactionCount': 42,
    },
    {
        'Label': '0x7f8759c2eb70.anonymous.Google Chrome H',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[32282].subset.281',
        'MachServices': {
            'com.Breakpad.BootstrapParent': 0,
        },
        'OnDemand': 1,
        'PID': 32282,
        'Program': 'Google Chrome H',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d28f10.anonymous.login',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'OnDemand': 1,
        'PID': 83461,
        'Program': 'login',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c1fb00.anonymous.Google Chrome C',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[60522].subset.309',
        'OnDemand': 1,
        'PID': 60513,
        'Program': 'Google Chrome C',
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.bluetoothAudioAgent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.bluetoothAudioAgent': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/CoreServices/BluetoothAudioAgent.app/Contents/MacOS/BluetoothAudioAgent'
        ],
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.mdworker.pool.framework.0',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'MachServices': {
            'com.apple.mdworker.pool.framework.0': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/Frameworks/CoreServices.framework/Frameworks/Metadata.framework/Versions/A/Support/mdworker',
            '-s',
            'mdworker',
            '-c',
            'MDSImporterWorker',
            '-m',
            'com.apple.mdworker.pool.framework.0'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': '0x7f8759d20190.mach_init.crash_inspector',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[32297].subset.637',
        'MachServices': {
            'com.Breakpad.Inspector32297': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/Applications/Google Chrome.app/Contents/Versions/21.0.1180.79/Google Chrome Framework.framework/Resources/crash_inspector',
            'com.Breakpad.Inspector32297'
        ],
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': '[0x0-0x19019].com.apple.AppleSpell',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
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
        'OnDemand': 1,
        'PID': 727,
        'ProgramArguments': [
            '/System/Library/Services/AppleSpell.service/Contents/MacOS/AppleSpell',
            '-psn_0_102425'
        ],
        'TimeOut': 30,
        'TransactionCount': 0,
    },
    {
        'Label': '0x7f8759d22370.anonymous.Google Chrome',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[32656].subset.619',
        'OnDemand': 1,
        'PID': 32275,
        'Program': 'Google Chrome',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d2f3c0.mach_init.crash_inspector',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': '[0x0-0x34c34c].com.google.Chrome.canary[60513].subset.374',
        'MachServices': {
            'com.Breakpad.Inspector60513': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/Applications/Google Chrome Canary.app/Contents/Versions/180.1.1025.40/Google Chrome Framework.framework/Resources/crash_inspector',
            'com.Breakpad.Inspector60513'
        ],
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.mdworker.pool.framework.1',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'MachServices': {
            'com.apple.mdworker.pool.framework.1': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/Frameworks/CoreServices.framework/Frameworks/Metadata.framework/Versions/A/Support/mdworker',
            '-s',
            'mdworker',
            '-c',
            'MDSImporterWorker',
            '-m',
            'com.apple.mdworker.pool.framework.1'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.mdworker.lsb.framework.0',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'MachServices': {
            'com.apple.mdworker.lsb.framework.0': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/Frameworks/CoreServices.framework/Frameworks/Metadata.framework/Versions/A/Support/mdworker',
            '-s',
            'mdworker-lsb',
            '-c',
            'MDSImporterWorker',
            '-m',
            'com.apple.mdworker.lsb.framework.0'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': '0x7f8759c16060.anonymous.bash',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'OnDemand': 1,
        'PID': 68666,
        'Program': 'sshd',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.store_helper',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.store_helper': 0,
        },
        'OnDemand': 1,
        'Program': '/System/Library/PrivateFrameworks/CommerceKit.framework/Resources/store_helper.app/Contents/MacOS/store_helper',
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.mdworker.pool.framework.2',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'MachServices': {
            'com.apple.mdworker.pool.framework.2': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/Frameworks/CoreServices.framework/Frameworks/Metadata.framework/Versions/A/Support/mdworker',
            '-s',
            'mdworker',
            '-c',
            'MDSImporterWorker',
            '-m',
            'com.apple.mdworker.pool.framework.2'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': 'com.apple.FontRegistryUIAgent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.FontRegistry.FontRegistryUIAgent': 0,
        },
        'OnDemand': 1,
        'Program': '/System/Library/Frameworks/ApplicationServices.framework/Frameworks/ATS.framework/Support/FontRegistryUIAgent.app/Contents/MacOS/FontRegistryUIAgent',
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.softwareupdateagent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/CoreServices/Software Update.app/Contents/Resources/SoftwareUpdateCheck',
            '-LaunchApp',
            'YES'
        ],
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.ubd',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/PrivateFrameworks/Ubiquity.framework/Versions/A/Support/ubd'
        ],
        'Sockets': {
            'Apple_Ubiquity_Message': (
                '-1'
                ),
        },
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d07d60.anonymous.applepushservic',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'OnDemand': 1,
        'PID': 85,
        'Program': 'applepushservic',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c1c700.anonymous.Google Chrome H',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[32291].subset.223',
        'MachServices': {
            'com.Breakpad.BootstrapParent': 0,
        },
        'OnDemand': 1,
        'PID': 32291,
        'Program': 'Google Chrome H',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d2c7e0.anonymous.Google Chrome',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[32438].subset.554',
        'OnDemand': 1,
        'PID': 32275,
        'Program': 'Google Chrome',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c103c0.anonymous.bash',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'PID': 24593,
        'Program': 'login',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.mdworker.pool.framework.3',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'MachServices': {
            'com.apple.mdworker.pool.framework.3': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/Frameworks/CoreServices.framework/Frameworks/Metadata.framework/Versions/A/Support/mdworker',
            '-s',
            'mdworker',
            '-c',
            'MDSImporterWorker',
            '-m',
            'com.apple.mdworker.pool.framework.3'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.ScreenReaderUIServer',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.ScreenReaderUIServer': 0,
        },
        'OnDemand': 1,
        'Program': '/System/Library/PrivateFrameworks/ScreenReader.framework/Resources/ScreenReaderUIServer.app/Contents/MacOS/ScreenReaderUIServer',
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': '0x7f8759c1ab70.anonymous.Google Chrome',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[32283].subset.231',
        'OnDemand': 1,
        'PID': 32275,
        'Program': 'Google Chrome',
        'TimeOut': 30,
    },
    {
        'Label': '[0x0-0x34c34c].com.google.Chrome.canary',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.google.Chrome.canary.rohitfork.60513': 0,
        },
        'OnDemand': 1,
        'PID': 60513,
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.CFPasteboardClient': 0,
            'com.apple.axserver': 0,
            'com.apple.coredrag': 0,
            'com.apple.tsm.portname': 0,
        },
        'ProgramArguments': [
            '/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary',
            '-psn_0_3457868'
        ],
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c1bde0.anonymous.launchd',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[32285].subset.229',
        'OnDemand': 1,
        'PID': 499,
        'Program': 'launchd',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.warmd_agent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'PID': 737,
        'ProgramArguments': [
            '/usr/libexec/warmd_agent'
        ],
        'TimeOut': 30,
        'TransactionCount': 0,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.ATS.FontValidator',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.ATS.FontValidator': 0,
        },
        'OnDemand': 1,
        'Program': '/System/Library/Frameworks/ApplicationServices.framework/Versions/A/Frameworks/ATS.framework/Versions/A/Support/FontValidator',
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': '0x7f8759c115d0.anonymous.Google Chrome C',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[60518].subset.363',
        'OnDemand': 1,
        'PID': 60513,
        'Program': 'Google Chrome C',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.mdworker.pool.3',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'MachServices': {
            'com.apple.mdworker.pool.3': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/Frameworks/CoreServices.framework/Frameworks/Metadata.framework/Versions/A/Support/mdworker',
            '-s',
            'mdworker',
            '-c',
            'MDSImporterWorker',
            '-m',
            'com.apple.mdworker.pool.3'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': '0x7f8759c1e5a0.mach_init.crash_inspector',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[60518].subset.363',
        'MachServices': {
            'com.Breakpad.Inspector60518': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/Applications/Google Chrome Canary.app/Contents/Versions/180.1.1025.40/Google Chrome Framework.framework/Resources/crash_inspector',
            'com.Breakpad.Inspector60518'
        ],
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.RemoteDesktop.agent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.RemoteDesktop.agent': 0,
        },
        'OnDemand': 1,
        'Program': '/System/Library/CoreServices/RemoteManagement/ARDAgent.app/Contents/MacOS/ARDAgent',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c24490.anonymous.launchd',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[60518].subset.363',
        'OnDemand': 1,
        'PID': 499,
        'Program': 'launchd',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c18730.anonymous.sh',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'PID': 68799,
        'Program': 'sh',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d2fcf0.anonymous.Google Chrome H',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[35271].subset.440',
        'MachServices': {
            'com.Breakpad.BootstrapParent': 0,
        },
        'OnDemand': 1,
        'PID': 35271,
        'Program': 'Google Chrome H',
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.FTCleanup',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'ProgramArguments': [
            '/bin/sh',
            '-c',
            "if [ \"$HOME\" == \"/System\" ], then exit 0, fi, if [ -f \"$HOME/Library/LaunchAgents/com.apple.imagent.plist\" ] , then launchctl unload -wF ~/Library/LaunchAgents/com.apple.imagent.plist , launchctl load -wF /System/Library/LaunchAgents/com.apple.imagent.plist , fi , if [ -f \"$HOME/Library/LaunchAgents/com.apple.apsd-ft.plist\" ] , then launchctl unload -wF -S 'Aqua' ~/Library/LaunchAgents/com.apple.apsd-ft.plist, fi , if [ -f \"$HOME/Library/LaunchAgents/com.apple.marcoagent.plist\" ] , then launchctl unload -wF ~/Library/LaunchAgents/com.apple.marcoagent.plist , launchctl load -wF /System/Library/LaunchAgents/com.apple.marcoagent.plist , fi , if [ -f \"$HOME/Library/LaunchAgents/com.apple.FTMonitor.plist\" ] , then launchctl unload -wF ~/Library/LaunchAgents/com.apple.FTMonitor.plist , fi ,"
        ],
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.mdworker.isolation.0',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'MachServices': {
            'com.apple.mdworker.isolation.0': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/Frameworks/CoreServices.framework/Frameworks/Metadata.framework/Versions/A/Support/mdworker',
            '-s',
            'mdworker',
            '-c',
            'MDSImporterWorker',
            '-m',
            'com.apple.mdworker.isolation.0'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': 'com.apple.netauth.user.gui',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.netauth.user.gui': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/CoreServices/NetAuthAgent.app/Contents/MacOS/NetAuthAgent'
        ],
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d28310.anonymous.bash',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'PID': 83462,
        'Program': 'login',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d31250.anonymous.launchd',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[60520].subset.399',
        'OnDemand': 1,
        'PID': 499,
        'Program': 'launchd',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': '[0x0-0x9009].com.apple.Terminal',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.Terminal.ServiceProvider': 0,
        },
        'OnDemand': 1,
        'PID': 634,
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.CFPasteboardClient': 0,
            'com.apple.axserver': 0,
            'com.apple.coredrag': 0,
            'com.apple.tsm.portname': 0,
        },
        'ProgramArguments': [
            '/Applications/Utilities/Terminal.app/Contents/MacOS/Terminal',
            '-psn_0_36873'
        ],
        'TimeOut': 30,
        'TransactionCount': 1,
    },
    {
        'Label': '0x7f8759c2d1c0.anonymous.su',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'PID': 74539,
        'Program': 'su',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c1d940.anonymous.sshd',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'OnDemand': 1,
        'PID': 68714,
        'Program': 'sshd',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'org.openbsd.ssh-agent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'PID': 46009,
        'ProgramArguments': [
            '/usr/bin/ssh-agent',
            '-l'
        ],
        'Sockets': {
            'Listeners': (
                '-1'
            ),
        },
        'TimeOut': 30,
        'TransactionCount': 0,
    },
    {
        'Label': 'com.apple.familycontrols.useragent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.familycontrols.useragent': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/PrivateFrameworks/FamilyControls.framework/Resources/ParentalControls.app/Contents/MacOS/ParentalControls'
        ],
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c1b7c0.anonymous.Google Chrome H',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[32285].subset.229',
        'MachServices': {
            'com.Breakpad.BootstrapParent': 0,
        },
        'OnDemand': 1,
        'PID': 32285,
        'Program': 'Google Chrome H',
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.AppStoreUpdateAgent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.AppStoreUpdateAgent': 0,
        },
        'OnDemand': 1,
        'Program': '/Applications/App Store.app/Contents/Resources/appstoreupdateagent',
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.csuseragent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.csuseragent': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/CoreServices/CSUserAgent'
        ],
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.PubSub.Agent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.pubsub.ipc': 0,
            'com.apple.pubsub.notification': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/Frameworks/PubSub.framework/Versions/A/Resources/PubSubAgent.app/Contents/MacOS/PubSubAgent'
        ],
        'Sockets': {
            'Render': (
                '-1'
                ),
        },
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.rcd',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.rcd': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/CoreServices/rcd.app/Contents/MacOS/rcd'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': 'com.apple.netauth.user.auth',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'MachServices': {
            'com.apple.netauth.user.auth': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/CoreServices/NetAuthAgent.app/Contents/MacOS/NetAuthSysAgent'
        ],
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c1dc40.anonymous.bash',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'OnDemand': 1,
        'PID': 68720,
        'Program': 'sshd',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c2f7a0.anonymous.bash',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'PID': 75030,
        'Program': 'login',
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.BezelUIServer',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.BezelUI': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/LoginPlugins/BezelServices.loginPlugin/Contents/Resources/BezelUI/BezelUIServer'
        ],
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c0cf00.anonymous.com.apple.dock.',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
        },
        'OnDemand': 1,
        'PID': 652,
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.CFPasteboardClient': 0,
            'com.apple.axserver': 0,
            'com.apple.tsm.portname': 0,
        },
        'Program': 'com.apple.dock.',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d28c10.anonymous.bash',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'OnDemand': 1,
        'PID': 83462,
        'Program': 'bash',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.xgridd',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.xgridd': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/usr/libexec/xgrid/xgridd'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': 'com.apple.reclaimspace',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.ReclaimSpace': 0,
        },
        'OnDemand': 1,
        'Program': '/System/Library/CoreServices/backupd.bundle/Contents/Resources/ReclaimSpaceAgent.app/Contents/MacOS/ReclaimSpaceAgent',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d31550.mach_init.crash_inspector',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[60520].subset.399',
        'MachServices': {
            'com.Breakpad.Inspector60520': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/Applications/Google Chrome Canary.app/Contents/Versions/180.1.1025.40/Google Chrome Framework.framework/Resources/crash_inspector',
            'com.Breakpad.Inspector60520'
        ],
        'TimeOut': 30,
    },
    {
        'Label': '[0x0-0x4c54c5].com.google.Chrome',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.google.Chrome.rohitfork.32275': 0,
        },
        'OnDemand': 1,
        'PID': 32275,
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.CFPasteboardClient': 0,
            'com.apple.axserver': 0,
            'com.apple.coredrag': 0,
            'com.apple.tsm.portname': 0,
        },
        'ProgramArguments': [
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            '-psn_0_5002437'
        ],
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c0c320.anonymous.loginwindow',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'OnDemand': 1,
        'PID': 71,
        'Program': 'loginwindow',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.mdworker.lsb.0',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'MachServices': {
            'com.apple.mdworker.lsb.0': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/Frameworks/CoreServices.framework/Frameworks/Metadata.framework/Versions/A/Support/mdworker',
            '-s',
            'mdworker-lsb',
            '-c',
            'MDSImporterWorker',
            '-m',
            'com.apple.mdworker.lsb.0'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': 'com.apple.midiserver',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.midiserver': 0,
            'com.apple.midiserver.io': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/Frameworks/CoreMIDI.framework/MIDIServer'
        ],
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c15d50.anonymous.eapolclient',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'PID': 68168,
        'Program': 'eapolclient',
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.AddressBook.SourceSync',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.AddressBook.PushNotification': 0,
            'com.apple.AddressBook.SourceSync': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/Frameworks/AddressBook.framework/Versions/A/Resources/AddressBookSourceSync.app/Contents/MacOS/AddressBookSourceSync'
        ],
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.mdworker.i386.0',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'MachServices': {
            'com.apple.mdworker.i386.0': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/Frameworks/CoreServices.framework/Frameworks/Metadata.framework/Versions/A/Support/mdworker32',
            '-s',
            'mdworker-lsb',
            '-c',
            'MDSImporterWorker',
            '-m',
            'com.apple.mdworker.i386.0'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': '0x7f8759d2a8d0.mach_init.crash_inspector',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[32438].subset.554',
        'MachServices': {
            'com.Breakpad.Inspector32438': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/Applications/Google Chrome.app/Contents/Versions/21.0.1180.79/Google Chrome Framework.framework/Resources/crash_inspector',
            'com.Breakpad.Inspector32438'
        ],
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d2a130.anonymous.launchd',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[32656].subset.619',
        'OnDemand': 1,
        'PID': 499,
        'Program': 'launchd',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c1c0e0.mach_init.crash_inspector',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[32285].subset.229',
        'MachServices': {
            'com.Breakpad.Inspector32285': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/Applications/Google Chrome.app/Contents/Versions/21.0.1180.79/Google Chrome Framework.framework/Resources/crash_inspector',
            'com.Breakpad.Inspector32285'
        ],
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c15450.anonymous.sshd',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'OnDemand': 1,
        'PID': 68665,
        'Program': 'sshd',
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.tiswitcher',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.inputswitcher.running': 0,
            'com.apple.inputswitcher.startup': 0,
            'com.apple.inputswitcher.stop': 0,
        },
        'OnDemand': 1,
        'Program': '/System/Library/CoreServices/Menu Extras/TextInput.menu/Contents/SharedSupport/TISwitcher.app/Contents/MacOS/TISwitcher',
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.java.InstallOnDemandAgent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.java.installondemand': 0,
        },
        'OnDemand': 1,
        'Program': '/System/Library/Java/Support/CoreDeploy.bundle/Contents/Download Java Components.app/Contents/MacOS/Download Java Components',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c1a860.anonymous.Google Chrome H',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[32283].subset.231',
        'MachServices': {
            'com.Breakpad.BootstrapParent': 0,
        },
        'OnDemand': 1,
        'PID': 32283,
        'Program': 'Google Chrome H',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.cookied',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.cookied': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/CFNetwork.framework/Versions/A/Support/cookied'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': 'com.apple.speech.feedbackservicesserver',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.speech.feedbackservicesserver': 0,
        },
        'OnDemand': 1,
        'Program': '/System/Library/Frameworks/Carbon.framework/Frameworks/SpeechRecognition.framework/Versions/A/SpeechFeedbackWindow.app/Contents/MacOS/SpeechFeedbackWindow',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c1d020.mach_init.crash_inspector',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[32291].subset.223',
        'MachServices': {
            'com.Breakpad.Inspector32291': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/Applications/Google Chrome.app/Contents/Versions/21.0.1180.79/Google Chrome Framework.framework/Resources/crash_inspector',
            'com.Breakpad.Inspector32291'
        ],
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.AddressBook.abd',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.AddressBook.abd': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/Frameworks/AddressBook.framework/Versions/A/Resources/AddressBookManager.app/Contents/MacOS/AddressBookManager'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': 'com.apple.cfnetwork.AuthBrokerAgent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.cfnetwork.AuthBrokerAgent': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/CoreServices/AuthBrokerAgent'
        ],
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.SystemUIServer.agent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
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
        'OnDemand': 1,
        'PID': 641,
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.CFPasteboardClient': 0,
            'com.apple.axserver': 0,
            'com.apple.coredrag': 0,
            'com.apple.tsm.portname': 0,
        },
        'Program': '/System/Library/CoreServices/SystemUIServer.app/Contents/MacOS/SystemUIServer',
        'TimeOut': 30,
        'TransactionCount': 0,
    },
    {
        'Label': 'com.apple.safaridavclient',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.safaridavclient': 0,
            'com.apple.safaridavclient.push': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/PrivateFrameworks/BookmarkDAV.framework/Helpers/SafariDAVClient'
        ],
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.Dock.agent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.dock.appstore': 0,
            'com.apple.dock.downloads': 0,
            'com.apple.dock.fullscreen': 0,
            'com.apple.dock.server': 0,
        },
        'OnDemand': 1,
        'PID': 638,
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.axserver': 0,
            'com.apple.coredrag': 0,
        },
        'Program': '/System/Library/CoreServices/Dock.app/Contents/MacOS/Dock',
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.TrustEvaluationAgent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'MachServices': {
            'com.apple.TrustEvaluationAgent': 0,
        },
        'OnDemand': 1,
        'Program': '/System/Library/PrivateFrameworks/TrustEvaluationAgent.framework/Resources/trustevaluationagent',
        'ProgramArguments': [
            'trustevaluationagent'
        ],
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.storeagent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.storeagent': 0,
            'com.apple.storeagent-xpc': 0,
        },
        'OnDemand': 1,
        'Program': '/System/Library/PrivateFrameworks/CommerceKit.framework/Versions/A/Resources/storeagent',
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.imklaunchagent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.inputmethodkit.launchagent': 0,
            'com.apple.inputmethodkit.launcher': 0,
        },
        'OnDemand': 1,
        'Program': '/System/Library/Frameworks/InputMethodKit.framework/Resources/imklaunchagent',
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': '0x7f8759c1cd20.anonymous.launchd',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[32291].subset.223',
        'OnDemand': 1,
        'PID': 499,
        'Program': 'launchd',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d2eab0.anonymous.su',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'OnDemand': 1,
        'PID': 74539,
        'Program': 'su',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c2ee80.anonymous.Google Chrome',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[32282].subset.281',
        'OnDemand': 1,
        'PID': 32275,
        'Program': 'Google Chrome',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d2f9e0.anonymous.Google Chrome H',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
        },
        'OnDemand': 1,
        'PID': 60518,
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.axserver': 0,
            'com.apple.tsm.portname': 0,
        },
        'Program': 'Google Chrome H',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c16e10.anonymous.launchd',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'OnDemand': 1,
        'PID': 499,
        'Program': 'launchd',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.mdworker.pool.0',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'MachServices': {
            'com.apple.mdworker.pool.0': 0,
        },
        'OnDemand': 1,
        'PID': 68737,
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
        },
        'ProgramArguments': [
            '/System/Library/Frameworks/CoreServices.framework/Frameworks/Metadata.framework/Versions/A/Support/mdworker',
            '-s',
            'mdworker',
            '-c',
            'MDSImporterWorker',
            '-m',
            'com.apple.mdworker.pool.0'
        ],
        'TimeOut': 30,
        'TransactionCount': 0,
    },
    {
        'Label': '0x7f8759d1f460.anonymous.launchd',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': '[0x0-0x4c54c5].com.google.Chrome[32275].subset.632',
        'OnDemand': 1,
        'PID': 499,
        'Program': 'launchd',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d1e8f0.anonymous.launchd',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[32297].subset.637',
        'OnDemand': 1,
        'PID': 499,
        'Program': 'launchd',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c1d330.anonymous.sshd',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'OnDemand': 1,
        'PID': 68710,
        'Program': 'sshd',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d2ba80.anonymous.sudo',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'PID': 68719,
        'Program': 'sudo',
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.coredata.externalrecordswriter',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/Frameworks/CoreData.framework/Versions/A/Resources/ExternalRecordsWriter'
        ],
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c2f4a0.anonymous.login',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'OnDemand': 1,
        'PID': 73954,
        'Program': 'login',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c20110.mach_init.crash_inspector',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[60522].subset.309',
        'MachServices': {
            'com.Breakpad.Inspector60522': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/Applications/Google Chrome Canary.app/Contents/Versions/180.1.1025.40/Google Chrome Framework.framework/Resources/crash_inspector',
            'com.Breakpad.Inspector60522'
        ],
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c15750.anonymous.bash',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'OnDemand': 1,
        'PID': 38235,
        'Program': 'bash',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d231e0.anonymous.mds',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'OnDemand': 1,
        'PID': 68,
        'Program': 'mds',
        'TimeOut': 30,
    },
    {
        'Label': 'com.google.keystone.system.agent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'ProgramArguments': [
            '/Library/Google/GoogleSoftwareUpdate/GoogleSoftwareUpdate.bundle/Contents/Resources/GoogleSoftwareUpdateAgent.app/Contents/MacOS/GoogleSoftwareUpdateAgent',
            '-runMode',
            'ifneeded'
        ],
        'StandardErrorPath': '/dev/null',
        'StandardOutPath': '/dev/null',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c1ca10.anonymous.Google Chrome',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[32291].subset.223',
        'OnDemand': 1,
        'PID': 32275,
        'Program': 'Google Chrome',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.Finder',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.finder.ServiceProvider': 0,
        },
        'OnDemand': 1,
        'PID': 642,
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.CFPasteboardClient': 0,
            'com.apple.axserver': 0,
            'com.apple.coredrag': 0,
            'com.apple.tsm.portname': 0,
        },
        'Program': '/System/Library/CoreServices/Finder.app/Contents/MacOS/Finder',
        'TimeOut': 30,
        'TransactionCount': 0,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.quicklook.ui.helper',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.quicklook.ui.helper': 0,
            'com.apple.quicklook.ui.helper.active': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/Frameworks/Quartz.framework/Frameworks/QuickLookUI.framework/Resources/QuickLookUIHelper.app/Contents/MacOS/QuickLookUIHelper'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': '0x7f8759c2bce0.anonymous.Google Chrome H',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[35104].subset.553',
        'MachServices': {
            'com.Breakpad.BootstrapParent': 0,
        },
        'OnDemand': 1,
        'PID': 35104,
        'Program': 'Google Chrome H',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.KerberosHelper.LKDCHelper',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'MachServices': {
            'com.apple.KerberosHelper.LKDCHelper': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/PrivateFrameworks/KerberosHelper.framework/Helpers/LKDCHelper'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': '0x7f8759c1e8b0.anonymous.Google Chrome H',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
        },
        'OnDemand': 1,
        'PID': 60520,
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.axserver': 0,
            'com.apple.tsm.portname': 0,
        },
        'Program': 'Google Chrome H',
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.CoreLocationAgent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.CoreLocation.agent': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/CoreServices/CoreLocationAgent.app/Contents/MacOS/CoreLocationAgent'
        ],
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.DiskArbitrationAgent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.DiskArbitration.DiskArbitrationAgent': 0,
        },
        'OnDemand': 1,
        'Program': '/System/Library/Frameworks/DiskArbitration.framework/Versions/A/Support/DiskArbitrationAgent',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d22680.mach_init.crash_inspector',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[32656].subset.619',
        'MachServices': {
            'com.Breakpad.Inspector32656': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/Applications/Google Chrome.app/Contents/Versions/21.0.1180.79/Google Chrome Framework.framework/Resources/crash_inspector',
            'com.Breakpad.Inspector32656'
        ],
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.Kerberos.renew.plist',
        'LastExitStatus': 256,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'ProgramArguments': [
            '/usr/bin/kinit',
            '-R'
        ],
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.syncservices.SyncServer',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.syncservices.SyncServer': 0,
        },
        'OnDemand': 1,
        'Program': '/System/Library/Frameworks/SyncServices.framework/Versions/Current/Resources/SyncServer.app/Contents/MacOS/SyncServer',
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.librariand',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.librariand': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/usr/libexec/librariand'
        ],
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.scopedbookmarksagent.xpc',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.scopedbookmarksagent.xpc': 0,
        },
        'OnDemand': 1,
        'Program': '/System/Library/CoreServices/ScopedBookmarkAgent',
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': 'com.apple.ReportCrash.Self',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.ReportCrash.Self': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/CoreServices/ReportCrash'
        ],
        'StandardErrorPath': '/dev/null',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c2bff0.anonymous.Google Chrome H',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
        },
        'OnDemand': 1,
        'PID': 32656,
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.axserver': 0,
            'com.apple.tsm.portname': 0,
        },
        'Program': 'Google Chrome H',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.ServiceManagement.LoginItems',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.ServiceManagement.LoginItems': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/usr/libexec/launchproxyls',
            '-launchd'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': '0x7f8759d1fe80.anonymous.Google Chrome',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[32297].subset.637',
        'OnDemand': 1,
        'PID': 32275,
        'Program': 'Google Chrome',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d1e5e0.anonymous.Google Chrome H',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[32297].subset.637',
        'MachServices': {
            'com.Breakpad.BootstrapParent': 0,
        },
        'OnDemand': 1,
        'PID': 32297,
        'Program': 'Google Chrome H',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d1b910.anonymous.Google Chrome',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': '[0x0-0x4c54c5].com.google.Chrome[32275].subset.632',
        'MachServices': {
            'com.Breakpad.BootstrapParent': 0,
        },
        'OnDemand': 1,
        'PID': 32275,
        'Program': 'Google Chrome',
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.NetworkDiagnostics',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.NetworkDiagnostic.agent': 0,
        },
        'OnDemand': 1,
        'Program': '/System/Library/CoreServices/Network Diagnostics.app/Contents/MacOS/Network Diagnostics',
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.btsa',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.btsa': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/CoreServices/Bluetooth Setup Assistant.app/Contents/MacOS/Bluetooth Setup Assistant',
            '-autoConfigure'
        ],
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d2f6d0.anonymous.eapolclient',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'OnDemand': 1,
        'PID': 68168,
        'Program': 'eapolclient',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'org.x.startx',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'ProgramArguments': [
            '/usr/X11/bin/startx'
        ],
        'Sockets': {
            'org.x:0': (
                '-1'
            ),
        },
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': '0x7f8759c1bad0.anonymous.Google Chrome',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[32285].subset.229',
        'OnDemand': 1,
        'PID': 32275,
        'Program': 'Google Chrome',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.lookupd',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.lookupd': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/PrivateFrameworks/Lookup.framework/Resources/com.apple.lookupd'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.pboard',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.pasteboard.1': 0,
        },
        'OnDemand': 1,
        'PID': 631,
        'ProgramArguments': [
            '/usr/sbin/pboard'
        ],
        'TimeOut': 30,
        'TransactionCount': 0,
    },
    {
        'Label': '0x7f8759c00a30.anonymous.coreservicesd',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'OnDemand': 1,
        'PID': 32,
        'Program': 'coreservicesd',
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.java.updateSharing',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.java.updateSharing': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/Frameworks/JavaVM.framework/Versions/A/Resources/bin/updateSharingD'
        ],
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.ReportGPURestart',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/Frameworks/OpenGL.framework/Versions/A/Libraries/ReportGPURestart'
        ],
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.mdworker.prescan.0',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'MachServices': {
            'com.apple.mdworker.prescan.0': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/Frameworks/CoreServices.framework/Frameworks/Metadata.framework/Versions/A/Support/mdworker',
            '-s',
            'mdworker-lsb',
            '-c',
            'MDSImporterWorker',
            '-m',
            'com.apple.mdworker.prescan.0',
            '-p'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': '0x7f8759d2edb0.anonymous.login',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'PID': 75029,
        'Program': 'login',
        'TimeOut': 30,
    },
    {
        'Label': 'com.googlecode.munki.ManagedSoftwareUpdate',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'ProgramArguments': [
            '/usr/local/munki/launchapp',
            '-a',
            '/Applications/Utilities/Managed Software Update.app'
        ],
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d1d5f0.anonymous.Google Chrome C',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': '[0x0-0x34c34c].com.google.Chrome.canary[60513].subset.374',
        'MachServices': {
            'com.Breakpad.BootstrapParent': 0,
        },
        'OnDemand': 1,
        'PID': 60513,
        'Program': 'Google Chrome C',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.FileSyncAgent.PHD',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'MachServices': {
            'com.apple.FileSyncAgent.PHD': 0,
            'com.apple.FileSyncAgent.PHD.isRunning': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/CoreServices/FileSyncAgent.app/Contents/MacOS/FileSyncAgent',
            '-launchedByLaunchd',
            '-PHDPlist'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': 'com.apple.isst',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'Program': '/System/Library/CoreServices/Menu Extras/TextInput.menu/Contents/SharedSupport/isst',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.screensharing.agent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.screensharing.agent': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/CoreServices/RemoteManagement/ScreensharingAgent.bundle/Contents/MacOS/ScreensharingAgent'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.AOSNotification',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.AOSNotification': 0,
        },
        'OnDemand': 1,
        'Program': '/usr/sbin/aosnotifyd',
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': '0x7f8759d1acc0.anonymous.CVMServer',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'OnDemand': 1,
        'PID': 130,
        'Program': 'CVMServer',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.mdworker.isolation.framework.0',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'MachServices': {
            'com.apple.mdworker.isolation.framework.0': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/Frameworks/CoreServices.framework/Frameworks/Metadata.framework/Versions/A/Support/mdworker',
            '-s',
            'mdworker',
            '-c',
            'MDSImporterWorker',
            '-m',
            'com.apple.mdworker.isolation.framework.0'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': 'com.apple.LaunchServices.lsboxd',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.ls.boxd': 0,
        },
        'OnDemand': 1,
        'PID': 680,
        'ProgramArguments': [
            '/usr/libexec/lsboxd'
        ],
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.pbs',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.pbs.fetch_services': 0,
        },
        'OnDemand': 1,
        'Program': '/System/Library/CoreServices/pbs',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.printtool.agent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.printtool.agent': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/Frameworks/ApplicationServices.framework/Frameworks/PrintCore.framework/Versions/A/printtool',
            'agent'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': '0x7f8759d30000.anonymous.Google Chrome',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[35271].subset.440',
        'OnDemand': 1,
        'PID': 32275,
        'Program': 'Google Chrome',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.mdworker.pool.2',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'MachServices': {
            'com.apple.mdworker.pool.2': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/Frameworks/CoreServices.framework/Frameworks/Metadata.framework/Versions/A/Support/mdworker',
            '-s',
            'mdworker',
            '-c',
            'MDSImporterWorker',
            '-m',
            'com.apple.mdworker.pool.2'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.helpd',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.helpd': 0,
        },
        'OnDemand': 1,
        'Program': '/System/Library/PrivateFrameworks/HelpData.framework/Versions/A/Resources/helpd',
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.scrod',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.scrod': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/PrivateFrameworks/ScreenReader.framework/Frameworks/ScreenReaderOutput.framework/Resources/scrod'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.alf.useragent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.alf.useragent': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/usr/libexec/ApplicationFirewall/Firewall'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.FileSyncAgent.iDisk',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.FileSyncAgent.iDisk': 0,
            'com.apple.FileSyncAgent.iDisk.isRunning': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/CoreServices/FileSyncAgent.app/Contents/MacOS/FileSyncAgent',
            '-launchedByLaunchd',
            '-iDiskPlist'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.imagent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.imagent.desktop.Launched': 0,
            'com.apple.imagent.desktop.auth': 0,
        },
        'OnDemand': 1,
        'PID': 744,
        'ProgramArguments': [
            '/System/Library/PrivateFrameworks/IMCore.framework/imagent.app/Contents/MacOS/imagent'
        ],
        'TimeOut': 30,
        'TransactionCount': 0,
    },
    {
        'Label': 'com.apple.aos.migrate',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.aos.migrate': 0,
        },
        'OnDemand': 1,
        'Program': '/System/Library/CoreServices/AOSMigrateAgent',
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.pictd',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.pictd': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/usr/sbin/pictd'
        ],
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c0eb80.anonymous.bash',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'OnDemand': 1,
        'PID': 73991,
        'Program': 'bash',
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.TMLaunchAgent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/CoreServices/backupd.bundle/Contents/Resources/TMLaunchAgent.app/Contents/MacOS/TMLaunchAgent'
        ],
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c0daf0.anonymous.Terminal',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'OnDemand': 1,
        'PID': 634,
        'Program': 'Terminal',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.AirPortBaseStationAgent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'PID': 749,
        'ProgramArguments': [
            '/System/Library/CoreServices/AirPort Base Station Agent.app/Contents/MacOS/AirPort Base Station Agent',
            '-launchd',
            '-allowquit'
        ],
        'TimeOut': 30,
        'TransactionCount': 0,
    },
    {
        'Label': '0x7f8759c15140.anonymous.diskarbitration',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'OnDemand': 1,
        'PID': 16,
        'Program': 'diskarbitration',
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.launchctl.Aqua',
        'LastExitStatus': 256,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'ProgramArguments': [
            '/bin/launchctl',
            'bootstrap',
            '-S',
            'Aqua'
        ],
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.quicklook.32bit',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.quicklook.32bit': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/Frameworks/QuickLook.framework/Resources/quicklookd32.app/Contents/MacOS/quicklookd32'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': '0x7f8759d36970.anonymous.bash',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'PID': 82317,
        'Program': 'login',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.WebKit.PluginAgent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.WebKit.PluginAgent': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/Frameworks/WebKit.framework/WebKitPluginAgent'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': '0x7f8759c17420.anonymous.launchd',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[35104].subset.553',
        'OnDemand': 1,
        'PID': 499,
        'Program': 'launchd',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d2c1c0.anonymous.Google Chrome H',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
        },
        'OnDemand': 1,
        'PID': 32438,
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.axserver': 0,
            'com.apple.tsm.portname': 0,
        },
        'Program': 'Google Chrome H',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c10a50.anonymous.bash',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'PID': 38235,
        'Program': 'login',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c0df10.anonymous.Google Chrome H',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[60518].subset.363',
        'MachServices': {
            'com.Breakpad.BootstrapParent': 0,
        },
        'OnDemand': 1,
        'PID': 60518,
        'Program': 'Google Chrome H',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c1f4e0.anonymous.bash',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'PID': 78132,
        'Program': 'login',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d2f0c0.anonymous.launchd',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': '[0x0-0x34c34c].com.google.Chrome.canary[60513].subset.374',
        'OnDemand': 1,
        'PID': 499,
        'Program': 'launchd',
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.ReportCrash',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.ReportCrash': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/CoreServices/ReportCrash'
        ],
        'StandardErrorPath': '/dev/null',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c1a260.anonymous.login',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'PID': 69802,
        'Program': 'login',
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.PCIESlotCheck',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/CoreServices/Expansion Slot Utility.app/Contents/Resources/PCIESlotCheck'
        ],
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c00d40.anonymous.loginwindow',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.BezelServices': 0,
            'com.apple.SchedulerUpdateNotificationPort': 0,
            'com.apple.loginwindow.notify': 0,
            'com.apple.sessionAgent': 0,
        },
        'OnDemand': 1,
        'PID': 71,
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.CFPasteboardClient': 0,
            'com.apple.axserver': 0,
            'com.apple.tsm.portname': 0,
        },
        'Program': 'loginwindow',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d2c4d0.anonymous.Google Chrome H',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[32438].subset.554',
        'MachServices': {
            'com.Breakpad.BootstrapParent': 0,
        },
        'OnDemand': 1,
        'PID': 32438,
        'Program': 'Google Chrome H',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.metadata.mdwrite',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.metadata.mdwrite': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/System/Library/Frameworks/CoreServices.framework/Frameworks/Metadata.framework/Versions/A/Support/mdwrite'
        ],
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': 'com.apple.iCalPush',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.iCalPush': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/Applications/iCal.app/Contents/Resources/iCalPush'
        ],
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.locationmenu',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'Program': '/System/Library/CoreServices/LocationMenu.app/Contents/MacOS/LocationMenu',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d36670.anonymous.login',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'PID': 78130,
        'Program': 'login',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.mdmclient.agent',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.mdmclient.agent': 0,
        },
        'OnDemand': 1,
        'PID': 741,
        'ProgramArguments': [
            '/usr/libexec/mdmclient',
            'agent'
        ],
        'TimeOut': 30,
        'TransactionCount': 0,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.speech.voiceinstallerd',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.speech.voiceinstallerd': 0,
        },
        'OnDemand': 1,
        'Program': '/System/Library/PrivateFrameworks/SpeechObjects.framework/Versions/A/VoiceInstallerd',
        'TimeOut': 30,
        'TransactionCount': '-1',
    },
    {
        'Label': '0x7f8759c2d4c0.anonymous.login',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'PID': 82316,
        'Program': 'login',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c1c3f0.anonymous.Google Chrome H',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
        },
        'OnDemand': 1,
        'PID': 32291,
        'PerJobMachServices': {
            'WakeUpProcessPort': 0,
            'com.apple.axserver': 0,
            'com.apple.tsm.portname': 0,
        },
        'Program': 'Google Chrome H',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c1fe10.anonymous.launchd',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[60522].subset.309',
        'OnDemand': 1,
        'PID': 499,
        'Program': 'launchd',
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.parentalcontrols.check',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'OnDemand': 1,
        'Program': '/System/Library/PrivateFrameworks/FamilyControls.framework/Resources/pcdCheck',
        'TimeOut': 30,
    },
    {
        'Label': 'com.apple.findmymacmessenger',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'com.apple.findmymacmessenger': 0,
        },
        'OnDemand': 1,
        'Program': '/System/Library/PrivateFrameworks/FindMyMac.framework/Resources/FindMyMacMessenger.app/Contents/MacOS/FindMyMacMessenger',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d22060.anonymous.Google Chrome H',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[32656].subset.619',
        'MachServices': {
            'com.Breakpad.BootstrapParent': 0,
        },
        'OnDemand': 1,
        'PID': 32656,
        'Program': 'Google Chrome H',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d204a0.anonymous.GoogleTalkPlugi',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': '[0x0-0x4d44d4].com.google.GoogleTalkPluginD[32298].subset.257',
        'MachServices': {
            'com.Breakpad.BootstrapParent': 0,
        },
        'OnDemand': 1,
        'PID': 32298,
        'Program': 'GoogleTalkPlugi',
        'TimeOut': 30,
    },
    {
        'EnableTransactions': 1,
        'Label': 'com.apple.UserEventAgent-Aqua',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Aqua',
        'MachServices': {
            'Apple80211Agent': 0,
            'com.apple.UserEventAgent.EventMonitor': 0,
            'com.apple.crashreporter.appusage': 0,
        },
        'OnDemand': 1,
        'PID': 623,
        'ProgramArguments': [
            '/usr/libexec/UserEventAgent',
            '-l',
            'Aqua'
        ],
        'TimeOut': 30,
        'TransactionCount': 0,
    },
    {
        'Label': '0x7f8759d2b440.anonymous.diskimages-help',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Background',
        'OnDemand': 1,
        'PID': 48113,
        'Program': 'diskimages-help',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c2b5a0.mach_init.crash_inspector',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[32283].subset.231',
        'MachServices': {
            'com.Breakpad.Inspector32283': 0,
        },
        'OnDemand': 1,
        'ProgramArguments': [
            '/Applications/Google Chrome.app/Contents/Versions/21.0.1180.79/Google Chrome Framework.framework/Resources/crash_inspector',
            'com.Breakpad.Inspector32283'
        ],
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759c1ae80.anonymous.launchd',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[32283].subset.231',
        'OnDemand': 1,
        'PID': 499,
        'Program': 'launchd',
        'TimeOut': 30,
    },
    {
        'Label': '0x7f8759d2caf0.anonymous.launchd',
        'LastExitStatus': 0,
        'LimitLoadToSessionType': 'Google Chrome H[32438].subset.554',
        'OnDemand': 1,
        'PID': 499,
        'Program': 'launchd',
        'TimeOut': 30,
    }
]

#pylint: enable=C6310
