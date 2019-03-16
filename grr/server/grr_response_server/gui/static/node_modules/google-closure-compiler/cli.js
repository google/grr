#!/usr/bin/env node
'use strict'
const spawnSync = require('child_process').spawnSync
const COMPILER_PATH = require('./index.js').compiler.COMPILER_PATH
const result = spawnSync(
  'java',
  ['-jar', COMPILER_PATH].concat(process.argv.slice(2)),
  {stdio: 'inherit'}
)
if (result.error) {
  if (result.error.code === 'ENOENT') {
    console.error('Could not find "java" in your PATH.')
  } else {
    console.error(result.error.message)
  }
  process.exit(1)
} else {
  process.exit(result.status)
}

