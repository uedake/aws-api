#!/bin/bash

#usage: entrypoint.sh <python_version> <pip_install_args> ...
SRC=/python
DIST=/dist/layer.zip

if [ -f ${DIST} ]; then
  echo 'layer.zipが既に存在します。削除してから実行してください。'
  exit 1
fi

# download python
export PYENV_ROOT="$HOME/.pyenv"
command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"

pyenv install $1
pyenv global $1

# install python packages
mkdir SRC
pip3 install -t ${SRC} "${@:2}"

# zip
zip -q -r ${DIST} ${SRC}