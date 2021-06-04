# The student will be user "student" and their password will be "student"
FROM ubuntu:20.04

# Install stuff
RUN apt-get update && \
    # Man pages are removed in minimized ubuntu. See
    # https://stackoverflow.com/questions/54152906/how-to-install-man-pages-on-an-ubuntu-docker-image
    # https://github.com/tianon/docker-brew-ubuntu-core/issues/126
    # https://github.com/tianon/docker-brew-ubuntu-core/issues/122
    # To add them, remove man pages from dpkg excludes
    sed -i '/^path-exclude=\/usr\/share\/man\/\*/d' /etc/dpkg/dpkg.cfg.d/excludes && \
    # install man pages
    apt-get install -y man-db && \
    # Replace the man script telling you that this is a minimized version with the real man executable.
    mv /usr/bin/man.REAL /usr/bin/man && \
    # Reinstall everything so that the man pages get downloaded with them now.
    # Reinstalling "libc6" throws "Could not configure libc6:amd64", so we reinstall all packages except libc6
    # See https://manpages.ubuntu.com/manpages/focal/man7/apt-patterns.7.html for apt patterns
    apt-get reinstall -y '?and(?installed, !?name(libc6))' && \
    # Now we can install new packages
    apt-get install -y \
        binutils \
        bsdmainutils \
        file \
        iputils-ping \
        less \
        mlocate \
        nano \
        sudo \
        tree \
        unzip \
        vim-tiny \
        wget \
        zip \
    && \
    # Install Python
    apt-get install -y python3 python-is-python3 python3-pip && \
    python -m pip install retry python-lorem && \
    # Remove the cache made by apt update and other files to save space
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# if TESTING is 1 install pytest.
ARG TESTING=0
RUN if [ ${TESTING} -eq 1 ]; then \
        python -m pip --no-cache-dir install pytest pytest-cov && \
        rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* ; \
    fi

# Make new user and allow them to use sudo
RUN useradd -ms /bin/bash student && \
    echo "student:student" | chpasswd && \
    usermod -aG sudo student

USER student
WORKDIR /home/student

COPY docker_files/.bashrc /home/student/.bashrc

ENV PYTHONPATH=/usr/local
ENV PROMPT_COMMAND="python3 -m shell_adventure_docker.commit_container"

COPY shell_adventure_docker /usr/local/shell_adventure_docker/
# support code is shared between container and host.
COPY shell_adventure/support.py /usr/local/shell_adventure/support.py
# There doesn't seem to be a way to conditionally copy this only when testing..
COPY tests/docker_tests /usr/local/shell_adventure_docker_tests/

CMD ["bash"]
