date-format
===========

node.js formatting of Date objects as strings. Probably exactly the same as some other library out there.

```sh
npm install date-format
```

usage
=====

```js
var format = require('date-format');
format.asString(); //defaults to ISO8601 format and current date.
format.asString(new Date()); //defaults to ISO8601 format
format.asString('hh:mm:ss.SSS', new Date()); //just the time
```

or

```js
var format = require('date-format');
format(); //defaults to ISO8601 format and current date.
format(new Date());
format('hh:mm:ss.SSS', new Date());
```

Format string can be anything, but the following letters will be replaced (and leading zeroes added if necessary):
* dd - `date.getDate()`
* MM - `date.getMonth() + 1`
* yy - `date.getFullYear().toString().substring(2, 4)`
* yyyy - `date.getFullYear()`
* hh - `date.getHours()`
* mm - `date.getMinutes()`
* ss - `date.getSeconds()`
* SSS - `date.getMilliseconds()`
* O - timezone offset in +hm format

That's it.
