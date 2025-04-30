#!/bin/bash

set -euo pipefail

MAIN_BRANCH="master"
VERSION_FILE="VERSION"

# validate git state
if [[ ! $(git branch | grep \* | cut -d ' ' -f2) = "${MAIN_BRANCH}" ]]; then
  echo "Error: Not on ${MAIN_BRANCH} branch" >&2
  exit 1
fi
git fetch
if (( $(git log HEAD..origin/${MAIN_BRANCH} --oneline | wc -l) > 0 )); then
  echo "Error: Branch is not up-to-date with remote origin" >&2
  exit 2
fi

CURRENT_VERSION=$(cat ${VERSION_FILE} | sed -e s/\+dev//)

MAJOR=$(echo $CURRENT_VERSION | cut -d . -f 1 -)
MINOR=$(echo $CURRENT_VERSION | cut -d . -f 2 -)
PATCH=$(echo $CURRENT_VERSION | cut -d . -f 3 -)

case "$@" in
major)
    MAJOR=$((MAJOR+1))
    MINOR=0
    PATCH=0
    ;;
minor)
    MINOR=$((MINOR+1))
    PATCH=0
    ;;
patch)
    PATCH=$((PATCH+1))
    ;;
*)
    echo "Syntax: release.sh TYPE
This project uses semantic versioning. Valid release types: major, minor, patch"
    exit 3
    ;;
esac
RELEASE_VERSION=${MAJOR}.${MINOR}.${PATCH}

echo "${RELEASE_VERSION}" > ${VERSION_FILE}

# remove existing venv to reduce remove any build machine/environment specific issues
pipenv --quiet --rm 2>/dev/null || true

# install into project dir (ignored by .gitignore) and any installed ignore system deps
PIPENV_VENV_IN_PROJECT=1 PIP_IGNORE_INSTALLED=1 pipenv --quiet install --dev

# run unit tests
pipenv --quiet run pytest

git commit -a -m "Release ${RELEASE_VERSION}"
git tag -a v${RELEASE_VERSION} -m "vidarr-tools v${RELEASE_VERSION} release"
echo "${RELEASE_VERSION}+dev" > ${VERSION_FILE}
git commit -a -m "prepared for next development iteration"
git push origin ${MAIN_BRANCH}
git push origin v${RELEASE_VERSION}
echo "vidarr-tools release v${RELEASE_VERSION} completed."
