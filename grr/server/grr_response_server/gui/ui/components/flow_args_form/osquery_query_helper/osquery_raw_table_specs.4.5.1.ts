/** Osquery schema. */
export const tableSpecs451 =
    [
      {
        'cacheable': false,
        'evented': false,
        'name': 'account_policy_data',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/account_policy_data.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'uid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'User ID'
          },
          {
            'index': false,
            'name': 'creation_time',
            'required': false,
            'hidden': false,
            'type': 'double',
            'description': 'When the account was first created'
          },
          {
            'index': false,
            'name': 'failed_login_count',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description':
                'The number of failed login attempts using an incorrect password. Count resets after a correct password is entered.'
          },
          {
            'index': false,
            'name': 'failed_login_timestamp',
            'required': false,
            'hidden': false,
            'type': 'double',
            'description':
                'The time of the last failed login attempt. Resets after a correct password is entered'
          },
          {
            'index': false,
            'name': 'password_last_set_time',
            'required': false,
            'hidden': false,
            'type': 'double',
            'description': 'The time the password was last changed'
          }
        ],
        'description':
            'Additional OS X user account data from the AccountPolicy section of OpenDirectory.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'acpi_tables',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/acpi_tables.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'ACPI table name'
          },
          {
            'index': false,
            'name': 'size',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Size of compiled table data'
          },
          {
            'index': false,
            'name': 'md5',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'MD5 hash of table content'
          }
        ],
        'description':
            'Firmware ACPI functional table common metadata and content.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'ad_config',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/ad_config.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The OS X-specific configuration name'
          },
          {
            'index': false,
            'name': 'domain',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Active Directory trust domain'
          },
          {
            'index': false,
            'name': 'option',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Canonical name of option'
          },
          {
            'index': false,
            'name': 'value',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Variable typed option value'
          }
        ],
        'description': 'OS X Active Directory configuration.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'alf',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/alf.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'allow_signed_enabled',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 If allow signed mode is enabled else 0'
          },
          {
            'index': false,
            'name': 'firewall_unload',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 If firewall unloading enabled else 0'
          },
          {
            'index': false,
            'name': 'global_state',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                '1 If the firewall is enabled with exceptions, 2 if the firewall is configured to block all incoming connections, else 0'
          },
          {
            'index': false,
            'name': 'logging_enabled',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 If logging mode is enabled else 0'
          },
          {
            'index': false,
            'name': 'logging_option',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Firewall logging option'
          },
          {
            'index': false,
            'name': 'stealth_enabled',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 If stealth mode is enabled else 0'
          },
          {
            'index': false,
            'name': 'version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Application Layer Firewall version'
          }
        ],
        'description': 'OS X application layer firewall (ALF) service details.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'alf_exceptions',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/alf_exceptions.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Path to the executable that is excepted'
          },
          {
            'index': false,
            'name': 'state',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Firewall exception state'
          }
        ],
        'description':
            'OS X application layer firewall (ALF) service exceptions.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'alf_explicit_auths',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/alf_explicit_auths.table',
        'platforms': ['darwin'],
        'columns': [{
          'index': false,
          'name': 'process',
          'required': false,
          'hidden': false,
          'type': 'text',
          'description': 'Process name explicitly allowed'
        }],
        'description': 'ALF services explicitly allowed to perform networking.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'app_schemes',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/app_schemes.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'scheme',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of the scheme/protocol'
          },
          {
            'index': false,
            'name': 'handler',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Application label for the handler'
          },
          {
            'index': false,
            'name': 'enabled',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 if this handler is the OS default, else 0'
          },
          {
            'index': false,
            'name': 'external',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                '1 if this handler does NOT exist on OS X by default, else 0'
          },
          {
            'index': false,
            'name': 'protected',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                '1 if this handler is protected (reserved) by OS X, else 0'
          }
        ],
        'description':
            'OS X application schemes and handlers (e.g., http, file, mailto).'
      },
      {
        'cacheable': false,
        'evented': true,
        'name': 'apparmor_events',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/linux/apparmor_events.table',
        'platforms': ['linux'],
        'columns': [
          {
            'index': false,
            'name': 'type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Event type'
          },
          {
            'index': false,
            'name': 'message',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Raw audit message'
          },
          {
            'index': false,
            'name': 'time',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Time of execution in UNIX time'
          },
          {
            'index': false,
            'name': 'uptime',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Time of execution in system uptime'
          },
          {
            'index': false,
            'name': 'eid',
            'required': false,
            'hidden': true,
            'type': 'text',
            'description': 'Event ID'
          },
          {
            'index': false,
            'name': 'apparmor',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Apparmor Status like ALLOWED, DENIED etc.'
          },
          {
            'index': false,
            'name': 'operation',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Permission requested by the process'
          },
          {
            'index': false,
            'name': 'parent',
            'required': false,
            'hidden': false,
            'type': 'unsigned_bigint',
            'description': 'Parent process PID'
          },
          {
            'index': false,
            'name': 'profile',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Apparmor profile name'
          },
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Process name'
          },
          {
            'index': false,
            'name': 'pid',
            'required': false,
            'hidden': false,
            'type': 'unsigned_bigint',
            'description': 'Process ID'
          },
          {
            'index': false,
            'name': 'comm',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Command-line name of the command that was used to invoke the analyzed process'
          },
          {
            'index': false,
            'name': 'denied_mask',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Denied permissions for the process'
          },
          {
            'index': false,
            'name': 'capname',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Capability requested by the process'
          },
          {
            'index': false,
            'name': 'fsuid',
            'required': false,
            'hidden': false,
            'type': 'unsigned_bigint',
            'description': 'Filesystem user ID'
          },
          {
            'index': false,
            'name': 'ouid',
            'required': false,
            'hidden': false,
            'type': 'unsigned_bigint',
            'description': 'Object owner\'s user ID'
          },
          {
            'index': false,
            'name': 'capability',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Capability number'
          },
          {
            'index': false,
            'name': 'requested_mask',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Requested access mask'
          },
          {
            'index': false,
            'name': 'info',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Additional information'
          },
          {
            'index': false,
            'name': 'error',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Error information'
          },
          {
            'index': false,
            'name': 'namespace',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'AppArmor namespace'
          },
          {
            'index': false,
            'name': 'label',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'AppArmor label'
          }
        ],
        'description': 'Track AppArmor events.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'apparmor_profiles',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/linux/apparmor_profiles.table',
        'platforms': ['linux'],
        'columns': [
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Unique, aa-status compatible, policy identifier.'
          },
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Policy name.'
          },
          {
            'index': false,
            'name': 'attach',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Which executable(s) a profile will attach to.'
          },
          {
            'index': false,
            'name': 'mode',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'How the policy is applied.'
          },
          {
            'index': false,
            'name': 'sha1',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'A unique hash that identifies this policy.'
          }
        ],
        'description': 'Track active AppArmor profiles.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'appcompat_shims',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/appcompat_shims.table',
        'platforms': ['windows'],
        'columns': [
          {
            'index': false,
            'name': 'executable',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Name of the executable that is being shimmed. This is pulled from the registry.'
          },
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'This is the path to the SDB database.'
          },
          {
            'index': false,
            'name': 'description',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Description of the SDB.'
          },
          {
            'index': false,
            'name': 'install_time',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Install time of the SDB'
          },
          {
            'index': false,
            'name': 'type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Type of the SDB database.'
          },
          {
            'index': false,
            'name': 'sdb_id',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Unique GUID of the SDB.'
          }
        ],
        'description':
            'Application Compatibility shims are a way to persist malware. This table presents the AppCompat Shim information from the registry in a nice format. See http://files.brucon.org/2015/Tomczak_and_Ballenthin_Shims_for_the_Win.pdf for more details.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'apps',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/apps.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of the Name.app folder'
          },
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Absolute and full Name.app path'
          },
          {
            'index': false,
            'name': 'bundle_executable',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Info properties CFBundleExecutable label'
          },
          {
            'index': false,
            'name': 'bundle_identifier',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Info properties CFBundleIdentifier label'
          },
          {
            'index': false,
            'name': 'bundle_name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Info properties CFBundleName label'
          },
          {
            'index': false,
            'name': 'bundle_short_version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Info properties CFBundleShortVersionString label'
          },
          {
            'index': false,
            'name': 'bundle_version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Info properties CFBundleVersion label'
          },
          {
            'index': false,
            'name': 'bundle_package_type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Info properties CFBundlePackageType label'
          },
          {
            'index': false,
            'name': 'environment',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Application-set environment variables'
          },
          {
            'index': false,
            'name': 'element',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Does the app identify as a background agent'
          },
          {
            'index': false,
            'name': 'compiler',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Info properties DTCompiler label'
          },
          {
            'index': false,
            'name': 'development_region',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Info properties CFBundleDevelopmentRegion label'
          },
          {
            'index': false,
            'name': 'display_name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Info properties CFBundleDisplayName label'
          },
          {
            'index': false,
            'name': 'info_string',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Info properties CFBundleGetInfoString label'
          },
          {
            'index': false,
            'name': 'minimum_system_version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Minimum version of OS X required for the app to run'
          },
          {
            'index': false,
            'name': 'category',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The UTI that categorizes the app for the App Store'
          },
          {
            'index': false,
            'name': 'applescript_enabled',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Info properties NSAppleScriptEnabled label'
          },
          {
            'index': false,
            'name': 'copyright',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Info properties NSHumanReadableCopyright label'
          },
          {
            'index': false,
            'name': 'last_opened_time',
            'required': false,
            'hidden': false,
            'type': 'double',
            'description': 'The time that the app was last used'
          }
        ],
        'description':
            'OS X applications installed in known search paths (e.g., /Applications).'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'apt_sources',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/apt_sources.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Repository name'
          },
          {
            'index': false,
            'name': 'source',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Source file'
          },
          {
            'index': false,
            'name': 'base_uri',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Repository base URI'
          },
          {
            'index': false,
            'name': 'release',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Release name'
          },
          {
            'index': false,
            'name': 'version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Repository source version'
          },
          {
            'index': false,
            'name': 'maintainer',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Repository maintainer'
          },
          {
            'index': false,
            'name': 'components',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Repository components'
          },
          {
            'index': false,
            'name': 'architectures',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Repository architectures'
          }
        ],
        'description': 'Current list of APT repositories or software channels.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'arp_cache',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/arp_cache.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns': [
          {
            'index': false,
            'name': 'address',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'IPv4 address target'
          },
          {
            'index': false,
            'name': 'mac',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'MAC address of broadcasted address'
          },
          {
            'index': false,
            'name': 'interface',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Interface of the network for the MAC'
          },
          {
            'index': false,
            'name': 'permanent',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': '1 for true, 0 for false'
          }
        ],
        'description':
            'Address resolution cache, both static and dynamic (from ARP, NDP).'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'asl',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/asl.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'time',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Unix timestamp.  Set automatically'
          },
          {
            'index': false,
            'name': 'time_nano_sec',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Nanosecond time.'
          },
          {
            'index': false,
            'name': 'host',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Sender\'s address (set by the server).'
          },
          {
            'index': false,
            'name': 'sender',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Sender\'s identification string.  Default is process name.'
          },
          {
            'index': false,
            'name': 'facility',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Sender\'s facility.  Default is \'user\'.'
          },
          {
            'index': false,
            'name': 'pid',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'Sending process ID encoded as a string.  Set automatically.'
          },
          {
            'index': false,
            'name': 'gid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'GID that sent the log message (set by the server).'
          },
          {
            'index': false,
            'name': 'uid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'UID that sent the log message (set by the server).'
          },
          {
            'index': false,
            'name': 'level',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Log level number.  See levels in asl.h.'
          },
          {
            'index': false,
            'name': 'message',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Message text.'
          },
          {
            'index': false,
            'name': 'ref_pid',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Reference PID for messages proxied by launchd'
          },
          {
            'index': false,
            'name': 'ref_proc',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Reference process for messages proxied by launchd'
          },
          {
            'index': false,
            'name': 'extra',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Extra columns, in JSON format. Queries against this column are performed entirely in SQLite, so do not benefit from efficient querying via asl.h.'
          }
        ],
        'description':
            'Queries the Apple System Log data structure for system events.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'atom_packages',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/atom_packages.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Package display name'
          },
          {
            'index': false,
            'name': 'version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Package supplied version'
          },
          {
            'index': false,
            'name': 'description',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Package supplied description'
          },
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Package\'s package.json path'
          },
          {
            'index': false,
            'name': 'license',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'License for package'
          },
          {
            'index': false,
            'name': 'homepage',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Package supplied homepage'
          },
          {
            'index': false,
            'name': 'uid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'The local user that owns the plugin'
          }
        ],
        'description':
            'Lists all atom packages in a directory or globally installed in a system.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'augeas',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/augeas.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'node',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The node path of the configuration item'
          },
          {
            'index': false,
            'name': 'value',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The value of the configuration item'
          },
          {
            'index': false,
            'name': 'label',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The label of the configuration item'
          },
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The path to the configuration file'
          }
        ],
        'description': 'Configuration files parsed by augeas.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'authenticode',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/authenticode.table',
        'platforms': ['windows'],
        'columns': [
          {
            'index': false,
            'name': 'path',
            'required': true,
            'hidden': false,
            'type': 'text',
            'description': 'Must provide a path or directory'
          },
          {
            'index': false,
            'name': 'original_program_name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'The original program name that the publisher has signed'
          },
          {
            'index': false,
            'name': 'serial_number',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The certificate serial number'
          },
          {
            'index': false,
            'name': 'issuer_name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The certificate issuer name'
          },
          {
            'index': false,
            'name': 'subject_name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The certificate subject name'
          },
          {
            'index': false,
            'name': 'result',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The signature check result'
          }
        ],
        'description':
            'File (executable, bundle, installer, disk) code signing status.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'authorization_mechanisms',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/authorization_mechanisms.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'label',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Label of the authorization right'
          },
          {
            'index': false,
            'name': 'plugin',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Authorization plugin name'
          },
          {
            'index': false,
            'name': 'mechanism',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of the mechanism that will be called'
          },
          {
            'index': false,
            'name': 'privileged',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'If privileged it will run as root, else as an anonymous user'
          },
          {
            'index': false,
            'name': 'entry',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The whole string entry'
          }
        ],
        'description': 'OS X Authorization mechanisms database.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'authorizations',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/authorizations.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'label',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Item name, usually in reverse domain format'
          },
          {
            'index': false,
            'name': 'modified',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Label top-level key'
          },
          {
            'index': false,
            'name': 'allow_root',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Label top-level key'
          },
          {
            'index': false,
            'name': 'timeout',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Label top-level key'
          },
          {
            'index': false,
            'name': 'version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Label top-level key'
          },
          {
            'index': false,
            'name': 'tries',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Label top-level key'
          },
          {
            'index': false,
            'name': 'authenticate_user',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Label top-level key'
          },
          {
            'index': false,
            'name': 'shared',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Label top-level key'
          },
          {
            'index': false,
            'name': 'comment',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Label top-level key'
          },
          {
            'index': false,
            'name': 'created',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Label top-level key'
          },
          {
            'index': false,
            'name': 'class',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Label top-level key'
          },
          {
            'index': false,
            'name': 'session_owner',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Label top-level key'
          }
        ],
        'description': 'OS X Authorization rights database.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'authorized_keys',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/authorized_keys.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'uid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'The local owner of authorized_keys file'
          },
          {
            'index': false,
            'name': 'algorithm',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'algorithm of key'
          },
          {
            'index': false,
            'name': 'key',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'parsed authorized keys line'
          },
          {
            'index': false,
            'name': 'key_file',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Path to the authorized_keys file'
          }
        ],
        'description': 'A line-delimited authorized_keys table.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'autoexec',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/autoexec.table',
        'platforms': ['windows'],
        'columns': [
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Path to the executable'
          },
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of the program'
          },
          {
            'index': false,
            'name': 'source',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Source table of the autoexec item'
          }
        ],
        'description':
            'Aggregate of executables that will automatically execute on the target machine. This is an amalgamation of other tables like services, scheduled_tasks, startup_items and more.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'azure_instance_metadata',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/azure_instance_metadata.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns': [
          {
            'index': false,
            'name': 'location',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Azure Region the VM is running in'
          },
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of the VM'
          },
          {
            'index': false,
            'name': 'offer',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Offer information for the VM image (Azure image gallery VMs only)'
          },
          {
            'index': false,
            'name': 'publisher',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Publisher of the VM image'
          },
          {
            'index': false,
            'name': 'sku',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'SKU for the VM image'
          },
          {
            'index': false,
            'name': 'version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Version of the VM image'
          },
          {
            'index': false,
            'name': 'os_type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Linux or Windows'
          },
          {
            'index': false,
            'name': 'platform_update_domain',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Update domain the VM is running in'
          },
          {
            'index': false,
            'name': 'platform_fault_domain',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Fault domain the VM is running in'
          },
          {
            'index': false,
            'name': 'vm_id',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Unique identifier for the VM'
          },
          {
            'index': false,
            'name': 'vm_size',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'VM size'
          },
          {
            'index': false,
            'name': 'subscription_id',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Azure subscription for the VM'
          },
          {
            'index': false,
            'name': 'resource_group_name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Resource group for the VM'
          },
          {
            'index': false,
            'name': 'placement_group_id',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Placement group for the VM scale set'
          },
          {
            'index': false,
            'name': 'vm_scale_set_name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'VM scale set name'
          },
          {
            'index': false,
            'name': 'zone',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Availability zone of the VM'
          }
        ],
        'description': 'Azure instance metadata.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'azure_instance_tags',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/azure_instance_tags.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns': [
          {
            'index': false,
            'name': 'vm_id',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Unique identifier for the VM'
          },
          {
            'index': false,
            'name': 'key',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The tag key'
          },
          {
            'index': false,
            'name': 'value',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The tag value'
          }
        ],
        'description': 'Azure instance tags.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'background_activities_moderator',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/background_activities_moderator.table',
        'platforms': ['windows'],
        'columns': [
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Application file path.'
          },
          {
            'index': false,
            'name': 'last_execution_time',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Most recent time application was executed.'
          },
          {
            'index': false,
            'name': 'sid',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'User SID.'
          }
        ],
        'description':
            'Background Activities Moderator (BAM) tracks application execution.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'battery',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/battery.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'manufacturer',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The battery manufacturer\'s name'
          },
          {
            'index': false,
            'name': 'manufacture_date',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'The date the battery was manufactured UNIX Epoch'
          },
          {
            'index': false,
            'name': 'model',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The battery\'s model number'
          },
          {
            'index': false,
            'name': 'serial_number',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The battery\'s unique serial number'
          },
          {
            'index': false,
            'name': 'cycle_count',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'The number of charge/discharge cycles'
          },
          {
            'index': false,
            'name': 'health',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'One of the following: "Good" describes a well-performing battery, "Fair" describes a functional battery with limited capacity, or "Poor" describes a battery that\'s not capable of providing power'
          },
          {
            'index': false,
            'name': 'condition',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'One of the following: "Normal" indicates the condition of the battery is within normal tolerances, "Service Needed" indicates that the battery should be checked out by a licensed Mac repair service, "Permanent Failure" indicates the battery needs replacement'
          },
          {
            'index': false,
            'name': 'state',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'One of the following: "AC Power" indicates the battery is connected to an external power source, "Battery Power" indicates that the battery is drawing internal power, "Off Line" indicates the battery is off-line or no longer connected'
          },
          {
            'index': false,
            'name': 'charging',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                '1 if the battery is currently being charged by a power source. 0 otherwise'
          },
          {
            'index': false,
            'name': 'charged',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                '1 if the battery is currently completely charged. 0 otherwise'
          },
          {
            'index': false,
            'name': 'designed_capacity',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'The battery\'s designed capacity in mAh'
          },
          {
            'index': false,
            'name': 'max_capacity',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'The battery\'s actual capacity when it is fully charged in mAh'
          },
          {
            'index': false,
            'name': 'current_capacity',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'The battery\'s current charged capacity in mAh'
          },
          {
            'index': false,
            'name': 'percent_remaining',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'The percentage of battery remaining before it is drained'
          },
          {
            'index': false,
            'name': 'amperage',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'The battery\'s current amperage in mA'
          },
          {
            'index': false,
            'name': 'voltage',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'The battery\'s current voltage in mV'
          },
          {
            'index': false,
            'name': 'minutes_until_empty',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'The number of minutes until the battery is fully depleted. This value is -1 if this time is still being calculated'
          },
          {
            'index': false,
            'name': 'minutes_to_full_charge',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'The number of minutes until the battery is fully charged. This value is -1 if this time is still being calculated'
          }
        ],
        'description':
            'Provides information about the internal battery of a Macbook.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'bitlocker_info',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/bitlocker_info.table',
        'platforms': ['windows'],
        'columns': [
          {
            'index': false,
            'name': 'device_id',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'ID of the encrypted drive.'
          },
          {
            'index': false,
            'name': 'drive_letter',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Drive letter of the encrypted drive.'
          },
          {
            'index': false,
            'name': 'persistent_volume_id',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Persistent ID of the drive.'
          },
          {
            'index': false,
            'name': 'conversion_status',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'The bitlocker conversion status of the drive.'
          },
          {
            'index': false,
            'name': 'protection_status',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'The bitlocker protection status of the drive.'
          },
          {
            'index': false,
            'name': 'encryption_method',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The encryption type of the device.'
          },
          {
            'index': false,
            'name': 'version',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'The FVE metadata version of the drive.'
          },
          {
            'index': false,
            'name': 'percentage_encrypted',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'The percentage of the drive that is encrypted.'
          },
          {
            'index': false,
            'name': 'lock_status',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'The accessibility status of the drive from Windows.'
          }
        ],
        'description': 'Retrieve bitlocker status of the machine.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'block_devices',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/block_devices.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Block device name'
          },
          {
            'index': false,
            'name': 'parent',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Block device parent name'
          },
          {
            'index': false,
            'name': 'vendor',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Block device vendor string'
          },
          {
            'index': false,
            'name': 'model',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Block device model string identifier'
          },
          {
            'index': false,
            'name': 'size',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Block device size in blocks'
          },
          {
            'index': false,
            'name': 'block_size',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Block size in bytes'
          },
          {
            'index': false,
            'name': 'uuid',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Block device Universally Unique Identifier'
          },
          {
            'index': false,
            'name': 'type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Block device type string'
          },
          {
            'index': false,
            'name': 'label',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Block device label string'
          }
        ],
        'description':
            'Block (buffered access) device file nodes: disks, ramdisks, and DMG containers.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'browser_plugins',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/browser_plugins.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'uid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'The local user that owns the plugin'
          },
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Plugin display name'
          },
          {
            'index': false,
            'name': 'identifier',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Plugin identifier'
          },
          {
            'index': false,
            'name': 'version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Plugin short version'
          },
          {
            'index': false,
            'name': 'sdk',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Build SDK used to compile plugin'
          },
          {
            'index': false,
            'name': 'description',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Plugin description text'
          },
          {
            'index': false,
            'name': 'development_region',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Plugin language-localization'
          },
          {
            'index': false,
            'name': 'native',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Plugin requires native execution'
          },
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Path to plugin bundle'
          },
          {
            'index': false,
            'name': 'disabled',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Is the plugin disabled. 1 = Disabled'
          }
        ],
        'description': 'All C/NPAPI browser plugin details for all users.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'carbon_black_info',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/carbon_black_info.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns':
            [
              {
                'index': false,
                'name': 'sensor_id',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Sensor ID of the Carbon Black sensor'
              },
              {
                'index': false,
                'name': 'config_name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Sensor group'
              },
              {
                'index': false,
                'name': 'collect_store_files',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    'If the sensor is configured to send back binaries to the Carbon Black server'
              },
              {
                'index': false,
                'name': 'collect_module_loads',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    'If the sensor is configured to capture module loads'
              },
              {
                'index': false,
                'name': 'collect_module_info',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    'If the sensor is configured to collect metadata of binaries'
              },
              {
                'index': false,
                'name': 'collect_file_mods',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    'If the sensor is configured to collect file modification events'
              },
              {
                'index': false,
                'name': 'collect_reg_mods',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    'If the sensor is configured to collect registry modification events'
              },
              {
                'index': false,
                'name': 'collect_net_conns',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    'If the sensor is configured to collect network connections'
              },
              {
                'index': false,
                'name': 'collect_processes',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'If the sensor is configured to process events'
              },
              {
                'index': false,
                'name': 'collect_cross_processes',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    'If the sensor is configured to cross process events'
              },
              {
                'index': false,
                'name': 'collect_emet_events',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'If the sensor is configured to EMET events'
              },
              {
                'index': false,
                'name': 'collect_data_file_writes',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    'If the sensor is configured to collect non binary file writes'
              },
              {
                'index': false,
                'name': 'collect_process_user_context',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    'If the sensor is configured to collect the user running a process'
              },
              {
                'index': false,
                'name': 'collect_sensor_operations',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Unknown'
              },
              {
                'index': false,
                'name': 'log_file_disk_quota_mb',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Event file disk quota in MB'
              },
              {
                'index': false,
                'name': 'log_file_disk_quota_percentage',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Event file disk quota in a percentage'
              },
              {
                'index': false,
                'name': 'protection_disabled',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    'If the sensor is configured to report tamper events'
              },
              {
                'index': false,
                'name': 'sensor_ip_addr',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'IP address of the sensor'
              },
              {
                'index': false,
                'name': 'sensor_backend_server',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Carbon Black server'
              },
              {
                'index': false,
                'name': 'event_queue',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    'Size in bytes of Carbon Black event files on disk'
              },
              {
                'index': false,
                'name': 'binary_queue',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    'Size in bytes of binaries waiting to be sent to Carbon Black server'
              }
            ],
        'description': 'Returns info about a Carbon Black sensor install.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'carves',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/carves.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns':
            [
              {
                'index': false,
                'name': 'time',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Time at which the carve was kicked off'
              },
              {
                'index': false,
                'name': 'sha256',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'A SHA256 sum of the carved archive'
              },
              {
                'index': false,
                'name': 'size',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Size of the carved archive'
              },
              {
                'index': false,
                'name': 'path',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The path of the requested carve'
              },
              {
                'index': false,
                'name': 'status',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'Status of the carve, can be STARTING, PENDING, SUCCESS, or FAILED'
              },
              {
                'index': false,
                'name': 'carve_guid',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Identifying value of the carve session'
              },
              {
                'index': false,
                'name': 'carve',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Set this value to \'1\' to start a file carve'
              }
            ],
        'description':
            'List the set of completed and in-progress carves. If carve=1 then the query is treated as a new carve request.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'certificates',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/macwin/certificates.table',
        'platforms': ['darwin', 'windows'],
        'columns':
            [
              {
                'index': false,
                'name': 'common_name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Certificate CommonName'
              },
              {
                'index': false,
                'name': 'subject',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Certificate distinguished name'
              },
              {
                'index': false,
                'name': 'issuer',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Certificate issuer distinguished name'
              },
              {
                'index': false,
                'name': 'ca',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    '1 if CA: true (certificate is an authority) else 0'
              },
              {
                'index': false,
                'name': 'self_signed',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': '1 if self-signed, else 0'
              },
              {
                'index': false,
                'name': 'not_valid_before',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Lower bound of valid date'
              },
              {
                'index': false,
                'name': 'not_valid_after',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Certificate expiration data'
              },
              {
                'index': false,
                'name': 'signing_algorithm',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Signing algorithm used'
              },
              {
                'index': false,
                'name': 'key_algorithm',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Key algorithm used'
              },
              {
                'index': false,
                'name': 'key_strength',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Key size used for RSA/DSA, or curve name'
              },
              {
                'index': false,
                'name': 'key_usage',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Certificate key usage and extended key usage'
              },
              {
                'index': false,
                'name': 'subject_key_id',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'SKID an optionally included SHA1'
              },
              {
                'index': false,
                'name': 'authority_key_id',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'AKID an optionally included SHA1'
              },
              {
                'index': false,
                'name': 'sha1',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'SHA1 hash of the raw certificate contents'
              },
              {
                'index': false,
                'name': 'path',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Path to Keychain or PEM bundle'
              },
              {
                'index': false,
                'name': 'serial',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Certificate serial number'
              },
              {
                'index': false,
                'name': 'sid',
                'required': false,
                'hidden': true,
                'type': 'text',
                'description': 'SID'
              },
              {
                'index': false,
                'name': 'store_location',
                'required': false,
                'hidden': true,
                'type': 'text',
                'description': 'Certificate system store location'
              },
              {
                'index': false,
                'name': 'store',
                'required': false,
                'hidden': true,
                'type': 'text',
                'description': 'Certificate system store'
              },
              {
                'index': false,
                'name': 'username',
                'required': false,
                'hidden': true,
                'type': 'text',
                'description': 'Username'
              },
              {
                'index': false,
                'name': 'store_id',
                'required': false,
                'hidden': true,
                'type': 'text',
                'description':
                    'Exists for service/user stores. Contains raw store id provided by WinAPI.'
              }
            ],
        'description':
            'Certificate Authorities installed in Keychains/ca-bundles.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'chassis_info',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/chassis_info.table',
        'platforms': ['windows'],
        'columns':
            [
              {
                'index': false,
                'name': 'audible_alarm',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'If TRUE, the frame is equipped with an audible alarm.'
              },
              {
                'index': false,
                'name': 'breach_description',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'If provided, gives a more detailed description of a detected security breach.'
              },
              {
                'index': false,
                'name': 'chassis_types',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'A comma-separated list of chassis types, such as Desktop or Laptop.'
              },
              {
                'index': false,
                'name': 'description',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'An extended description of the chassis if available.'
              },
              {
                'index': false,
                'name': 'lock',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'If TRUE, the frame is equipped with a lock.'
              },
              {
                'index': false,
                'name': 'manufacturer',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The manufacturer of the chassis.'
              },
              {
                'index': false,
                'name': 'model',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The model of the chassis.'
              },
              {
                'index': false,
                'name': 'security_breach',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'The physical status of the chassis such as Breach Successful, Breach Attempted, etc.'
              },
              {
                'index': false,
                'name': 'serial',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The serial number of the chassis.'
              },
              {
                'index': false,
                'name': 'smbios_tag',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The assigned asset tag number of the chassis.'
              },
              {
                'index': false,
                'name': 'sku',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The Stock Keeping Unit number if available.'
              },
              {
                'index': false,
                'name': 'status',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'If available, gives various operational or nonoperational statuses such as OK, Degraded, and Pred Fail.'
              },
              {
                'index': false,
                'name': 'visible_alarm',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'If TRUE, the frame is equipped with a visual alarm.'
              }
            ],
        'description':
            'Display information pertaining to the chassis and its security status.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'chocolatey_packages',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/chocolatey_packages.table',
        'platforms': ['windows'],
        'columns':
            [
              {
                'index': false,
                'name': 'name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Package display name'
              },
              {
                'index': false,
                'name': 'version',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Package-supplied version'
              },
              {
                'index': false,
                'name': 'summary',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Package-supplied summary'
              },
              {
                'index': false,
                'name': 'author',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Optional package author'
              },
              {
                'index': false,
                'name': 'license',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'License under which package is launched'
              },
              {
                'index': false,
                'name': 'path',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Path at which this package resides'
              }
            ],
        'description': 'Chocolatey packages installed in a system.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'chrome_extension_content_scripts',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/chrome_extension_content_scripts.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns':
            [
              {
                'index': false,
                'name': 'uid',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'The local user that owns the extension'
              },
              {
                'index': false,
                'name': 'identifier',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Extension identifier'
              },
              {
                'index': false,
                'name': 'version',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Extension-supplied version'
              },
              {
                'index': false,
                'name': 'script',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The content script used by the extension'
              },
              {
                'index': false,
                'name': 'match',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The pattern that the script is matched against'
              }
            ],
        'description': 'Chrome browser extension content scripts.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'chrome_extensions',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/chrome_extensions.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns':
            [
              {
                'index': false,
                'name': 'uid',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'The local user that owns the extension'
              },
              {
                'index': false,
                'name': 'name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Extension display name'
              },
              {
                'index': false,
                'name': 'profile',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The Chrome profile that contains this extension'
              },
              {
                'index': false,
                'name': 'identifier',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Extension identifier'
              },
              {
                'index': false,
                'name': 'version',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Extension-supplied version'
              },
              {
                'index': false,
                'name': 'description',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Extension-optional description'
              },
              {
                'index': false,
                'name': 'locale',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Default locale supported by extension'
              },
              {
                'index': false,
                'name': 'update_url',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Extension-supplied update URI'
              },
              {
                'index': false,
                'name': 'author',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Optional extension author'
              },
              {
                'index': false,
                'name': 'persistent',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    '1 If extension is persistent across all tabs else 0'
              },
              {
                'index': false,
                'name': 'path',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Path to extension folder'
              },
              {
                'index': false,
                'name': 'permissions',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The permissions required by the extension'
              },
              {
                'index': false,
                'name': 'optional_permissions',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'The permissions optionally required by the extensions'
              }
            ],
        'description': 'Chrome browser extensions.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'connectivity',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/connectivity.table',
        'platforms': ['windows'],
        'columns':
            [
              {
                'index': false,
                'name': 'disconnected',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    'True if the all interfaces are not connected to any network'
              },
              {
                'index': false,
                'name': 'ipv4_no_traffic',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    'True if any interface is connected via IPv4, but has seen no traffic'
              },
              {
                'index': false,
                'name': 'ipv6_no_traffic',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    'True if any interface is connected via IPv6, but has seen no traffic'
              },
              {
                'index': false,
                'name': 'ipv4_subnet',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    'True if any interface is connected to the local subnet via IPv4'
              },
              {
                'index': false,
                'name': 'ipv4_local_network',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    'True if any interface is connected to a routed network via IPv4'
              },
              {
                'index': false,
                'name': 'ipv4_internet',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    'True if any interface is connected to the Internet via IPv4'
              },
              {
                'index': false,
                'name': 'ipv6_subnet',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    'True if any interface is connected to the local subnet via IPv6'
              },
              {
                'index': false,
                'name': 'ipv6_local_network',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    'True if any interface is connected to a routed network via IPv6'
              },
              {
                'index': false,
                'name': 'ipv6_internet',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    'True if any interface is connected to the Internet via IPv6'
              }
            ],
        'description': 'Provides the overall system\'s network state.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'cpu_info',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/cpu_info.table',
        'platforms': ['windows'],
        'columns':
            [
              {
                'index': false,
                'name': 'device_id',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The DeviceID of the CPU.'
              },
              {
                'index': false,
                'name': 'model',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The model of the CPU.'
              },
              {
                'index': false,
                'name': 'manufacturer',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The manufacturer of the CPU.'
              },
              {
                'index': false,
                'name': 'processor_type',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'The processor type, such as Central, Math, or Video.'
              },
              {
                'index': false,
                'name': 'availability',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The availability and status of the CPU.'
              },
              {
                'index': false,
                'name': 'cpu_status',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'The current operating status of the CPU.'
              },
              {
                'index': false,
                'name': 'number_of_cores',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The number of cores of the CPU.'
              },
              {
                'index': false,
                'name': 'logical_processors',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'The number of logical processors of the CPU.'
              },
              {
                'index': false,
                'name': 'address_width',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The width of the CPU address bus.'
              },
              {
                'index': false,
                'name': 'current_clock_speed',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'The current frequency of the CPU.'
              },
              {
                'index': false,
                'name': 'max_clock_speed',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'The maximum possible frequency of the CPU.'
              },
              {
                'index': false,
                'name': 'socket_designation',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'The assigned socket on the board for the given CPU.'
              }
            ],
        'description': 'Retrieve cpu hardware info of the machine.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'cpu_time',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/cpu_time.table',
        'platforms': ['darwin', 'linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'core',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Name of the cpu (core)'
              },
              {
                'index': false,
                'name': 'user',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Time spent in user mode'
              },
              {
                'index': false,
                'name': 'nice',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description':
                    'Time spent in user mode with low priority (nice)'
              },
              {
                'index': false,
                'name': 'system',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Time spent in system mode'
              },
              {
                'index': false,
                'name': 'idle',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Time spent in the idle task'
              },
              {
                'index': false,
                'name': 'iowait',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Time spent waiting for I/O to complete'
              },
              {
                'index': false,
                'name': 'irq',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Time spent servicing interrupts'
              },
              {
                'index': false,
                'name': 'softirq',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Time spent servicing softirqs'
              },
              {
                'index': false,
                'name': 'steal',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description':
                    'Time spent in other operating systems when running in a virtualized environment'
              },
              {
                'index': false,
                'name': 'guest',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description':
                    'Time spent running a virtual CPU for a guest OS under the control of the Linux kernel'
              },
              {
                'index': false,
                'name': 'guest_nice',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Time spent running a niced guest '
              }
            ],
        'description':
            'Displays information from /proc/stat file about the time the cpu cores spent in different parts of the system.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'cpuid',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/cpuid.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns':
            [
              {
                'index': false,
                'name': 'feature',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Present feature flags'
              },
              {
                'index': false,
                'name': 'value',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Bit value or string'
              },
              {
                'index': false,
                'name': 'output_register',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Register used to for feature value'
              },
              {
                'index': false,
                'name': 'output_bit',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Bit in register value for feature value'
              },
              {
                'index': false,
                'name': 'input_eax',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Value of EAX used'
              }
            ],
        'description': 'Useful CPU features from the cpuid ASM call.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'crashes',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/crashes.table',
        'platforms': ['darwin'],
        'columns':
            [
              {
                'index': false,
                'name': 'type',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Type of crash log'
              },
              {
                'index': false,
                'name': 'pid',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Process (or thread) ID of the crashed process'
              },
              {
                'index': false,
                'name': 'path',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Path to the crashed process'
              },
              {
                'index': false,
                'name': 'crash_path',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Location of log file'
              },
              {
                'index': false,
                'name': 'identifier',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Identifier of the crashed process'
              },
              {
                'index': false,
                'name': 'version',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Version info of the crashed process'
              },
              {
                'index': false,
                'name': 'parent',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Parent PID of the crashed process'
              },
              {
                'index': false,
                'name': 'responsible',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Process responsible for the crashed process'
              },
              {
                'index': false,
                'name': 'uid',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'User ID of the crashed process'
              },
              {
                'index': false,
                'name': 'datetime',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Date/Time at which the crash occurred'
              },
              {
                'index': false,
                'name': 'crashed_thread',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Thread ID which crashed'
              },
              {
                'index': false,
                'name': 'stack_trace',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Most recent frame from the stack trace'
              },
              {
                'index': false,
                'name': 'exception_type',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Exception type of the crash'
              },
              {
                'index': false,
                'name': 'exception_codes',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Exception codes from the crash'
              },
              {
                'index': false,
                'name': 'exception_notes',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Exception notes from the crash'
              },
              {
                'index': false,
                'name': 'registers',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The value of the system registers'
              }
            ],
        'description': 'Application, System, and Mobile App crash logs.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'crontab',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/crontab.table',
        'platforms': ['darwin', 'linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'event',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The job @event name (rare)'
              },
              {
                'index': false,
                'name': 'minute',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The exact minute for the job'
              },
              {
                'index': false,
                'name': 'hour',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The hour of the day for the job'
              },
              {
                'index': false,
                'name': 'day_of_month',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The day of the month for the job'
              },
              {
                'index': false,
                'name': 'month',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The month of the year for the job'
              },
              {
                'index': false,
                'name': 'day_of_week',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The day of the week for the job'
              },
              {
                'index': false,
                'name': 'command',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Raw command string'
              },
              {
                'index': false,
                'name': 'path',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'File parsed'
              }
            ],
        'description': 'Line parsed values from system and user cron/tab.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'cups_destinations',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/cups_destinations.table',
        'platforms': ['darwin'],
        'columns':
            [
              {
                'index': false,
                'name': 'name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Name of the printer'
              },
              {
                'index': false,
                'name': 'option_name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Option name'
              },
              {
                'index': false,
                'name': 'option_value',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Option value'
              }
            ],
        'description': 'Returns all configured printers.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'cups_jobs',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/cups_jobs.table',
        'platforms': ['darwin'],
        'columns':
            [
              {
                'index': false,
                'name': 'title',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Title of the printed job'
              },
              {
                'index': false,
                'name': 'destination',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The printer the job was sent to'
              },
              {
                'index': false,
                'name': 'user',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The user who printed the job'
              },
              {
                'index': false,
                'name': 'format',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The format of the print job'
              },
              {
                'index': false,
                'name': 'size',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'The size of the print job'
              },
              {
                'index': false,
                'name': 'completed_time',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'When the job completed printing'
              },
              {
                'index': false,
                'name': 'processing_time',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'How long the job took to process'
              },
              {
                'index': false,
                'name': 'creation_time',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'When the print request was initiated'
              }
            ],
        'description': 'Returns all completed print jobs from cups.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'curl',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/curl.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns':
            [
              {
                'index': false,
                'name': 'url',
                'required': true,
                'hidden': false,
                'type': 'text',
                'description': 'The url for the request'
              },
              {
                'index': false,
                'name': 'method',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The HTTP method for the request'
              },
              {
                'index': false,
                'name': 'user_agent',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The user-agent string to use for the request'
              },
              {
                'index': false,
                'name': 'response_code',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'The HTTP status code for the response'
              },
              {
                'index': false,
                'name': 'round_trip_time',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Time taken to complete the request'
              },
              {
                'index': false,
                'name': 'bytes',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Number of bytes in the response'
              },
              {
                'index': false,
                'name': 'result',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The HTTP response body'
              }
            ],
        'description': 'Perform an http request and return stats about it.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'curl_certificate',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/curl_certificate.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns':
            [
              {
                'index': false,
                'name': 'hostname',
                'required': true,
                'hidden': false,
                'type': 'text',
                'description': 'Hostname (domain[:port]) to CURL'
              },
              {
                'index': false,
                'name': 'common_name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Common name of company issued to'
              },
              {
                'index': false,
                'name': 'organization',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Organization issued to'
              },
              {
                'index': false,
                'name': 'organization_unit',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Organization unit issued to'
              },
              {
                'index': false,
                'name': 'serial_number',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Certificate serial number'
              },
              {
                'index': false,
                'name': 'issuer_common_name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Issuer common name'
              },
              {
                'index': false,
                'name': 'issuer_organization',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Issuer organization'
              },
              {
                'index': false,
                'name': 'issuer_organization_unit',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Issuer organization unit'
              },
              {
                'index': false,
                'name': 'valid_from',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Period of validity start date'
              },
              {
                'index': false,
                'name': 'valid_to',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Period of validity end date'
              },
              {
                'index': false,
                'name': 'sha256_fingerprint',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'SHA-256 fingerprint'
              },
              {
                'index': false,
                'name': 'sha1_fingerprint',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'SHA1 fingerprint'
              },
              {
                'index': false,
                'name': 'version',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Version Number'
              },
              {
                'index': false,
                'name': 'signature_algorithm',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Signature Algorithm'
              },
              {
                'index': false,
                'name': 'signature',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Signature'
              },
              {
                'index': false,
                'name': 'subject_key_identifier',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Subject Key Identifier'
              },
              {
                'index': false,
                'name': 'authority_key_identifier',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Authority Key Identifier'
              },
              {
                'index': false,
                'name': 'key_usage',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Usage of key in certificate'
              },
              {
                'index': false,
                'name': 'extended_key_usage',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Extended usage of key in certificate'
              },
              {
                'index': false,
                'name': 'policies',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Certificate Policies'
              },
              {
                'index': false,
                'name': 'subject_alternative_names',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Subject Alternative Name'
              },
              {
                'index': false,
                'name': 'issuer_alternative_names',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Issuer Alternative Name'
              },
              {
                'index': false,
                'name': 'info_access',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Authority Information Access'
              },
              {
                'index': false,
                'name': 'subject_info_access',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Subject Information Access'
              },
              {
                'index': false,
                'name': 'policy_mappings',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Policy Mappings'
              },
              {
                'index': false,
                'name': 'has_expired',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': '1 if the certificate has expired, 0 otherwise'
              },
              {
                'index': false,
                'name': 'basic_constraint',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Basic Constraints'
              },
              {
                'index': false,
                'name': 'name_constraints',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Name Constraints'
              },
              {
                'index': false,
                'name': 'policy_constraints',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Policy Constraints'
              },
              {
                'index': false,
                'name': 'dump_certificate',
                'required': false,
                'hidden': true,
                'type': 'integer',
                'description': 'Set this value to \'1\' to dump certificate'
              },
              {
                'index': false,
                'name': 'timeout',
                'required': false,
                'hidden': true,
                'type': 'integer',
                'description':
                    'Set this value to the timeout in seconds to complete the TLS handshake (default 4s, use 0 for no timeout)'
              },
              {
                'index': false,
                'name': 'pem',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Certificate PEM format'
              }
            ],
        'description':
            'Inspect TLS certificates by connecting to input hostnames.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'deb_packages',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/linux/deb_packages.table',
        'platforms': ['linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Package name'
              },
              {
                'index': false,
                'name': 'version',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Package version'
              },
              {
                'index': false,
                'name': 'source',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Package source'
              },
              {
                'index': false,
                'name': 'size',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Package size in bytes'
              },
              {
                'index': false,
                'name': 'arch',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Package architecture'
              },
              {
                'index': false,
                'name': 'revision',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Package revision'
              },
              {
                'index': false,
                'name': 'status',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Package status'
              },
              {
                'index': false,
                'name': 'maintainer',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Package maintainer'
              },
              {
                'index': false,
                'name': 'section',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Package section'
              },
              {
                'index': false,
                'name': 'priority',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Package priority'
              },
              {
                'index': false,
                'name': 'pid_with_namespace',
                'required': false,
                'hidden': true,
                'type': 'integer',
                'description': 'Pids that contain a namespace'
              },
              {
                'index': false,
                'name': 'mount_namespace_id',
                'required': false,
                'hidden': true,
                'type': 'text',
                'description': 'Mount namespace id'
              }
            ],
        'description': 'The installed DEB package database.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'default_environment',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/default_environment.table',
        'platforms': ['windows'],
        'columns':
            [
              {
                'index': false,
                'name': 'variable',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Name of the environment variable'
              },
              {
                'index': false,
                'name': 'value',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Value of the environment variable'
              },
              {
                'index': false,
                'name': 'expand',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': '1 if the variable needs expanding, 0 otherwise'
              }
            ],
        'description': 'Default environment variables and values.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'device_file',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/sleuthkit/device_file.table',
        'platforms': ['darwin', 'linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'device',
                'required': true,
                'hidden': false,
                'type': 'text',
                'description': 'Absolute file path to device node'
              },
              {
                'index': false,
                'name': 'partition',
                'required': true,
                'hidden': false,
                'type': 'text',
                'description': 'A partition number'
              },
              {
                'index': false,
                'name': 'path',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'A logical path within the device node'
              },
              {
                'index': false,
                'name': 'filename',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Name portion of file path'
              },
              {
                'index': false,
                'name': 'inode',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Filesystem inode number'
              },
              {
                'index': false,
                'name': 'uid',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Owning user ID'
              },
              {
                'index': false,
                'name': 'gid',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Owning group ID'
              },
              {
                'index': false,
                'name': 'mode',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Permission bits'
              },
              {
                'index': false,
                'name': 'size',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Size of file in bytes'
              },
              {
                'index': false,
                'name': 'block_size',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Block size of filesystem'
              },
              {
                'index': false,
                'name': 'atime',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Last access time'
              },
              {
                'index': false,
                'name': 'mtime',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Last modification time'
              },
              {
                'index': false,
                'name': 'ctime',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Creation time'
              },
              {
                'index': false,
                'name': 'hard_links',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Number of hard links'
              },
              {
                'index': false,
                'name': 'type',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'File status'
              }
            ],
        'description':
            'Similar to the file table, but use TSK and allow block address access.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'device_firmware',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/device_firmware.table',
        'platforms': ['darwin'],
        'columns':
            [
              {
                'index': false,
                'name': 'type',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Type of device'
              },
              {
                'index': false,
                'name': 'device',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The device name'
              },
              {
                'index': false,
                'name': 'version',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Firmware version'
              }
            ],
        'description': 'A best-effort list of discovered firmware versions.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'device_hash',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/sleuthkit/device_hash.table',
        'platforms': ['darwin', 'linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'device',
                'required': true,
                'hidden': false,
                'type': 'text',
                'description': 'Absolute file path to device node'
              },
              {
                'index': false,
                'name': 'partition',
                'required': true,
                'hidden': false,
                'type': 'text',
                'description': 'A partition number'
              },
              {
                'index': false,
                'name': 'inode',
                'required': true,
                'hidden': false,
                'type': 'bigint',
                'description': 'Filesystem inode number'
              },
              {
                'index': false,
                'name': 'md5',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'MD5 hash of provided inode data'
              },
              {
                'index': false,
                'name': 'sha1',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'SHA1 hash of provided inode data'
              },
              {
                'index': false,
                'name': 'sha256',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'SHA256 hash of provided inode data'
              }
            ],
        'description':
            'Similar to the hash table, but use TSK and allow block address access.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'device_partitions',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/sleuthkit/device_partitions.table',
        'platforms': ['darwin', 'linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'device',
                'required': true,
                'hidden': false,
                'type': 'text',
                'description': 'Absolute file path to device node'
              },
              {
                'index': false,
                'name': 'partition',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'A partition number or description'
              },
              {
                'index': false,
                'name': 'label',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': ''
              },
              {
                'index': false,
                'name': 'type',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': ''
              },
              {
                'index': false,
                'name': 'offset',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': ''
              },
              {
                'index': false,
                'name': 'blocks_size',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Byte size of each block'
              },
              {
                'index': false,
                'name': 'blocks',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Number of blocks'
              },
              {
                'index': false,
                'name': 'inodes',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Number of meta nodes'
              },
              {
                'index': false,
                'name': 'flags',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': ''
              }
            ],
        'description':
            'Use TSK to enumerate details about partitions on a disk device.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'disk_encryption',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/disk_encryption.table',
        'platforms': ['darwin', 'linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Disk name'
              },
              {
                'index': false,
                'name': 'uuid',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Disk Universally Unique Identifier'
              },
              {
                'index': false,
                'name': 'encrypted',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    '1 If encrypted: true (disk is encrypted), else 0'
              },
              {
                'index': false,
                'name': 'type',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'Description of cipher type and mode if available'
              },
              {
                'index': false,
                'name': 'uid',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'Currently authenticated user if available (Apple)'
              },
              {
                'index': false,
                'name': 'user_uuid',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'UUID of authenticated user if available (Apple)'
              },
              {
                'index': false,
                'name': 'encryption_status',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'Disk encryption status with one of following values: encrypted | not encrypted | undefined'
              }
            ],
        'description': 'Disk encryption status and information.'
      },
      {
        'cacheable': false,
        'evented': true,
        'name': 'disk_events',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/disk_events.table',
        'platforms': ['darwin'],
        'columns':
            [
              {
                'index': false,
                'name': 'action',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Appear or disappear'
              },
              {
                'index': false,
                'name': 'path',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Path of the DMG file accessed'
              },
              {
                'index': false,
                'name': 'name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Disk event name'
              },
              {
                'index': false,
                'name': 'device',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Disk event BSD name'
              },
              {
                'index': false,
                'name': 'uuid',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'UUID of the volume inside DMG if available'
              },
              {
                'index': false,
                'name': 'size',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Size of partition in bytes'
              },
              {
                'index': false,
                'name': 'ejectable',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': '1 if ejectable, 0 if not'
              },
              {
                'index': false,
                'name': 'mountable',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': '1 if mountable, 0 if not'
              },
              {
                'index': false,
                'name': 'writable',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': '1 if writable, 0 if not'
              },
              {
                'index': false,
                'name': 'content',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Disk event content'
              },
              {
                'index': false,
                'name': 'media_name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Disk event media name string'
              },
              {
                'index': false,
                'name': 'vendor',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Disk event vendor string'
              },
              {
                'index': false,
                'name': 'filesystem',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Filesystem if available'
              },
              {
                'index': false,
                'name': 'checksum',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'UDIF Master checksum if available (CRC32)'
              },
              {
                'index': false,
                'name': 'time',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Time of appearance/disappearance in UNIX time'
              },
              {
                'index': false,
                'name': 'eid',
                'required': false,
                'hidden': true,
                'type': 'text',
                'description': 'Event ID'
              }
            ],
        'description':
            'Track DMG disk image events (appearance/disappearance) when opened.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'disk_info',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/disk_info.table',
        'platforms': ['windows'],
        'columns':
            [
              {
                'index': false,
                'name': 'partitions',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Number of detected partitions on disk.'
              },
              {
                'index': false,
                'name': 'disk_index',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Physical drive number of the disk.'
              },
              {
                'index': false,
                'name': 'type',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The interface type of the disk.'
              },
              {
                'index': false,
                'name': 'id',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'The unique identifier of the drive on the system.'
              },
              {
                'index': false,
                'name': 'pnp_device_id',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'The unique identifier of the drive on the system.'
              },
              {
                'index': false,
                'name': 'disk_size',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Size of the disk.'
              },
              {
                'index': false,
                'name': 'manufacturer',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The manufacturer of the disk.'
              },
              {
                'index': false,
                'name': 'hardware_model',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Hard drive model.'
              },
              {
                'index': false,
                'name': 'name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The label of the disk object.'
              },
              {
                'index': false,
                'name': 'serial',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The serial number of the disk.'
              },
              {
                'index': false,
                'name': 'description',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The OS\'s description of the disk.'
              }
            ],
        'description':
            'Retrieve basic information about the physical disks of a system.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'dns_cache',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/dns_cache.table',
        'platforms': ['windows'],
        'columns':
            [
              {
                'index': false,
                'name': 'name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'DNS record name'
              },
              {
                'index': false,
                'name': 'type',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'DNS record type'
              },
              {
                'index': false,
                'name': 'flags',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'DNS record flags'
              }
            ],
        'description':
            'Enumerate the DNS cache using the undocumented DnsGetCacheDataTable function in dnsapi.dll.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'dns_resolvers',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/dns_resolvers.table',
        'platforms': ['darwin', 'linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'id',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Address type index or order'
              },
              {
                'index': false,
                'name': 'type',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Address type: sortlist, nameserver, search'
              },
              {
                'index': false,
                'name': 'address',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Resolver IP/IPv6 address'
              },
              {
                'index': false,
                'name': 'netmask',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Address (sortlist) netmask length'
              },
              {
                'index': false,
                'name': 'options',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Resolver options'
              }
            ],
        'description': 'Resolvers used by this host.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'docker_container_fs_changes',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/docker_container_fs_changes.table',
        'platforms': ['darwin', 'linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'id',
                'required': true,
                'hidden': false,
                'type': 'text',
                'description': 'Container ID'
              },
              {
                'index': false,
                'name': 'path',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'FIle or directory path relative to rootfs'
              },
              {
                'index': false,
                'name': 'change_type',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Type of change: C:Modified, A:Added, D:Deleted'
              }
            ],
        'description':
            'Changes to files or directories on container\'s filesystem.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'docker_container_labels',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/docker_container_labels.table',
        'platforms': ['darwin', 'linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'id',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Container ID'
              },
              {
                'index': false,
                'name': 'key',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Label key'
              },
              {
                'index': false,
                'name': 'value',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Optional label value'
              }
            ],
        'description': 'Docker container labels.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'docker_container_mounts',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/docker_container_mounts.table',
        'platforms': ['darwin', 'linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'id',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Container ID'
              },
              {
                'index': false,
                'name': 'type',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Type of mount (bind, volume)'
              },
              {
                'index': false,
                'name': 'name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Optional mount name'
              },
              {
                'index': false,
                'name': 'source',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Source path on host'
              },
              {
                'index': false,
                'name': 'destination',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Destination path inside container'
              },
              {
                'index': false,
                'name': 'driver',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Driver providing the mount'
              },
              {
                'index': false,
                'name': 'mode',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Mount options (rw, ro)'
              },
              {
                'index': false,
                'name': 'rw',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': '1 if read/write. 0 otherwise'
              },
              {
                'index': false,
                'name': 'propagation',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Mount propagation'
              }
            ],
        'description': 'Docker container mounts.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'docker_container_networks',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/docker_container_networks.table',
        'platforms': ['darwin', 'linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'id',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Container ID'
              },
              {
                'index': false,
                'name': 'name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Network name'
              },
              {
                'index': false,
                'name': 'network_id',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Network ID'
              },
              {
                'index': false,
                'name': 'endpoint_id',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Endpoint ID'
              },
              {
                'index': false,
                'name': 'gateway',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Gateway'
              },
              {
                'index': false,
                'name': 'ip_address',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'IP address'
              },
              {
                'index': false,
                'name': 'ip_prefix_len',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'IP subnet prefix length'
              },
              {
                'index': false,
                'name': 'ipv6_gateway',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'IPv6 gateway'
              },
              {
                'index': false,
                'name': 'ipv6_address',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'IPv6 address'
              },
              {
                'index': false,
                'name': 'ipv6_prefix_len',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'IPv6 subnet prefix length'
              },
              {
                'index': false,
                'name': 'mac_address',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'MAC address'
              }
            ],
        'description': 'Docker container networks.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'docker_container_ports',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/docker_container_ports.table',
        'platforms': ['darwin', 'linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'id',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Container ID'
              },
              {
                'index': false,
                'name': 'type',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Protocol (tcp, udp)'
              },
              {
                'index': false,
                'name': 'port',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Port inside the container'
              },
              {
                'index': false,
                'name': 'host_ip',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'Host IP address on which public port is listening'
              },
              {
                'index': false,
                'name': 'host_port',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Host port'
              }
            ],
        'description': 'Docker container ports.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'docker_container_processes',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/docker_container_processes.table',
        'platforms': ['darwin', 'linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'id',
                'required': true,
                'hidden': false,
                'type': 'text',
                'description': 'Container ID'
              },
              {
                'index': false,
                'name': 'pid',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Process ID'
              },
              {
                'index': false,
                'name': 'name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The process path or shorthand argv[0]'
              },
              {
                'index': false,
                'name': 'cmdline',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Complete argv'
              },
              {
                'index': false,
                'name': 'state',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Process state'
              },
              {
                'index': false,
                'name': 'uid',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'User ID'
              },
              {
                'index': false,
                'name': 'gid',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Group ID'
              },
              {
                'index': false,
                'name': 'euid',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Effective user ID'
              },
              {
                'index': false,
                'name': 'egid',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Effective group ID'
              },
              {
                'index': false,
                'name': 'suid',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Saved user ID'
              },
              {
                'index': false,
                'name': 'sgid',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Saved group ID'
              },
              {
                'index': false,
                'name': 'wired_size',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Bytes of unpagable memory used by process'
              },
              {
                'index': false,
                'name': 'resident_size',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Bytes of private memory used by process'
              },
              {
                'index': false,
                'name': 'total_size',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Total virtual memory size'
              },
              {
                'index': false,
                'name': 'start_time',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description':
                    'Process start in seconds since boot (non-sleeping)'
              },
              {
                'index': false,
                'name': 'parent',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Process parent\'s PID'
              },
              {
                'index': false,
                'name': 'pgroup',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Process group'
              },
              {
                'index': false,
                'name': 'threads',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Number of threads used by process'
              },
              {
                'index': false,
                'name': 'nice',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Process nice level (-20 to 20, default 0)'
              },
              {
                'index': false,
                'name': 'user',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'User name'
              },
              {
                'index': false,
                'name': 'time',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Cumulative CPU time. [DD-]HH:MM:SS format'
              },
              {
                'index': false,
                'name': 'cpu',
                'required': false,
                'hidden': false,
                'type': 'double',
                'description': 'CPU utilization as percentage'
              },
              {
                'index': false,
                'name': 'mem',
                'required': false,
                'hidden': false,
                'type': 'double',
                'description': 'Memory utilization as percentage'
              }
            ],
        'description': 'Docker container processes.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'docker_container_stats',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/docker_container_stats.table',
        'platforms': ['darwin', 'linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'id',
                'required': true,
                'hidden': false,
                'type': 'text',
                'description': 'Container ID'
              },
              {
                'index': false,
                'name': 'name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Container name'
              },
              {
                'index': false,
                'name': 'pids',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Number of processes'
              },
              {
                'index': false,
                'name': 'read',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'UNIX time when stats were read'
              },
              {
                'index': false,
                'name': 'preread',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'UNIX time when stats were last read'
              },
              {
                'index': false,
                'name': 'interval',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description':
                    'Difference between read and preread in nano-seconds'
              },
              {
                'index': false,
                'name': 'disk_read',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Total disk read bytes'
              },
              {
                'index': false,
                'name': 'disk_write',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Total disk write bytes'
              },
              {
                'index': false,
                'name': 'num_procs',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Number of processors'
              },
              {
                'index': false,
                'name': 'cpu_total_usage',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Total CPU usage'
              },
              {
                'index': false,
                'name': 'cpu_kernelmode_usage',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'CPU kernel mode usage'
              },
              {
                'index': false,
                'name': 'cpu_usermode_usage',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'CPU user mode usage'
              },
              {
                'index': false,
                'name': 'system_cpu_usage',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'CPU system usage'
              },
              {
                'index': false,
                'name': 'online_cpus',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Online CPUs'
              },
              {
                'index': false,
                'name': 'pre_cpu_total_usage',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Last read total CPU usage'
              },
              {
                'index': false,
                'name': 'pre_cpu_kernelmode_usage',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Last read CPU kernel mode usage'
              },
              {
                'index': false,
                'name': 'pre_cpu_usermode_usage',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Last read CPU user mode usage'
              },
              {
                'index': false,
                'name': 'pre_system_cpu_usage',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Last read CPU system usage'
              },
              {
                'index': false,
                'name': 'pre_online_cpus',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Last read online CPUs'
              },
              {
                'index': false,
                'name': 'memory_usage',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Memory usage'
              },
              {
                'index': false,
                'name': 'memory_max_usage',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Memory maximum usage'
              },
              {
                'index': false,
                'name': 'memory_limit',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Memory limit'
              },
              {
                'index': false,
                'name': 'network_rx_bytes',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Total network bytes read'
              },
              {
                'index': false,
                'name': 'network_tx_bytes',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Total network bytes transmitted'
              }
            ],
        'description':
            'Docker container statistics. Queries on this table take at least one second.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'docker_containers',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/docker_containers.table',
        'platforms': ['darwin', 'linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'id',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Container ID'
              },
              {
                'index': false,
                'name': 'name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Container name'
              },
              {
                'index': false,
                'name': 'image',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'Docker image (name) used to launch this container'
              },
              {
                'index': false,
                'name': 'image_id',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Docker image ID'
              },
              {
                'index': false,
                'name': 'command',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Command with arguments'
              },
              {
                'index': false,
                'name': 'created',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Time of creation as UNIX time'
              },
              {
                'index': false,
                'name': 'state',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'Container state (created, restarting, running, removing, paused, exited, dead)'
              },
              {
                'index': false,
                'name': 'status',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Container status information'
              },
              {
                'index': false,
                'name': 'pid',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Identifier of the initial process'
              },
              {
                'index': false,
                'name': 'path',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Container path'
              },
              {
                'index': false,
                'name': 'config_entrypoint',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Container entrypoint(s)'
              },
              {
                'index': false,
                'name': 'started_at',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Container start time as string'
              },
              {
                'index': false,
                'name': 'finished_at',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Container finish time as string'
              },
              {
                'index': false,
                'name': 'privileged',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Is the container privileged'
              },
              {
                'index': false,
                'name': 'security_options',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'List of container security options'
              },
              {
                'index': false,
                'name': 'env_variables',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Container environmental variables'
              },
              {
                'index': false,
                'name': 'readonly_rootfs',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Is the root filesystem mounted as read only'
              },
              {
                'index': false,
                'name': 'cgroup_namespace',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'cgroup namespace'
              },
              {
                'index': false,
                'name': 'ipc_namespace',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'IPC namespace'
              },
              {
                'index': false,
                'name': 'mnt_namespace',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Mount namespace'
              },
              {
                'index': false,
                'name': 'net_namespace',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Network namespace'
              },
              {
                'index': false,
                'name': 'pid_namespace',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'PID namespace'
              },
              {
                'index': false,
                'name': 'user_namespace',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'User namespace'
              },
              {
                'index': false,
                'name': 'uts_namespace',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'UTS namespace'
              }
            ],
        'description': 'Docker containers information.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'docker_image_labels',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/docker_image_labels.table',
        'platforms': ['darwin', 'linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'id',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Image ID'
              },
              {
                'index': false,
                'name': 'key',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Label key'
              },
              {
                'index': false,
                'name': 'value',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Optional label value'
              }
            ],
        'description': 'Docker image labels.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'docker_image_layers',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/docker_image_layers.table',
        'platforms': ['darwin', 'linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'id',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Image ID'
              },
              {
                'index': false,
                'name': 'layer_id',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Layer ID'
              },
              {
                'index': false,
                'name': 'layer_order',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Layer Order (1 = base layer)'
              }
            ],
        'description': 'Docker image layers information.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'docker_images',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/docker_images.table',
        'platforms': ['darwin', 'linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'id',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Image ID'
              },
              {
                'index': false,
                'name': 'created',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Time of creation as UNIX time'
              },
              {
                'index': false,
                'name': 'size_bytes',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Size of image in bytes'
              },
              {
                'index': false,
                'name': 'tags',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Comma-separated list of repository tags'
              }
            ],
        'description': 'Docker images information.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'docker_info',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/docker_info.table',
        'platforms': ['darwin', 'linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'id',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Docker system ID'
              },
              {
                'index': false,
                'name': 'containers',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Total number of containers'
              },
              {
                'index': false,
                'name': 'containers_running',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Number of containers currently running'
              },
              {
                'index': false,
                'name': 'containers_paused',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Number of containers in paused state'
              },
              {
                'index': false,
                'name': 'containers_stopped',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Number of containers in stopped state'
              },
              {
                'index': false,
                'name': 'images',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Number of images'
              },
              {
                'index': false,
                'name': 'storage_driver',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Storage driver'
              },
              {
                'index': false,
                'name': 'memory_limit',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    '1 if memory limit support is enabled. 0 otherwise'
              },
              {
                'index': false,
                'name': 'swap_limit',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': '1 if swap limit support is enabled. 0 otherwise'
              },
              {
                'index': false,
                'name': 'kernel_memory',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    '1 if kernel memory limit support is enabled. 0 otherwise'
              },
              {
                'index': false,
                'name': 'cpu_cfs_period',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    '1 if CPU Completely Fair Scheduler (CFS) period support is enabled. 0 otherwise'
              },
              {
                'index': false,
                'name': 'cpu_cfs_quota',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    '1 if CPU Completely Fair Scheduler (CFS) quota support is enabled. 0 otherwise'
              },
              {
                'index': false,
                'name': 'cpu_shares',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    '1 if CPU share weighting support is enabled. 0 otherwise'
              },
              {
                'index': false,
                'name': 'cpu_set',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    '1 if CPU set selection support is enabled. 0 otherwise'
              },
              {
                'index': false,
                'name': 'ipv4_forwarding',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': '1 if IPv4 forwarding is enabled. 0 otherwise'
              },
              {
                'index': false,
                'name': 'bridge_nf_iptables',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    '1 if bridge netfilter iptables is enabled. 0 otherwise'
              },
              {
                'index': false,
                'name': 'bridge_nf_ip6tables',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    '1 if bridge netfilter ip6tables is enabled. 0 otherwise'
              },
              {
                'index': false,
                'name': 'oom_kill_disable',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    '1 if Out-of-memory kill is disabled. 0 otherwise'
              },
              {
                'index': false,
                'name': 'logging_driver',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Logging driver'
              },
              {
                'index': false,
                'name': 'cgroup_driver',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Control groups driver'
              },
              {
                'index': false,
                'name': 'kernel_version',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Kernel version'
              },
              {
                'index': false,
                'name': 'os',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Operating system'
              },
              {
                'index': false,
                'name': 'os_type',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Operating system type'
              },
              {
                'index': false,
                'name': 'architecture',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Hardware architecture'
              },
              {
                'index': false,
                'name': 'cpus',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Number of CPUs'
              },
              {
                'index': false,
                'name': 'memory',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Total memory'
              },
              {
                'index': false,
                'name': 'http_proxy',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'HTTP proxy'
              },
              {
                'index': false,
                'name': 'https_proxy',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'HTTPS proxy'
              },
              {
                'index': false,
                'name': 'no_proxy',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'Comma-separated list of domain extensions proxy should not be used for'
              },
              {
                'index': false,
                'name': 'name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Name of the docker host'
              },
              {
                'index': false,
                'name': 'server_version',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Server version'
              },
              {
                'index': false,
                'name': 'root_dir',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Docker root directory'
              }
            ],
        'description': 'Docker system information.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'docker_network_labels',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/docker_network_labels.table',
        'platforms': ['darwin', 'linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'id',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Network ID'
              },
              {
                'index': false,
                'name': 'key',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Label key'
              },
              {
                'index': false,
                'name': 'value',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Optional label value'
              }
            ],
        'description': 'Docker network labels.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'docker_networks',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/docker_networks.table',
        'platforms': ['darwin', 'linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'id',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Network ID'
              },
              {
                'index': false,
                'name': 'name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Network name'
              },
              {
                'index': false,
                'name': 'driver',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Network driver'
              },
              {
                'index': false,
                'name': 'created',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Time of creation as UNIX time'
              },
              {
                'index': false,
                'name': 'enable_ipv6',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    '1 if IPv6 is enabled on this network. 0 otherwise'
              },
              {
                'index': false,
                'name': 'subnet',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Network subnet'
              },
              {
                'index': false,
                'name': 'gateway',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Network gateway'
              }
            ],
        'description': 'Docker networks information.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'docker_version',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/docker_version.table',
        'platforms': ['darwin', 'linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'version',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Docker version'
              },
              {
                'index': false,
                'name': 'api_version',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'API version'
              },
              {
                'index': false,
                'name': 'min_api_version',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Minimum API version supported'
              },
              {
                'index': false,
                'name': 'git_commit',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Docker build git commit'
              },
              {
                'index': false,
                'name': 'go_version',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Go version'
              },
              {
                'index': false,
                'name': 'os',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Operating system'
              },
              {
                'index': false,
                'name': 'arch',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Hardware architecture'
              },
              {
                'index': false,
                'name': 'kernel_version',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Kernel version'
              },
              {
                'index': false,
                'name': 'build_time',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Build time'
              }
            ],
        'description': 'Docker version information.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'docker_volume_labels',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/docker_volume_labels.table',
        'platforms': ['darwin', 'linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Volume name'
              },
              {
                'index': false,
                'name': 'key',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Label key'
              },
              {
                'index': false,
                'name': 'value',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Optional label value'
              }
            ],
        'description': 'Docker volume labels.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'docker_volumes',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/docker_volumes.table',
        'platforms': ['darwin', 'linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Volume name'
              },
              {
                'index': false,
                'name': 'driver',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Volume driver'
              },
              {
                'index': false,
                'name': 'mount_point',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Mount point'
              },
              {
                'index': false,
                'name': 'type',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Volume type'
              }
            ],
        'description': 'Docker volumes information.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'drivers',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/drivers.table',
        'platforms': ['windows'],
        'columns':
            [
              {
                'index': false,
                'name': 'device_id',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Device ID'
              },
              {
                'index': false,
                'name': 'device_name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Device name'
              },
              {
                'index': false,
                'name': 'image',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Path to driver image file'
              },
              {
                'index': false,
                'name': 'description',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Driver description'
              },
              {
                'index': false,
                'name': 'service',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Driver service name, if one exists'
              },
              {
                'index': false,
                'name': 'service_key',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Driver service registry key'
              },
              {
                'index': false,
                'name': 'version',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Driver version'
              },
              {
                'index': false,
                'name': 'inf',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Associated inf file'
              },
              {
                'index': false,
                'name': 'class',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Device/driver class name'
              },
              {
                'index': false,
                'name': 'provider',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Driver provider'
              },
              {
                'index': false,
                'name': 'manufacturer',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Device manufacturer'
              },
              {
                'index': false,
                'name': 'driver_key',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Driver key'
              },
              {
                'index': false,
                'name': 'date',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Driver date'
              },
              {
                'index': false,
                'name': 'signed',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Whether the driver is signed or not'
              }
            ],
        'description':
            'Details for in-use Windows device drivers. This does not display installed but unused drivers.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'ec2_instance_metadata',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/linux/ec2_instance_metadata.table',
        'platforms': ['linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'instance_id',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'EC2 instance ID'
              },
              {
                'index': false,
                'name': 'instance_type',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'EC2 instance type'
              },
              {
                'index': false,
                'name': 'architecture',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Hardware architecture of this EC2 instance'
              },
              {
                'index': false,
                'name': 'region',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'AWS region in which this instance launched'
              },
              {
                'index': false,
                'name': 'availability_zone',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'Availability zone in which this instance launched'
              },
              {
                'index': false,
                'name': 'local_hostname',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'Private IPv4 DNS hostname of the first interface of this instance'
              },
              {
                'index': false,
                'name': 'local_ipv4',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'Private IPv4 address of the first interface of this instance'
              },
              {
                'index': false,
                'name': 'mac',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'MAC address for the first network interface of this EC2 instance'
              },
              {
                'index': false,
                'name': 'security_groups',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Comma separated list of security group names'
              },
              {
                'index': false,
                'name': 'iam_arn',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'If there is an IAM role associated with the instance, contains instance profile ARN'
              },
              {
                'index': false,
                'name': 'ami_id',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'AMI ID used to launch this EC2 instance'
              },
              {
                'index': false,
                'name': 'reservation_id',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'ID of the reservation'
              },
              {
                'index': false,
                'name': 'account_id',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'AWS account ID which owns this EC2 instance'
              },
              {
                'index': false,
                'name': 'ssh_public_key',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'SSH public key. Only available if supplied at instance launch time'
              }
            ],
        'description': 'EC2 instance metadata.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'ec2_instance_tags',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/linux/ec2_instance_tags.table',
        'platforms': ['linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'instance_id',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'EC2 instance ID'
              },
              {
                'index': false,
                'name': 'key',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Tag key'
              },
              {
                'index': false,
                'name': 'value',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Tag value'
              }
            ],
        'description': 'EC2 instance tag key value pairs.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'elf_dynamic',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/linux/elf_dynamic.table',
        'platforms': ['linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'tag',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Tag ID'
              },
              {
                'index': false,
                'name': 'value',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Tag value'
              },
              {
                'index': false,
                'name': 'class',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Class (32 or 64)'
              },
              {
                'index': false,
                'name': 'path',
                'required': true,
                'hidden': false,
                'type': 'text',
                'description': 'Path to ELF file'
              }
            ],
        'description': 'ELF dynamic section information.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'elf_info',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/linux/elf_info.table',
        'platforms': ['linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'class',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Class type, 32 or 64bit'
              },
              {
                'index': false,
                'name': 'abi',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Section type'
              },
              {
                'index': false,
                'name': 'abi_version',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Section virtual address in memory'
              },
              {
                'index': false,
                'name': 'type',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Offset of section in file'
              },
              {
                'index': false,
                'name': 'machine',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Machine type'
              },
              {
                'index': false,
                'name': 'version',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Object file version'
              },
              {
                'index': false,
                'name': 'entry',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Entry point address'
              },
              {
                'index': false,
                'name': 'flags',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'ELF header flags'
              },
              {
                'index': false,
                'name': 'path',
                'required': true,
                'hidden': false,
                'type': 'text',
                'description': 'Path to ELF file'
              }
            ],
        'description': 'ELF file information.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'elf_sections',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/linux/elf_sections.table',
        'platforms': ['linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Section name'
              },
              {
                'index': false,
                'name': 'type',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Section type'
              },
              {
                'index': false,
                'name': 'vaddr',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Section virtual address in memory'
              },
              {
                'index': false,
                'name': 'offset',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Offset of section in file'
              },
              {
                'index': false,
                'name': 'size',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Size of section'
              },
              {
                'index': false,
                'name': 'flags',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Section attributes'
              },
              {
                'index': false,
                'name': 'link',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Link to other section'
              },
              {
                'index': false,
                'name': 'align',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Segment alignment'
              },
              {
                'index': false,
                'name': 'path',
                'required': true,
                'hidden': false,
                'type': 'text',
                'description': 'Path to ELF file'
              }
            ],
        'description': 'ELF section information.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'elf_segments',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/linux/elf_segments.table',
        'platforms': ['linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Segment type/name'
              },
              {
                'index': false,
                'name': 'offset',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Segment offset in file'
              },
              {
                'index': false,
                'name': 'vaddr',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Segment virtual address in memory'
              },
              {
                'index': false,
                'name': 'psize',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Size of segment in file'
              },
              {
                'index': false,
                'name': 'msize',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Segment offset in memory'
              },
              {
                'index': false,
                'name': 'flags',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Segment attributes'
              },
              {
                'index': false,
                'name': 'align',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Segment alignment'
              },
              {
                'index': false,
                'name': 'path',
                'required': true,
                'hidden': false,
                'type': 'text',
                'description': 'Path to ELF file'
              }
            ],
        'description': 'ELF segment information.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'elf_symbols',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/linux/elf_symbols.table',
        'platforms': ['linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Symbol name'
              },
              {
                'index': false,
                'name': 'addr',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Symbol address (value)'
              },
              {
                'index': false,
                'name': 'size',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Size of object'
              },
              {
                'index': false,
                'name': 'type',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Symbol type'
              },
              {
                'index': false,
                'name': 'binding',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Binding type'
              },
              {
                'index': false,
                'name': 'offset',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Section table index'
              },
              {
                'index': false,
                'name': 'table',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Table name containing symbol'
              },
              {
                'index': false,
                'name': 'path',
                'required': true,
                'hidden': false,
                'type': 'text',
                'description': 'Path to ELF file'
              }
            ],
        'description': 'ELF symbol list.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'etc_hosts',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/etc_hosts.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns':
            [
              {
                'index': false,
                'name': 'address',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'IP address mapping'
              },
              {
                'index': false,
                'name': 'hostnames',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Raw hosts mapping'
              }
            ],
        'description': 'Line-parsed /etc/hosts.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'etc_protocols',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/etc_protocols.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns':
            [
              {
                'index': false,
                'name': 'name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Protocol name'
              },
              {
                'index': false,
                'name': 'number',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Protocol number'
              },
              {
                'index': false,
                'name': 'alias',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Protocol alias'
              },
              {
                'index': false,
                'name': 'comment',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Comment with protocol description'
              }
            ],
        'description': 'Line-parsed /etc/protocols.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'etc_services',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/etc_services.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns':
            [
              {
                'index': false,
                'name': 'name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Service name'
              },
              {
                'index': false,
                'name': 'port',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Service port number'
              },
              {
                'index': false,
                'name': 'protocol',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Transport protocol (TCP/UDP)'
              },
              {
                'index': false,
                'name': 'aliases',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'Optional space separated list of other names for a service'
              },
              {
                'index': false,
                'name': 'comment',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Optional comment for a service.'
              }
            ],
        'description': 'Line-parsed /etc/services.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'event_taps',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/event_taps.table',
        'platforms': ['darwin'],
        'columns':
            [
              {
                'index': false,
                'name': 'enabled',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Is the Event Tap enabled'
              },
              {
                'index': false,
                'name': 'event_tap_id',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Unique ID for the Tap'
              },
              {
                'index': false,
                'name': 'event_tapped',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'The mask that identifies the set of events to be observed.'
              },
              {
                'index': false,
                'name': 'process_being_tapped',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'The process ID of the target application'
              },
              {
                'index': false,
                'name': 'tapping_process',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    'The process ID of the application that created the event tap.'
              }
            ],
        'description': 'Returns information about installed event taps.'
      },
      {
        'cacheable': false,
        'evented': true,
        'name': 'example',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/example.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns':
            [
              {
                'index': false,
                'name': 'name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Description for name column'
              },
              {
                'index': false,
                'name': 'points',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'This is a signed SQLite int column'
              },
              {
                'index': false,
                'name': 'size',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'This is a signed SQLite bigint column'
              },
              {
                'index': false,
                'name': 'action',
                'required': true,
                'hidden': false,
                'type': 'text',
                'description': 'Action performed in generation'
              },
              {
                'index': false,
                'name': 'id',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'An index of some sort'
              },
              {
                'index': false,
                'name': 'path',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Path of example'
              }
            ],
        'description': 'This is an example table spec.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'extended_attributes',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/extended_attributes.table',
        'platforms': ['darwin'],
        'columns':
            [
              {
                'index': false,
                'name': 'path',
                'required': true,
                'hidden': false,
                'type': 'text',
                'description': 'Absolute file path'
              },
              {
                'index': false,
                'name': 'directory',
                'required': true,
                'hidden': false,
                'type': 'text',
                'description': 'Directory of file(s)'
              },
              {
                'index': false,
                'name': 'key',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'Name of the value generated from the extended attribute'
              },
              {
                'index': false,
                'name': 'value',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The parsed information from the attribute'
              },
              {
                'index': false,
                'name': 'base64',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': '1 if the value is base64 encoded else 0'
              }
            ],
        'description':
            'Returns the extended attributes for files (similar to Windows ADS).'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'fan_speed_sensors',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/fan_speed_sensors.table',
        'platforms': ['darwin'],
        'columns':
            [
              {
                'index': false,
                'name': 'fan',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Fan number'
              },
              {
                'index': false,
                'name': 'name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Fan name'
              },
              {
                'index': false,
                'name': 'actual',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Actual speed'
              },
              {
                'index': false,
                'name': 'min',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Minimum speed'
              },
              {
                'index': false,
                'name': 'max',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Maximum speed'
              },
              {
                'index': false,
                'name': 'target',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Target speed'
              }
            ],
        'description': 'Fan speeds.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'fbsd_kmods',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/freebsd/fbsd_kmods.table',
        'platforms': ['freebsd'],
        'columns':
            [
              {
                'index': false,
                'name': 'name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Module name'
              },
              {
                'index': false,
                'name': 'size',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Size of module content'
              },
              {
                'index': false,
                'name': 'refs',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Module reverse dependencies'
              },
              {
                'index': false,
                'name': 'address',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Kernel module address'
              }
            ],
        'description': 'Loaded FreeBSD kernel modules.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'file',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/utility/file.table',
        'platforms': ['darwin', 'linux', 'freebsd', 'windows'],
        'columns':
            [
              {
                'index': false,
                'name': 'path',
                'required': true,
                'hidden': false,
                'type': 'text',
                'description': 'Absolute file path'
              },
              {
                'index': false,
                'name': 'directory',
                'required': true,
                'hidden': false,
                'type': 'text',
                'description': 'Directory of file(s)'
              },
              {
                'index': false,
                'name': 'filename',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Name portion of file path'
              },
              {
                'index': false,
                'name': 'inode',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Filesystem inode number'
              },
              {
                'index': false,
                'name': 'uid',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Owning user ID'
              },
              {
                'index': false,
                'name': 'gid',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Owning group ID'
              },
              {
                'index': false,
                'name': 'mode',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Permission bits'
              },
              {
                'index': false,
                'name': 'device',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Device ID (optional)'
              },
              {
                'index': false,
                'name': 'size',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Size of file in bytes'
              },
              {
                'index': false,
                'name': 'block_size',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Block size of filesystem'
              },
              {
                'index': false,
                'name': 'atime',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Last access time'
              },
              {
                'index': false,
                'name': 'mtime',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Last modification time'
              },
              {
                'index': false,
                'name': 'ctime',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Last status change time'
              },
              {
                'index': false,
                'name': 'btime',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': '(B)irth or (cr)eate time'
              },
              {
                'index': false,
                'name': 'hard_links',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Number of hard links'
              },
              {
                'index': false,
                'name': 'symlink',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': '1 if the path is a symlink, otherwise 0'
              },
              {
                'index': false,
                'name': 'type',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'File status'
              },
              {
                'index': false,
                'name': 'attributes',
                'required': false,
                'hidden': true,
                'type': 'text',
                'description':
                    'File attrib string. See: https://ss64.com/nt/attrib.html'
              },
              {
                'index': false,
                'name': 'volume_serial',
                'required': false,
                'hidden': true,
                'type': 'text',
                'description': 'Volume serial number'
              },
              {
                'index': false,
                'name': 'file_id',
                'required': false,
                'hidden': true,
                'type': 'text',
                'description': 'file ID'
              },
              {
                'index': false,
                'name': 'file_version',
                'required': false,
                'hidden': true,
                'type': 'text',
                'description': 'File version'
              },
              {
                'index': false,
                'name': 'product_version',
                'required': false,
                'hidden': true,
                'type': 'text',
                'description': 'File product version'
              },
              {
                'index': false,
                'name': 'bsd_flags',
                'required': false,
                'hidden': true,
                'type': 'text',
                'description':
                    'The BSD file flags (chflags). Possible values: NODUMP, UF_IMMUTABLE, UF_APPEND, OPAQUE, HIDDEN, ARCHIVED, SF_IMMUTABLE, SF_APPEND'
              },
              {
                'index': false,
                'name': 'pid_with_namespace',
                'required': false,
                'hidden': true,
                'type': 'integer',
                'description': 'Pids that contain a namespace'
              },
              {
                'index': false,
                'name': 'mount_namespace_id',
                'required': false,
                'hidden': true,
                'type': 'text',
                'description': 'Mount namespace id'
              }
            ],
        'description': 'Interactive filesystem attributes and metadata.'
      },
      {
        'cacheable': false,
        'evented': true,
        'name': 'file_events',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/file_events.table',
        'platforms': ['darwin', 'linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'target_path',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The path associated with the event'
              },
              {
                'index': false,
                'name': 'category',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The category of the file defined in the config'
              },
              {
                'index': false,
                'name': 'action',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Change action (UPDATE, REMOVE, etc)'
              },
              {
                'index': false,
                'name': 'transaction_id',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'ID used during bulk update'
              },
              {
                'index': false,
                'name': 'inode',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Filesystem inode number'
              },
              {
                'index': false,
                'name': 'uid',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Owning user ID'
              },
              {
                'index': false,
                'name': 'gid',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Owning group ID'
              },
              {
                'index': false,
                'name': 'mode',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Permission bits'
              },
              {
                'index': false,
                'name': 'size',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Size of file in bytes'
              },
              {
                'index': false,
                'name': 'atime',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Last access time'
              },
              {
                'index': false,
                'name': 'mtime',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Last modification time'
              },
              {
                'index': false,
                'name': 'ctime',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Last status change time'
              },
              {
                'index': false,
                'name': 'md5',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The MD5 of the file after change'
              },
              {
                'index': false,
                'name': 'sha1',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The SHA1 of the file after change'
              },
              {
                'index': false,
                'name': 'sha256',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The SHA256 of the file after change'
              },
              {
                'index': false,
                'name': 'hashed',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    '1 if the file was hashed, 0 if not, -1 if hashing failed'
              },
              {
                'index': false,
                'name': 'time',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Time of file event'
              },
              {
                'index': false,
                'name': 'eid',
                'required': false,
                'hidden': true,
                'type': 'text',
                'description': 'Event ID'
              }
            ],
        'description':
            'Track time/action changes to files specified in configuration data.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'firefox_addons',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/firefox_addons.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns':
            [
              {
                'index': false,
                'name': 'uid',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'The local user that owns the addon'
              },
              {
                'index': false,
                'name': 'name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Addon display name'
              },
              {
                'index': false,
                'name': 'identifier',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Addon identifier'
              },
              {
                'index': false,
                'name': 'creator',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Addon-supported creator string'
              },
              {
                'index': false,
                'name': 'type',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Extension, addon, webapp'
              },
              {
                'index': false,
                'name': 'version',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Addon-supplied version string'
              },
              {
                'index': false,
                'name': 'description',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Addon-supplied description string'
              },
              {
                'index': false,
                'name': 'source_url',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'URL that installed the addon'
              },
              {
                'index': false,
                'name': 'visible',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': '1 If the addon is shown in browser else 0'
              },
              {
                'index': false,
                'name': 'active',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': '1 If the addon is active else 0'
              },
              {
                'index': false,
                'name': 'disabled',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': '1 If the addon is application-disabled else 0'
              },
              {
                'index': false,
                'name': 'autoupdate',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    '1 If the addon applies background updates else 0'
              },
              {
                'index': false,
                'name': 'native',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    '1 If the addon includes binary components else 0'
              },
              {
                'index': false,
                'name': 'location',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Global, profile location'
              },
              {
                'index': false,
                'name': 'path',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Path to plugin bundle'
              }
            ],
        'description': 'Firefox browser extensions, webapps, and addons.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'gatekeeper',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/gatekeeper.table',
        'platforms': ['darwin'],
        'columns':
            [
              {
                'index': false,
                'name': 'assessments_enabled',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': '1 If a Gatekeeper is enabled else 0'
              },
              {
                'index': false,
                'name': 'dev_id_enabled',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    '1 If a Gatekeeper allows execution from identified developers else 0'
              },
              {
                'index': false,
                'name': 'version',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Version of Gatekeeper\'s gke.bundle'
              },
              {
                'index': false,
                'name': 'opaque_version',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Version of Gatekeeper\'s gkopaque.bundle'
              }
            ],
        'description': 'OS X Gatekeeper Details.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'gatekeeper_approved_apps',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/gatekeeper_approved_apps.table',
        'platforms': ['darwin'],
        'columns':
            [
              {
                'index': false,
                'name': 'path',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Path of executable allowed to run'
              },
              {
                'index': false,
                'name': 'requirement',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Code signing requirement language'
              },
              {
                'index': false,
                'name': 'ctime',
                'required': false,
                'hidden': false,
                'type': 'double',
                'description': 'Last change time'
              },
              {
                'index': false,
                'name': 'mtime',
                'required': false,
                'hidden': false,
                'type': 'double',
                'description': 'Last modification time'
              }
            ],
        'description': 'Gatekeeper apps a user has allowed to run.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'groups',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/groups.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns':
            [
              {
                'index': false,
                'name': 'gid',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Unsigned int64 group ID'
              },
              {
                'index': false,
                'name': 'gid_signed',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'A signed int64 version of gid'
              },
              {
                'index': false,
                'name': 'groupname',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Canonical local group name'
              },
              {
                'index': false,
                'name': 'group_sid',
                'required': false,
                'hidden': true,
                'type': 'text',
                'description': 'Unique group ID'
              },
              {
                'index': false,
                'name': 'comment',
                'required': false,
                'hidden': true,
                'type': 'text',
                'description': 'Remarks or comments associated with the group'
              },
              {
                'index': false,
                'name': 'is_hidden',
                'required': false,
                'hidden': true,
                'type': 'integer',
                'description': 'IsHidden attribute set in OpenDirectory'
              }
            ],
        'description': 'Local system groups.'
      },
      {
        'cacheable': false,
        'evented': true,
        'name': 'hardware_events',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/hardware_events.table',
        'platforms': ['darwin', 'linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'action',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Remove, insert, change properties, etc'
              },
              {
                'index': false,
                'name': 'path',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Local device path assigned (optional)'
              },
              {
                'index': false,
                'name': 'type',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Type of hardware and hardware event'
              },
              {
                'index': false,
                'name': 'driver',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Driver claiming the device'
              },
              {
                'index': false,
                'name': 'vendor',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Hardware device vendor'
              },
              {
                'index': false,
                'name': 'vendor_id',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Hex encoded Hardware vendor identifier'
              },
              {
                'index': false,
                'name': 'model',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Hardware device model'
              },
              {
                'index': false,
                'name': 'model_id',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Hex encoded Hardware model identifier'
              },
              {
                'index': false,
                'name': 'serial',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Device serial (optional)'
              },
              {
                'index': false,
                'name': 'revision',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Device revision (optional)'
              },
              {
                'index': false,
                'name': 'time',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Time of hardware event'
              },
              {
                'index': false,
                'name': 'eid',
                'required': false,
                'hidden': true,
                'type': 'text',
                'description': 'Event ID'
              }
            ],
        'description': 'Hardware (PCI/USB/HID) events from UDEV or IOKit.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'hash',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/hash.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns':
            [
              {
                'index': false,
                'name': 'path',
                'required': true,
                'hidden': false,
                'type': 'text',
                'description': 'Must provide a path or directory'
              },
              {
                'index': false,
                'name': 'directory',
                'required': true,
                'hidden': false,
                'type': 'text',
                'description': 'Must provide a path or directory'
              },
              {
                'index': false,
                'name': 'md5',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'MD5 hash of provided filesystem data'
              },
              {
                'index': false,
                'name': 'sha1',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'SHA1 hash of provided filesystem data'
              },
              {
                'index': false,
                'name': 'sha256',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'SHA256 hash of provided filesystem data'
              },
              {
                'index': false,
                'name': 'ssdeep',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'ssdeep hash of provided filesystem data'
              },
              {
                'index': false,
                'name': 'pid_with_namespace',
                'required': false,
                'hidden': true,
                'type': 'integer',
                'description': 'Pids that contain a namespace'
              },
              {
                'index': false,
                'name': 'mount_namespace_id',
                'required': false,
                'hidden': true,
                'type': 'text',
                'description': 'Mount namespace id'
              }
            ],
        'description': 'Filesystem hash data.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'homebrew_packages',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/homebrew_packages.table',
        'platforms': ['darwin'],
        'columns':
            [
              {
                'index': false,
                'name': 'name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Package name'
              },
              {
                'index': false,
                'name': 'path',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Package install path'
              },
              {
                'index': false,
                'name': 'version',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Current \'linked\' version'
              }
            ],
        'description': 'The installed homebrew package database.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'hvci_status',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/hvci_status.table',
        'platforms': ['windows'],
        'columns':
            [
              {
                'index': false,
                'name': 'version',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The version number of the Device Guard build.'
              },
              {
                'index': false,
                'name': 'instance_identifier',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The instance ID of Device Guard.'
              },
              {
                'index': false,
                'name': 'vbs_status',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'The status of the virtualization based security settings. Returns UNKNOWN if an error is encountered.'
              },
              {
                'index': false,
                'name': 'code_integrity_policy_enforcement_status',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'The status of the code integrity policy enforcement settings. Returns UNKNOWN if an error is encountered.'
              },
              {
                'index': false,
                'name': 'umci_policy_status',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'The status of the User Mode Code Integrity security settings. Returns UNKNOWN if an error is encountered.'
              }
            ],
        'description': 'Retrieve HVCI info of the machine.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'ibridge_info',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/ibridge_info.table',
        'platforms': ['darwin'],
        'columns':
            [
              {
                'index': false,
                'name': 'boot_uuid',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Boot UUID of the iBridge controller'
              },
              {
                'index': false,
                'name': 'coprocessor_version',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The manufacturer and chip version'
              },
              {
                'index': false,
                'name': 'firmware_version',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The build version of the firmware'
              },
              {
                'index': false,
                'name': 'unique_chip_id',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Unique id of the iBridge controller'
              }
            ],
        'description':
            'Information about the Apple iBridge hardware controller.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'ie_extensions',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/ie_extensions.table',
        'platforms': ['windows'],
        'columns':
            [
              {
                'index': false,
                'name': 'name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Extension display name'
              },
              {
                'index': false,
                'name': 'registry_path',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Extension identifier'
              },
              {
                'index': false,
                'name': 'version',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Version of the executable'
              },
              {
                'index': false,
                'name': 'path',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Path to executable'
              }
            ],
        'description': 'Internet Explorer browser extensions.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'intel_me_info',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/linwin/intel_me_info.table',
        'platforms': ['darwin', 'linux', 'freebsd', 'windows'],
        'columns':
            [{
              'index': false,
              'name': 'version',
              'required': false,
              'hidden': false,
              'type': 'text',
              'description': 'Intel ME version'
            }],
        'description': 'Intel ME/CSE Info.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'interface_addresses',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/interface_addresses.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns':
            [
              {
                'index': false,
                'name': 'interface',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Interface name'
              },
              {
                'index': false,
                'name': 'address',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Specific address for interface'
              },
              {
                'index': false,
                'name': 'mask',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Interface netmask'
              },
              {
                'index': false,
                'name': 'broadcast',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Broadcast address for the interface'
              },
              {
                'index': false,
                'name': 'point_to_point',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'PtP address for the interface'
              },
              {
                'index': false,
                'name': 'type',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'Type of address. One of dhcp, manual, auto, other, unknown'
              },
              {
                'index': false,
                'name': 'friendly_name',
                'required': false,
                'hidden': true,
                'type': 'text',
                'description': 'The friendly display name of the interface.'
              }
            ],
        'description': 'Network interfaces and relevant metadata.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'interface_details',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/interface_details.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns':
            [
              {
                'index': false,
                'name': 'interface',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Interface name'
              },
              {
                'index': false,
                'name': 'mac',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'MAC of interface (optional)'
              },
              {
                'index': false,
                'name': 'type',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Interface type (includes virtual)'
              },
              {
                'index': false,
                'name': 'mtu',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Network MTU'
              },
              {
                'index': false,
                'name': 'metric',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Metric based on the speed of the interface'
              },
              {
                'index': false,
                'name': 'flags',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Flags (netdevice) for the device'
              },
              {
                'index': false,
                'name': 'ipackets',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Input packets'
              },
              {
                'index': false,
                'name': 'opackets',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Output packets'
              },
              {
                'index': false,
                'name': 'ibytes',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Input bytes'
              },
              {
                'index': false,
                'name': 'obytes',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Output bytes'
              },
              {
                'index': false,
                'name': 'ierrors',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Input errors'
              },
              {
                'index': false,
                'name': 'oerrors',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Output errors'
              },
              {
                'index': false,
                'name': 'idrops',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Input drops'
              },
              {
                'index': false,
                'name': 'odrops',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Output drops'
              },
              {
                'index': false,
                'name': 'collisions',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Packet Collisions detected'
              },
              {
                'index': false,
                'name': 'last_change',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Time of last device modification (optional)'
              },
              {
                'index': false,
                'name': 'link_speed',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Interface speed in Mb/s'
              },
              {
                'index': false,
                'name': 'pci_slot',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'PCI slot number'
              },
              {
                'index': false,
                'name': 'friendly_name',
                'required': false,
                'hidden': true,
                'type': 'text',
                'description': 'The friendly display name of the interface.'
              },
              {
                'index': false,
                'name': 'description',
                'required': false,
                'hidden': true,
                'type': 'text',
                'description':
                    'Short description of the object a one-line string.'
              },
              {
                'index': false,
                'name': 'manufacturer',
                'required': false,
                'hidden': true,
                'type': 'text',
                'description': 'Name of the network adapter\'s manufacturer.'
              },
              {
                'index': false,
                'name': 'connection_id',
                'required': false,
                'hidden': true,
                'type': 'text',
                'description':
                    'Name of the network connection as it appears in the Network Connections Control Panel program.'
              },
              {
                'index': false,
                'name': 'connection_status',
                'required': false,
                'hidden': true,
                'type': 'text',
                'description':
                    'State of the network adapter connection to the network.'
              },
              {
                'index': false,
                'name': 'enabled',
                'required': false,
                'hidden': true,
                'type': 'integer',
                'description':
                    'Indicates whether the adapter is enabled or not.'
              },
              {
                'index': false,
                'name': 'physical_adapter',
                'required': false,
                'hidden': true,
                'type': 'integer',
                'description':
                    'Indicates whether the adapter is a physical or a logical adapter.'
              },
              {
                'index': false,
                'name': 'speed',
                'required': false,
                'hidden': true,
                'type': 'integer',
                'description':
                    'Estimate of the current bandwidth in bits per second.'
              },
              {
                'index': false,
                'name': 'service',
                'required': false,
                'hidden': true,
                'type': 'text',
                'description':
                    'The name of the service the network adapter uses.'
              },
              {
                'index': false,
                'name': 'dhcp_enabled',
                'required': false,
                'hidden': true,
                'type': 'integer',
                'description':
                    'If TRUE, the dynamic host configuration protocol (DHCP) server automatically assigns an IP address to the computer system when establishing a network connection.'
              },
              {
                'index': false,
                'name': 'dhcp_lease_expires',
                'required': false,
                'hidden': true,
                'type': 'text',
                'description':
                    'Expiration date and time for a leased IP address that was assigned to the computer by the dynamic host configuration protocol (DHCP) server.'
              },
              {
                'index': false,
                'name': 'dhcp_lease_obtained',
                'required': false,
                'hidden': true,
                'type': 'text',
                'description':
                    'Date and time the lease was obtained for the IP address assigned to the computer by the dynamic host configuration protocol (DHCP) server.'
              },
              {
                'index': false,
                'name': 'dhcp_server',
                'required': false,
                'hidden': true,
                'type': 'text',
                'description':
                    'IP address of the dynamic host configuration protocol (DHCP) server.'
              },
              {
                'index': false,
                'name': 'dns_domain',
                'required': false,
                'hidden': true,
                'type': 'text',
                'description':
                    'Organization name followed by a period and an extension that indicates the type of organization, such as \'microsoft.com\'.'
              },
              {
                'index': false,
                'name': 'dns_domain_suffix_search_order',
                'required': false,
                'hidden': true,
                'type': 'text',
                'description':
                    'Array of DNS domain suffixes to be appended to the end of host names during name resolution.'
              },
              {
                'index': false,
                'name': 'dns_host_name',
                'required': false,
                'hidden': true,
                'type': 'text',
                'description':
                    'Host name used to identify the local computer for authentication by some utilities.'
              },
              {
                'index': false,
                'name': 'dns_server_search_order',
                'required': false,
                'hidden': true,
                'type': 'text',
                'description':
                    'Array of server IP addresses to be used in querying for DNS servers.'
              }
            ],
        'description': 'Detailed information and stats of network interfaces.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'interface_ipv6',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/interface_ipv6.table',
        'platforms': ['darwin', 'linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'interface',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Interface name'
              },
              {
                'index': false,
                'name': 'hop_limit',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Current Hop Limit'
              },
              {
                'index': false,
                'name': 'forwarding_enabled',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Enable IP forwarding'
              },
              {
                'index': false,
                'name': 'redirect_accept',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Accept ICMP redirect messages'
              },
              {
                'index': false,
                'name': 'rtadv_accept',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Accept ICMP Router Advertisement'
              }
            ],
        'description': 'IPv6 configuration and stats of network interfaces.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'iokit_devicetree',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/iokit_devicetree.table',
        'platforms': ['darwin'],
        'columns':
            [
              {
                'index': false,
                'name': 'name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Device node name'
              },
              {
                'index': false,
                'name': 'class',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'Best matching device class (most-specific category)'
              },
              {
                'index': false,
                'name': 'id',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'IOKit internal registry ID'
              },
              {
                'index': false,
                'name': 'parent',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Parent device registry ID'
              },
              {
                'index': false,
                'name': 'device_path',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Device tree path'
              },
              {
                'index': false,
                'name': 'service',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': '1 if the device conforms to IOService else 0'
              },
              {
                'index': false,
                'name': 'busy_state',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': '1 if the device is in a busy state else 0'
              },
              {
                'index': false,
                'name': 'retain_count',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'The device reference count'
              },
              {
                'index': false,
                'name': 'depth',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Device nested depth'
              }
            ],
        'description': 'The IOKit registry matching the DeviceTree plane.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'iokit_registry',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/iokit_registry.table',
        'platforms': ['darwin'],
        'columns':
            [
              {
                'index': false,
                'name': 'name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Default name of the node'
              },
              {
                'index': false,
                'name': 'class',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'Best matching device class (most-specific category)'
              },
              {
                'index': false,
                'name': 'id',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'IOKit internal registry ID'
              },
              {
                'index': false,
                'name': 'parent',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Parent registry ID'
              },
              {
                'index': false,
                'name': 'busy_state',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': '1 if the node is in a busy state else 0'
              },
              {
                'index': false,
                'name': 'retain_count',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'The node reference count'
              },
              {
                'index': false,
                'name': 'depth',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Node nested depth'
              }
            ],
        'description': 'The full IOKit registry without selecting a plane.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'iptables',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/linux/iptables.table',
        'platforms': ['linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'filter_name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Packet matching filter table name.'
              },
              {
                'index': false,
                'name': 'chain',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Size of module content.'
              },
              {
                'index': false,
                'name': 'policy',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Policy that applies for this rule.'
              },
              {
                'index': false,
                'name': 'target',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Target that applies for this rule.'
              },
              {
                'index': false,
                'name': 'protocol',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Protocol number identification.'
              },
              {
                'index': false,
                'name': 'src_port',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Protocol source port(s).'
              },
              {
                'index': false,
                'name': 'dst_port',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Protocol destination port(s).'
              },
              {
                'index': false,
                'name': 'src_ip',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Source IP address.'
              },
              {
                'index': false,
                'name': 'src_mask',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Source IP address mask.'
              },
              {
                'index': false,
                'name': 'iniface',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Input interface for the rule.'
              },
              {
                'index': false,
                'name': 'iniface_mask',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Input interface mask for the rule.'
              },
              {
                'index': false,
                'name': 'dst_ip',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Destination IP address.'
              },
              {
                'index': false,
                'name': 'dst_mask',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Destination IP address mask.'
              },
              {
                'index': false,
                'name': 'outiface',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Output interface for the rule.'
              },
              {
                'index': false,
                'name': 'outiface_mask',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Output interface mask for the rule.'
              },
              {
                'index': false,
                'name': 'match',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Matching rule that applies.'
              },
              {
                'index': false,
                'name': 'packets',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Number of matching packets for this rule.'
              },
              {
                'index': false,
                'name': 'bytes',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Number of matching bytes for this rule.'
              }
            ],
        'description': 'Linux IP packet filtering and NAT tool.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'kernel_extensions',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/kernel_extensions.table',
        'platforms': ['darwin'],
        'columns':
            [
              {
                'index': false,
                'name': 'idx',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Extension load tag or index'
              },
              {
                'index': false,
                'name': 'refs',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Reference count'
              },
              {
                'index': false,
                'name': 'size',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Bytes of wired memory used by extension'
              },
              {
                'index': false,
                'name': 'name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Extension label'
              },
              {
                'index': false,
                'name': 'version',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Extension version'
              },
              {
                'index': false,
                'name': 'linked_against',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'Indexes of extensions this extension is linked against'
              },
              {
                'index': false,
                'name': 'path',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Optional path to extension bundle'
              }
            ],
        'description':
            'OS X\'s kernel extensions, both loaded and within the load search path.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'kernel_info',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/kernel_info.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns':
            [
              {
                'index': false,
                'name': 'version',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Kernel version'
              },
              {
                'index': false,
                'name': 'arguments',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Kernel arguments'
              },
              {
                'index': false,
                'name': 'path',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Kernel path'
              },
              {
                'index': false,
                'name': 'device',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Kernel device identifier'
              }
            ],
        'description': 'Basic active kernel information.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'kernel_modules',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/linux/kernel_modules.table',
        'platforms': ['linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Module name'
              },
              {
                'index': false,
                'name': 'size',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Size of module content'
              },
              {
                'index': false,
                'name': 'used_by',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Module reverse dependencies'
              },
              {
                'index': false,
                'name': 'status',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Kernel module status'
              },
              {
                'index': false,
                'name': 'address',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Kernel module address'
              }
            ],
        'description':
            'Linux kernel modules both loaded and within the load search path.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'kernel_panics',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/kernel_panics.table',
        'platforms': ['darwin'],
        'columns':
            [
              {
                'index': false,
                'name': 'path',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Location of log file'
              },
              {
                'index': false,
                'name': 'time',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Formatted time of the event'
              },
              {
                'index': false,
                'name': 'registers',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'A space delimited line of register:value pairs'
              },
              {
                'index': false,
                'name': 'frame_backtrace',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Backtrace of the crashed module'
              },
              {
                'index': false,
                'name': 'module_backtrace',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'Modules appearing in the crashed module\'s backtrace'
              },
              {
                'index': false,
                'name': 'dependencies',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'Module dependencies existing in crashed module\'s backtrace'
              },
              {
                'index': false,
                'name': 'name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Process name corresponding to crashed thread'
              },
              {
                'index': false,
                'name': 'os_version',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Version of the operating system'
              },
              {
                'index': false,
                'name': 'kernel_version',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Version of the system kernel'
              },
              {
                'index': false,
                'name': 'system_model',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'Physical system model, for example \'MacBookPro12,1 (Mac-E43C1C25D4880AD6)\''
              },
              {
                'index': false,
                'name': 'uptime',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'System uptime at kernel panic in nanoseconds'
              },
              {
                'index': false,
                'name': 'last_loaded',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Last loaded module before panic'
              },
              {
                'index': false,
                'name': 'last_unloaded',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Last unloaded module before panic'
              }
            ],
        'description': 'System kernel panic logs.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'keychain_acls',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/keychain_acls.table',
        'platforms': ['darwin'],
        'columns':
            [
              {
                'index': false,
                'name': 'keychain_path',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The path of the keychain'
              },
              {
                'index': false,
                'name': 'authorizations',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'A space delimited set of authorization attributes'
              },
              {
                'index': false,
                'name': 'path',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The path of the authorized application'
              },
              {
                'index': false,
                'name': 'description',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The description included with the ACL entry'
              },
              {
                'index': false,
                'name': 'label',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'An optional label tag that may be included with the keychain entry'
              }
            ],
        'description': 'Applications that have ACL entries in the keychain.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'keychain_items',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/keychain_items.table',
        'platforms': ['darwin'],
        'columns':
            [
              {
                'index': false,
                'name': 'label',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Generic item name'
              },
              {
                'index': false,
                'name': 'description',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Optional item description'
              },
              {
                'index': false,
                'name': 'comment',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Optional keychain comment'
              },
              {
                'index': false,
                'name': 'created',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Data item was created'
              },
              {
                'index': false,
                'name': 'modified',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Date of last modification'
              },
              {
                'index': false,
                'name': 'type',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Keychain item type (class)'
              },
              {
                'index': false,
                'name': 'path',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Path to keychain containing item'
              }
            ],
        'description': 'Generic details about keychain items.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'known_hosts',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/known_hosts.table',
        'platforms': ['darwin', 'linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'uid',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'The local user that owns the known_hosts file'
              },
              {
                'index': false,
                'name': 'key',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'parsed authorized keys line'
              },
              {
                'index': false,
                'name': 'key_file',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Path to known_hosts file'
              }
            ],
        'description': 'A line-delimited known_hosts table.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'kva_speculative_info',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/kva_speculative_info.table',
        'platforms': ['windows'],
        'columns':
            [
              {
                'index': false,
                'name': 'kva_shadow_enabled',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Kernel Virtual Address shadowing is enabled.'
              },
              {
                'index': false,
                'name': 'kva_shadow_user_global',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'User pages are marked as global.'
              },
              {
                'index': false,
                'name': 'kva_shadow_pcid',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    'Kernel VA PCID flushing optimization is enabled.'
              },
              {
                'index': false,
                'name': 'kva_shadow_inv_pcid',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Kernel VA INVPCID is enabled.'
              },
              {
                'index': false,
                'name': 'bp_mitigations',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Branch Prediction mitigations are enabled.'
              },
              {
                'index': false,
                'name': 'bp_system_pol_disabled',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    'Branch Predictions are disabled via system policy.'
              },
              {
                'index': false,
                'name': 'bp_microcode_disabled',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description':
                    'Branch Predictions are disabled due to lack of microcode update.'
              },
              {
                'index': false,
                'name': 'cpu_spec_ctrl_supported',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'SPEC_CTRL MSR supported by CPU Microcode.'
              },
              {
                'index': false,
                'name': 'ibrs_support_enabled',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Windows uses IBRS.'
              },
              {
                'index': false,
                'name': 'stibp_support_enabled',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Windows uses STIBP.'
              },
              {
                'index': false,
                'name': 'cpu_pred_cmd_supported',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'PRED_CMD MSR supported by CPU Microcode.'
              }
            ],
        'description':
            'Display kernel virtual address and speculative execution information for the system.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'last',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/last.table',
        'platforms': ['darwin', 'linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'username',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Entry username'
              },
              {
                'index': false,
                'name': 'tty',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Entry terminal'
              },
              {
                'index': false,
                'name': 'pid',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Process (or thread) ID'
              },
              {
                'index': false,
                'name': 'type',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Entry type, according to ut_type types (utmp.h)'
              },
              {
                'index': false,
                'name': 'time',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Entry timestamp'
              },
              {
                'index': false,
                'name': 'host',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Entry hostname'
              }
            ],
        'description': 'System logins and logouts.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'launchd',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/launchd.table',
        'platforms': ['darwin'],
        'columns':
            [
              {
                'index': false,
                'name': 'path',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Path to daemon or agent plist'
              },
              {
                'index': false,
                'name': 'name',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'File name of plist (used by launchd)'
              },
              {
                'index': false,
                'name': 'label',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Daemon or agent service name'
              },
              {
                'index': false,
                'name': 'program',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Path to target program'
              },
              {
                'index': false,
                'name': 'run_at_load',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Should the program run on launch load'
              },
              {
                'index': false,
                'name': 'keep_alive',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Should the process be restarted if killed'
              },
              {
                'index': false,
                'name': 'on_demand',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Deprecated key, replaced by keep_alive'
              },
              {
                'index': false,
                'name': 'disabled',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Skip loading this daemon or agent on boot'
              },
              {
                'index': false,
                'name': 'username',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Run this daemon or agent as this username'
              },
              {
                'index': false,
                'name': 'groupname',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Run this daemon or agent as this group'
              },
              {
                'index': false,
                'name': 'stdout_path',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Pipe stdout to a target path'
              },
              {
                'index': false,
                'name': 'stderr_path',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Pipe stderr to a target path'
              },
              {
                'index': false,
                'name': 'start_interval',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Frequency to run in seconds'
              },
              {
                'index': false,
                'name': 'program_arguments',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Command line arguments passed to program'
              },
              {
                'index': false,
                'name': 'watch_paths',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'Key that launches daemon or agent if path is modified'
              },
              {
                'index': false,
                'name': 'queue_directories',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'Similar to watch_paths but only with non-empty directories'
              },
              {
                'index': false,
                'name': 'inetd_compatibility',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'Run this daemon or agent as it was launched from inetd'
              },
              {
                'index': false,
                'name': 'start_on_mount',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'Run daemon or agent every time a filesystem is mounted'
              },
              {
                'index': false,
                'name': 'root_directory',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'Key used to specify a directory to chroot to before launch'
              },
              {
                'index': false,
                'name': 'working_directory',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description':
                    'Key used to specify a directory to chdir to before launch'
              },
              {
                'index': false,
                'name': 'process_type',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Key describes the intended purpose of the job'
              }
            ],
        'description':
            'LaunchAgents and LaunchDaemons from default search paths.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'launchd_overrides',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/launchd_overrides.table',
        'platforms': ['darwin'],
        'columns':
            [
              {
                'index': false,
                'name': 'label',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Daemon or agent service name'
              },
              {
                'index': false,
                'name': 'key',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Name of the override key'
              },
              {
                'index': false,
                'name': 'value',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Overridden value'
              },
              {
                'index': false,
                'name': 'uid',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description':
                    'User ID applied to the override, 0 applies to all'
              },
              {
                'index': false,
                'name': 'path',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Path to daemon or agent plist'
              }
            ],
        'description': 'Override keys, per user, for LaunchDaemons and Agents.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'listening_ports',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/listening_ports.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns':
            [
              {
                'index': false,
                'name': 'pid',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Process (or thread) ID'
              },
              {
                'index': false,
                'name': 'port',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Transport layer port'
              },
              {
                'index': false,
                'name': 'protocol',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Transport protocol (TCP/UDP)'
              },
              {
                'index': false,
                'name': 'family',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Network protocol (IPv4, IPv6)'
              },
              {
                'index': false,
                'name': 'address',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Specific address for bind'
              },
              {
                'index': false,
                'name': 'fd',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Socket file descriptor number'
              },
              {
                'index': false,
                'name': 'socket',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Socket handle or inode number'
              },
              {
                'index': false,
                'name': 'path',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Path for UNIX domain sockets'
              },
              {
                'index': false,
                'name': 'net_namespace',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'The inode number of the network namespace'
              }
            ],
        'description': 'Processes with listening (bound) network sockets/ports.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'lldp_neighbors',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/lldpd/lldp_neighbors.table',
        'platforms': ['linux'],
        'columns':
            [
              {
                'index': false,
                'name': 'interface',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Interface name'
              },
              {
                'index': false,
                'name': 'rid',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Neighbor chassis index'
              },
              {
                'index': false,
                'name': 'chassis_id_type',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Neighbor chassis ID type'
              },
              {
                'index': false,
                'name': 'chassis_id',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Neighbor chassis ID value'
              },
              {
                'index': false,
                'name': 'chassis_sysname',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'CPU brand string, contains vendor and model'
              },
              {
                'index': false,
                'name': 'chassis_sys_description',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Max number of CPU physical cores'
              },
              {
                'index': false,
                'name': 'chassis_bridge_capability_available',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Chassis bridge capability availability'
              },
              {
                'index': false,
                'name': 'chassis_bridge_capability_enabled',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Is chassis bridge capability enabled.'
              },
              {
                'index': false,
                'name': 'chassis_router_capability_available',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Chassis router capability availability'
              },
              {
                'index': false,
                'name': 'chassis_router_capability_enabled',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Chassis router capability enabled'
              },
              {
                'index': false,
                'name': 'chassis_repeater_capability_available',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Chassis repeater capability availability'
              },
              {
                'index': false,
                'name': 'chassis_repeater_capability_enabled',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Chassis repeater capability enabled'
              },
              {
                'index': false,
                'name': 'chassis_wlan_capability_available',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Chassis wlan capability availability'
              },
              {
                'index': false,
                'name': 'chassis_wlan_capability_enabled',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Chassis wlan capability enabled'
              },
              {
                'index': false,
                'name': 'chassis_tel_capability_available',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Chassis telephone capability availability'
              },
              {
                'index': false,
                'name': 'chassis_tel_capability_enabled',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Chassis telephone capability enabled'
              },
              {
                'index': false,
                'name': 'chassis_docsis_capability_available',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Chassis DOCSIS capability availability'
              },
              {
                'index': false,
                'name': 'chassis_docsis_capability_enabled',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Chassis DOCSIS capability enabled'
              },
              {
                'index': false,
                'name': 'chassis_station_capability_available',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Chassis station capability availability'
              },
              {
                'index': false,
                'name': 'chassis_station_capability_enabled',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Chassis station capability enabled'
              },
              {
                'index': false,
                'name': 'chassis_other_capability_available',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Chassis other capability availability'
              },
              {
                'index': false,
                'name': 'chassis_other_capability_enabled',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Chassis other capability enabled'
              },
              {
                'index': false,
                'name': 'chassis_mgmt_ips',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Comma delimited list of chassis management IPS'
              },
              {
                'index': false,
                'name': 'port_id_type',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Port ID type'
              },
              {
                'index': false,
                'name': 'port_id',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Port ID value'
              },
              {
                'index': false,
                'name': 'port_description',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Port description'
              },
              {
                'index': false,
                'name': 'port_ttl',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Age of neighbor port'
              },
              {
                'index': false,
                'name': 'port_mfs',
                'required': false,
                'hidden': false,
                'type': 'bigint',
                'description': 'Port max frame size'
              },
              {
                'index': false,
                'name': 'port_aggregation_id',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Port aggregation ID'
              },
              {
                'index': false,
                'name': 'port_autoneg_supported',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Auto negotiation supported'
              },
              {
                'index': false,
                'name': 'port_autoneg_enabled',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Is auto negotiation enabled'
              },
              {
                'index': false,
                'name': 'port_mau_type',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'MAU type'
              },
              {
                'index': false,
                'name': 'port_autoneg_10baset_hd_enabled',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': '10Base-T HD auto negotiation enabled'
              },
              {
                'index': false,
                'name': 'port_autoneg_10baset_fd_enabled',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': '10Base-T FD auto negotiation enabled'
              },
              {
                'index': false,
                'name': 'port_autoneg_100basetx_hd_enabled',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': '100Base-TX HD auto negotiation enabled'
              },
              {
                'index': false,
                'name': 'port_autoneg_100basetx_fd_enabled',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': '100Base-TX FD auto negotiation enabled'
              },
              {
                'index': false,
                'name': 'port_autoneg_100baset2_hd_enabled',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': '100Base-T2 HD auto negotiation enabled'
              },
              {
                'index': false,
                'name': 'port_autoneg_100baset2_fd_enabled',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': '100Base-T2 FD auto negotiation enabled'
              },
              {
                'index': false,
                'name': 'port_autoneg_100baset4_hd_enabled',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': '100Base-T4 HD auto negotiation enabled'
              },
              {
                'index': false,
                'name': 'port_autoneg_100baset4_fd_enabled',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': '100Base-T4 FD auto negotiation enabled'
              },
              {
                'index': false,
                'name': 'port_autoneg_1000basex_hd_enabled',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': '1000Base-X HD auto negotiation enabled'
              },
              {
                'index': false,
                'name': 'port_autoneg_1000basex_fd_enabled',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': '1000Base-X FD auto negotiation enabled'
              },
              {
                'index': false,
                'name': 'port_autoneg_1000baset_hd_enabled',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': '1000Base-T HD auto negotiation enabled'
              },
              {
                'index': false,
                'name': 'port_autoneg_1000baset_fd_enabled',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': '1000Base-T FD auto negotiation enabled'
              },
              {
                'index': false,
                'name': 'power_device_type',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Dot3 power device type'
              },
              {
                'index': false,
                'name': 'power_mdi_supported',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'MDI power supported'
              },
              {
                'index': false,
                'name': 'power_mdi_enabled',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Is MDI power enabled'
              },
              {
                'index': false,
                'name': 'power_paircontrol_enabled',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Is power pair control enabled'
              },
              {
                'index': false,
                'name': 'power_pairs',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Dot3 power pairs'
              },
              {
                'index': false,
                'name': 'power_class',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Power class'
              },
              {
                'index': false,
                'name': 'power_8023at_enabled',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Is 802.3at enabled'
              },
              {
                'index': false,
                'name': 'power_8023at_power_type',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': '802.3at power type'
              },
              {
                'index': false,
                'name': 'power_8023at_power_source',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': '802.3at power source'
              },
              {
                'index': false,
                'name': 'power_8023at_power_priority',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': '802.3at power priority'
              },
              {
                'index': false,
                'name': 'power_8023at_power_allocated',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': '802.3at power allocated'
              },
              {
                'index': false,
                'name': 'power_8023at_power_requested',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': '802.3at power requested'
              },
              {
                'index': false,
                'name': 'med_device_type',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Chassis MED type'
              },
              {
                'index': false,
                'name': 'med_capability_capabilities',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Is MED capabilities enabled'
              },
              {
                'index': false,
                'name': 'med_capability_policy',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Is MED policy capability enabled'
              },
              {
                'index': false,
                'name': 'med_capability_location',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Is MED location capability enabled'
              },
              {
                'index': false,
                'name': 'med_capability_mdi_pse',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Is MED MDI PSE capability enabled'
              },
              {
                'index': false,
                'name': 'med_capability_mdi_pd',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Is MED MDI PD capability enabled'
              },
              {
                'index': false,
                'name': 'med_capability_inventory',
                'required': false,
                'hidden': false,
                'type': 'integer',
                'description': 'Is MED inventory capability enabled'
              },
              {
                'index': false,
                'name': 'med_policies',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Comma delimited list of MED policies'
              },
              {
                'index': false,
                'name': 'vlans',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Comma delimited list of vlan ids'
              },
              {
                'index': false,
                'name': 'pvid',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Primary VLAN id'
              },
              {
                'index': false,
                'name': 'ppvids_supported',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Comma delimited list of supported PPVIDs'
              },
              {
                'index': false,
                'name': 'ppvids_enabled',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Comma delimited list of enabled PPVIDs'
              },
              {
                'index': false,
                'name': 'pids',
                'required': false,
                'hidden': false,
                'type': 'text',
                'description': 'Comma delimited list of PIDs'
              }
            ],
        'description': 'LLDP neighbors of interfaces.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'load_average',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/load_average.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'period',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Period over which the average is calculated.'
          },
          {
            'index': false,
            'name': 'average',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Load average over the specified period.'
          }
        ],
        'description':
            'Displays information about the system wide load averages.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'logged_in_users',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/logged_in_users.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns': [
          {
            'index': false,
            'name': 'type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Login type'
          },
          {
            'index': false,
            'name': 'user',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'User login name'
          },
          {
            'index': false,
            'name': 'tty',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Device name'
          },
          {
            'index': false,
            'name': 'host',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Remote hostname'
          },
          {
            'index': false,
            'name': 'time',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Time entry was made'
          },
          {
            'index': false,
            'name': 'pid',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Process (or thread) ID'
          },
          {
            'index': false,
            'name': 'sid',
            'required': false,
            'hidden': true,
            'type': 'text',
            'description': 'The user\'s unique security identifier'
          },
          {
            'index': false,
            'name': 'registry_hive',
            'required': false,
            'hidden': true,
            'type': 'text',
            'description': 'HKEY_USERS registry hive'
          }
        ],
        'description': 'Users with an active shell on the system.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'logical_drives',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/logical_drives.table',
        'platforms': ['windows'],
        'columns': [
          {
            'index': false,
            'name': 'device_id',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The drive id, usually the drive name, e.g., \'C:\'.'
          },
          {
            'index': false,
            'name': 'type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Deprecated (always \'Unknown\').'
          },
          {
            'index': false,
            'name': 'description',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'The canonical description of the drive, e.g. \'Logical Fixed Disk\', \'CD-ROM Disk\'.'
          },
          {
            'index': false,
            'name': 'free_space',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description':
                'The amount of free space, in bytes, of the drive (-1 on failure).'
          },
          {
            'index': false,
            'name': 'size',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description':
                'The total amount of space, in bytes, of the drive (-1 on failure).'
          },
          {
            'index': false,
            'name': 'file_system',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The file system of the drive.'
          },
          {
            'index': false,
            'name': 'boot_partition',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'True if Windows booted from this drive.'
          }
        ],
        'description':
            'Details for logical drives on the system. A logical drive generally represents a single partition.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'logon_sessions',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/logon_sessions.table',
        'platforms': ['windows'],
        'columns': [
          {
            'index': false,
            'name': 'logon_id',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'A locally unique identifier (LUID) that identifies a logon session.'
          },
          {
            'index': false,
            'name': 'user',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'The account name of the security principal that owns the logon session.'
          },
          {
            'index': false,
            'name': 'logon_domain',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'The name of the domain used to authenticate the owner of the logon session.'
          },
          {
            'index': false,
            'name': 'authentication_package',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'The authentication package used to authenticate the owner of the logon session.'
          },
          {
            'index': false,
            'name': 'logon_type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The logon method.'
          },
          {
            'index': false,
            'name': 'session_id',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'The Terminal Services session identifier.'
          },
          {
            'index': false,
            'name': 'logon_sid',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The user\'s security identifier (SID).'
          },
          {
            'index': false,
            'name': 'logon_time',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'The time the session owner logged on.'
          },
          {
            'index': false,
            'name': 'logon_server',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'The name of the server used to authenticate the owner of the logon session.'
          },
          {
            'index': false,
            'name': 'dns_domain_name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The DNS name for the owner of the logon session.'
          },
          {
            'index': false,
            'name': 'upn',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'The user principal name (UPN) for the owner of the logon session.'
          },
          {
            'index': false,
            'name': 'logon_script',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The script used for logging on.'
          },
          {
            'index': false,
            'name': 'profile_path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The home directory for the logon session.'
          },
          {
            'index': false,
            'name': 'home_directory',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The home directory for the logon session.'
          },
          {
            'index': false,
            'name': 'home_directory_drive',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'The drive location of the home directory of the logon session.'
          }
        ],
        'description': 'Windows Logon Session.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'lxd_certificates',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/lxd_certificates.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of the certificate'
          },
          {
            'index': false,
            'name': 'type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Type of the certificate'
          },
          {
            'index': false,
            'name': 'fingerprint',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'SHA256 hash of the certificate'
          },
          {
            'index': false,
            'name': 'certificate',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Certificate content'
          }
        ],
        'description': 'LXD certificates information.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'lxd_cluster',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/lxd_cluster.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'server_name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of the LXD server node'
          },
          {
            'index': false,
            'name': 'enabled',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'Whether clustering enabled (1) or not (0) on this node'
          },
          {
            'index': false,
            'name': 'member_config_entity',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Type of configuration parameter for this node'
          },
          {
            'index': false,
            'name': 'member_config_name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of configuration parameter'
          },
          {
            'index': false,
            'name': 'member_config_key',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Config key'
          },
          {
            'index': false,
            'name': 'member_config_value',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Config value'
          },
          {
            'index': false,
            'name': 'member_config_description',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Config description'
          }
        ],
        'description': 'LXD cluster information.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'lxd_cluster_members',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/lxd_cluster_members.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'server_name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of the LXD server node'
          },
          {
            'index': false,
            'name': 'url',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'URL of the node'
          },
          {
            'index': false,
            'name': 'database',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'Whether the server is a database node (1) or not (0)'
          },
          {
            'index': false,
            'name': 'status',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Status of the node (Online/Offline)'
          },
          {
            'index': false,
            'name': 'message',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Message from the node (Online/Offline)'
          }
        ],
        'description': 'LXD cluster members information.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'lxd_images',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/lxd_images.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'id',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Image ID'
          },
          {
            'index': false,
            'name': 'architecture',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Target architecture for the image'
          },
          {
            'index': false,
            'name': 'os',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'OS on which image is based'
          },
          {
            'index': false,
            'name': 'release',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'OS release version on which the image is based'
          },
          {
            'index': false,
            'name': 'description',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Image description'
          },
          {
            'index': false,
            'name': 'aliases',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Comma-separated list of image aliases'
          },
          {
            'index': false,
            'name': 'filename',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Filename of the image file'
          },
          {
            'index': false,
            'name': 'size',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Size of image in bytes'
          },
          {
            'index': false,
            'name': 'auto_update',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Whether the image auto-updates (1) or not (0)'
          },
          {
            'index': false,
            'name': 'cached',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Whether image is cached (1) or not (0)'
          },
          {
            'index': false,
            'name': 'public',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Whether image is public (1) or not (0)'
          },
          {
            'index': false,
            'name': 'created_at',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'ISO time of image creation'
          },
          {
            'index': false,
            'name': 'expires_at',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'ISO time of image expiration'
          },
          {
            'index': false,
            'name': 'uploaded_at',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'ISO time of image upload'
          },
          {
            'index': false,
            'name': 'last_used_at',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'ISO time for the most recent use of this image in terms of container spawn'
          },
          {
            'index': false,
            'name': 'update_source_server',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Server for image update'
          },
          {
            'index': false,
            'name': 'update_source_protocol',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Protocol used for image information update and image import from source server'
          },
          {
            'index': false,
            'name': 'update_source_certificate',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Certificate for update source server'
          },
          {
            'index': false,
            'name': 'update_source_alias',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Alias of image at update source server'
          }
        ],
        'description': 'LXD images information.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'lxd_instance_config',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/lxd_instance_config.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': true,
            'hidden': false,
            'type': 'text',
            'description': 'Instance name'
          },
          {
            'index': false,
            'name': 'key',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Configuration parameter name'
          },
          {
            'index': false,
            'name': 'value',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Configuration parameter value'
          }
        ],
        'description': 'LXD instance configuration information.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'lxd_instance_devices',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/lxd_instance_devices.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': true,
            'hidden': false,
            'type': 'text',
            'description': 'Instance name'
          },
          {
            'index': false,
            'name': 'device',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of the device'
          },
          {
            'index': false,
            'name': 'device_type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Device type'
          },
          {
            'index': false,
            'name': 'key',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Device info param name'
          },
          {
            'index': false,
            'name': 'value',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Device info param value'
          }
        ],
        'description': 'LXD instance devices information.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'lxd_instances',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/lxd_instances.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Instance name'
          },
          {
            'index': false,
            'name': 'status',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Instance state (running, stopped, etc.)'
          },
          {
            'index': false,
            'name': 'stateful',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Whether the instance is stateful(1) or not(0)'
          },
          {
            'index': false,
            'name': 'ephemeral',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Whether the instance is ephemeral(1) or not(0)'
          },
          {
            'index': false,
            'name': 'created_at',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'ISO time of creation'
          },
          {
            'index': false,
            'name': 'base_image',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'ID of image used to launch this instance'
          },
          {
            'index': false,
            'name': 'architecture',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Instance architecture'
          },
          {
            'index': false,
            'name': 'os',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The OS of this instance'
          },
          {
            'index': false,
            'name': 'description',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Instance description'
          },
          {
            'index': false,
            'name': 'pid',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Instance\'s process ID'
          },
          {
            'index': false,
            'name': 'processes',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Number of processes running inside this instance'
          }
        ],
        'description': 'LXD instances information.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'lxd_networks',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/lxd_networks.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of the network'
          },
          {
            'index': false,
            'name': 'type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Type of network'
          },
          {
            'index': false,
            'name': 'managed',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 if network created by LXD, 0 otherwise'
          },
          {
            'index': false,
            'name': 'ipv4_address',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'IPv4 address'
          },
          {
            'index': false,
            'name': 'ipv6_address',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'IPv6 address'
          },
          {
            'index': false,
            'name': 'used_by',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'URLs for containers using this network'
          },
          {
            'index': false,
            'name': 'bytes_received',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Number of bytes received on this network'
          },
          {
            'index': false,
            'name': 'bytes_sent',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Number of bytes sent on this network'
          },
          {
            'index': false,
            'name': 'packets_received',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Number of packets received on this network'
          },
          {
            'index': false,
            'name': 'packets_sent',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Number of packets sent on this network'
          },
          {
            'index': false,
            'name': 'hwaddr',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Hardware address for this network'
          },
          {
            'index': false,
            'name': 'state',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Network status'
          },
          {
            'index': false,
            'name': 'mtu',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'MTU size'
          }
        ],
        'description': 'LXD network information.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'lxd_storage_pools',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/lxd_storage_pools.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of the storage pool'
          },
          {
            'index': false,
            'name': 'driver',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Storage driver'
          },
          {
            'index': false,
            'name': 'source',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Storage pool source'
          },
          {
            'index': false,
            'name': 'size',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Size of the storage pool'
          },
          {
            'index': false,
            'name': 'space_used',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Storgae space used in bytes'
          },
          {
            'index': false,
            'name': 'space_total',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description':
                'Total available storage space in bytes for this storage pool'
          },
          {
            'index': false,
            'name': 'inodes_used',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Number of inodes used'
          },
          {
            'index': false,
            'name': 'inodes_total',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description':
                'Total number of inodes available in this storage pool'
          }
        ],
        'description': 'LXD storage pool information.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'magic',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/magic.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'path',
            'required': true,
            'hidden': false,
            'type': 'text',
            'description': 'Absolute path to target file'
          },
          {
            'index': false,
            'name': 'magic_db_files',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Colon(:) separated list of files where the magic db file can be found. By default one of the following is used: /usr/share/file/magic/magic, /usr/share/misc/magic or /usr/share/misc/magic.mgc'
          },
          {
            'index': false,
            'name': 'data',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Magic number data from libmagic'
          },
          {
            'index': false,
            'name': 'mime_type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'MIME type data from libmagic'
          },
          {
            'index': false,
            'name': 'mime_encoding',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'MIME encoding data from libmagic'
          }
        ],
        'description': 'Magic number recognition library table.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'managed_policies',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/managed_policies.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'domain',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'System or manager-chosen domain key'
          },
          {
            'index': false,
            'name': 'uuid',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Optional UUID assigned to policy set'
          },
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Policy key name'
          },
          {
            'index': false,
            'name': 'value',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Policy value'
          },
          {
            'index': false,
            'name': 'username',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Policy applies only this user'
          },
          {
            'index': false,
            'name': 'manual',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 if policy was loaded manually, otherwise 0'
          }
        ],
        'description':
            'The managed configuration policies from AD, MDM, MCX, etc.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'md_devices',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/linux/md_devices.table',
        'platforms': ['linux'],
        'columns': [
          {
            'index': false,
            'name': 'device_name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'md device name'
          },
          {
            'index': false,
            'name': 'status',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Current state of the array'
          },
          {
            'index': false,
            'name': 'raid_level',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Current raid level of the array'
          },
          {
            'index': false,
            'name': 'size',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'size of the array in blocks'
          },
          {
            'index': false,
            'name': 'chunk_size',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'chunk size in bytes'
          },
          {
            'index': false,
            'name': 'raid_disks',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Number of configured RAID disks in array'
          },
          {
            'index': false,
            'name': 'nr_raid_disks',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'Number of partitions or disk devices to comprise the array'
          },
          {
            'index': false,
            'name': 'working_disks',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Number of working disks in array'
          },
          {
            'index': false,
            'name': 'active_disks',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Number of active disks in array'
          },
          {
            'index': false,
            'name': 'failed_disks',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Number of failed disks in array'
          },
          {
            'index': false,
            'name': 'spare_disks',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Number of idle disks in array'
          },
          {
            'index': false,
            'name': 'superblock_state',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'State of the superblock'
          },
          {
            'index': false,
            'name': 'superblock_version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Version of the superblock'
          },
          {
            'index': false,
            'name': 'superblock_update_time',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Unix timestamp of last update'
          },
          {
            'index': false,
            'name': 'bitmap_on_mem',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Pages allocated in in-memory bitmap, if enabled'
          },
          {
            'index': false,
            'name': 'bitmap_chunk_size',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Bitmap chunk size'
          },
          {
            'index': false,
            'name': 'bitmap_external_file',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'External referenced bitmap file'
          },
          {
            'index': false,
            'name': 'recovery_progress',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Progress of the recovery activity'
          },
          {
            'index': false,
            'name': 'recovery_finish',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Estimated duration of recovery activity'
          },
          {
            'index': false,
            'name': 'recovery_speed',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Speed of recovery activity'
          },
          {
            'index': false,
            'name': 'resync_progress',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Progress of the resync activity'
          },
          {
            'index': false,
            'name': 'resync_finish',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Estimated duration of resync activity'
          },
          {
            'index': false,
            'name': 'resync_speed',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Speed of resync activity'
          },
          {
            'index': false,
            'name': 'reshape_progress',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Progress of the reshape activity'
          },
          {
            'index': false,
            'name': 'reshape_finish',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Estimated duration of reshape activity'
          },
          {
            'index': false,
            'name': 'reshape_speed',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Speed of reshape activity'
          },
          {
            'index': false,
            'name': 'check_array_progress',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Progress of the check array activity'
          },
          {
            'index': false,
            'name': 'check_array_finish',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Estimated duration of the check array activity'
          },
          {
            'index': false,
            'name': 'check_array_speed',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Speed of the check array activity'
          },
          {
            'index': false,
            'name': 'unused_devices',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Unused devices'
          },
          {
            'index': false,
            'name': 'other',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Other information associated with array from /proc/mdstat'
          }
        ],
        'description': 'Software RAID array settings.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'md_drives',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/linux/md_drives.table',
        'platforms': ['linux'],
        'columns': [
          {
            'index': false,
            'name': 'md_device_name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'md device name'
          },
          {
            'index': false,
            'name': 'drive_name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Drive device name'
          },
          {
            'index': false,
            'name': 'slot',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Slot position of disk'
          },
          {
            'index': false,
            'name': 'state',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'State of the drive'
          }
        ],
        'description': 'Drive devices used for Software RAID.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'md_personalities',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/linux/md_personalities.table',
        'platforms': ['linux'],
        'columns': [{
          'index': false,
          'name': 'name',
          'required': false,
          'hidden': false,
          'type': 'text',
          'description': 'Name of personality supported by kernel'
        }],
        'description': 'Software RAID setting supported by the kernel.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'mdfind',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/mdfind.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Path of the file returned from spotlight'
          },
          {
            'index': false,
            'name': 'query',
            'required': true,
            'hidden': false,
            'type': 'text',
            'description': 'The query that was run to find the file'
          }
        ],
        'description': 'Run searches against the spotlight database.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'mdls',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/mdls.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'path',
            'required': true,
            'hidden': false,
            'type': 'text',
            'description': 'Path of the file'
          },
          {
            'index': false,
            'name': 'key',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of the metadata key'
          },
          {
            'index': false,
            'name': 'value',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Value stored in the metadata key'
          },
          {
            'index': false,
            'name': 'valuetype',
            'required': false,
            'hidden': true,
            'type': 'text',
            'description': 'CoreFoundation type of data stored in value'
          }
        ],
        'description': 'Query file metadata in the Spotlight database.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'memory_array_mapped_addresses',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/memory_array_mapped_addresses.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'handle',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Handle, or instance number, associated with the structure'
          },
          {
            'index': false,
            'name': 'memory_array_handle',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Handle of the memory array associated with this structure'
          },
          {
            'index': false,
            'name': 'starting_address',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Physical stating address, in kilobytes, of a range of memory mapped to physical memory array'
          },
          {
            'index': false,
            'name': 'ending_address',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Physical ending address of last kilobyte of a range of memory mapped to physical memory array'
          },
          {
            'index': false,
            'name': 'partition_width',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'Number of memory devices that form a single row of memory for the address partition of this structure'
          }
        ],
        'description':
            'Data associated for address mapping of physical memory arrays.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'memory_arrays',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/memory_arrays.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'handle',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Handle, or instance number, associated with the array'
          },
          {
            'index': false,
            'name': 'location',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Physical location of the memory array'
          },
          {
            'index': false,
            'name': 'use',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Function for which the array is used'
          },
          {
            'index': false,
            'name': 'memory_error_correction',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Primary hardware error correction or detection method supported'
          },
          {
            'index': false,
            'name': 'max_capacity',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Maximum capacity of array in gigabytes'
          },
          {
            'index': false,
            'name': 'memory_error_info_handle',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Handle, or instance number, associated with any error that was detected for the array'
          },
          {
            'index': false,
            'name': 'number_memory_devices',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Number of memory devices on array'
          }
        ],
        'description':
            'Data associated with collection of memory devices that operate to form a memory address.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'memory_device_mapped_addresses',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/memory_device_mapped_addresses.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'handle',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Handle, or instance number, associated with the structure'
          },
          {
            'index': false,
            'name': 'memory_device_handle',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Handle of the memory device structure associated with this structure'
          },
          {
            'index': false,
            'name': 'memory_array_mapped_address_handle',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Handle of the memory array mapped address to which this device range is mapped to'
          },
          {
            'index': false,
            'name': 'starting_address',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Physical stating address, in kilobytes, of a range of memory mapped to physical memory array'
          },
          {
            'index': false,
            'name': 'ending_address',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Physical ending address of last kilobyte of a range of memory mapped to physical memory array'
          },
          {
            'index': false,
            'name': 'partition_row_position',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'Identifies the position of the referenced memory device in a row of the address partition'
          },
          {
            'index': false,
            'name': 'interleave_position',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'The position of the device in a interleave, i.e. 0 indicates non-interleave, 1 indicates 1st interleave, 2 indicates 2nd interleave, etc.'
          },
          {
            'index': false,
            'name': 'interleave_data_depth',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'The max number of consecutive rows from memory device that are accessed in a single interleave transfer; 0 indicates device is non-interleave'
          }
        ],
        'description':
            'Data associated for address mapping of physical memory devices.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'memory_devices',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/memory_devices.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'handle',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Handle, or instance number, associated with the structure in SMBIOS'
          },
          {
            'index': false,
            'name': 'array_handle',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The memory array that the device is attached to'
          },
          {
            'index': false,
            'name': 'form_factor',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Implementation form factor for this memory device'
          },
          {
            'index': false,
            'name': 'total_width',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'Total width, in bits, of this memory device, including any check or error-correction bits'
          },
          {
            'index': false,
            'name': 'data_width',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Data width, in bits, of this memory device'
          },
          {
            'index': false,
            'name': 'size',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Size of memory device in Megabyte'
          },
          {
            'index': false,
            'name': 'set',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'Identifies if memory device is one of a set of devices.  A value of 0 indicates no set affiliation.'
          },
          {
            'index': false,
            'name': 'device_locator',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'String number of the string that identifies the physically-labeled socket or board position where the memory device is located'
          },
          {
            'index': false,
            'name': 'bank_locator',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'String number of the string that identifies the physically-labeled bank where the memory device is located'
          },
          {
            'index': false,
            'name': 'memory_type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Type of memory used'
          },
          {
            'index': false,
            'name': 'memory_type_details',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Additional details for memory device'
          },
          {
            'index': false,
            'name': 'max_speed',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'Max speed of memory device in megatransfers per second (MT/s)'
          },
          {
            'index': false,
            'name': 'configured_clock_speed',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'Configured speed of memory device in megatransfers per second (MT/s)'
          },
          {
            'index': false,
            'name': 'manufacturer',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Manufacturer ID string'
          },
          {
            'index': false,
            'name': 'serial_number',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Serial number of memory device'
          },
          {
            'index': false,
            'name': 'asset_tag',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Manufacturer specific asset tag of memory device'
          },
          {
            'index': false,
            'name': 'part_number',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Manufacturer specific serial number of memory device'
          },
          {
            'index': false,
            'name': 'min_voltage',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Minimum operating voltage of device in millivolts'
          },
          {
            'index': false,
            'name': 'max_voltage',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Maximum operating voltage of device in millivolts'
          },
          {
            'index': false,
            'name': 'configured_voltage',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'Configured operating voltage of device in millivolts'
          }
        ],
        'description':
            'Physical memory device (type 17) information retrieved from SMBIOS.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'memory_error_info',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/memory_error_info.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'handle',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Handle, or instance number, associated with the structure'
          },
          {
            'index': false,
            'name': 'error_type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'type of error associated with current error status for array or device'
          },
          {
            'index': false,
            'name': 'error_granularity',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Granularity to which the error can be resolved'
          },
          {
            'index': false,
            'name': 'error_operation',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Memory access operation that caused the error'
          },
          {
            'index': false,
            'name': 'vendor_syndrome',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Vendor specific ECC syndrome or CRC data associated with the erroneous access'
          },
          {
            'index': false,
            'name': 'memory_array_error_address',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                '32 bit physical address of the error based on the addressing of the bus to which the memory array is connected'
          },
          {
            'index': false,
            'name': 'device_error_address',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                '32 bit physical address of the error relative to the start of the failing memory address, in bytes'
          },
          {
            'index': false,
            'name': 'error_resolution',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Range, in bytes, within which this error can be determined, when an error address is given'
          }
        ],
        'description': 'Data associated with errors of a physical memory array.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'memory_info',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/linux/memory_info.table',
        'platforms': ['linux'],
        'columns': [
          {
            'index': false,
            'name': 'memory_total',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Total amount of physical RAM, in bytes'
          },
          {
            'index': false,
            'name': 'memory_free',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description':
                'The amount of physical RAM, in bytes, left unused by the system'
          },
          {
            'index': false,
            'name': 'buffers',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description':
                'The amount of physical RAM, in bytes, used for file buffers'
          },
          {
            'index': false,
            'name': 'cached',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description':
                'The amount of physical RAM, in bytes, used as cache memory'
          },
          {
            'index': false,
            'name': 'swap_cached',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'The amount of swap, in bytes, used as cache memory'
          },
          {
            'index': false,
            'name': 'active',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description':
                'The total amount of buffer or page cache memory, in bytes, that is in active use'
          },
          {
            'index': false,
            'name': 'inactive',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description':
                'The total amount of buffer or page cache memory, in bytes, that are free and available'
          },
          {
            'index': false,
            'name': 'swap_total',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'The total amount of swap available, in bytes'
          },
          {
            'index': false,
            'name': 'swap_free',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'The total amount of swap free, in bytes'
          }
        ],
        'description': 'Main memory information in bytes.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'memory_map',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/linux/memory_map.table',
        'platforms': ['linux'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Region name'
          },
          {
            'index': false,
            'name': 'start',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Start address of memory region'
          },
          {
            'index': false,
            'name': 'end',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'End address of memory region'
          }
        ],
        'description': 'OS memory region map.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'mounts',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/mounts.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'device',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Mounted device'
          },
          {
            'index': false,
            'name': 'device_alias',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Mounted device alias'
          },
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Mounted device path'
          },
          {
            'index': false,
            'name': 'type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Mounted device type'
          },
          {
            'index': false,
            'name': 'blocks_size',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Block size in bytes'
          },
          {
            'index': false,
            'name': 'blocks',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Mounted device used blocks'
          },
          {
            'index': false,
            'name': 'blocks_free',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Mounted device free blocks'
          },
          {
            'index': false,
            'name': 'blocks_available',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Mounted device available blocks'
          },
          {
            'index': false,
            'name': 'inodes',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Mounted device used inodes'
          },
          {
            'index': false,
            'name': 'inodes_free',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Mounted device free inodes'
          },
          {
            'index': false,
            'name': 'flags',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Mounted device flags'
          }
        ],
        'description':
            'System mounted devices and filesystems (not process specific).'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'msr',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/linux/msr.table',
        'platforms': ['linux'],
        'columns': [
          {
            'index': false,
            'name': 'processor_number',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'The processor number as reported in /proc/cpuinfo'
          },
          {
            'index': false,
            'name': 'turbo_disabled',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Whether the turbo feature is disabled.'
          },
          {
            'index': false,
            'name': 'turbo_ratio_limit',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'The turbo feature ratio limit.'
          },
          {
            'index': false,
            'name': 'platform_info',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Platform information.'
          },
          {
            'index': false,
            'name': 'perf_ctl',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Performance setting for the processor.'
          },
          {
            'index': false,
            'name': 'perf_status',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Performance status for the processor.'
          },
          {
            'index': false,
            'name': 'feature_control',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Bitfield controlling enabled features.'
          },
          {
            'index': false,
            'name': 'rapl_power_limit',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Run Time Average Power Limiting power limit.'
          },
          {
            'index': false,
            'name': 'rapl_energy_status',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Run Time Average Power Limiting energy status.'
          },
          {
            'index': false,
            'name': 'rapl_power_units',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Run Time Average Power Limiting power units.'
          }
        ],
        'description':
            'Various pieces of data stored in the model specific register per processor. NOTE: the msr kernel module must be enabled, and osquery must be run as root.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'nfs_shares',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/nfs_shares.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'share',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Filesystem path to the share'
          },
          {
            'index': false,
            'name': 'options',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Options string set on the export share'
          },
          {
            'index': false,
            'name': 'readonly',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 if the share is exported readonly else 0'
          }
        ],
        'description': 'NFS shares exported by the host.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'npm_packages',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/linux/npm_packages.table',
        'platforms': ['linux'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Package display name'
          },
          {
            'index': false,
            'name': 'version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Package supplied version'
          },
          {
            'index': false,
            'name': 'description',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Package supplied description'
          },
          {
            'index': false,
            'name': 'author',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Package author name'
          },
          {
            'index': false,
            'name': 'license',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'License for package'
          },
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Module\'s package.json path'
          },
          {
            'index': false,
            'name': 'directory',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Node module\'s directory where this package is located'
          },
          {
            'index': false,
            'name': 'pid_with_namespace',
            'required': false,
            'hidden': true,
            'type': 'integer',
            'description': 'Pids that contain a namespace'
          },
          {
            'index': false,
            'name': 'mount_namespace_id',
            'required': false,
            'hidden': true,
            'type': 'text',
            'description': 'Mount namespace id'
          }
        ],
        'description':
            'Lists all npm packages in a directory or globally installed in a system.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'ntdomains',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/ntdomains.table',
        'platforms': ['windows'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The label by which the object is known.'
          },
          {
            'index': false,
            'name': 'client_site_name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'The name of the site where the domain controller is configured.'
          },
          {
            'index': false,
            'name': 'dc_site_name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'The name of the site where the domain controller is located.'
          },
          {
            'index': false,
            'name': 'dns_forest_name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The name of the root of the DNS tree.'
          },
          {
            'index': false,
            'name': 'domain_controller_address',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'The IP Address of the discovered domain controller..'
          },
          {
            'index': false,
            'name': 'domain_controller_name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The name of the discovered domain controller.'
          },
          {
            'index': false,
            'name': 'domain_name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The name of the domain.'
          },
          {
            'index': false,
            'name': 'status',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The current status of the domain object.'
          }
        ],
        'description':
            'Display basic NT domain information of a Windows machine.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'ntfs_acl_permissions',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/ntfs_acl_permissions.table',
        'platforms': ['windows'],
        'columns': [
          {
            'index': false,
            'name': 'path',
            'required': true,
            'hidden': false,
            'type': 'text',
            'description': 'Path to the file or directory.'
          },
          {
            'index': false,
            'name': 'type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Type of access mode for the access control entry.'
          },
          {
            'index': false,
            'name': 'principal',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'User or group to which the ACE applies.'
          },
          {
            'index': false,
            'name': 'access',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Specific permissions that indicate the rights described by the ACE.'
          },
          {
            'index': false,
            'name': 'inherited_from',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The inheritance policy of the ACE.'
          }
        ],
        'description':
            'Retrieve NTFS ACL permission information for files and directories.'
      },
      {
        'cacheable': false,
        'evented': true,
        'name': 'ntfs_journal_events',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/ntfs_journal_events.table',
        'platforms': ['windows'],
        'columns': [
          {
            'index': false,
            'name': 'action',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Change action (Write, Delete, etc)'
          },
          {
            'index': false,
            'name': 'category',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The category that the event originated from'
          },
          {
            'index': false,
            'name': 'old_path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Old path (renames only)'
          },
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Path'
          },
          {
            'index': false,
            'name': 'record_timestamp',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Journal record timestamp'
          },
          {
            'index': false,
            'name': 'record_usn',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'The update sequence number that identifies the journal record'
          },
          {
            'index': false,
            'name': 'node_ref_number',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'The ordinal that associates a journal record with a filename'
          },
          {
            'index': false,
            'name': 'parent_ref_number',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'The ordinal that associates a journal record with a filename\'s parent directory'
          },
          {
            'index': false,
            'name': 'drive_letter',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The drive letter identifying the source journal'
          },
          {
            'index': false,
            'name': 'file_attributes',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'File attributes'
          },
          {
            'index': false,
            'name': 'partial',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description':
                'Set to 1 if either path or old_path only contains the file or folder name'
          },
          {
            'index': false,
            'name': 'time',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Time of file event'
          },
          {
            'index': false,
            'name': 'eid',
            'required': false,
            'hidden': true,
            'type': 'text',
            'description': 'Event ID'
          }
        ],
        'description':
            'Track time/action changes to files specified in configuration data.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'nvram',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/nvram.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Variable name'
          },
          {
            'index': false,
            'name': 'type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Data type (CFData, CFString, etc)'
          },
          {
            'index': false,
            'name': 'value',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Raw variable data'
          }
        ],
        'description': 'Apple NVRAM variable listing.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'oem_strings',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/oem_strings.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'handle',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Handle, or instance number, associated with the Type 11 structure'
          },
          {
            'index': false,
            'name': 'number',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'The string index of the structure'
          },
          {
            'index': false,
            'name': 'value',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The value of the OEM string'
          }
        ],
        'description': 'OEM defined strings retrieved from SMBIOS.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'office_mru',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/office_mru.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns': [
          {
            'index': false,
            'name': 'application',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Associated Office application'
          },
          {
            'index': false,
            'name': 'version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Office application version number'
          },
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'File path'
          },
          {
            'index': false,
            'name': 'last_opened_time',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Most recent opened time file was opened'
          },
          {
            'index': false,
            'name': 'sid',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'User SID'
          }
        ],
        'description': 'View recently opened Office documents.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'opera_extensions',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/opera_extensions.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'uid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'The local user that owns the extension'
          },
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Extension display name'
          },
          {
            'index': false,
            'name': 'identifier',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Extension identifier'
          },
          {
            'index': false,
            'name': 'version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Extension-supplied version'
          },
          {
            'index': false,
            'name': 'description',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Extension-optional description'
          },
          {
            'index': false,
            'name': 'locale',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Default locale supported by extension'
          },
          {
            'index': false,
            'name': 'update_url',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Extension-supplied update URI'
          },
          {
            'index': false,
            'name': 'author',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Optional extension author'
          },
          {
            'index': false,
            'name': 'persistent',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 If extension is persistent across all tabs else 0'
          },
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Path to extension folder'
          }
        ],
        'description': 'Opera browser extensions.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'os_version',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/os_version.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Distribution or product name'
          },
          {
            'index': false,
            'name': 'version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Pretty, suitable for presentation, OS version'
          },
          {
            'index': false,
            'name': 'major',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Major release version'
          },
          {
            'index': false,
            'name': 'minor',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Minor release version'
          },
          {
            'index': false,
            'name': 'patch',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Optional patch release'
          },
          {
            'index': false,
            'name': 'build',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Optional build-specific or variant string'
          },
          {
            'index': false,
            'name': 'platform',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'OS Platform or ID'
          },
          {
            'index': false,
            'name': 'platform_like',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Closely related platforms'
          },
          {
            'index': false,
            'name': 'codename',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'OS version codename'
          },
          {
            'index': false,
            'name': 'arch',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'OS Architecture'
          },
          {
            'index': false,
            'name': 'install_date',
            'required': false,
            'hidden': true,
            'type': 'bigint',
            'description': 'The install date of the OS.'
          },
          {
            'index': false,
            'name': 'pid_with_namespace',
            'required': false,
            'hidden': true,
            'type': 'integer',
            'description': 'Pids that contain a namespace'
          },
          {
            'index': false,
            'name': 'mount_namespace_id',
            'required': false,
            'hidden': true,
            'type': 'text',
            'description': 'Mount namespace id'
          }
        ],
        'description':
            'A single row containing the operating system name and version.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'osquery_events',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/utility/osquery_events.table',
        'platforms': ['darwin', 'linux', 'freebsd', 'windows'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Event publisher or subscriber name'
          },
          {
            'index': false,
            'name': 'publisher',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of the associated publisher'
          },
          {
            'index': false,
            'name': 'type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Either publisher or subscriber'
          },
          {
            'index': false,
            'name': 'subscriptions',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'Number of subscriptions the publisher received or subscriber used'
          },
          {
            'index': false,
            'name': 'events',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'Number of events emitted or received since osquery started'
          },
          {
            'index': false,
            'name': 'refreshes',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Publisher only: number of runloop restarts'
          },
          {
            'index': false,
            'name': 'active',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 if the publisher or subscriber is active else 0'
          }
        ],
        'description': 'Information about the event publishers and subscribers.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'osquery_extensions',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/utility/osquery_extensions.table',
        'platforms': ['darwin', 'linux', 'freebsd', 'windows'],
        'columns': [
          {
            'index': false,
            'name': 'uuid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'The transient ID assigned for communication'
          },
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Extension\'s name'
          },
          {
            'index': false,
            'name': 'version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Extension\'s version'
          },
          {
            'index': false,
            'name': 'sdk_version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'osquery SDK version used to build the extension'
          },
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Path of the extenion\'s domain socket or library path'
          },
          {
            'index': false,
            'name': 'type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'SDK extension type: extension or module'
          }
        ],
        'description': 'List of active osquery extensions.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'osquery_flags',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/utility/osquery_flags.table',
        'platforms': ['darwin', 'linux', 'freebsd', 'windows'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Flag name'
          },
          {
            'index': false,
            'name': 'type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Flag type'
          },
          {
            'index': false,
            'name': 'description',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Flag description'
          },
          {
            'index': false,
            'name': 'default_value',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Flag default value'
          },
          {
            'index': false,
            'name': 'value',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Flag value'
          },
          {
            'index': false,
            'name': 'shell_only',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Is the flag shell only?'
          }
        ],
        'description': 'Configurable flags that modify osquery\'s behavior.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'osquery_info',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/utility/osquery_info.table',
        'platforms': ['darwin', 'linux', 'freebsd', 'windows'],
        'columns': [
          {
            'index': false,
            'name': 'pid',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Process (or thread/handle) ID'
          },
          {
            'index': false,
            'name': 'uuid',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Unique ID provided by the system'
          },
          {
            'index': false,
            'name': 'instance_id',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Unique, long-lived ID per instance of osquery'
          },
          {
            'index': false,
            'name': 'version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'osquery toolkit version'
          },
          {
            'index': false,
            'name': 'config_hash',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Hash of the working configuration state'
          },
          {
            'index': false,
            'name': 'config_valid',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                '1 if the config was loaded and considered valid, else 0'
          },
          {
            'index': false,
            'name': 'extensions',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'osquery extensions status'
          },
          {
            'index': false,
            'name': 'build_platform',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'osquery toolkit build platform'
          },
          {
            'index': false,
            'name': 'build_distro',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'osquery toolkit platform distribution name (os version)'
          },
          {
            'index': false,
            'name': 'start_time',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'UNIX time in seconds when the process started'
          },
          {
            'index': false,
            'name': 'watcher',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'Process (or thread/handle) ID of optional watcher process'
          },
          {
            'index': false,
            'name': 'platform_mask',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'The osquery platform bitmask'
          }
        ],
        'description':
            'Top level information about the running version of osquery.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'osquery_packs',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/utility/osquery_packs.table',
        'platforms': ['darwin', 'linux', 'freebsd', 'windows'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The given name for this query pack'
          },
          {
            'index': false,
            'name': 'platform',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Platforms this query is supported on'
          },
          {
            'index': false,
            'name': 'version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Minimum osquery version that this query will run on'
          },
          {
            'index': false,
            'name': 'shard',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'Shard restriction limit, 1-100, 0 meaning no restriction'
          },
          {
            'index': false,
            'name': 'discovery_cache_hits',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'The number of times that the discovery query used cached values since the last time the config was reloaded'
          },
          {
            'index': false,
            'name': 'discovery_executions',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'The number of times that the discovery queries have been executed since the last time the config was reloaded'
          },
          {
            'index': false,
            'name': 'active',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'Whether this pack is active (the version, platform and discovery queries match) yes=1, no=0.'
          }
        ],
        'description':
            'Information about the current query packs that are loaded in osquery.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'osquery_registry',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/utility/osquery_registry.table',
        'platforms': ['darwin', 'linux', 'freebsd', 'windows'],
        'columns': [
          {
            'index': false,
            'name': 'registry',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of the osquery registry'
          },
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of the plugin item'
          },
          {
            'index': false,
            'name': 'owner_uuid',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Extension route UUID (0 for core)'
          },
          {
            'index': false,
            'name': 'internal',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 If the plugin is internal else 0'
          },
          {
            'index': false,
            'name': 'active',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 If this plugin is active else 0'
          }
        ],
        'description': 'List the osquery registry plugins.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'osquery_schedule',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/utility/osquery_schedule.table',
        'platforms': ['darwin', 'linux', 'freebsd', 'windows'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The given name for this query'
          },
          {
            'index': false,
            'name': 'query',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The exact query to run'
          },
          {
            'index': false,
            'name': 'interval',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'The interval in seconds to run this query, not an exact interval'
          },
          {
            'index': false,
            'name': 'executions',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Number of times the query was executed'
          },
          {
            'index': false,
            'name': 'last_executed',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description':
                'UNIX time stamp in seconds of the last completed execution'
          },
          {
            'index': false,
            'name': 'denylisted',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 if the query is denylisted else 0'
          },
          {
            'index': false,
            'name': 'output_size',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Total number of bytes generated by the query'
          },
          {
            'index': false,
            'name': 'wall_time',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Total wall time spent executing'
          },
          {
            'index': false,
            'name': 'user_time',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Total user time spent executing'
          },
          {
            'index': false,
            'name': 'system_time',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Total system time spent executing'
          },
          {
            'index': false,
            'name': 'average_memory',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Average private memory left after executing'
          }
        ],
        'description':
            'Information about the current queries that are scheduled in osquery.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'package_bom',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/package_bom.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'filepath',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Package file or directory'
          },
          {
            'index': false,
            'name': 'uid',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Expected user of file or directory'
          },
          {
            'index': false,
            'name': 'gid',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Expected group of file or directory'
          },
          {
            'index': false,
            'name': 'mode',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Expected permissions'
          },
          {
            'index': false,
            'name': 'size',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Expected file size'
          },
          {
            'index': false,
            'name': 'modified_time',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Timestamp the file was installed'
          },
          {
            'index': false,
            'name': 'path',
            'required': true,
            'hidden': false,
            'type': 'text',
            'description': 'Path of package bom'
          }
        ],
        'description': 'OS X package bill of materials (BOM) file list.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'package_install_history',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/package_install_history.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'package_id',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Label packageIdentifiers'
          },
          {
            'index': false,
            'name': 'time',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Label date as UNIX timestamp'
          },
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Package display name'
          },
          {
            'index': false,
            'name': 'version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Package display version'
          },
          {
            'index': false,
            'name': 'source',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Install source: usually the installer process name'
          },
          {
            'index': false,
            'name': 'content_type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Package content_type (optional)'
          }
        ],
        'description': 'OS X package install history.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'package_receipts',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/package_receipts.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'package_id',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Package domain identifier'
          },
          {
            'index': false,
            'name': 'package_filename',
            'required': false,
            'hidden': true,
            'type': 'text',
            'description': 'Filename of original .pkg file'
          },
          {
            'index': false,
            'name': 'version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Installed package version'
          },
          {
            'index': false,
            'name': 'location',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Optional relative install path on volume'
          },
          {
            'index': false,
            'name': 'install_time',
            'required': false,
            'hidden': false,
            'type': 'double',
            'description': 'Timestamp of install time'
          },
          {
            'index': false,
            'name': 'installer_name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of installer process'
          },
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Path of receipt plist'
          }
        ],
        'description': 'OS X package receipt details.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'patches',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/patches.table',
        'platforms': ['windows'],
        'columns': [
          {
            'index': false,
            'name': 'csname',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The name of the host the patch is installed on.'
          },
          {
            'index': false,
            'name': 'hotfix_id',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The KB ID of the patch.'
          },
          {
            'index': false,
            'name': 'caption',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Short description of the patch.'
          },
          {
            'index': false,
            'name': 'description',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Fuller description of the patch.'
          },
          {
            'index': false,
            'name': 'fix_comments',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Additional comments about the patch.'
          },
          {
            'index': false,
            'name': 'installed_by',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The system context in which the patch as installed.'
          },
          {
            'index': false,
            'name': 'install_date',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Indicates when the patch was installed. Lack of a value does not indicate that the patch was not installed.'
          },
          {
            'index': false,
            'name': 'installed_on',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The date when the patch was installed.'
          }
        ],
        'description':
            'Lists all the patches applied. Note: This does not include patches applied via MSI or downloaded from Windows Update (e.g. Service Packs).'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'pci_devices',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/pci_devices.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'pci_slot',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'PCI Device used slot'
          },
          {
            'index': false,
            'name': 'pci_class',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'PCI Device class'
          },
          {
            'index': false,
            'name': 'driver',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'PCI Device used driver'
          },
          {
            'index': false,
            'name': 'vendor',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'PCI Device vendor'
          },
          {
            'index': false,
            'name': 'vendor_id',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Hex encoded PCI Device vendor identifier'
          },
          {
            'index': false,
            'name': 'model',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'PCI Device model'
          },
          {
            'index': false,
            'name': 'model_id',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Hex encoded PCI Device model identifier'
          },
          {
            'index': false,
            'name': 'pci_class_id',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'PCI Device class ID in hex format'
          },
          {
            'index': false,
            'name': 'pci_subclass_id',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'PCI Device  subclass in hex format'
          },
          {
            'index': false,
            'name': 'pci_subclass',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'PCI Device subclass'
          },
          {
            'index': false,
            'name': 'subsystem_vendor_id',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Vendor ID of PCI device subsystem'
          },
          {
            'index': false,
            'name': 'subsystem_vendor',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Vendor of PCI device subsystem'
          },
          {
            'index': false,
            'name': 'subsystem_model_id',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Model ID of PCI device subsystem'
          },
          {
            'index': false,
            'name': 'subsystem_model',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Device description of PCI device subsystem'
          }
        ],
        'description': 'PCI devices active on the host system.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'physical_disk_performance',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/physical_disk_performance.table',
        'platforms': ['windows'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of the physical disk'
          },
          {
            'index': false,
            'name': 'avg_disk_bytes_per_read',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description':
                'Average number of bytes transferred from the disk during read operations'
          },
          {
            'index': false,
            'name': 'avg_disk_bytes_per_write',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description':
                'Average number of bytes transferred to the disk during write operations'
          },
          {
            'index': false,
            'name': 'avg_disk_read_queue_length',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description':
                'Average number of read requests that were queued for the selected disk during the sample interval'
          },
          {
            'index': false,
            'name': 'avg_disk_write_queue_length',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description':
                'Average number of write requests that were queued for the selected disk during the sample interval'
          },
          {
            'index': false,
            'name': 'avg_disk_sec_per_read',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'Average time, in seconds, of a read operation of data from the disk'
          },
          {
            'index': false,
            'name': 'avg_disk_sec_per_write',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'Average time, in seconds, of a write operation of data to the disk'
          },
          {
            'index': false,
            'name': 'current_disk_queue_length',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'Number of requests outstanding on the disk at the time the performance data is collected'
          },
          {
            'index': false,
            'name': 'percent_disk_read_time',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description':
                'Percentage of elapsed time that the selected disk drive is busy servicing read requests'
          },
          {
            'index': false,
            'name': 'percent_disk_write_time',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description':
                'Percentage of elapsed time that the selected disk drive is busy servicing write requests'
          },
          {
            'index': false,
            'name': 'percent_disk_time',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description':
                'Percentage of elapsed time that the selected disk drive is busy servicing read or write requests'
          },
          {
            'index': false,
            'name': 'percent_idle_time',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description':
                'Percentage of time during the sample interval that the disk was idle'
          }
        ],
        'description':
            'Provides provides raw data from performance counters that monitor hard or fixed disk drives on the system.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'pipes',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/pipes.table',
        'platforms': ['windows'],
        'columns': [
          {
            'index': false,
            'name': 'pid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Process ID of the process to which the pipe belongs'
          },
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of the pipe'
          },
          {
            'index': false,
            'name': 'instances',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Number of instances of the named pipe'
          },
          {
            'index': false,
            'name': 'max_instances',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'The maximum number of instances creatable for this pipe'
          },
          {
            'index': false,
            'name': 'flags',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'The flags indicating whether this pipe connection is a server or client end, and if the pipe for sending messages or bytes'
          }
        ],
        'description': 'Named and Anonymous pipes.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'pkg_packages',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/freebsd/pkg_packages.table',
        'platforms': ['freebsd'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Package name'
          },
          {
            'index': false,
            'name': 'version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Package version'
          },
          {
            'index': false,
            'name': 'flatsize',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Package size in bytes'
          },
          {
            'index': false,
            'name': 'arch',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Architecture(s) supported'
          }
        ],
        'description':
            'pkgng packages that are currently installed on the host system.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'platform_info',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/platform_info.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns': [
          {
            'index': false,
            'name': 'vendor',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Platform code vendor'
          },
          {
            'index': false,
            'name': 'version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Platform code version'
          },
          {
            'index': false,
            'name': 'date',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Self-reported platform code update date'
          },
          {
            'index': false,
            'name': 'revision',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'BIOS major and minor revision'
          },
          {
            'index': false,
            'name': 'address',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Relative address of firmware mapping'
          },
          {
            'index': false,
            'name': 'size',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Size in bytes of firmware'
          },
          {
            'index': false,
            'name': 'volume_size',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '(Optional) size of firmware volume'
          },
          {
            'index': false,
            'name': 'extra',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Platform-specific additional information'
          }
        ],
        'description': 'Information about EFI/UEFI/ROM and platform/boot.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'plist',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/plist.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'key',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Preference top-level key'
          },
          {
            'index': false,
            'name': 'subkey',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Intermediate key path, includes lists/dicts'
          },
          {
            'index': false,
            'name': 'value',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'String value of most CF types'
          },
          {
            'index': false,
            'name': 'path',
            'required': true,
            'hidden': false,
            'type': 'text',
            'description': '(required) read preferences from a plist'
          }
        ],
        'description': 'Read and parse a plist file.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'portage_keywords',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/linux/portage_keywords.table',
        'platforms': ['linux'],
        'columns': [
          {
            'index': false,
            'name': 'package',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Package name'
          },
          {
            'index': false,
            'name': 'version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'The version which are affected by the use flags, empty means all'
          },
          {
            'index': false,
            'name': 'keyword',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The keyword applied to the package'
          },
          {
            'index': false,
            'name': 'mask',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'If the package is masked'
          },
          {
            'index': false,
            'name': 'unmask',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'If the package is unmasked'
          }
        ],
        'description':
            'A summary about portage configurations like keywords, mask and unmask.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'portage_packages',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/linux/portage_packages.table',
        'platforms': ['linux'],
        'columns': [
          {
            'index': false,
            'name': 'package',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Package name'
          },
          {
            'index': false,
            'name': 'version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'The version which are affected by the use flags, empty means all'
          },
          {
            'index': false,
            'name': 'slot',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The slot used by package'
          },
          {
            'index': false,
            'name': 'build_time',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Unix time when package was built'
          },
          {
            'index': false,
            'name': 'repository',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'From which repository the ebuild was used'
          },
          {
            'index': false,
            'name': 'eapi',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'The eapi for the ebuild'
          },
          {
            'index': false,
            'name': 'size',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'The size of the package'
          },
          {
            'index': false,
            'name': 'world',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'If package is in the world file'
          }
        ],
        'description': 'List of currently installed packages.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'portage_use',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/linux/portage_use.table',
        'platforms': ['linux'],
        'columns': [
          {
            'index': false,
            'name': 'package',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Package name'
          },
          {
            'index': false,
            'name': 'version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The version of the installed package'
          },
          {
            'index': false,
            'name': 'use',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'USE flag which has been enabled for package'
          }
        ],
        'description':
            'List of enabled portage USE values for specific package.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'power_sensors',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/power_sensors.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'key',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The SMC key on OS X'
          },
          {
            'index': false,
            'name': 'category',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The sensor category: currents, voltage, wattage'
          },
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of power source'
          },
          {
            'index': false,
            'name': 'value',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Power in Watts'
          }
        ],
        'description':
            'Machine power (currents, voltages, wattages, etc) sensors.'
      },
      {
        'cacheable': false,
        'evented': true,
        'name': 'powershell_events',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/powershell_events.table',
        'platforms': ['windows'],
        'columns': [
          {
            'index': false,
            'name': 'time',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description':
                'Timestamp the event was received by the osquery event publisher'
          },
          {
            'index': false,
            'name': 'datetime',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'System time at which the Powershell script event occurred'
          },
          {
            'index': false,
            'name': 'script_block_id',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'The unique GUID of the powershell script to which this block belongs'
          },
          {
            'index': false,
            'name': 'script_block_count',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'The total number of script blocks for this script'
          },
          {
            'index': false,
            'name': 'script_text',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The text content of the Powershell script'
          },
          {
            'index': false,
            'name': 'script_name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The name of the Powershell script'
          },
          {
            'index': false,
            'name': 'script_path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The path for the Powershell script'
          },
          {
            'index': false,
            'name': 'cosine_similarity',
            'required': false,
            'hidden': false,
            'type': 'double',
            'description':
                'How similar the Powershell script is to a provided \'normal\' character frequency'
          }
        ],
        'description':
            'Powershell script blocks reconstructed to their full script content, this table requires script block logging to be enabled.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'preferences',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/preferences.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'domain',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Application ID usually in com.name.product format'
          },
          {
            'index': false,
            'name': 'key',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Preference top-level key'
          },
          {
            'index': false,
            'name': 'subkey',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Intemediate key path, includes lists/dicts'
          },
          {
            'index': false,
            'name': 'value',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'String value of most CF types'
          },
          {
            'index': false,
            'name': 'forced',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 if the value is forced/managed, else 0'
          },
          {
            'index': false,
            'name': 'username',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': '(optional) read preferences for a specific user'
          },
          {
            'index': false,
            'name': 'host',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                '\'current\' or \'any\' host, where \'current\' takes precedence'
          }
        ],
        'description': 'OS X defaults and managed preferences.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'process_envs',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/process_envs.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'pid',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Process (or thread) ID'
          },
          {
            'index': false,
            'name': 'key',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Environment variable name'
          },
          {
            'index': false,
            'name': 'value',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Environment variable value'
          }
        ],
        'description':
            'A key/value table of environment variables for each process.'
      },
      {
        'cacheable': false,
        'evented': true,
        'name': 'process_events',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/process_events.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'pid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Process (or thread) ID'
          },
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Path of executed file'
          },
          {
            'index': false,
            'name': 'mode',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'File mode permissions'
          },
          {
            'index': false,
            'name': 'cmdline',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Command line arguments (argv)'
          },
          {
            'index': false,
            'name': 'cmdline_size',
            'required': false,
            'hidden': true,
            'type': 'bigint',
            'description': 'Actual size (bytes) of command line arguments'
          },
          {
            'index': false,
            'name': 'env',
            'required': false,
            'hidden': true,
            'type': 'text',
            'description': 'Environment variables delimited by spaces'
          },
          {
            'index': false,
            'name': 'env_count',
            'required': false,
            'hidden': true,
            'type': 'bigint',
            'description': 'Number of environment variables'
          },
          {
            'index': false,
            'name': 'env_size',
            'required': false,
            'hidden': true,
            'type': 'bigint',
            'description': 'Actual size (bytes) of environment list'
          },
          {
            'index': false,
            'name': 'cwd',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The process current working directory'
          },
          {
            'index': false,
            'name': 'auid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Audit User ID at process start'
          },
          {
            'index': false,
            'name': 'uid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'User ID at process start'
          },
          {
            'index': false,
            'name': 'euid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Effective user ID at process start'
          },
          {
            'index': false,
            'name': 'gid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Group ID at process start'
          },
          {
            'index': false,
            'name': 'egid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Effective group ID at process start'
          },
          {
            'index': false,
            'name': 'owner_uid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'File owner user ID'
          },
          {
            'index': false,
            'name': 'owner_gid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'File owner group ID'
          },
          {
            'index': false,
            'name': 'atime',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'File last access in UNIX time'
          },
          {
            'index': false,
            'name': 'mtime',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'File modification in UNIX time'
          },
          {
            'index': false,
            'name': 'ctime',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'File last metadata change in UNIX time'
          },
          {
            'index': false,
            'name': 'btime',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'File creation in UNIX time'
          },
          {
            'index': false,
            'name': 'overflows',
            'required': false,
            'hidden': true,
            'type': 'text',
            'description': 'List of structures that overflowed'
          },
          {
            'index': false,
            'name': 'parent',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description':
                'Process parent\'s PID, or -1 if cannot be determined.'
          },
          {
            'index': false,
            'name': 'time',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Time of execution in UNIX time'
          },
          {
            'index': false,
            'name': 'uptime',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Time of execution in system uptime'
          },
          {
            'index': false,
            'name': 'eid',
            'required': false,
            'hidden': true,
            'type': 'text',
            'description': 'Event ID'
          },
          {
            'index': false,
            'name': 'status',
            'required': false,
            'hidden': true,
            'type': 'bigint',
            'description': 'OpenBSM Attribute: Status of the process'
          },
          {
            'index': false,
            'name': 'fsuid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Filesystem user ID at process start'
          },
          {
            'index': false,
            'name': 'suid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Saved user ID at process start'
          },
          {
            'index': false,
            'name': 'fsgid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Filesystem group ID at process start'
          },
          {
            'index': false,
            'name': 'sgid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Saved group ID at process start'
          },
          {
            'index': false,
            'name': 'syscall',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Syscall name: fork, vfork, clone, execve, execveat'
          }
        ],
        'description': 'Track time/action process executions.'
      },
      {
        'cacheable': false,
        'evented': true,
        'name': 'process_file_events',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/linux/process_file_events.table',
        'platforms': ['linux'],
        'columns': [
          {
            'index': false,
            'name': 'operation',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Operation type'
          },
          {
            'index': false,
            'name': 'pid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Process ID'
          },
          {
            'index': false,
            'name': 'ppid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Parent process ID'
          },
          {
            'index': false,
            'name': 'time',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Time of execution in UNIX time'
          },
          {
            'index': false,
            'name': 'executable',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The executable path'
          },
          {
            'index': false,
            'name': 'partial',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'True if this is a partial event (i.e.: this process existed before we started osquery)'
          },
          {
            'index': false,
            'name': 'cwd',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The current working directory of the process'
          },
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The path associated with the event'
          },
          {
            'index': false,
            'name': 'dest_path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The canonical path associated with the event'
          },
          {
            'index': false,
            'name': 'uid',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The uid of the process performing the action'
          },
          {
            'index': false,
            'name': 'gid',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The gid of the process performing the action'
          },
          {
            'index': false,
            'name': 'auid',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Audit user ID of the process using the file'
          },
          {
            'index': false,
            'name': 'euid',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Effective user ID of the process using the file'
          },
          {
            'index': false,
            'name': 'egid',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Effective group ID of the process using the file'
          },
          {
            'index': false,
            'name': 'fsuid',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Filesystem user ID of the process using the file'
          },
          {
            'index': false,
            'name': 'fsgid',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Filesystem group ID of the process using the file'
          },
          {
            'index': false,
            'name': 'suid',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Saved user ID of the process using the file'
          },
          {
            'index': false,
            'name': 'sgid',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Saved group ID of the process using the file'
          },
          {
            'index': false,
            'name': 'uptime',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Time of execution in system uptime'
          },
          {
            'index': false,
            'name': 'eid',
            'required': false,
            'hidden': true,
            'type': 'text',
            'description': 'Event ID'
          }
        ],
        'description':
            'A File Integrity Monitor implementation using the audit service.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'process_memory_map',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/process_memory_map.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns': [
          {
            'index': false,
            'name': 'pid',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Process (or thread) ID'
          },
          {
            'index': false,
            'name': 'start',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Virtual start address (hex)'
          },
          {
            'index': false,
            'name': 'end',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Virtual end address (hex)'
          },
          {
            'index': false,
            'name': 'permissions',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'r=read, w=write, x=execute, p=private (cow)'
          },
          {
            'index': false,
            'name': 'offset',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Offset into mapped path'
          },
          {
            'index': false,
            'name': 'device',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'MA:MI Major/minor device ID'
          },
          {
            'index': false,
            'name': 'inode',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Mapped path inode, 0 means uninitialized (BSS)'
          },
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Path to mapped file or mapped type'
          },
          {
            'index': false,
            'name': 'pseudo',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 If path is a pseudo path, else 0'
          }
        ],
        'description': 'Process memory mapped files and pseudo device/regions.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'process_namespaces',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/linux/process_namespaces.table',
        'platforms': ['linux'],
        'columns': [
          {
            'index': false,
            'name': 'pid',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Process (or thread) ID'
          },
          {
            'index': false,
            'name': 'cgroup_namespace',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'cgroup namespace inode'
          },
          {
            'index': false,
            'name': 'ipc_namespace',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'ipc namespace inode'
          },
          {
            'index': false,
            'name': 'mnt_namespace',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'mnt namespace inode'
          },
          {
            'index': false,
            'name': 'net_namespace',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'net namespace inode'
          },
          {
            'index': false,
            'name': 'pid_namespace',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'pid namespace inode'
          },
          {
            'index': false,
            'name': 'user_namespace',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'user namespace inode'
          },
          {
            'index': false,
            'name': 'uts_namespace',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'uts namespace inode'
          }
        ],
        'description':
            'Linux namespaces for processes running on the host system.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'process_open_files',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/process_open_files.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'pid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Process (or thread) ID'
          },
          {
            'index': false,
            'name': 'fd',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Process-specific file descriptor number'
          },
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Filesystem path of descriptor'
          }
        ],
        'description': 'File descriptors for each process.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'process_open_pipes',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/process_open_pipes.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'pid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Process ID'
          },
          {
            'index': false,
            'name': 'fd',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'File descriptor'
          },
          {
            'index': false,
            'name': 'mode',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Pipe open mode (r/w)'
          },
          {
            'index': false,
            'name': 'inode',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Pipe inode number'
          },
          {
            'index': false,
            'name': 'type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Pipe Type: named vs unnamed/anonymous'
          },
          {
            'index': false,
            'name': 'partner_pid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description':
                'Process ID of partner process sharing a particular pipe'
          },
          {
            'index': false,
            'name': 'partner_fd',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'File descriptor of shared pipe at partner\'s end'
          },
          {
            'index': false,
            'name': 'partner_mode',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Mode of shared pipe at partner\'s end'
          }
        ],
        'description': 'Pipes and partner processes for each process.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'process_open_sockets',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/process_open_sockets.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns': [
          {
            'index': false,
            'name': 'pid',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Process (or thread) ID'
          },
          {
            'index': false,
            'name': 'fd',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Socket file descriptor number'
          },
          {
            'index': false,
            'name': 'socket',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Socket handle or inode number'
          },
          {
            'index': false,
            'name': 'family',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Network protocol (IPv4, IPv6)'
          },
          {
            'index': false,
            'name': 'protocol',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Transport protocol (TCP/UDP)'
          },
          {
            'index': false,
            'name': 'local_address',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Socket local address'
          },
          {
            'index': false,
            'name': 'remote_address',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Socket remote address'
          },
          {
            'index': false,
            'name': 'local_port',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Socket local port'
          },
          {
            'index': false,
            'name': 'remote_port',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Socket remote port'
          },
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'For UNIX sockets (family=AF_UNIX), the domain path'
          },
          {
            'index': false,
            'name': 'state',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'TCP socket state'
          },
          {
            'index': false,
            'name': 'net_namespace',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The inode number of the network namespace'
          }
        ],
        'description':
            'Processes which have open network sockets on the system.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'processes',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/processes.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns': [
          {
            'index': false,
            'name': 'pid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Process (or thread) ID'
          },
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The process path or shorthand argv[0]'
          },
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Path to executed binary'
          },
          {
            'index': false,
            'name': 'cmdline',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Complete argv'
          },
          {
            'index': false,
            'name': 'state',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Process state'
          },
          {
            'index': false,
            'name': 'cwd',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Process current working directory'
          },
          {
            'index': false,
            'name': 'root',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Process virtual root directory'
          },
          {
            'index': false,
            'name': 'uid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Unsigned user ID'
          },
          {
            'index': false,
            'name': 'gid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Unsigned group ID'
          },
          {
            'index': false,
            'name': 'euid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Unsigned effective user ID'
          },
          {
            'index': false,
            'name': 'egid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Unsigned effective group ID'
          },
          {
            'index': false,
            'name': 'suid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Unsigned saved user ID'
          },
          {
            'index': false,
            'name': 'sgid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Unsigned saved group ID'
          },
          {
            'index': false,
            'name': 'on_disk',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'The process path exists yes=1, no=0, unknown=-1'
          },
          {
            'index': false,
            'name': 'wired_size',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Bytes of unpagable memory used by process'
          },
          {
            'index': false,
            'name': 'resident_size',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Bytes of private memory used by process'
          },
          {
            'index': false,
            'name': 'total_size',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Total virtual memory size'
          },
          {
            'index': false,
            'name': 'user_time',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'CPU time in milliseconds spent in user space'
          },
          {
            'index': false,
            'name': 'system_time',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'CPU time in milliseconds spent in kernel space'
          },
          {
            'index': false,
            'name': 'disk_bytes_read',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Bytes read from disk'
          },
          {
            'index': false,
            'name': 'disk_bytes_written',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Bytes written to disk'
          },
          {
            'index': false,
            'name': 'start_time',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description':
                'Process start time in seconds since Epoch, in case of error -1'
          },
          {
            'index': false,
            'name': 'parent',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Process parent\'s PID'
          },
          {
            'index': false,
            'name': 'pgroup',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Process group'
          },
          {
            'index': false,
            'name': 'threads',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Number of threads used by process'
          },
          {
            'index': false,
            'name': 'nice',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Process nice level (-20 to 20, default 0)'
          },
          {
            'index': false,
            'name': 'is_elevated_token',
            'required': false,
            'hidden': true,
            'type': 'integer',
            'description': 'Process uses elevated token yes=1, no=0'
          },
          {
            'index': false,
            'name': 'elapsed_time',
            'required': false,
            'hidden': true,
            'type': 'bigint',
            'description':
                'Elapsed time in seconds this process has been running.'
          },
          {
            'index': false,
            'name': 'handle_count',
            'required': false,
            'hidden': true,
            'type': 'bigint',
            'description':
                'Total number of handles that the process has open. This number is the sum of the handles currently opened by each thread in the process.'
          },
          {
            'index': false,
            'name': 'percent_processor_time',
            'required': false,
            'hidden': true,
            'type': 'bigint',
            'description':
                'Returns elapsed time that all of the threads of this process used the processor to execute instructions in 100 nanoseconds ticks.'
          },
          {
            'index': false,
            'name': 'upid',
            'required': false,
            'hidden': true,
            'type': 'bigint',
            'description':
                'A 64bit pid that is never reused. Returns -1 if we couldn\'t gather them from the system.'
          },
          {
            'index': false,
            'name': 'uppid',
            'required': false,
            'hidden': true,
            'type': 'bigint',
            'description':
                'The 64bit parent pid that is never reused. Returns -1 if we couldn\'t gather them from the system.'
          },
          {
            'index': false,
            'name': 'cpu_type',
            'required': false,
            'hidden': true,
            'type': 'integer',
            'description':
                'Indicates the specific processor designed for installation.'
          },
          {
            'index': false,
            'name': 'cpu_subtype',
            'required': false,
            'hidden': true,
            'type': 'integer',
            'description':
                'Indicates the specific processor on which an entry may be used.'
          }
        ],
        'description': 'All running processes on the host system.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'programs',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/programs.table',
        'platforms': ['windows'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Commonly used product name.'
          },
          {
            'index': false,
            'name': 'version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Product version information.'
          },
          {
            'index': false,
            'name': 'install_location',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The installation location directory of the product.'
          },
          {
            'index': false,
            'name': 'install_source',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The installation source of the product.'
          },
          {
            'index': false,
            'name': 'language',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The language of the product.'
          },
          {
            'index': false,
            'name': 'publisher',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of the product supplier.'
          },
          {
            'index': false,
            'name': 'uninstall_string',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Path and filename of the uninstaller.'
          },
          {
            'index': false,
            'name': 'install_date',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Date that this product was installed on the system. '
          },
          {
            'index': false,
            'name': 'identifying_number',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Product identification such as a serial number on software, or a die number on a hardware chip.'
          }
        ],
        'description':
            'Represents products as they are installed by Windows Installer. A product generally correlates to one installation package on Windows. Some fields may be blank as Windows installation details are left to the discretion of the product author.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'prometheus_metrics',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/prometheus_metrics.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'target_name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Address of prometheus target'
          },
          {
            'index': false,
            'name': 'metric_name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of collected Prometheus metric'
          },
          {
            'index': false,
            'name': 'metric_value',
            'required': false,
            'hidden': false,
            'type': 'double',
            'description': 'Value of collected Prometheus metric'
          },
          {
            'index': false,
            'name': 'timestamp_ms',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Unix timestamp of collected data in MS'
          }
        ],
        'description': 'Retrieve metrics from a Prometheus server.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'python_packages',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/python_packages.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Package display name'
          },
          {
            'index': false,
            'name': 'version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Package-supplied version'
          },
          {
            'index': false,
            'name': 'summary',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Package-supplied summary'
          },
          {
            'index': false,
            'name': 'author',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Optional package author'
          },
          {
            'index': false,
            'name': 'license',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'License under which package is launched'
          },
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Path at which this module resides'
          },
          {
            'index': false,
            'name': 'directory',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Directory where Python modules are located'
          }
        ],
        'description': 'Python packages installed in a system.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'quicklook_cache',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/quicklook_cache.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Path of file'
          },
          {
            'index': false,
            'name': 'rowid',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Quicklook file rowid key'
          },
          {
            'index': false,
            'name': 'fs_id',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Quicklook file fs_id key'
          },
          {
            'index': false,
            'name': 'volume_id',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Parsed volume ID from fs_id'
          },
          {
            'index': false,
            'name': 'inode',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Parsed file ID (inode) from fs_id'
          },
          {
            'index': false,
            'name': 'mtime',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Parsed version date field'
          },
          {
            'index': false,
            'name': 'size',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Parsed version size field'
          },
          {
            'index': false,
            'name': 'label',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Parsed version \'gen\' field'
          },
          {
            'index': false,
            'name': 'last_hit_date',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Apple date format for last thumbnail cache hit'
          },
          {
            'index': false,
            'name': 'hit_count',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Number of cache hits on thumbnail'
          },
          {
            'index': false,
            'name': 'icon_mode',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Thumbnail icon mode'
          },
          {
            'index': false,
            'name': 'cache_path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Path to cache data'
          }
        ],
        'description': 'Files and thumbnails within OS X\'s Quicklook Cache.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'registry',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/registry.table',
        'platforms': ['windows'],
        'columns': [
          {
            'index': false,
            'name': 'key',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of the key to search for'
          },
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Full path to the value'
          },
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of the registry value entry'
          },
          {
            'index': false,
            'name': 'type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Type of the registry value, or \'subkey\' if item is a subkey'
          },
          {
            'index': false,
            'name': 'data',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Data content of registry value'
          },
          {
            'index': false,
            'name': 'mtime',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'timestamp of the most recent registry write'
          }
        ],
        'description': 'All of the Windows registry hives.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'routes',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/routes.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns': [
          {
            'index': false,
            'name': 'destination',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Destination IP address'
          },
          {
            'index': false,
            'name': 'netmask',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Netmask length'
          },
          {
            'index': false,
            'name': 'gateway',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Route gateway'
          },
          {
            'index': false,
            'name': 'source',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Route source'
          },
          {
            'index': false,
            'name': 'flags',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Flags to describe route'
          },
          {
            'index': false,
            'name': 'interface',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Route local interface'
          },
          {
            'index': false,
            'name': 'mtu',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Maximum Transmission Unit for the route'
          },
          {
            'index': false,
            'name': 'metric',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Cost of route. Lowest is preferred'
          },
          {
            'index': false,
            'name': 'type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Type of route'
          },
          {
            'index': false,
            'name': 'hopcount',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Max hops expected'
          }
        ],
        'description': 'The active route table for the host system.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'rpm_package_files',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/linux/rpm_package_files.table',
        'platforms': ['linux'],
        'columns': [
          {
            'index': false,
            'name': 'package',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'RPM package name'
          },
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'File path within the package'
          },
          {
            'index': false,
            'name': 'username',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'File default username from info DB'
          },
          {
            'index': false,
            'name': 'groupname',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'File default groupname from info DB'
          },
          {
            'index': false,
            'name': 'mode',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'File permissions mode from info DB'
          },
          {
            'index': false,
            'name': 'size',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Expected file size in bytes from RPM info DB'
          },
          {
            'index': false,
            'name': 'sha256',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'SHA256 file digest from RPM info DB'
          }
        ],
        'description':
            'RPM packages that are currently installed on the host system.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'rpm_packages',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/linux/rpm_packages.table',
        'platforms': ['linux'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'RPM package name'
          },
          {
            'index': false,
            'name': 'version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Package version'
          },
          {
            'index': false,
            'name': 'release',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Package release'
          },
          {
            'index': false,
            'name': 'source',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Source RPM package name (optional)'
          },
          {
            'index': false,
            'name': 'size',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Package size in bytes'
          },
          {
            'index': false,
            'name': 'sha1',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'SHA1 hash of the package contents'
          },
          {
            'index': false,
            'name': 'arch',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Architecture(s) supported'
          },
          {
            'index': false,
            'name': 'epoch',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Package epoch value'
          },
          {
            'index': false,
            'name': 'install_time',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'When the package was installed'
          },
          {
            'index': false,
            'name': 'vendor',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Package vendor'
          },
          {
            'index': false,
            'name': 'package_group',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Package group'
          },
          {
            'index': false,
            'name': 'pid_with_namespace',
            'required': false,
            'hidden': true,
            'type': 'integer',
            'description': 'Pids that contain a namespace'
          },
          {
            'index': false,
            'name': 'mount_namespace_id',
            'required': false,
            'hidden': true,
            'type': 'text',
            'description': 'Mount namespace id'
          }
        ],
        'description':
            'RPM packages that are currently installed on the host system.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'running_apps',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/running_apps.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'pid',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'The pid of the application'
          },
          {
            'index': false,
            'name': 'bundle_identifier',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The bundle identifier of the application'
          },
          {
            'index': false,
            'name': 'is_active',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 if the application is in focus, 0 otherwise'
          }
        ],
        'description':
            'macOS applications currently running on the host system.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'safari_extensions',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/safari_extensions.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'uid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'The local user that owns the extension'
          },
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Extension display name'
          },
          {
            'index': false,
            'name': 'identifier',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Extension identifier'
          },
          {
            'index': false,
            'name': 'version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Extension long version'
          },
          {
            'index': false,
            'name': 'sdk',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Bundle SDK used to compile extension'
          },
          {
            'index': false,
            'name': 'update_url',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Extension-supplied update URI'
          },
          {
            'index': false,
            'name': 'author',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Optional extension author'
          },
          {
            'index': false,
            'name': 'developer_id',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Optional developer identifier'
          },
          {
            'index': false,
            'name': 'description',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Optional extension description text'
          },
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Path to extension XAR bundle'
          }
        ],
        'description': 'Safari browser extension details for all users.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'sandboxes',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/sandboxes.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'label',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'UTI-format bundle or label ID'
          },
          {
            'index': false,
            'name': 'user',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Sandbox owner'
          },
          {
            'index': false,
            'name': 'enabled',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Application sandboxings enabled on container'
          },
          {
            'index': false,
            'name': 'build_id',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Sandbox-specific identifier'
          },
          {
            'index': false,
            'name': 'bundle_path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Application bundle used by the sandbox'
          },
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Path to sandbox container directory'
          }
        ],
        'description': 'OS X application sandboxes container details.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'scheduled_tasks',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/scheduled_tasks.table',
        'platforms': ['windows'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of the scheduled task'
          },
          {
            'index': false,
            'name': 'action',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Actions executed by the scheduled task'
          },
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Path to the executable to be run'
          },
          {
            'index': false,
            'name': 'enabled',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Whether or not the scheduled task is enabled'
          },
          {
            'index': false,
            'name': 'state',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'State of the scheduled task'
          },
          {
            'index': false,
            'name': 'hidden',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Whether or not the task is visible in the UI'
          },
          {
            'index': false,
            'name': 'last_run_time',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Timestamp the task last ran'
          },
          {
            'index': false,
            'name': 'next_run_time',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Timestamp the task is scheduled to run next'
          },
          {
            'index': false,
            'name': 'last_run_message',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Exit status message of the last task run'
          },
          {
            'index': false,
            'name': 'last_run_code',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Exit status code of the last task run'
          }
        ],
        'description': 'Lists all of the tasks in the Windows task scheduler.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'screenlock',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/screenlock.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'enabled',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                '1 If a password is required after sleep or the screensaver begins; else 0'
          },
          {
            'index': false,
            'name': 'grace_period',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'The amount of time in seconds the screen must be asleep or the screensaver on before a password is required on-wake. 0 = immediately; -1 = no password is required on-wake'
          }
        ],
        'description':
            'macOS screenlock status for the current logged in user context.'
      },
      {
        'cacheable': false,
        'evented': true,
        'name': 'selinux_events',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/linux/selinux_events.table',
        'platforms': ['linux'],
        'columns': [
          {
            'index': false,
            'name': 'type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Event type'
          },
          {
            'index': false,
            'name': 'message',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Message'
          },
          {
            'index': false,
            'name': 'time',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Time of execution in UNIX time'
          },
          {
            'index': false,
            'name': 'uptime',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Time of execution in system uptime'
          },
          {
            'index': false,
            'name': 'eid',
            'required': false,
            'hidden': true,
            'type': 'text',
            'description': 'Event ID'
          }
        ],
        'description': 'Track SELinux events.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'selinux_settings',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/linux/selinux_settings.table',
        'platforms': ['linux'],
        'columns': [
          {
            'index': false,
            'name': 'scope',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Where the key is located inside the SELinuxFS mount point.'
          },
          {
            'index': false,
            'name': 'key',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Key or class name.'
          },
          {
            'index': false,
            'name': 'value',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Active value.'
          }
        ],
        'description': 'Track active SELinux settings.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'services',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/services.table',
        'platforms': ['windows'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Service name'
          },
          {
            'index': false,
            'name': 'service_type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Service Type: OWN_PROCESS, SHARE_PROCESS and maybe Interactive (can interact with the desktop)'
          },
          {
            'index': false,
            'name': 'display_name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Service Display name'
          },
          {
            'index': false,
            'name': 'status',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Service Current status: STOPPED, START_PENDING, STOP_PENDING, RUNNING, CONTINUE_PENDING, PAUSE_PENDING, PAUSED'
          },
          {
            'index': false,
            'name': 'pid',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'the Process ID of the service'
          },
          {
            'index': false,
            'name': 'start_type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Service start type: BOOT_START, SYSTEM_START, AUTO_START, DEMAND_START, DISABLED'
          },
          {
            'index': false,
            'name': 'win32_exit_code',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'The error code that the service uses to report an error that occurs when it is starting or stopping'
          },
          {
            'index': false,
            'name': 'service_exit_code',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'The service-specific error code that the service returns when an error occurs while the service is starting or stopping'
          },
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Path to Service Executable'
          },
          {
            'index': false,
            'name': 'module_path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Path to ServiceDll'
          },
          {
            'index': false,
            'name': 'description',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Service Description'
          },
          {
            'index': false,
            'name': 'user_account',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'The name of the account that the service process will be logged on as when it runs. This name can be of the form Domain\\UserName. If the account belongs to the built-in domain, the name can be of the form .\\UserName.'
          }
        ],
        'description':
            'Lists all installed Windows services and their relevant data.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'shadow',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/linux/shadow.table',
        'platforms': ['linux'],
        'columns': [
          {
            'index': false,
            'name': 'password_status',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Password status'
          },
          {
            'index': false,
            'name': 'hash_alg',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Password hashing algorithm'
          },
          {
            'index': false,
            'name': 'last_change',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description':
                'Date of last password change (starting from UNIX epoch date)'
          },
          {
            'index': false,
            'name': 'min',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Minimal number of days between password changes'
          },
          {
            'index': false,
            'name': 'max',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Maximum number of days between password changes'
          },
          {
            'index': false,
            'name': 'warning',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description':
                'Number of days before password expires to warn user about it'
          },
          {
            'index': false,
            'name': 'inactive',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description':
                'Number of days after password expires until account is blocked'
          },
          {
            'index': false,
            'name': 'expire',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description':
                'Number of days since UNIX epoch date until account is disabled'
          },
          {
            'index': false,
            'name': 'flag',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Reserved'
          },
          {
            'index': false,
            'name': 'username',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Username'
          }
        ],
        'description':
            'Local system users encrypted passwords and related information. Please note, that you usually need superuser rights to access `/etc/shadow`.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'shared_folders',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/shared_folders.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'The shared name of the folder as it appears to other users'
          },
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Absolute path of shared folder on the local system'
          }
        ],
        'description': 'Folders available to others via SMB or AFP.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'shared_memory',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/linux/shared_memory.table',
        'platforms': ['linux'],
        'columns': [
          {
            'index': false,
            'name': 'shmid',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Shared memory segment ID'
          },
          {
            'index': false,
            'name': 'owner_uid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'User ID of owning process'
          },
          {
            'index': false,
            'name': 'creator_uid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'User ID of creator process'
          },
          {
            'index': false,
            'name': 'pid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Process ID to last use the segment'
          },
          {
            'index': false,
            'name': 'creator_pid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Process ID that created the segment'
          },
          {
            'index': false,
            'name': 'atime',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Attached time'
          },
          {
            'index': false,
            'name': 'dtime',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Detached time'
          },
          {
            'index': false,
            'name': 'ctime',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Changed time'
          },
          {
            'index': false,
            'name': 'permissions',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Memory segment permissions'
          },
          {
            'index': false,
            'name': 'size',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Size in bytes'
          },
          {
            'index': false,
            'name': 'attached',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Number of attached processes'
          },
          {
            'index': false,
            'name': 'status',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Destination/attach status'
          },
          {
            'index': false,
            'name': 'locked',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 if segment is locked else 0'
          }
        ],
        'description': 'OS shared memory regions.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'shared_resources',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/shared_resources.table',
        'platforms': ['windows'],
        'columns': [
          {
            'index': false,
            'name': 'description',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'A textual description of the object'
          },
          {
            'index': false,
            'name': 'install_date',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Indicates when the object was installed. Lack of a value does not indicate that the object is not installed.'
          },
          {
            'index': false,
            'name': 'status',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'String that indicates the current status of the object.'
          },
          {
            'index': false,
            'name': 'allow_maximum',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'Number of concurrent users for this resource has been limited. If True, the value in the MaximumAllowed property is ignored.'
          },
          {
            'index': false,
            'name': 'maximum_allowed',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'Limit on the maximum number of users allowed to use this resource concurrently. The value is only valid if the AllowMaximum property is set to FALSE.'
          },
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Alias given to a path set up as a share on a computer system running Windows.'
          },
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Local path of the Windows share.'
          },
          {
            'index': false,
            'name': 'type',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'Type of resource being shared. Types include: disk drives, print queues, interprocess communications (IPC), and general devices.'
          }
        ],
        'description':
            'Displays shared resources on a computer system running Windows. This may be a disk drive, printer, interprocess communication, or other shareable device.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'sharing_preferences',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/sharing_preferences.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'screen_sharing',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 If screen sharing is enabled else 0'
          },
          {
            'index': false,
            'name': 'file_sharing',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 If file sharing is enabled else 0'
          },
          {
            'index': false,
            'name': 'printer_sharing',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 If printer sharing is enabled else 0'
          },
          {
            'index': false,
            'name': 'remote_login',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 If remote login is enabled else 0'
          },
          {
            'index': false,
            'name': 'remote_management',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 If remote management is enabled else 0'
          },
          {
            'index': false,
            'name': 'remote_apple_events',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 If remote apple events are enabled else 0'
          },
          {
            'index': false,
            'name': 'internet_sharing',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 If internet sharing is enabled else 0'
          },
          {
            'index': false,
            'name': 'bluetooth_sharing',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                '1 If bluetooth sharing is enabled for any user else 0'
          },
          {
            'index': false,
            'name': 'disc_sharing',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 If CD or DVD sharing is enabled else 0'
          },
          {
            'index': false,
            'name': 'content_caching',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 If content caching is enabled else 0'
          }
        ],
        'description': 'OS X Sharing preferences.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'shell_history',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/shell_history.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'uid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Shell history owner'
          },
          {
            'index': false,
            'name': 'time',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'Entry timestamp. It could be absent, default value is 0.'
          },
          {
            'index': false,
            'name': 'command',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Unparsed date/line/command history line'
          },
          {
            'index': false,
            'name': 'history_file',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Path to the .*_history for this user'
          }
        ],
        'description':
            'A line-delimited (command) table of per-user .*_history data.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'shimcache',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/shimcache.table',
        'platforms': ['windows'],
        'columns': [
          {
            'index': false,
            'name': 'entry',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Execution order.'
          },
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'This is the path to the executed file.'
          },
          {
            'index': false,
            'name': 'modified_time',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'File Modified time.'
          },
          {
            'index': false,
            'name': 'execution_flag',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'Boolean Execution flag, 1 for execution, 0 for no execution, -1 for missing (this flag does not exist on Windows 10 and higher).'
          }
        ],
        'description':
            'Application Compatibility Cache, contains artifacts of execution.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'signature',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/signature.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'path',
            'required': true,
            'hidden': false,
            'type': 'text',
            'description': 'Must provide a path or directory'
          },
          {
            'index': false,
            'name': 'hash_resources',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'Set to 1 to also hash resources, or 0 otherwise. Default is 1'
          },
          {
            'index': false,
            'name': 'arch',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'If applicable, the arch of the signed code'
          },
          {
            'index': false,
            'name': 'signed',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 If the file is signed else 0'
          },
          {
            'index': false,
            'name': 'identifier',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The signing identifier sealed into the signature'
          },
          {
            'index': false,
            'name': 'cdhash',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Hash of the application Code Directory'
          },
          {
            'index': false,
            'name': 'team_identifier',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'The team signing identifier sealed into the signature'
          },
          {
            'index': false,
            'name': 'authority',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Certificate Common Name'
          }
        ],
        'description':
            'File (executable, bundle, installer, disk) code signing status.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'sip_config',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/sip_config.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'config_flag',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The System Integrity Protection config flag'
          },
          {
            'index': false,
            'name': 'enabled',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 if this configuration is enabled, otherwise 0'
          },
          {
            'index': false,
            'name': 'enabled_nvram',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 if this configuration is enabled, otherwise 0'
          }
        ],
        'description': 'Apple\'s System Integrity Protection (rootless) status.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'smart_drive_info',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/smart/smart_drive_info.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'device_name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of block device'
          },
          {
            'index': false,
            'name': 'disk_id',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'Physical slot number of device, only exists when hardware storage controller exists'
          },
          {
            'index': false,
            'name': 'driver_type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'The explicit device type used to retrieve the SMART information'
          },
          {
            'index': false,
            'name': 'model_family',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Drive model family'
          },
          {
            'index': false,
            'name': 'device_model',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Device Model'
          },
          {
            'index': false,
            'name': 'serial_number',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Device serial number'
          },
          {
            'index': false,
            'name': 'lu_wwn_device_id',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Device Identifier'
          },
          {
            'index': false,
            'name': 'additional_product_id',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'An additional drive identifier if any'
          },
          {
            'index': false,
            'name': 'firmware_version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Drive firmware version'
          },
          {
            'index': false,
            'name': 'user_capacity',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Bytes of drive capacity'
          },
          {
            'index': false,
            'name': 'sector_sizes',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Bytes of drive sector sizes'
          },
          {
            'index': false,
            'name': 'rotation_rate',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Drive RPM'
          },
          {
            'index': false,
            'name': 'form_factor',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Form factor if reported'
          },
          {
            'index': false,
            'name': 'in_smartctl_db',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Boolean value for if drive is recognized'
          },
          {
            'index': false,
            'name': 'ata_version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'ATA version of drive'
          },
          {
            'index': false,
            'name': 'transport_type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Drive transport type'
          },
          {
            'index': false,
            'name': 'sata_version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'SATA version, if any'
          },
          {
            'index': false,
            'name': 'read_device_identity_failure',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Error string for device id read, if any'
          },
          {
            'index': false,
            'name': 'smart_supported',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'SMART support status'
          },
          {
            'index': false,
            'name': 'smart_enabled',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'SMART enabled status'
          },
          {
            'index': false,
            'name': 'packet_device_type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Packet device type'
          },
          {
            'index': false,
            'name': 'power_mode',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Device power mode'
          },
          {
            'index': false,
            'name': 'warnings',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Warning messages from SMART controller'
          }
        ],
        'description':
            'Drive information read by SMART controller utilizing autodetect.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'smbios_tables',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/smbios_tables.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'number',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Table entry number'
          },
          {
            'index': false,
            'name': 'type',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Table entry type'
          },
          {
            'index': false,
            'name': 'description',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Table entry description'
          },
          {
            'index': false,
            'name': 'handle',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Table entry handle'
          },
          {
            'index': false,
            'name': 'header_size',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Header size in bytes'
          },
          {
            'index': false,
            'name': 'size',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Table entry size in bytes'
          },
          {
            'index': false,
            'name': 'md5',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'MD5 hash of table entry'
          }
        ],
        'description': 'BIOS (DMI) structure common details and content.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'smc_keys',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/smc_keys.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'key',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': '4-character key'
          },
          {
            'index': false,
            'name': 'type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'SMC-reported type literal type'
          },
          {
            'index': false,
            'name': 'size',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Reported size of data in bytes'
          },
          {
            'index': false,
            'name': 'value',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'A type-encoded representation of the key value'
          },
          {
            'index': false,
            'name': 'hidden',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 if this key is normally hidden, otherwise 0'
          }
        ],
        'description': 'Apple\'s system management controller keys.'
      },
      {
        'cacheable': false,
        'evented': true,
        'name': 'socket_events',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/socket_events.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'action',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The socket action (bind, listen, close)'
          },
          {
            'index': false,
            'name': 'pid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Process (or thread) ID'
          },
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Path of executed file'
          },
          {
            'index': false,
            'name': 'fd',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The file description for the process socket'
          },
          {
            'index': false,
            'name': 'auid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Audit User ID'
          },
          {
            'index': false,
            'name': 'success',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'The socket open attempt status'
          },
          {
            'index': false,
            'name': 'family',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'The Internet protocol family ID'
          },
          {
            'index': false,
            'name': 'protocol',
            'required': false,
            'hidden': true,
            'type': 'integer',
            'description': 'The network protocol ID'
          },
          {
            'index': false,
            'name': 'local_address',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Local address associated with socket'
          },
          {
            'index': false,
            'name': 'remote_address',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Remote address associated with socket'
          },
          {
            'index': false,
            'name': 'local_port',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Local network protocol port number'
          },
          {
            'index': false,
            'name': 'remote_port',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Remote network protocol port number'
          },
          {
            'index': false,
            'name': 'socket',
            'required': false,
            'hidden': true,
            'type': 'text',
            'description': 'The local path (UNIX domain socket only)'
          },
          {
            'index': false,
            'name': 'time',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Time of execution in UNIX time'
          },
          {
            'index': false,
            'name': 'uptime',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Time of execution in system uptime'
          },
          {
            'index': false,
            'name': 'eid',
            'required': false,
            'hidden': true,
            'type': 'text',
            'description': 'Event ID'
          }
        ],
        'description': 'Track network socket opens and closes.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'ssh_configs',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/ssh_configs.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns': [
          {
            'index': false,
            'name': 'uid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'The local owner of the ssh_config file'
          },
          {
            'index': false,
            'name': 'block',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The host or match block'
          },
          {
            'index': false,
            'name': 'option',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The option and value'
          },
          {
            'index': false,
            'name': 'ssh_config_file',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Path to the ssh_config file'
          }
        ],
        'description': 'A table of parsed ssh_configs.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'startup_items',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/macwin/startup_items.table',
        'platforms': ['darwin', 'windows'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of startup item'
          },
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Path of startup item'
          },
          {
            'index': false,
            'name': 'args',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Arguments provided to startup executable'
          },
          {
            'index': false,
            'name': 'type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Startup Item or Login Item'
          },
          {
            'index': false,
            'name': 'source',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Directory or plist containing startup item'
          },
          {
            'index': false,
            'name': 'status',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Startup status; either enabled or disabled'
          },
          {
            'index': false,
            'name': 'username',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The user associated with the startup item'
          }
        ],
        'description':
            'Applications and binaries set as user/login startup items.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'sudoers',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/sudoers.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'source',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Source file containing the given rule'
          },
          {
            'index': false,
            'name': 'header',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Symbol for given rule'
          },
          {
            'index': false,
            'name': 'rule_details',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Rule definition'
          }
        ],
        'description': 'Rules for running commands as other users via sudo.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'suid_bin',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/suid_bin.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Binary path'
          },
          {
            'index': false,
            'name': 'username',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Binary owner username'
          },
          {
            'index': false,
            'name': 'groupname',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Binary owner group'
          },
          {
            'index': false,
            'name': 'permissions',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Binary permissions'
          }
        ],
        'description': 'suid binaries in common locations.'
      },
      {
        'cacheable': false,
        'evented': true,
        'name': 'syslog_events',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/linux/syslog_events.table',
        'platforms': ['linux'],
        'columns': [
          {
            'index': false,
            'name': 'time',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Current unix epoch time'
          },
          {
            'index': false,
            'name': 'datetime',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Time known to syslog'
          },
          {
            'index': false,
            'name': 'host',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Hostname configured for syslog'
          },
          {
            'index': false,
            'name': 'severity',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Syslog severity'
          },
          {
            'index': false,
            'name': 'facility',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Syslog facility'
          },
          {
            'index': false,
            'name': 'tag',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The syslog tag'
          },
          {
            'index': false,
            'name': 'message',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The syslog message'
          },
          {
            'index': false,
            'name': 'eid',
            'required': false,
            'hidden': true,
            'type': 'text',
            'description': 'Event ID'
          }
        ],
        'description': ''
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'system_controls',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/system_controls.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Full sysctl MIB name'
          },
          {
            'index': false,
            'name': 'oid',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Control MIB'
          },
          {
            'index': false,
            'name': 'subsystem',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Subsystem ID, control type'
          },
          {
            'index': false,
            'name': 'current_value',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Value of setting'
          },
          {
            'index': false,
            'name': 'config_value',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The MIB value set in /etc/sysctl.conf'
          },
          {
            'index': false,
            'name': 'type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Data type'
          },
          {
            'index': false,
            'name': 'field_name',
            'required': false,
            'hidden': true,
            'type': 'text',
            'description': 'Specific attribute of opaque type'
          }
        ],
        'description': 'sysctl names, values, and settings information.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'system_info',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/system_info.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns': [
          {
            'index': false,
            'name': 'hostname',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Network hostname including domain'
          },
          {
            'index': false,
            'name': 'uuid',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Unique ID provided by the system'
          },
          {
            'index': false,
            'name': 'cpu_type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'CPU type'
          },
          {
            'index': false,
            'name': 'cpu_subtype',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'CPU subtype'
          },
          {
            'index': false,
            'name': 'cpu_brand',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'CPU brand string, contains vendor and model'
          },
          {
            'index': false,
            'name': 'cpu_physical_cores',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Number of physical CPU cores in to the system'
          },
          {
            'index': false,
            'name': 'cpu_logical_cores',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Number of logical CPU cores available to the system'
          },
          {
            'index': false,
            'name': 'cpu_microcode',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Microcode version'
          },
          {
            'index': false,
            'name': 'physical_memory',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Total physical memory in bytes'
          },
          {
            'index': false,
            'name': 'hardware_vendor',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Hardware vendor'
          },
          {
            'index': false,
            'name': 'hardware_model',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Hardware model'
          },
          {
            'index': false,
            'name': 'hardware_version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Hardware version'
          },
          {
            'index': false,
            'name': 'hardware_serial',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Device serial number'
          },
          {
            'index': false,
            'name': 'board_vendor',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Board vendor'
          },
          {
            'index': false,
            'name': 'board_model',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Board model'
          },
          {
            'index': false,
            'name': 'board_version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Board version'
          },
          {
            'index': false,
            'name': 'board_serial',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Board serial number'
          },
          {
            'index': false,
            'name': 'computer_name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Friendly computer name (optional)'
          },
          {
            'index': false,
            'name': 'local_hostname',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Local hostname (optional)'
          }
        ],
        'description': 'System information for identification.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'temperature_sensors',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/temperature_sensors.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'key',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The SMC key on OS X'
          },
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of temperature source'
          },
          {
            'index': false,
            'name': 'celsius',
            'required': false,
            'hidden': false,
            'type': 'double',
            'description': 'Temperature in Celsius'
          },
          {
            'index': false,
            'name': 'fahrenheit',
            'required': false,
            'hidden': false,
            'type': 'double',
            'description': 'Temperature in Fahrenheit'
          }
        ],
        'description': 'Machine\'s temperature sensors.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'time',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/utility/time.table',
        'platforms': ['darwin', 'linux', 'freebsd', 'windows'],
        'columns': [
          {
            'index': false,
            'name': 'weekday',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Current weekday in the system'
          },
          {
            'index': false,
            'name': 'year',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Current year in the system'
          },
          {
            'index': false,
            'name': 'month',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Current month in the system'
          },
          {
            'index': false,
            'name': 'day',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Current day in the system'
          },
          {
            'index': false,
            'name': 'hour',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Current hour in the system'
          },
          {
            'index': false,
            'name': 'minutes',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Current minutes in the system'
          },
          {
            'index': false,
            'name': 'seconds',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Current seconds in the system'
          },
          {
            'index': false,
            'name': 'timezone',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Current timezone in the system'
          },
          {
            'index': false,
            'name': 'local_time',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Current local UNIX time in the system'
          },
          {
            'index': false,
            'name': 'local_timezone',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Current local timezone in the system'
          },
          {
            'index': false,
            'name': 'unix_time',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'Current UNIX time in the system, converted to UTC if --utc enabled'
          },
          {
            'index': false,
            'name': 'timestamp',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Current timestamp (log format) in the system'
          },
          {
            'index': false,
            'name': 'datetime',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Current date and time (ISO format) in the system'
          },
          {
            'index': false,
            'name': 'iso_8601',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Current time (ISO format) in the system'
          },
          {
            'index': false,
            'name': 'win_timestamp',
            'required': false,
            'hidden': true,
            'type': 'bigint',
            'description': 'Timestamp value in 100 nanosecond units.'
          }
        ],
        'description': 'Track current date and time in the system.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'time_machine_backups',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/time_machine_backups.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'destination_id',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Time Machine destination ID'
          },
          {
            'index': false,
            'name': 'backup_date',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Backup Date'
          }
        ],
        'description': 'Backups to drives using TimeMachine.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'time_machine_destinations',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/time_machine_destinations.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'alias',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Human readable name of drive'
          },
          {
            'index': false,
            'name': 'destination_id',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Time Machine destination ID'
          },
          {
            'index': false,
            'name': 'consistency_scan_date',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Consistency scan date'
          },
          {
            'index': false,
            'name': 'root_volume_uuid',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Root UUID of backup volume'
          },
          {
            'index': false,
            'name': 'bytes_available',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Bytes available on volume'
          },
          {
            'index': false,
            'name': 'bytes_used',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Bytes used on volume'
          },
          {
            'index': false,
            'name': 'encryption',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Last known encrypted state'
          }
        ],
        'description': 'Locations backed up to using Time Machine.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'ulimit_info',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/ulimit_info.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'System resource to be limited'
          },
          {
            'index': false,
            'name': 'soft_limit',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Current limit value'
          },
          {
            'index': false,
            'name': 'hard_limit',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Maximum limit value'
          }
        ],
        'description': 'System resource usage limits.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'uptime',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/uptime.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns': [
          {
            'index': false,
            'name': 'days',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Days of uptime'
          },
          {
            'index': false,
            'name': 'hours',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Hours of uptime'
          },
          {
            'index': false,
            'name': 'minutes',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Minutes of uptime'
          },
          {
            'index': false,
            'name': 'seconds',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Seconds of uptime'
          },
          {
            'index': false,
            'name': 'total_seconds',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Total uptime seconds'
          }
        ],
        'description': 'Track time passed since last boot.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'usb_devices',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/usb_devices.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'usb_address',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'USB Device used address'
          },
          {
            'index': false,
            'name': 'usb_port',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'USB Device used port'
          },
          {
            'index': false,
            'name': 'vendor',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'USB Device vendor string'
          },
          {
            'index': false,
            'name': 'vendor_id',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Hex encoded USB Device vendor identifier'
          },
          {
            'index': false,
            'name': 'version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'USB Device version number'
          },
          {
            'index': false,
            'name': 'model',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'USB Device model string'
          },
          {
            'index': false,
            'name': 'model_id',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Hex encoded USB Device model identifier'
          },
          {
            'index': false,
            'name': 'serial',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'USB Device serial connection'
          },
          {
            'index': false,
            'name': 'class',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'USB Device class'
          },
          {
            'index': false,
            'name': 'subclass',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'USB Device subclass'
          },
          {
            'index': false,
            'name': 'protocol',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'USB Device protocol'
          },
          {
            'index': false,
            'name': 'removable',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 If USB device is removable else 0'
          }
        ],
        'description':
            'USB devices that are actively plugged into the host system.'
      },
      {
        'cacheable': false,
        'evented': true,
        'name': 'user_events',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/user_events.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'uid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'User ID'
          },
          {
            'index': false,
            'name': 'auid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Audit User ID'
          },
          {
            'index': false,
            'name': 'pid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Process (or thread) ID'
          },
          {
            'index': false,
            'name': 'message',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Message from the event'
          },
          {
            'index': false,
            'name': 'type',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'The file description for the process socket'
          },
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Supplied path from event'
          },
          {
            'index': false,
            'name': 'address',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The Internet protocol address or family ID'
          },
          {
            'index': false,
            'name': 'terminal',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The network protocol ID'
          },
          {
            'index': false,
            'name': 'time',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Time of execution in UNIX time'
          },
          {
            'index': false,
            'name': 'uptime',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Time of execution in system uptime'
          },
          {
            'index': false,
            'name': 'eid',
            'required': false,
            'hidden': true,
            'type': 'text',
            'description': 'Event ID'
          }
        ],
        'description': 'Track user events from the audit framework.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'user_groups',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/user_groups.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns': [
          {
            'index': false,
            'name': 'uid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'User ID'
          },
          {
            'index': false,
            'name': 'gid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Group ID'
          }
        ],
        'description': 'Local system user group relationships.'
      },
      {
        'cacheable': false,
        'evented': true,
        'name': 'user_interaction_events',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/user_interaction_events.table',
        'platforms': ['darwin'],
        'columns': [{
          'index': false,
          'name': 'time',
          'required': false,
          'hidden': false,
          'type': 'bigint',
          'description': 'Time'
        }],
        'description':
            'Track user interaction events from macOS\' event tapping framework.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'user_ssh_keys',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/user_ssh_keys.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns': [
          {
            'index': false,
            'name': 'uid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'The local user that owns the key file'
          },
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Path to key file'
          },
          {
            'index': false,
            'name': 'encrypted',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 if key is encrypted, 0 otherwise'
          }
        ],
        'description':
            'Returns the private keys in the users ~/.ssh directory and whether or not they are encrypted.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'userassist',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/userassist.table',
        'platforms': ['windows'],
        'columns': [
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Application file path.'
          },
          {
            'index': false,
            'name': 'last_execution_time',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Most recent time application was executed.'
          },
          {
            'index': false,
            'name': 'count',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Number of times the application has been executed.'
          },
          {
            'index': false,
            'name': 'sid',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'User SID.'
          }
        ],
        'description':
            'UserAssist Registry Key tracks when a user executes an application from Windows Explorer.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'users',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/users.table',
        'platforms': ['darwin', 'linux', 'windows', 'freebsd'],
        'columns': [
          {
            'index': false,
            'name': 'uid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'User ID'
          },
          {
            'index': false,
            'name': 'gid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Group ID (unsigned)'
          },
          {
            'index': false,
            'name': 'uid_signed',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'User ID as int64 signed (Apple)'
          },
          {
            'index': false,
            'name': 'gid_signed',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Default group ID as int64 signed (Apple)'
          },
          {
            'index': false,
            'name': 'username',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Username'
          },
          {
            'index': false,
            'name': 'description',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Optional user description'
          },
          {
            'index': false,
            'name': 'directory',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'User\'s home directory'
          },
          {
            'index': false,
            'name': 'shell',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'User\'s configured default shell'
          },
          {
            'index': false,
            'name': 'uuid',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'User\'s UUID (Apple) or SID (Windows)'
          },
          {
            'index': false,
            'name': 'type',
            'required': false,
            'hidden': true,
            'type': 'text',
            'description':
                'Whether the account is roaming (domain), local, or a system profile'
          },
          {
            'index': false,
            'name': 'is_hidden',
            'required': false,
            'hidden': true,
            'type': 'integer',
            'description': 'IsHidden attribute set in OpenDirectory'
          }
        ],
        'description':
            'Local user accounts (including domain accounts that have logged on locally (Windows)).'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'video_info',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/video_info.table',
        'platforms': ['windows'],
        'columns': [
          {
            'index': false,
            'name': 'color_depth',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'The amount of bits per pixel to represent color.'
          },
          {
            'index': false,
            'name': 'driver',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The driver of the device.'
          },
          {
            'index': false,
            'name': 'driver_date',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'The date listed on the installed driver.'
          },
          {
            'index': false,
            'name': 'driver_version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The version of the installed driver.'
          },
          {
            'index': false,
            'name': 'manufacturer',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The manufaturer of the gpu.'
          },
          {
            'index': false,
            'name': 'model',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The model of the gpu.'
          },
          {
            'index': false,
            'name': 'series',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The series of the gpu.'
          },
          {
            'index': false,
            'name': 'video_mode',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The current resolution of the display.'
          }
        ],
        'description': 'Retrieve video card information of the machine.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'virtual_memory_info',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/virtual_memory_info.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'free',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Total number of free pages.'
          },
          {
            'index': false,
            'name': 'active',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Total number of active pages.'
          },
          {
            'index': false,
            'name': 'inactive',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Total number of inactive pages.'
          },
          {
            'index': false,
            'name': 'speculative',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Total number of speculative pages.'
          },
          {
            'index': false,
            'name': 'throttled',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Total number of throttled pages.'
          },
          {
            'index': false,
            'name': 'wired',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Total number of wired down pages.'
          },
          {
            'index': false,
            'name': 'purgeable',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Total number of purgeable pages.'
          },
          {
            'index': false,
            'name': 'faults',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Total number of calls to vm_faults.'
          },
          {
            'index': false,
            'name': 'copy',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Total number of copy-on-write pages.'
          },
          {
            'index': false,
            'name': 'zero_fill',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Total number of zero filled pages.'
          },
          {
            'index': false,
            'name': 'reactivated',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Total number of reactivated pages.'
          },
          {
            'index': false,
            'name': 'purged',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Total number of purged pages.'
          },
          {
            'index': false,
            'name': 'file_backed',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Total number of file backed pages.'
          },
          {
            'index': false,
            'name': 'anonymous',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Total number of anonymous pages.'
          },
          {
            'index': false,
            'name': 'uncompressed',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Total number of uncompressed pages.'
          },
          {
            'index': false,
            'name': 'compressor',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description':
                'The number of pages used to store compressed VM pages.'
          },
          {
            'index': false,
            'name': 'decompressed',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description':
                'The total number of pages that have been decompressed by the VM compressor.'
          },
          {
            'index': false,
            'name': 'compressed',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description':
                'The total number of pages that have been compressed by the VM compressor.'
          },
          {
            'index': false,
            'name': 'page_ins',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description':
                'The total number of requests for pages from a pager.'
          },
          {
            'index': false,
            'name': 'page_outs',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Total number of pages paged out.'
          },
          {
            'index': false,
            'name': 'swap_ins',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description':
                'The total number of compressed pages that have been swapped out to disk.'
          },
          {
            'index': false,
            'name': 'swap_outs',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description':
                'The total number of compressed pages that have been swapped back in from disk.'
          }
        ],
        'description': 'Darwin Virtual Memory statistics.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'wifi_networks',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/wifi_networks.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'ssid',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'SSID octets of the network'
          },
          {
            'index': false,
            'name': 'network_name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of the network'
          },
          {
            'index': false,
            'name': 'security_type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Type of security on this network'
          },
          {
            'index': false,
            'name': 'last_connected',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'Last time this netword was connected to as a unix_time'
          },
          {
            'index': false,
            'name': 'passpoint',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 if Passpoint is supported, 0 otherwise'
          },
          {
            'index': false,
            'name': 'possibly_hidden',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                '1 if network is possibly a hidden network, 0 otherwise'
          },
          {
            'index': false,
            'name': 'roaming',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 if roaming is supported, 0 otherwise'
          },
          {
            'index': false,
            'name': 'roaming_profile',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Describe the roaming profile, usually one of Single, Dual  or Multi'
          },
          {
            'index': false,
            'name': 'captive_portal',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 if this network has a captive portal, 0 otherwise'
          },
          {
            'index': false,
            'name': 'auto_login',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 if auto login is enabled, 0 otherwise'
          },
          {
            'index': false,
            'name': 'temporarily_disabled',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                '1 if this network is temporarily disabled, 0 otherwise'
          },
          {
            'index': false,
            'name': 'disabled',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 if this network is disabled, 0 otherwise'
          }
        ],
        'description': 'OS X known/remembered Wi-Fi networks list.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'wifi_status',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/wifi_status.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'interface',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of the interface'
          },
          {
            'index': false,
            'name': 'ssid',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'SSID octets of the network'
          },
          {
            'index': false,
            'name': 'bssid',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The current basic service set identifier'
          },
          {
            'index': false,
            'name': 'network_name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of the network'
          },
          {
            'index': false,
            'name': 'country_code',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'The country code (ISO/IEC 3166-1:1997) for the network'
          },
          {
            'index': false,
            'name': 'security_type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Type of security on this network'
          },
          {
            'index': false,
            'name': 'rssi',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'The current received signal strength indication (dbm)'
          },
          {
            'index': false,
            'name': 'noise',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'The current noise measurement (dBm)'
          },
          {
            'index': false,
            'name': 'channel',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Channel number'
          },
          {
            'index': false,
            'name': 'channel_width',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Channel width'
          },
          {
            'index': false,
            'name': 'channel_band',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Channel band'
          },
          {
            'index': false,
            'name': 'transmit_rate',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The current transmit rate'
          },
          {
            'index': false,
            'name': 'mode',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The current operating mode for the Wi-Fi interface'
          }
        ],
        'description': 'OS X current WiFi status.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'wifi_survey',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/wifi_scan.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'interface',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of the interface'
          },
          {
            'index': false,
            'name': 'ssid',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'SSID octets of the network'
          },
          {
            'index': false,
            'name': 'bssid',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The current basic service set identifier'
          },
          {
            'index': false,
            'name': 'network_name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of the network'
          },
          {
            'index': false,
            'name': 'country_code',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'The country code (ISO/IEC 3166-1:1997) for the network'
          },
          {
            'index': false,
            'name': 'rssi',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'The current received signal strength indication (dbm)'
          },
          {
            'index': false,
            'name': 'noise',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'The current noise measurement (dBm)'
          },
          {
            'index': false,
            'name': 'channel',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Channel number'
          },
          {
            'index': false,
            'name': 'channel_width',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Channel width'
          },
          {
            'index': false,
            'name': 'channel_band',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Channel band'
          }
        ],
        'description': 'Scan for nearby WiFi networks.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'winbaseobj',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/winbaseobj.table',
        'platforms': ['windows'],
        'columns': [
          {
            'index': false,
            'name': 'session_id',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Terminal Services Session Id'
          },
          {
            'index': false,
            'name': 'object_name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Object Name'
          },
          {
            'index': false,
            'name': 'object_type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Object Type'
          }
        ],
        'description':
            'Lists named Windows objects in the default object directories, across all terminal services sessions.  Example Windows object types include Mutexes, Events, Jobs and Semaphores.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'windows_crashes',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/windows_crashes.table',
        'platforms': ['windows'],
        'columns': [
          {
            'index': false,
            'name': 'datetime',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Timestamp (log format) of the crash'
          },
          {
            'index': false,
            'name': 'module',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Path of the crashed module within the process'
          },
          {
            'index': false,
            'name': 'path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Path of the executable file for the crashed process'
          },
          {
            'index': false,
            'name': 'pid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Process ID of the crashed process'
          },
          {
            'index': false,
            'name': 'tid',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Thread ID of the crashed thread'
          },
          {
            'index': false,
            'name': 'version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'File version info of the crashed process'
          },
          {
            'index': false,
            'name': 'process_uptime',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Uptime of the process in seconds'
          },
          {
            'index': false,
            'name': 'stack_trace',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Multiple stack frames from the stack trace'
          },
          {
            'index': false,
            'name': 'exception_code',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The Windows exception code'
          },
          {
            'index': false,
            'name': 'exception_message',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'The NTSTATUS error message associated with the exception code'
          },
          {
            'index': false,
            'name': 'exception_address',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Address (in hex) where the exception occurred'
          },
          {
            'index': false,
            'name': 'registers',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The values of the system registers'
          },
          {
            'index': false,
            'name': 'command_line',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Command-line string passed to the crashed process'
          },
          {
            'index': false,
            'name': 'current_directory',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Current working directory of the crashed process'
          },
          {
            'index': false,
            'name': 'username',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Username of the user who ran the crashed process'
          },
          {
            'index': false,
            'name': 'machine_name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of the machine where the crash happened'
          },
          {
            'index': false,
            'name': 'major_version',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Windows major version of the machine'
          },
          {
            'index': false,
            'name': 'minor_version',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Windows minor version of the machine'
          },
          {
            'index': false,
            'name': 'build_number',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Windows build number of the crashing machine'
          },
          {
            'index': false,
            'name': 'type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Type of crash log'
          },
          {
            'index': false,
            'name': 'crash_path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Path of the log file'
          }
        ],
        'description':
            'Extracted information from Windows crash logs (Minidumps).'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'windows_eventlog',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/windows_eventlog.table',
        'platforms': ['windows'],
        'columns': [
          {
            'index': false,
            'name': 'channel',
            'required': true,
            'hidden': false,
            'type': 'text',
            'description': 'Source or channel of the event'
          },
          {
            'index': false,
            'name': 'datetime',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'System time at which the event occurred'
          },
          {
            'index': false,
            'name': 'task',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Task value associated with the event'
          },
          {
            'index': false,
            'name': 'level',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Severity level associated with the event'
          },
          {
            'index': false,
            'name': 'provider_name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Provider name of the event'
          },
          {
            'index': false,
            'name': 'provider_guid',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Provider guid of the event'
          },
          {
            'index': false,
            'name': 'eventid',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Event ID of the event'
          },
          {
            'index': false,
            'name': 'keywords',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'A bitmask of the keywords defined in the event'
          },
          {
            'index': false,
            'name': 'data',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Data associated with the event'
          },
          {
            'index': false,
            'name': 'pid',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Process ID which emitted the event record'
          },
          {
            'index': false,
            'name': 'tid',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Thread ID which emitted the event record'
          },
          {
            'index': false,
            'name': 'time_range',
            'required': false,
            'hidden': true,
            'type': 'text',
            'description': 'System time to selectively filter the events'
          },
          {
            'index': false,
            'name': 'timestamp',
            'required': false,
            'hidden': true,
            'type': 'text',
            'description': 'Timestamp to selectively filter the events'
          },
          {
            'index': false,
            'name': 'xpath',
            'required': true,
            'hidden': true,
            'type': 'text',
            'description': 'The custom query to filter events'
          }
        ],
        'description': 'Table for querying all recorded Windows event logs.'
      },
      {
        'cacheable': false,
        'evented': true,
        'name': 'windows_events',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/windows_events.table',
        'platforms': ['windows'],
        'columns': [
          {
            'index': false,
            'name': 'time',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Timestamp the event was received'
          },
          {
            'index': false,
            'name': 'datetime',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'System time at which the event occurred'
          },
          {
            'index': false,
            'name': 'source',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Source or channel of the event'
          },
          {
            'index': false,
            'name': 'provider_name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Provider name of the event'
          },
          {
            'index': false,
            'name': 'provider_guid',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Provider guid of the event'
          },
          {
            'index': false,
            'name': 'eventid',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Event ID of the event'
          },
          {
            'index': false,
            'name': 'task',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Task value associated with the event'
          },
          {
            'index': false,
            'name': 'level',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'The severity level associated with the event'
          },
          {
            'index': false,
            'name': 'keywords',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'A bitmask of the keywords defined in the event'
          },
          {
            'index': false,
            'name': 'data',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Data associated with the event'
          },
          {
            'index': false,
            'name': 'eid',
            'required': false,
            'hidden': true,
            'type': 'text',
            'description': 'Event ID'
          }
        ],
        'description': 'Windows Event logs.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'windows_optional_features',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/windows_optional_features.table',
        'platforms': ['windows'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of the feature'
          },
          {
            'index': false,
            'name': 'caption',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Caption of feature in settings UI'
          },
          {
            'index': false,
            'name': 'state',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'Installation state value. 1 == Enabled, 2 == Disabled, 3 == Absent'
          },
          {
            'index': false,
            'name': 'statename',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Installation state name. \'Enabled\',\'Disabled\',\'Absent\''
          }
        ],
        'description':
            'Lists names and installation states of windows features. Maps to Win32_OptionalFeature WMI class.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'windows_security_center',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/windows_security_center.table',
        'platforms': ['windows'],
        'columns': [
          {
            'index': false,
            'name': 'firewall',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'The health of the monitored Firewall (see windows_security_products)'
          },
          {
            'index': false,
            'name': 'autoupdate',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The health of the Windows Autoupdate feature'
          },
          {
            'index': false,
            'name': 'antivirus',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'The health of the monitored Antivirus solution (see windows_security_products)'
          },
          {
            'index': false,
            'name': 'antispyware',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'The health of the monitored Antispyware solution (see windows_security_products)'
          },
          {
            'index': false,
            'name': 'internet_settings',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The health of the Internet Settings'
          },
          {
            'index': false,
            'name': 'windows_security_center_service',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The health of the Windows Security Center Service'
          },
          {
            'index': false,
            'name': 'user_account_control',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'The health of the User Account Control (UAC) capability in Windows'
          }
        ],
        'description':
            'The health status of Window Security features. Health values can be "Good", "Poor". "Snoozed", "Not Monitored", and "Error".'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'windows_security_products',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/windows_security_products.table',
        'platforms': ['windows'],
        'columns': [
          {
            'index': false,
            'name': 'type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Type of security product'
          },
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of product'
          },
          {
            'index': false,
            'name': 'state',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'State of protection'
          },
          {
            'index': false,
            'name': 'state_timestamp',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Timestamp for the product state'
          },
          {
            'index': false,
            'name': 'remediation_path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Remediation path'
          },
          {
            'index': false,
            'name': 'signatures_up_to_date',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': '1 if product signatures are up to date, else 0'
          }
        ],
        'description': 'Enumeration of registered Windows security products.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'wmi_bios_info',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/wmi_bios_info.table',
        'platforms': ['windows'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Name of the Bios setting'
          },
          {
            'index': false,
            'name': 'value',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Value of the Bios setting'
          }
        ],
        'description': 'Lists important information from the system bios.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'wmi_cli_event_consumers',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/wmi_cli_event_consumers.table',
        'platforms': ['windows'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Unique name of a consumer.'
          },
          {
            'index': false,
            'name': 'command_line_template',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Standard string template that specifies the process to be started. This property can be NULL, and the ExecutablePath property is used as the command line.'
          },
          {
            'index': false,
            'name': 'executable_path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Module to execute. The string can specify the full path and file name of the module to execute, or it can specify a partial name. If a partial name is specified, the current drive and current directory are assumed.'
          },
          {
            'index': false,
            'name': 'class',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The name of the class.'
          },
          {
            'index': false,
            'name': 'relative_path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Relative path to the class or instance.'
          }
        ],
        'description':
            'WMI CommandLineEventConsumer, which can be used for persistence on Windows. See https://www.blackhat.com/docs/us-15/materials/us-15-Graeber-Abusing-Windows-Management-Instrumentation-WMI-To-Build-A-Persistent%20Asynchronous-And-Fileless-Backdoor-wp.pdf for more details.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'wmi_event_filters',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/wmi_event_filters.table',
        'platforms': ['windows'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Unique identifier of an event filter.'
          },
          {
            'index': false,
            'name': 'query',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Windows Management Instrumentation Query Language (WQL) event query that specifies the set of events for consumer notification, and the specific conditions for notification.'
          },
          {
            'index': false,
            'name': 'query_language',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Query language that the query is written in.'
          },
          {
            'index': false,
            'name': 'class',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The name of the class.'
          },
          {
            'index': false,
            'name': 'relative_path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Relative path to the class or instance.'
          }
        ],
        'description': 'Lists WMI event filters.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'wmi_filter_consumer_binding',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/wmi_filter_consumer_binding.table',
        'platforms': ['windows'],
        'columns': [
          {
            'index': false,
            'name': 'consumer',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Reference to an instance of __EventConsumer that represents the object path to a logical consumer, the recipient of an event.'
          },
          {
            'index': false,
            'name': 'filter',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Reference to an instance of __EventFilter that represents the object path to an event filter which is a query that specifies the type of event to be received.'
          },
          {
            'index': false,
            'name': 'class',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The name of the class.'
          },
          {
            'index': false,
            'name': 'relative_path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Relative path to the class or instance.'
          }
        ],
        'description':
            'Lists the relationship between event consumers and filters.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'wmi_script_event_consumers',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/windows/wmi_script_event_consumers.table',
        'platforms': ['windows'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Unique identifier for the event consumer. '
          },
          {
            'index': false,
            'name': 'scripting_engine',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Name of the scripting engine to use, for example, \'VBScript\'. This property cannot be NULL.'
          },
          {
            'index': false,
            'name': 'script_file_name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Name of the file from which the script text is read, intended as an alternative to specifying the text of the script in the ScriptText property.'
          },
          {
            'index': false,
            'name': 'script_text',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description':
                'Text of the script that is expressed in a language known to the scripting engine. This property must be NULL if the ScriptFileName property is not NULL.'
          },
          {
            'index': false,
            'name': 'class',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The name of the class.'
          },
          {
            'index': false,
            'name': 'relative_path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Relative path to the class or instance.'
          }
        ],
        'description':
            'WMI ActiveScriptEventConsumer, which can be used for persistence on Windows. See https://www.blackhat.com/docs/us-15/materials/us-15-Graeber-Abusing-Windows-Management-Instrumentation-WMI-To-Build-A-Persistent%20Asynchronous-And-Fileless-Backdoor-wp.pdf for more details.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'xprotect_entries',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/xprotect_entries.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Description of XProtected malware'
          },
          {
            'index': false,
            'name': 'launch_type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Launch services content type'
          },
          {
            'index': false,
            'name': 'identity',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'XProtect identity (SHA1) of content'
          },
          {
            'index': false,
            'name': 'filename',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Use this file name to match'
          },
          {
            'index': false,
            'name': 'filetype',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Use this file type to match'
          },
          {
            'index': false,
            'name': 'optional',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description':
                'Match any of the identities/patterns for this XProtect name'
          },
          {
            'index': false,
            'name': 'uses_pattern',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Uses a match pattern instead of identity'
          }
        ],
        'description': 'Database of the machine\'s XProtect signatures.'
      },
      {
        'cacheable': true,
        'evented': false,
        'name': 'xprotect_meta',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/xprotect_meta.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'identifier',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Browser plugin or extension identifier'
          },
          {
            'index': false,
            'name': 'type',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Either plugin or extension'
          },
          {
            'index': false,
            'name': 'developer_id',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Developer identity (SHA1) of extension'
          },
          {
            'index': false,
            'name': 'min_version',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The minimum allowed plugin version.'
          }
        ],
        'description':
            'Database of the machine\'s XProtect browser-related signatures.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'xprotect_reports',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/darwin/xprotect_reports.table',
        'platforms': ['darwin'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Description of XProtected malware'
          },
          {
            'index': false,
            'name': 'user_action',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Action taken by user after prompted'
          },
          {
            'index': false,
            'name': 'time',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Quarantine alert time'
          }
        ],
        'description':
            'Database of XProtect matches (if user generated/sent an XProtect report).'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'yara',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/yara/yara.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'path',
            'required': true,
            'hidden': false,
            'type': 'text',
            'description': 'The path scanned'
          },
          {
            'index': false,
            'name': 'matches',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'List of YARA matches'
          },
          {
            'index': false,
            'name': 'count',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Number of YARA matches'
          },
          {
            'index': false,
            'name': 'sig_group',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Signature group used'
          },
          {
            'index': false,
            'name': 'sigfile',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Signature file used'
          },
          {
            'index': false,
            'name': 'sigrule',
            'required': false,
            'hidden': true,
            'type': 'text',
            'description': 'Signature strings used'
          },
          {
            'index': false,
            'name': 'strings',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Matching strings'
          },
          {
            'index': false,
            'name': 'tags',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Matching tags'
          },
          {
            'index': false,
            'name': 'sigurl',
            'required': false,
            'hidden': true,
            'type': 'text',
            'description': 'Signature url'
          }
        ],
        'description': 'Track YARA matches for files or PIDs.'
      },
      {
        'cacheable': false,
        'evented': true,
        'name': 'yara_events',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/yara/yara_events.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'target_path',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The path scanned'
          },
          {
            'index': false,
            'name': 'category',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'The category of the file'
          },
          {
            'index': false,
            'name': 'action',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Change action (UPDATE, REMOVE, etc)'
          },
          {
            'index': false,
            'name': 'transaction_id',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'ID used during bulk update'
          },
          {
            'index': false,
            'name': 'matches',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'List of YARA matches'
          },
          {
            'index': false,
            'name': 'count',
            'required': false,
            'hidden': false,
            'type': 'integer',
            'description': 'Number of YARA matches'
          },
          {
            'index': false,
            'name': 'strings',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Matching strings'
          },
          {
            'index': false,
            'name': 'tags',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Matching tags'
          },
          {
            'index': false,
            'name': 'time',
            'required': false,
            'hidden': false,
            'type': 'bigint',
            'description': 'Time of the scan'
          },
          {
            'index': false,
            'name': 'eid',
            'required': false,
            'hidden': true,
            'type': 'text',
            'description': 'Event ID'
          }
        ],
        'description':
            'Track YARA matches for files specified in configuration data.'
      },
      {
        'cacheable': false,
        'evented': false,
        'name': 'yum_sources',
        'url':
            'https://github.com/osquery/osquery/blob/master/specs/posix/yum_sources.table',
        'platforms': ['darwin', 'linux'],
        'columns': [
          {
            'index': false,
            'name': 'name',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Repository name'
          },
          {
            'index': false,
            'name': 'baseurl',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Repository base URL'
          },
          {
            'index': false,
            'name': 'enabled',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Whether the repository is used'
          },
          {
            'index': false,
            'name': 'gpgcheck',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'Whether packages are GPG checked'
          },
          {
            'index': false,
            'name': 'gpgkey',
            'required': false,
            'hidden': false,
            'type': 'text',
            'description': 'URL to GPG key'
          }
        ],
        'description': 'Current list of Yum repositories or software channels.'
      }
    ];
