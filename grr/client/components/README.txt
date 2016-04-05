Client Components.
==================

What is a client component? The GRR Client componets are versioned modules which
can be loaded into the client at runtime. The component is essentially a
separate Virtual Env site-packages directory which is added to the client at
runtime.

The goals of GRR client components are:

1) To separate functionality in the client. Decoupling componentns into separate
   modules allows individual modules to be tested, upgraded and distributed
   independently.

2) To be able to update a client's running code in a persistent way during
   deployment. Without needing to re-deploy new clients through standard
   mechansims.

3) By separating complex modules from the basic client, we can keep the basic
   client functionality simple. A failure in a component only affect clients
   which are running the relevant flow - once the client restart the component
   is no longer used in the client.

How do I make a new component?
------------------------------

It is important to note that a client component is only modular from the
client's point of view. For the server, new functionality typically involves
writing new flows, artifacts, GUI components etc. The goal of client component
is not to insert new code into the running server - only to affect the
client. The server part of the new functionality is developed as normal
therefore.

Usually the new functionality involves implementing new client actions, which do
not exist on a bare client. The client will need to load the component to be
able to handle requests for these new client actions. The new client actions
would also typically have some dependencies in terms of third party libraries
the code might need.

Step 1: Create a directory for the component.

Step 2: Write the relevant client actions in that directory.

Step 3: Add a setup.py file. This file packages the grr specific code in its own
  package and also introduces the dependencies this code needs. For example
  consider the rekall_support component:

```
setup_args = dict(
    name="grr-rekall",
    version="0.1",
    description="Rekall GRR Integration module.",
    license="GPL",
    url="https://www.rekall-forensic.com/",
    author="The Rekall team",
    author_email="rekall-discuss@googlegroups.com",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
    ],
    py_modules=[
        "grr_rekall",
        "memory",
    ],
    install_requires=[
        "rekall-core >= 1.4.1",
    ],
)

if __name__ == "__main__":
  setup(**setup_args)
```

NOTE: The current tooling for manipulating components need to be able to parse
the setup.py file. Currently it is done by looking for a setup_args dict inside
the module - therefore currently the setup.py file must be written in this exact
way.

The most important fields are:

- name: This is the name of the component. We recommend prefixing it with "grr-".
- version: This is the version of the component.
- py_modules: The client will import these modules after installing the
  component. These are normally files which define the new client actions which
  must be registered.
- install_requires: This lists all the dependencies required for this
  package. (NOTE: you can use any of the usual formats supported by setuptools -
  including github commit IDs).

Step 4: Finally we build the component binary. This basically installs the
  component into a zip file, and packages it up in a protobuf.

```
$ python grr/client/client_build.py --config grr-server.yaml build_component \
  grr/client/components/rekall_support/setup.py /tmp/rekall_component.bin
Building component grr-rekall, Version 0.1
Creating Virtual Env /tmp/tmpc8ggGP
New python executable in /tmp/tmpc8ggGP/bin/python
Installing setuptools, pip...done.
running sdist
running egg_info
creating grr_rekall.egg-info
writing dependency_links to grr_rekall.egg-info/dependency_links.txt
writing requirements to grr_rekall.egg-info/requires.txt
writing grr_rekall.egg-info/PKG-INFO
....
Using /usr/lib/python2.7
Finished processing dependencies for grr-rekall==0.1
message ClientComponent {
 summary :   message ClientComponentSummary {
     build_system :   message Uname {
         libc_ver : u'glibc_2.4'
         machine : u'x86_64'
         release : u'Ubuntu'
         system : u'Linux'
         version : u'14.04'
        }
     cipher :   message SymmetricCipher {
         _algorithm : AES128CBC
         _iv : '>\x18\x1f\xe7%\x8f\xd6G\xb9\xe47\xa7c\xa1\x84\xbb'
         _key : '\x1d\xc2\xb1[\x99\xd7\xe7\t\x05\xde\xf6\x19\x0e<\xac\xbc'
        }
     modules : [
       u'grr_rekall'
       u'memory'
      ]
     name : u'grr-rekall'
     version : u'0.1'
    }
}
```

Finally the `build_component.py` tool prints the details about the
component. Note that this component is build for a single architecture (x86_64
linux). If you want to have it supported on multiple architectures you need to
repeat this step on these different architectures.

Step 5: Sign and upload the component to the data store.

Copy the binary file produced in the last step to a system with access to the
GRR data store, and then sign and upload the component.

```
$ python grr/tools/config_updater.py --config grr-server.yaml upload_component \
  /tmp/rekall_component.bin
Opened component grr-rekall from /tmp/rekall_component.bin
Storing component summary at aff4:/config/component/grr-rekall_0.1
Storing signed component at aff4:/web/static/components/9b4b177a56699091/glibc_2.4_x86_64_Ubuntu_Linux
```

Now, flows that use the component can simply tell the client to load it if
required.
