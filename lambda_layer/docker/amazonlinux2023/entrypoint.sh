#!/bin/bash

#usage: entrypoint.sh <output_zip_name> <pip_install_args> ...
INSTALL=/python
OUT_ZIP=/mount/$1

# enable pyenv
eval "$(pyenv init -)"

# install python packages
mkdir ${INSTALL}
echo "--------- start to install python packages"
pip3 install --root-user-action=ignore -t ${INSTALL} "${@:2}" || exit 1

# zip
echo "--------- start to zip installed python packages"
zip -q -r ${OUT_ZIP} ${INSTALL} || exit 1
ls -l ${OUT_ZIP}
