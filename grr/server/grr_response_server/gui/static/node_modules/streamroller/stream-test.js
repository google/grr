// const fs = require('fs');
const streamroller = require('./lib/index');

const stream = new streamroller.RollingFileStream('stream-test.log');
// const stream = fs.createWriteStream('stream-test.log');

for (let i = 0; i < 1000000; i += 1) {
  stream.write('[2017-06-15 08:16:52.760] [INFO] memory-test - Doing something.\n', 'utf-8');
  if (i % 5000 === 0) {
    console.log("Wrote ", i);
  }
}

stream.end('\n', () => { console.log("done"); });
