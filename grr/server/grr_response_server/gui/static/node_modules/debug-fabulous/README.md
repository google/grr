# debug-fabulous

## Install
`npm install --save debug-fabulous`

# Purpose

Wrapper / Extension around [visionmedia's debug](https://github.com/visionmedia/debug) to allow lazy evaluation of debugging via closure handling.

This library essentially wraps two things:

- [lazy-debug](https://github.com/apihlaja/lazy-debug) for easy namespace naming by files
- [lazy-eval](./src/lazy-eval.js) debug closure handling

## Use

For thorough usage see the [tests](./test).

## lazy-eval

```js
var debug = require('')();
// force namespace to be enabled otherwise it assumes process.env.DEBUG is setup
// debug.save('myNamespace');
// debug.enable(debug.load())
debug = debug('debug-fabulous');
debug(function(){return 'ya something to log' + someLargeHarryString;});
debug('small out');
```
