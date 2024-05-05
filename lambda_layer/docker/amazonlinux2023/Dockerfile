FROM amazonlinux:2023

RUN dnf install -y git tar gcc zlib-devel bzip2-devel readline-devel sqlite sqlite-devel openssl-devel tk-devel libffi-devel xz-devel
RUN curl https://pyenv.run | bash

ADD entrypoint.sh /
RUN chmod +x /entrypoint.sh

# download python
ENV PATH="~/.pyenv/bin:$PATH"
ARG PYTHON_VER="3.12.3"
RUN echo PYTHON_VER=${PYTHON_VER}
RUN ~/.pyenv/bin/pyenv install ${PYTHON_VER}
RUN ~/.pyenv/bin/pyenv global ${PYTHON_VER}

ENTRYPOINT ["/entrypoint.sh"]