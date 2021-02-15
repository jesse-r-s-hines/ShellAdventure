# ARGS
# USERNAME The user the student will be logged in as. Defaults to "student".
# PASSWORD The password the student will have, for use in running "sudo" commands and such. Defaults to USERNAME

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
    # Install stuff to allow running python and a GUI
    apt-get install -y x11-apps python3 python-is-python3 python3-tk && \
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
        wget \
        zip \
    # Remove the cache made by apt update and other files to save space
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ARG username=student
ARG password=${username}

# Make new user and allow them to use sudo
RUN useradd -ms /bin/bash ${username} && \
    echo "${username}:${password}" | chpasswd && \
    usermod -aG sudo ${username}

# TODO move this into a seperate "test" container
RUN apt-get update && \
    apt-get install -y python3-pip && \
    python -m pip --no-cache-dir install pytest PyYAML && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

USER ${username}
WORKDIR /home/${username}

COPY shell_adventure_docker /usr/local/shell_adventure_docker/

# TODO move this into a sperate "test" container
COPY tests/docker_tests /usr/local/shell_adventure_docker/tests/

CMD ["bash"]
