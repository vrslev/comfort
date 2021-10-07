set -e

$executable
dir=~/Library/Services

# Install python package
python3.9 -m venv $dir/comfort/venv

# Symlink if `-s` is specified
cp -R comfort.workflow $dir || true
exec_files="main.js comfort_browser_ext.py setup.py $dir/comfort"
if [[ $1 == --link ]]; then
    ln -Ff $exec_files
else
    cp $exec_files
fi

. $dir/comfort/venv/bin/activate
pip install -e $dir/comfort

# Create config
cd $dir/comfort
python -m comfort_browser_ext || true
open $dir/comfort/config.ini