# lazy-debug

[![npm lazy-debug](https://nodei.co/npm/lazy-debug.png?compact=true)](https://www.npmjs.com/package/lazy-debug)

Node.js module which generates app & module names for [visionmedia´s debug](https://github.com/visionmedia/debug) using `__filename` and package.json.

Basic usage example:

```javascript
var debug = require('lazy-debug-legacy').get(__filename);
```

Depending on `__filename`, debug name will be something like packageName:dir:file. File extension is removed and if file name is `index`, its removed too. For futher customization, to fit better for project structure, you can provide filter function:

```javascript
var lazyDebug = require('lazy-debug-legacy');
lazyDebug.configure({filter: function (pathArray) {
  if ( pathArray[0] === 'src' ) {
    pathArray.shift();
  }
  return pathArray;
}});

// now, when called in packageRoot/src/module1/index.js
var debug = require('lazy-debug-legacy').get(__filename);
// debug name will be projectName:module1
```


## Install

`npm install --save debug lazy-debug`

## Tests

`npm test`

## License

[The MIT License](LICENSE.md)
