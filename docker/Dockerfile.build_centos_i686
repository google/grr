FROM centos_i686:7_base

LABEL maintainer="grr-dev@googlegroups.com"

# Install Python from source.
RUN cd /tmp && curl -O -L http://python.org/ftp/python/2.7.14/Python-2.7.14.tar.xz && \
  tar xf Python-2.7.14.tar.xz && \
  cd Python-2.7.14 && \
  linux32 ./configure --prefix=/usr/local --enable-unicode=ucs4 --enable-shared LDFLAGS="-Wl,-rpath /usr/local/lib" && \
  linux32 make && \
  linux32 make install

# Install pip.
RUN linux32 curl https://bootstrap.pypa.io/get-pip.py | /usr/local/bin/python

# Install virtualenv.
RUN linux32 pip install --upgrade pip virtualenv

CMD ["/bin/bash"]