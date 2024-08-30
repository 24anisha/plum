FROM ubuntu:20.04
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    # Bitcoin dependencies
    build-essential \
    libtool \
    autotools-dev \
    automake \
    pkg-config \
    bsdmainutils \
    python3 \
    libevent-dev \
    libboost-dev \
    libsqlite3-dev \
    git \
    # bullet3 dependencies
    build-essential \
    cmake \
    ninja-build \
    git \
    # fmtlib dependencies
    build-essential \
    cmake \
    ninja-build \
    git \
    # nlohmann/json dependencies
    build-essential \
    cmake \
    ninja-build \
    git \
    # chromaprint dependencies
    build-essential \
    cmake \
    gdb \
    git \
    python3 \
    # xlearn dependencies
    build-essential \
    cmake \
    gdb \
    git \
    python3 \
    # pokerstove dependencies
    build-essential \
    cmake \
    gdb \
    git \
    libboost-all-dev \
    # assimp dependencies
    build-essential \
    cmake \
    gdb \
    git \
    # backward-cpp dependencies
    build-essential \
    cmake \
    gdb \
    git \
    clang \
    # cpputest dependencies
    build-essential \
    cmake \
    gdb \
    git \
    clang \
    # google/benchmark dependencies
    build-essential \
    cmake \
    gdb \
    git \
    clang \
    # brotli dependencies
    build-essential \
    cmake \
    gdb \
    git \
    clang \
    # libsndfile dependencies
    build-essential \
    cmake \
    gdb \
    git \
    clang \
    # ring-span-lite dependencies
    build-essential \
    cmake \
    gdb \
    git \
    clang \
    && rm -rf /var/lib/apt/lists/*
COPY scripts /scripts
RUN find /scripts -type f -exec chmod +x {} \;