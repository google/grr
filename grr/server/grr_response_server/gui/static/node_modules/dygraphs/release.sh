#!/bin/bash
# This script "releases" a version of dygraphs.

if [ $# -ne 1 ]; then
  echo "Usage: $0 X.Y.Z" >&2
  exit 1
fi

VERSION=$1
echo $VERSION | egrep '\d+\.\d+\.\d+' > /dev/null
if [ $? -ne 0 ]; then
  echo "Version must be of the form 1.2.3 (got '$VERSION')" >&2
  exit 1
fi

# Make sure this is being run from a release branch with the correct name.
branch=$(git rev-parse --abbrev-ref HEAD)
if [ $branch != "release-$VERSION" ]; then
  echo "Must be on a branch named 'release-$VERSION' (found '$branch')" >&2
  exit 1
fi

git status | grep 'working directory clean' > /dev/null
if [ $? -ne 0 ]; then
  echo "Must release with a clean working directory. Commit your changes." >&2
  exit 1
fi

grep "$VERSION" package.json
if [ $? -ne 0 ]; then
  echo "Version in package.json doesn't match command line argument." >&2
  exit 1
fi

grep "v$VERSION" bower.json
if [ $? -ne 0 ]; then
  echo "Version in bower.json doesn't match command line argument." >&2
  exit 1
fi

grep "$VERSION" releases.json
if [ $? -ne 0 ]; then
  echo "Version $VERSION does not appear in releases.json." >&2
  exit 1
fi

rm dygraph-combined.js  # changes to this will make the tests fail.
make lint test test-combined
if [ $? -ne 0 ]; then
  echo "Tests failed. Won't release!" >&2
  exit 1
fi
git reset --hard  # make test-combined deletes the source map

# Push a permanent copy of documentation & generated files to a versioned copy
# of the site. This is where the downloadable files are generated.
# TODO(danvk): make sure this actually generates the downloadable files!
echo "Pushing docs and generated files to dygraphs.com/$VERSION"
./push-to-web.sh dygraphs.com:dygraphs.com/$VERSION
if [ $? -ne 0 ]; then
  echo "Push to web failed" >&2
  exit 1
fi

# Everything is good.
# Switch to the "releases" branch, merge this change and tag it.
echo "Switching branches to do the release."
git checkout releases
git merge --no-ff $branch

COMMIT=$(git rev-parse HEAD)
echo "Tagging commit $COMMIT as version $VERSION"
git tag -a "v$VERSION" -m "Release of version $VERSION"
git push --tags

echo "Release was successful!"
echo "Pushing the new version to dygraphs.com..."
./push-to-web.sh dygraphs.com:dygraphs.com

echo "Success!\n"
echo "Don't forget to merge changes on this branch back into master:"
echo "git merge --no-ff $branch"

# Discourage users from working on the "releases" branch.
git checkout master
