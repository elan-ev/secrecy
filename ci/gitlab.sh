#!/bin/sh

set -eu

secrecy_dir="$(dirname "$(readlink -f "$0")")"

# TODO: for merge requests, it would be better to use CI_MERGE_REQUEST_SOURCE_BRANCH and
# CI_MERGE_REQUEST_TARGET_BRANCH. However, those apparently only work in special
# circumstances and are only really useful if you are using the premium feature
# "Pipelines for Merged Results", which I cannot test.

# When the "before commit" is invalid (in case of new branches or force pushes),
# use the merge base with the default branch. If the new branch is completely
# independent of the main branch, we just have to check all commits.
base="$CI_COMMIT_BEFORE_SHA"
if ! git merge-base --is-ancestor $base HEAD > /dev/null 2>&1;
then
    echo "Invalid 'before' commit -> trying to use merge base with default branch"
    # We need to fetch as the default branch might not be available yet
    git fetch
    base=$(git merge-base remotes/origin/$CI_DEFAULT_BRANCH $CI_COMMIT_SHA \
        || git rev-list --max-parents=0 $CI_COMMIT_SHA)
fi

echo "Checking for secrets in all commits from $base to $CI_COMMIT_SHA"
$secrecy_dir/secrecy.py between $base $CI_COMMIT_SHA
