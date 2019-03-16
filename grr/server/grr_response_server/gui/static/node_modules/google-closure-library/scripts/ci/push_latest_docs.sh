#!/bin/bash

# Deploy the gh-pages branch, adapted from
# https://github.com/google/dagger/blob/master/util/generate-latest-docs.sh
# See also http://stackoverflow.com/a/22977235 for ssh-based deploy.

set -e

# Only push if we've just committed to google/closure-library:master.
# Start by decrypting the deploy password, and pre-populate GitHub's
# RSA key to avoid needing to manually accept it when connecting.
if [ "$TRAVIS_REPO_SLUG" == "google/closure-library" -a \
     "$TRAVIS_PULL_REQUEST" == "false" -a \
     "$TRAVIS_BRANCH" == "master" ]; then 

  # If we're on travis, use a secure $deploy_password
  if [ -n "$deploy_password" ]; then
    touch scripts/ci/deploy
    chmod 600 scripts/ci/deploy
    openssl aes-256-cbc -k "$deploy_password" -d -a \
            -in scripts/ci/deploy.enc -out scripts/ci/deploy \
            &> /dev/null
    echo -e "Host github.com\n  IdentityFile $PWD/scripts/ci/deploy" > ~/.ssh/config
    echo "github.com ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAq2A7hRGmdnm9tUDbO9IDSwBK6Tb
          Qa+PXYPCPy6rbTrTtw7PHkccKrpp0yVhp5HdEIcKr6pLlVDBfOLX9QUsyCOV0wzfjIJNlGEYsd
          lLJizHhbn2mUjvSAHQqZETYP81eFzLQNnPHt4EVVUh7VfDESU84KezmD5QlWpXLmvU31/yMf+S
          e8xhHTvKSCZIFImWwoG6mbUoWf9nzpIoaSjB+weqqUUmpaaasXVal72J+UX2B+2RPW3RcT0eOz
          QgqlJL3RKrTJvdsjE3JEAvGq3lGHSZXy28G3skua2SmVi/w4yCE6gbODqnTWlg7+wC604ydGXA
          8VJiS5ap43JXiUFFAaQ==" | sed 's/^ *//' | tr -d '\n' > ~/.ssh/known_hosts
  fi

  # Push the commit and delete the repo.
  export GIT_WORK_TREE="$GH_PAGES"
  export GIT_DIR="$GH_PAGES/.git"
  git push -fq origin gh-pages > /dev/null
  rm -f scripts/ci/deploy
  rm -rf "$GH_PAGES"
  echo "Published gh-pages."

fi
