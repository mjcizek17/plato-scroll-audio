#!/usr/bin/env bash
# publish.sh SRC_DIR NAME — copy one job's results (mp3, json, refs, log) to the `samples` branch,
# under audition/run-<run number>/<NAME>/. Safe when several jobs publish at once (rebase + retry).
set -u
src="$1"; name="$2"
repo="https://x-access-token:${GITHUB_TOKEN}@github.com/${GITHUB_REPOSITORY}"
git config --global user.name "audition-bot"
git config --global user.email "audition-bot@users.noreply.github.com"
rm -rf /tmp/s
if ! git clone -q --depth 1 --branch samples "$repo" /tmp/s 2>/dev/null; then
  git init -q /tmp/s && git -C /tmp/s checkout -q --orphan samples && git -C /tmp/s remote add origin "$repo"
fi
d="/tmp/s/audition/run-${GITHUB_RUN_NUMBER}/${name}"; mkdir -p "$d"
cp "$src"/*.mp3 "$src"/*.json "$src"/*.txt "$d/" 2>/dev/null || true
[ -d "$src/refs" ] && cp -r "$src/refs" "$d/" || true
echo "${GITHUB_SHA}" > "/tmp/s/audition/run-${GITHUB_RUN_NUMBER}/commit.txt"
cd /tmp/s && git add -A && git commit -qm "audition run ${GITHUB_RUN_NUMBER}: ${name}" || exit 0
for i in 1 2 3 4 5 6; do
  git push -q origin HEAD:samples && exit 0
  git fetch -q --depth 1 origin samples && git rebase -q origin/samples || git rebase --abort
  sleep $((RANDOM % 10 + 3))
done
echo "publish failed" >&2; exit 1
