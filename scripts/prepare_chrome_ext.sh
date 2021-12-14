set -e
set -x

TMP_DIR=/tmp/chrome_browser_ext
rm -rf "$TMP_DIR"
mkdir $TMP_DIR
cp -R browser_ext/chrome "$TMP_DIR/comfort"

CUR_DIR="$(pwd)"
cd $TMP_DIR
zip -r "$CUR_DIR/chrome.zip" comfort
