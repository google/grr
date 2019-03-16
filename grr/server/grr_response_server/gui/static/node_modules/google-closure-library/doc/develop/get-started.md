---
section: develop
---


<!-- Documentation licensed under CC BY 4.0 -->
<!-- License available at https://creativecommons.org/licenses/by/4.0/ -->

# Get Started with the Closure Library

This get started guide is designed to teach you some fundamental Closure
development concepts in the context of creating your first Closure application.
This guide also provides the steps common to a Closure development workflow.


## Download the Closure library

Execute the following command from the command line to download the Closure
Library from the Git repository:

```
git clone https://github.com/google/closure-library
```

A directory named `closure-library` is created. This directory contains the
Closure Library code.


## Create Closure JavaScript

Create a `hello.js` JavaScript file in `path/to/myapp/` with the
following contents:

```
/**
 * @fileoverview Closure getting started tutorial code example.
 */
goog.require('goog.dom');

/**
 * Appends an `h1` tag to the body with the message "Hello world!".
 * @export
 */
function sayHi() {
  var newHeader = goog.dom.createDom(goog.dom.TagName.H1, {'style': 'background-color:#EEE'},
    'Hello world!');
  goog.dom.appendChild(document.body, newHeader);
}
```

The `hello.js` JavaScript calls two Closure Library functions:
`goog.dom.createDom()` and `goog.dom.appendChild()`. These functions are defined
in the Closure Library's `closure/goog/dom/dom.js` file. The next steps
explains how the correct files are loaded to provide access these functions.

## Create an HTML file

Create a `hello.html` file in `path/to/myapp/` with the
following contents::

```
<html>
  <head>
    <script src="closure/goog/base.js"></script>
    <script src="hello.js"></script>
  </head>
  <body onload="sayHi()">
  </body>
</html>
```

The first thing this HTML file does is to load `base.js` which defines the
function `goog.require` and other core functionality. Then the HTML file loads
`hello.js` (from step 2) which calls `goog.require()`
(`goog.require('goog.dom')`) to load `dom.js` (where `goog.dom.createDom()` and
`goog.dom.appendChild()` are defined). Typically a single `goog.require()`
statement will load a JavaScript file and all of its transitive dependencies.

The Closure Library loads required files by dynamically adding a script tag to
the document for each needed Closure Library file.


## Test your app with a web server
Use a simple HTTP server, such as the [node.js](https://nodejs.org/en/) or
[python simple http server](https://docs.python.org/2/library/simplehttpserver.html)
to test your application.

For example, start a simple server in your project directory with:

```
python -m SimpleHTTPServer 8000
```

And visit localhost:8000/path/to/myapp/hello.html.

## Compile your app
Use the Closure compiler to compile your application when your app is ready for
production. The Closure Compiler (also known as JSCompiler) creates a
single-file version of the application library. This file includes all the
dependencies your application needs, but  shortens identifier names where
possible to minimize the size of the code and the time it takes to transmit
over the network. In addition, the Closure Compiler performs type checking,
removes dead code, and applies optimizations.


To compile your application:

1. Download and install the latest release of the Closure compiler from the
[Getting Started section of the compiler's Git Hub page](https://github.com/google/closure-compiler).

2. Execute the closure compiler on your JavaScript file:

    ```
    java -jar compiler.jar --js hello.js --js_output_file hello-compiled_dev.js
    ```

    **Note:** You can compile multiple JavaScript files at once using the Closure
    Compiler. For example:

    ```
    java -jar compiler.jar --js_output_file=out.js in1.js in2.js in3.js ...
    ```

3. Reference the compiled file in your HTML file without using
`base.js` to load the dependencies individually (`hello_compiled.js` includes
`hello.js` as well as all of its requirements, in compiled form):

```
<html>
  <head>
    <script src="/hello_compiled_dev.js"></script>
  </head>
  <body onload="sayHi()">
  </body>
</html>
```

Refer to [Getting Started with the Closure Compiler Application](https://developers.google.com/closure/compiler/docs/gettingstarted_app#the-hello-world-of the-closure-compiler-application)
for more information on the Closure Compiler.

